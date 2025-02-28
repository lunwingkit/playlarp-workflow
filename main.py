import logging
import os
import config
import web_scraping
import data_update
import data_processing
import cloudinary_upload
from logging_config import setup_logger
import asyncio
import prisma_operations
import time

def main(mode='incremental', log_level='INFO', start_step=1):
    # Set up logging
    log_file = setup_logger(log_level=log_level, log_folder=config.LOG_FOLDER)
    logging.info(f"Starting cron job in {mode} mode from step {start_step}. Log file: {log_file}")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(config.SCRIPT_LIST_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(config.DETAILED_CSV_PATH), exist_ok=True)
    os.makedirs(config.SCRIPT_COVER_FOLDER, exist_ok=True)
    os.makedirs(config.SCRIPT_IMAGE_CONTENT_FOLDER, exist_ok=True)
    os.makedirs(config.INCREMENTAL_OUTPUT_FOLDER_PATH, exist_ok=True)

    # Step 1: Fetch and update script list
    if start_step <= 1:
        script_list = web_scraping.fetch_script_list_sync()  # Should return a list directly
        inserted_count = data_update.update_script_list(script_list, mode=mode)
        logging.info(f"Step 1: Script list updated. {inserted_count} new records inserted.")
    else:
        script_list = data_update.read_csv(config.SCRIPT_LIST_PATH)
        logging.debug(f"Skipping Step 1, loaded {len(script_list)} scripts from {config.SCRIPT_LIST_PATH}")

    # Step 2: Fetch and update script details
    if start_step <= 2:
        if mode == 'incremental':
            existing_details = {row['scriptId'] for row in data_update.read_csv(config.DETAILED_CSV_PATH)}
            existing_scripts = data_update.read_csv(config.SCRIPT_LIST_PATH)
            new_script_ids = [
                s['scriptId'] for s in script_list
                if s['scriptId'] not in existing_details or s.get('databaseInserted', 'False') == 'False'
            ]
            logging.debug(f"New script IDs to fetch (new or databaseInserted=False): {len(new_script_ids)}")
        else:
            new_script_ids = [s['scriptId'] for s in script_list]
        
        new_details = web_scraping.fetch_script_details_sync(new_script_ids)  # Should return a list directly
        details_inserted_count = data_update.update_script_details(new_details, mode=mode)
        logging.info(f"Step 2: Detailed data updated. {details_inserted_count} new records inserted.")
    else:
        new_details = []  # Empty if skipping Step 2
        logging.debug("Skipping Step 2, new_details set to empty list")

    # Step 3: Download images and update details and script list flags
    if start_step <= 3:
        if mode == 'incremental':
            existing_scripts = data_update.read_csv(config.SCRIPT_LIST_PATH)
            scripts_to_redownload = [
                script for script in existing_scripts
                if script.get('coverImageDownloaded', 'True') == 'False' or script.get('imageContentDownloaded', 'True') == 'False'
            ]
            redownload_ids = [script['scriptId'] for script in scripts_to_redownload]
            logging.info(f"Scripts identified for redownload ({len(redownload_ids)}):")
            for script in scripts_to_redownload:
                logging.info(f"  scriptId: {script['scriptId']}, scriptName: {script['scriptName']}")
            
            existing_details_dict = {detail['scriptId']: detail for detail in new_details}
            scripts_to_fetch = [script_id for script_id in redownload_ids if script_id not in existing_details_dict]
            if scripts_to_fetch:
                redownload_details = web_scraping.fetch_script_details_sync(scripts_to_fetch)
                logging.info(f"Fetched details for {len(redownload_details)} scripts needing redownload")
                redownload_dict = {detail['scriptId']: detail for detail in redownload_details}
                for script in scripts_to_redownload:
                    if script['scriptId'] in redownload_dict:
                        detail = redownload_dict[script['scriptId']]
                        script.update(detail)
                        for flag in ['coverImageDownloaded', 'imageContentDownloaded', 'coverImageUploaded', 'imageContentUploaded', 'databaseInserted']:
                            if script.get(flag, 'False') == 'True':
                                script[flag] = 'True'
                        if 'firstFetchAt' not in detail:
                            script['firstFetchAt'] = script.get('firstFetchAt', int(time.time()))
            
            scripts_to_download_dict = {script['scriptId']: script for script in new_details}
            for script in scripts_to_redownload:
                if script['scriptId'] not in scripts_to_download_dict:
                    scripts_to_download_dict[script['scriptId']] = script
                else:
                    existing = scripts_to_download_dict[script['scriptId']]
                    existing.update(script)
                    for flag in ['coverImageDownloaded', 'imageContentDownloaded', 'coverImageUploaded', 'imageContentUploaded', 'databaseInserted']:
                        if script.get(flag, 'False') == 'True':
                            existing[flag] = 'True'
                    if 'firstFetchAt' not in existing:
                        existing['firstFetchAt'] = script.get('firstFetchAt', int(time.time()))
            scripts_to_download = list(scripts_to_download_dict.values())
            logging.info(f"Step 3: Preparing to download images for {len(scripts_to_download)} scripts (new: {len(new_details)}, redownload: {len(scripts_to_redownload)})")
        else:
            scripts_to_download = data_update.read_csv(config.DETAILED_CSV_PATH)
        
        downloaded_images, total_size = web_scraping.download_images_sync(scripts_to_download)
        data_update.update_script_details(scripts_to_download, mode=mode)
        data_update.update_script_list_flags(scripts_to_download)
        logging.info(f"Step 3: {downloaded_images} images downloaded, total size: {total_size:.2f} MB")
    else:
        scripts_to_download = data_update.read_csv(config.SCRIPT_LIST_PATH)
        logging.debug(f"Skipping Step 3, loaded {len(scripts_to_download)} scripts from SCRIPT_LIST_PATH for next steps")

    # Step 4: Upload images to Cloudinary and update details and script list flags
    if start_step <= 4:
        cover_uploaded_count, cover_status = cloudinary_upload.upload_to_cloudinary(config.SCRIPT_COVER_FOLDER, "cover")
        content_uploaded_count, content_status = cloudinary_upload.upload_to_cloudinary(config.SCRIPT_IMAGE_CONTENT_FOLDER, "content")
        total_uploaded_count = cover_uploaded_count + content_uploaded_count
        
        for script in scripts_to_download:
            script_id = script['scriptId']
            if script_id in cover_status and script.get('coverImageUploaded', 'False') != 'True':
                script['coverImageUploaded'] = str(cover_status[script_id])
            if script_id in content_status and script.get('imageContentUploaded', 'False') != 'True':
                script['imageContentUploaded'] = str(content_status[script_id])
        data_update.update_script_details(scripts_to_download, mode=mode)
        data_update.update_script_list_flags(scripts_to_download)
        logging.info(f"Step 4: {total_uploaded_count} images uploaded successfully "
                     f"({cover_uploaded_count} covers, {content_uploaded_count} content)")
    else:
        logging.debug("Skipping Step 4")

    # Step 5: Translate the detailed CSV
    if start_step <= 5:
        data_processing.translate_csv(config.DETAILED_CSV_PATH, config.TRANSLATED_CSV_PATH)
        logging.info("Step 5: Data translated")
        # Load translated data for Step 6
        translated_details = data_update.read_csv(config.TRANSLATED_CSV_PATH)
        # Merge with script_list to include flags
        script_list_dict = {s['scriptId']: s for s in data_update.read_csv(config.SCRIPT_LIST_PATH)}
        for detail in translated_details:
            if detail['scriptId'] in script_list_dict:
                detail.update({
                    'coverImageDownloaded': script_list_dict[detail['scriptId']].get('coverImageDownloaded', 'False'),
                    'imageContentDownloaded': script_list_dict[detail['scriptId']].get('imageContentDownloaded', 'False'),
                    'coverImageUploaded': script_list_dict[detail['scriptId']].get('coverImageUploaded', 'False'),
                    'imageContentUploaded': script_list_dict[detail['scriptId']].get('imageContentUploaded', 'False'),
                    'databaseInserted': script_list_dict[detail['scriptId']].get('databaseInserted', 'False')
                })
    else:
        translated_details = data_update.read_csv(config.TRANSLATED_CSV_PATH) if os.path.exists(config.TRANSLATED_CSV_PATH) else []
        script_list_dict = {s['scriptId']: s for s in data_update.read_csv(config.SCRIPT_LIST_PATH)}
        for detail in translated_details:
            if detail['scriptId'] in script_list_dict:
                detail.update({
                    'coverImageDownloaded': script_list_dict[detail['scriptId']].get('coverImageDownloaded', 'False'),
                    'imageContentDownloaded': script_list_dict[detail['scriptId']].get('imageContentDownloaded', 'False'),
                    'coverImageUploaded': script_list_dict[detail['scriptId']].get('coverImageUploaded', 'False'),
                    'imageContentUploaded': script_list_dict[detail['scriptId']].get('imageContentUploaded', 'False'),
                    'databaseInserted': script_list_dict[detail['scriptId']].get('databaseInserted', 'False')
                })
        logging.debug(f"Skipping Step 5, loaded {len(translated_details)} translated details from {config.TRANSLATED_CSV_PATH}")

    # Step 6: Update Prisma database with translated scripts where databaseInserted=False
    if start_step <= 6:
        # Filter translated_details for scripts where databaseInserted=False
        scripts_to_upsert = [script for script in translated_details if script.get('databaseInserted', 'False') == 'False']
        logging.info(f"Step 6: Importing {len(scripts_to_upsert)} translated scripts with databaseInserted=False into Prisma database")
        if scripts_to_upsert:
            asyncio.run(prisma_operations.import_scripts_and_relations(scripts_to_upsert))
            # Update databaseInserted flag for successfully upserted scripts
            for script in scripts_to_upsert:
                script['databaseInserted'] = 'True'
            data_update.update_script_list_flags(scripts_to_upsert)
        else:
            logging.info("Step 6: No scripts to upsert (all databaseInserted=True)")
        logging.info("Step 6: Prisma database update completed")
    else:
        logging.debug("Skipping Step 6")

if __name__ == "__main__":
    import sys
    start_step = 1  # Default to step 2
    if len(sys.argv) > 1:
        try:
            start_step = int(sys.argv[1])
            if start_step < 1 or start_step > 6:
                raise ValueError("start_step must be between 1 and 6")
        except ValueError as e:
            print(f"Error: {e}. Using default start_step=2")
            start_step = 2
    main(mode='incremental', log_level='INFO', start_step=start_step)
    logging.info(f"Cron job execution completed from step {start_step}")
