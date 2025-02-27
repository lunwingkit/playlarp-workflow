import cloudinary
import cloudinary.uploader
import os
from datetime import datetime
import config
import logging

def upload_to_cloudinary(folder_path, account_type):
    """Upload images from a folder to the specified Cloudinary account."""
    # Configure Cloudinary based on account type
    if account_type == "cover":
        cloudinary.config(
            cloud_name=config.CLOUDINARY_COVER_CLOUD_NAME,
            api_key=config.CLOUDINARY_COVER_API_KEY,
            api_secret=config.CLOUDINARY_COVER_API_SECRET,
            secure=True
        )
        folder = "larp_script_cover"
    elif account_type == "content":
        cloudinary.config(
            cloud_name=config.CLOUDINARY_CONTENT_CLOUD_NAME,
            api_key=config.CLOUDINARY_CONTENT_API_KEY,
            api_secret=config.CLOUDINARY_CONTENT_API_SECRET,
            secure=True
        )
        folder = "larp_script_image_content"
    else:
        raise ValueError("Invalid account_type. Use 'cover' or 'content'.")

    # Check if the folder exists
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")

    # Supported image extensions
    image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith(image_extensions)]
    total_files = len(all_files)
    uploaded_count = 0
    error_count = 0

    for index, filename in enumerate(all_files, 1):
        file_path = os.path.join(folder_path, filename)
        public_id = os.path.splitext(filename)[0]
        try:
            response = cloudinary.uploader.upload(
                file_path,
                public_id=public_id,
                folder=folder,
                use_filename=True,
                unique_filename=False,
                overwrite=False
            )
            uploaded_count += 1
            logging.info(f"[{index}/{total_files}] Uploaded {filename}: {response['secure_url']}")
        except Exception as e:
            error_count += 1
            logging.error(f"[{index}/{total_files}] ERROR uploading {filename}: {e}")

    logging.info(f"Upload Summary: {uploaded_count} uploaded, {error_count} errors")
    return uploaded_count