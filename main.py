import logging
import os
from datetime import datetime
import config
import web_scraping
import data_update
import data_processing
import cloudinary_upload
from logging_config import setup_logger

def main(mode='incremental', log_level='INFO'):
    # Set up logging
    log_file = setup_logger(log_level=log_level, log_folder=config.LOG_FOLDER)
    logging.info(f"Starting cron job in {mode} mode. Log file: {log_file}")
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(config.SCRIPT_LIST_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(config.DETAILED_CSV_PATH), exist_ok=True)
    os.makedirs(config.SCRIPT_COVER_FOLDER, exist_ok=True)
    os.makedirs(config.SCRIPT_IMAGE_CONTENT_FOLDER, exist_ok=True)

    # Step 1: Fetch and update script list
    script_list = web_scraping.fetch_script_list()
    inserted_count = data_update.update_script_list(script_list, mode=mode)
    logging.info(f"Step 1: Script list updated. {inserted_count} new records inserted.")
    
    # Step 2: Fetch and update script details
    if mode == 'incremental':
        existing_details = {row['scriptId'] for row in data_update.read_csv(config.DETAILED_CSV_PATH)}
        new_script_ids = [s['scriptId'] for s in script_list if s['scriptId'] not in existing_details]
    else:
        new_script_ids = [s['scriptId'] for s in script_list]
    
    new_details = web_scraping.fetch_script_details(new_script_ids)
    details_inserted_count = data_update.update_script_details(new_details, mode=mode)
    logging.info(f"Step 2: Detailed data updated. {details_inserted_count} new records inserted.")
    
    # Step 3: Translate the detailed CSV
    data_processing.translate_csv(config.DETAILED_CSV_PATH, config.TRANSLATED_CSV_PATH)
    logging.info("Step 3: Data translated")
    
    # Step 4: Download images
    if mode == 'incremental':
        scripts_to_download = new_details
    else:
        scripts_to_download = data_update.read_csv(config.DETAILED_CSV_PATH)
    
    downloaded_images, total_size = web_scraping.download_images(scripts_to_download)
    logging.info(f"Step 4: {downloaded_images} images downloaded, total size: {total_size:.2f} MB")
    
    # Step 5: Upload images to Cloudinary
    cover_uploaded_count = cloudinary_upload.upload_to_cloudinary(config.SCRIPT_COVER_FOLDER, account_type="cover")
    content_uploaded_count = cloudinary_upload.upload_to_cloudinary(config.SCRIPT_IMAGE_CONTENT_FOLDER, account_type="content")
    total_uploaded_count = cover_uploaded_count + content_uploaded_count
    logging.info(f"Step 5: {total_uploaded_count} images uploaded successfully "
                 f"({cover_uploaded_count} covers, {content_uploaded_count} content)")

if __name__ == "__main__":
    main(mode='incremental', log_level='INFO')
    logging.info("Cron job execution completed.")