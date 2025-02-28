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

def main(mode='incremental', log_level='INFO', start_step=1, fetch_images=True, upload_images=True):
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
        script_list = web_scraping.fetch_script_list_sync()
        inserted_count = data_update.update_script_list(script_list, mode=mode)
        logging.info(f"Step 1: Script list updated. {inserted_count} new records inserted.")
        if mode == 'incremental':
            existing_scripts = data_update.read_csv(config.SCRIPT_LIST_PATH)
            existing_ids = {s['scriptId'] for s in existing_scripts}
            new_scripts = [s for s in script_list if s['scriptId'] not in existing_ids]
            updated_scripts = existing_scripts + new_scripts
            data_update.write_csv(config.SCRIPT_LIST_PATH, updated_scripts)
            logging.info(f"Step 1: Appended {len(new_scripts)} new scripts to SCRIPT_LIST_PATH")
        else:
            data_update.write_csv(config.SCRIPT_LIST_PATH, script_list)
            logging.info(f"Step 1: Overwrote SCRIPT_LIST_PATH with {len(script_list)} scripts in full mode")
    else:
        script_list = data_update.read_csv(config.SCRIPT_LIST_PATH)
        logging.debug(f"Skipping Step 1, loaded {len(script_list)} scripts from {config.SCRIPT_LIST_PATH}")

    # Step 2: Fetch and update script details
    if start_step <= 2:
        if mode == 'incremental':
            existing_scripts = data_update.read_csv(config.SCRIPT_LIST_PATH)
            existing_details = {row['scriptId'] for row in data_update.read_csv(config.DETAILED_CSV_PATH)}
            new_script_ids = [s['scriptId'] for s in existing_scripts if s['scriptId'] not in existing_details]
            logging.debug(f"New script IDs to fetch in incremental mode: {len(new_script_ids)}")
        else:
            new_script_ids = [s['scriptId'] for s in script_list]
            logging.debug(f"Fetching all {len(new_script_ids)} script IDs in full mode")
        
        if new_script_ids:
            new_details = web_scraping.fetch_script_details_sync(new_script_ids)
            details_inserted_count = data_update.update_script_details(new_details, mode=mode)
            logging.info(f"Step 2: Detailed data updated. {details_inserted_count} new records inserted.")
        else:
            new_details = []
            logging.info("Step 2: No new script IDs to fetch.")
    else:
        new_details = []
        logging.debug("Skipping Step 2, new_details set to empty list")

    # Step 3: Download images and update details and script list flags
    if start_step <= 3:
        if mode == 'incremental':
            existing_scripts = data_update.read_csv(config.SCRIPT_LIST_PATH)
            # Filter scripts needing image downloads based on flags
            scripts_to_download = [
                script for script in existing_scripts
                if script.get('coverImageDownloaded', 'False') == 'False' or 
                   script.get('imageContentDownloaded', 'False') == 'False'
            ]
            # Load existing details from DETAILED_CSV_PATH to get URLs
            detailed_data = {row['scriptId']: row for row in data_update.read_csv(config.DETAILED_CSV_PATH)}
            # Merge details into scripts_to_download
            scripts_to_download_dict = {script['scriptId']: script for script in scripts_to_download}
            for script_id, script in scripts_to_download_dict.items():
                if script_id in detailed_data:
                    script.update(detailed_data[script_id])
                else:
                    logging.debug(f"scriptId={script_id} needs download but has no details in DETAILED_CSV_PATH")
            # Merge new_details if available
            for detail in new_details:
                if detail['scriptId'] in scripts_to_download_dict:
                    scripts_to_download_dict[detail['scriptId']].update(detail)
            scripts_to_download = list(scripts_to_download_dict.values())
            logging.info(f"Step 3: Preparing to download images for {len(scripts_to_download)} scripts based on download flags")
        else:
            scripts_to_download = new_details if new_details else data_update.read_csv(config.DETAILED_CSV_PATH)
            logging.info(f"Step 3: Preparing to download images for {len(scripts_to_download)} scripts in full mode")
        
        if fetch_images and scripts_to_download:
            downloaded_images, total_size = web_scraping.download_images_sync(scripts_to_download)
            logging.info(f"Step 3: {downloaded_images} images downloaded, total size: {total_size:.2f} MB")
            data_update.update_script_details(scripts_to_download, mode=mode)
            data_update.update_script_list_flags(scripts_to_download)
        else:
            logging.info("Step 3: Image downloading skipped as per user request or no scripts to process.")
    else:
        scripts_to_download = data_update.read_csv(config.SCRIPT_LIST_PATH)
        logging.debug(f"Skipping Step 3, loaded {len(scripts_to_download)} scripts from SCRIPT_LIST_PATH")

    # Step 4: Upload images to Cloudinary and update details and script list flags
    if start_step <= 4:
        if upload_images:
            existing_scripts = data_update.read_csv(config.SCRIPT_LIST_PATH)
            scripts_to_upload = [
                script for script in existing_scripts
                if (script.get('coverImageDownloaded', 'False') == 'True' and script.get('coverImageUploaded', 'False') == 'False') or
                   (script.get('imageContentDownloaded', 'False') == 'True' and script.get('imageContentUploaded', 'False') == 'False')
            ]
            script_ids_to_upload = {script['scriptId'] for script in scripts_to_upload}
            scripts_to_download = [s for s in scripts_to_download if s['scriptId'] in script_ids_to_upload]
            logging.info(f"Step 4: Identified {len(scripts_to_upload)} scripts needing uploads based on upload flags")

            if scripts_to_upload:
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
                logging.info("Step 4: No scripts require image uploads.")
        else:
            logging.info("Step 4: Image uploading to Cloudinary skipped as per user request.")
    else:
        logging.debug("Skipping Step 4")

    # Step 5: Translate the detailed CSV
    if start_step <= 5:
        data_processing.translate_csv(config.DETAILED_CSV_PATH, config.TRANSLATED_CSV_PATH)
        logging.info("Step 5: Data translated")
        translated_details = data_update.read_csv(config.TRANSLATED_CSV_PATH)
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
        logging.debug(f"Skipping Step 5, loaded {len(translated_details)} translated details")

    # Step 6: Import into Prisma database
    if start_step <= 6:
        if mode == 'full':
            scripts_to_upsert = translated_details
            logging.info(f"Step 6: Importing all {len(scripts_to_upsert)} scripts into Prisma database (full mode)")
        else:
            scripts_to_upsert = [script for script in translated_details if script.get('databaseInserted', 'False') == 'False']
            logging.info(f"Step 6: Importing {len(scripts_to_upsert)} scripts with databaseInserted=False into Prisma database (incremental mode)")

        if scripts_to_upsert:
            asyncio.run(prisma_operations.import_scripts_and_relations(scripts_to_upsert))
            for script in scripts_to_upsert:
                script['databaseInserted'] = 'True'
            data_update.update_script_list_flags(scripts_to_upsert)
        else:
            logging.info("Step 6: No scripts to upsert")
        logging.info("Step 6: Prisma database update completed")
    else:
        logging.debug("Skipping Step 6")

if __name__ == "__main__":
    mode = 'incremental'
    start_step = 2
    log_level = 'DEBUG'  # Set to DEBUG for detailed logs
    fetch_images = True
    upload_images = True

    main(mode=mode, log_level=log_level, start_step=start_step, fetch_images=fetch_images, upload_images=upload_images)
    logging.info(f"Cron job execution completed from step {start_step}")