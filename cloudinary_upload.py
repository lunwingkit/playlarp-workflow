import cloudinary
import cloudinary.uploader
import os
from datetime import datetime
import config
import logging
import re
import csv

def read_script_list(file_path):
    """Read SCRIPT_LIST_PATH into a dictionary of scriptId to flags."""
    if not os.path.exists(file_path):
        logging.warning(f"SCRIPT_LIST_PATH '{file_path}' does not exist, assuming all flags are False")
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {row['scriptId']: {
            'coverImageUploaded': row.get('coverImageUploaded', 'False') == 'True',
            'imageContentUploaded': row.get('imageContentUploaded', 'False') == 'True'
        } for row in reader}

def upload_to_cloudinary(folder_path, account_type):
    """Upload images from a folder to the specified Cloudinary account, respecting upload flags."""
    # Log initial configuration attempt
    logging.debug(f"Configuring Cloudinary for account_type={account_type}")

    # Select configuration based on account_type
    if account_type == "cover":
        cloud_config = {
            "cloud_name": config.CLOUDINARY_COVER_CLOUD_NAME,
            "api_key": config.CLOUDINARY_COVER_API_KEY,
            "api_secret": config.CLOUDINARY_COVER_API_SECRET,
            "secure": True
        }
        folder = "your_cloudinary_folder_name"  # Consider making this configurable via config.py
        flag_key = 'coverImageUploaded'
    elif account_type == "content":
        cloud_config = {
            "cloud_name": config.CLOUDINARY_CONTENT_CLOUD_NAME,
            "api_key": config.CLOUDINARY_CONTENT_API_KEY,
            "api_secret": config.CLOUDINARY_CONTENT_API_SECRET,
            "secure": True
        }
        folder = "larp_script_image_content"
        flag_key = 'imageContentUploaded'
    else:
        raise ValueError("Invalid account_type. Use 'cover' or 'content'.")

    # Validate configuration values
    for key, value in cloud_config.items():
        if not value:
            logging.error(f"Cloudinary {key} for {account_type} is not set. Current value: {value}")
            raise ValueError(f"Cloudinary {key} for {account_type} is missing or empty")

    # Apply configuration and log it
    cloudinary.config(**cloud_config)
    logging.debug(f"Cloudinary configured: cloud_name={cloud_config['cloud_name']}, api_key={cloud_config['api_key'][:5]}****, secure={cloud_config['secure']}")

    # Check if the folder exists
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")

    # Read SCRIPT_LIST_PATH to check upload status
    script_list_status = read_script_list(config.SCRIPT_LIST_PATH)
    logging.debug(f"Loaded {len(script_list_status)} scripts from SCRIPT_LIST_PATH for {account_type} upload check")

    # Supported image extensions
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith(image_extensions)]
    total_files = len(all_files)
    uploaded_count = 0
    error_count = 0

    uploaded_status = {}  # Track upload status per scriptId
    
    # Regex patterns to extract scriptId from filename
    cover_pattern = re.compile(r"^(.*?)_(\d+)_(.*?)_\d+_cover_(.*)\.(\w+)$")
    content_pattern = re.compile(r"^(.*?)_(\d+)_(.*?)_\d+_image_content_(.*)\.(\w+)$")

    for index, filename in enumerate(all_files, 1):
        file_path = os.path.join(folder_path, filename)
        script_id = None
        public_id = None

        # Extract scriptId based on account_type
        if account_type == "cover":
            match = cover_pattern.match(filename)
            if match:
                script_id = match.group(2)
                public_id = f"{script_id}"
            else:
                logging.warning(f"[{index}/{total_files}] Filename {filename} does not match cover pattern, skipping")
                continue
        elif account_type == "content":
            match = content_pattern.match(filename)
            if match:
                script_id = match.group(2)
                file_name = match.group(4)
                public_id = f"{script_id}_{file_name}"
            else:
                logging.warning(f"[{index}/{total_files}] Filename {filename} does not match content pattern, skipping")
                continue

        # Check if upload is needed based on SCRIPT_LIST_PATH
        if script_id in script_list_status and script_list_status[script_id][flag_key]:
            logging.debug(f"[{index}/{total_files}] Skipping {filename} for scriptId={script_id} as {flag_key} is already True")
            uploaded_status[script_id] = True
            continue

        if script_id not in uploaded_status:
            uploaded_status[script_id] = True

        # Log before upload attempt to confirm configuration
        current_config = cloudinary.config()
        logging.debug(f"Before upload [{index}/{total_files}] of {filename}: cloud_name={current_config.cloud_name}, api_key={current_config.api_key[:5] if current_config.api_key else 'None'}****")

        try:
            response = cloudinary.uploader.upload(
                file_path,
                public_id=public_id,
                folder=folder,
                use_filename=False,
                unique_filename=False,
                overwrite=False
            )
            uploaded_count += 1
            logging.info(f"[{index}/{total_files}] Uploaded {filename}: {response['secure_url']}")
        except Exception as e:
            uploaded_status[script_id] = False
            error_count += 1
            logging.error(f"[{index}/{total_files}] ERROR uploading {filename}: {str(e)}")

    logging.info(f"Upload Summary: {uploaded_count} uploaded, {error_count} errors")
    return uploaded_count, uploaded_status