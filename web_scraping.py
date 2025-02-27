import config
import hashlib
import requests
import json
import random
import os
from datetime import datetime
from PIL import Image
import logging
import brotli
import gzip
from io import BytesIO

# Configuration
HOST = config.HOST
SCRIPT_SEARCH_PAGE = config.SCRIPT_SEARCH_PAGE
PLAT_FORM_SCRIPT_INFO = config.PLAT_FORM_SCRIPT_INFO
REQUEST_TIMEOUT = config.REQUEST_TIMEOUT
TIMEOUT_RETRY_LIMIT = config.TIMEOUT_RETRY_LIMIT
SCRIPT_COVER_FOLDER = config.SCRIPT_COVER_FOLDER
SCRIPT_IMAGE_CONTENT_FOLDER = config.SCRIPT_IMAGE_CONTENT_FOLDER
COMPRESSION_THRESHOLD = config.COMPRESSION_THRESHOLD
USER_AGENT = config.USER_AGENT

# Headers from the working example
HEADERS_TEMPLATE = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-Hant-HK;q=1, yue-Hant-HK;q=0.9, en-HK;q=0.8, zh-Hans-HK;q=0.7",
    "CityCode": "810000",
    "User-Agent": "mi quan/3.5.9 (iPhone; iOS 17.6.1; Scale/3.00)",
    "UserToken": "432931758547890751",
    "AppHeader": '{"mobileType":"0","mobileMode":"iPhone13ProMax","mobileSys":"17.6.1","mobileCode":"007E3209-9BFF-4A31-A085-F11F55852313","appVersion":"3.5.9","channelId":"10005"}'
}

def serialize_data(data):
    """Serialize payload data for checksum calculation."""
    sorted_keys = sorted(data.keys())
    serialized_str = ""
    for key in sorted_keys:
        if isinstance(data[key], list):
            serialized_str += f"{key}=dfghdfgprt87089bxcvsdf245TTY~!#$%ASDFSFA14793347TYRTthdgh!@$$fgdfghdfgj3^&hdfgsF&"
        else:
            serialized_str += f"{key}={data[key]}&"
    return serialized_str[:-1]

def fetch_script_list():
    """Fetch script list with pagination and return a list of dicts with scriptId and scriptName."""
    url = HOST + SCRIPT_SEARCH_PAGE
    payload = {
        'scriptPlotTagType': '0', 'scriptLabelType': '0', 'pageNum': 0,
        'scriptDifficultyDegreeTagType': '0', 'sceneType': 0,
        'scriptDurationTagType': '0', 'scriptThemeTagType': '0',
        'scriptBackgroundTagType': '0', 'scriptSaleModeTagType': '0',
        'scriptPlayWayTagType': '0', 'personType': '0', 'cityCode': '810000',
        'curShowSize': 0, 'pageSize': 20
    }
    all_data = []  # List of dicts

    while True:
        random_float = random.uniform(0, 1)
        nonce = f"{random_float:.16f}"
        serialized = serialize_data(payload)
        checksum_input = f"{nonce}{serialized}rytujfghjd#$%^$%^*#^2345thdghdfgWERTSFS356E6Ysssfgsyw5$&^*#%^^@%$TFgsfyew5yq465467456SFGDHERTYERTY#%$6yhdgh"
        checksum = hashlib.md5(checksum_input.encode('utf-8')).hexdigest()

        headers = HEADERS_TEMPLATE.copy()
        headers.update({
            "Checksum": checksum,
            "Nonce": nonce,
            "Accept-Encoding": "gzip, deflate, br",  # Let requests handle Brotli
        })

        success = False
        items = []
        for attempt in range(TIMEOUT_RETRY_LIMIT):
            logging.info(f"Fetching script list page {payload['pageNum']}, attempt {attempt+1}")
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()

                logging.debug(f"Response headers: {response.headers}")
                content_type = response.headers.get('Content-Type', '').lower()
                content_encoding = response.headers.get('Content-Encoding', '').lower()
                logging.info(f"Content-Type: {content_type}, Content-Encoding: {content_encoding}")

                if 'application/json' not in content_type:
                    logging.error(f"Unexpected content type for pageNum={payload['pageNum']}: {content_type}. Raw response: {response.content[:100]}")
                    break

                # Parse JSON
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON for pageNum={payload['pageNum']}: {e}. Raw response: {response.content[:100]}")
                    break

                # Check response code
                if not isinstance(data, dict) or 'head' not in data or data['head'].get('code') != 200:
                    logging.warning(f"Server error for pageNum={payload['pageNum']}: {json.dumps(data, ensure_ascii=False)}")
                    break

                if 'data' not in data or not isinstance(data['data'], dict):
                    logging.warning(f"Invalid data structure for pageNum={payload['pageNum']}: {response.text[:100]}")
                    break

                items = data['data'].get('items', [])
                if not items:
                    logging.info(f"End of list at pageNum={payload['pageNum']}.")
                    break

                # Process items into a list
                page_scripts = []
                for item in items:
                    script_id = str(item.get('scriptId', ''))
                    script_name = item.get('scriptName', '')
                    if script_id:
                        all_data.append({'scriptId': script_id, 'scriptName': script_name})
                        page_scripts.append(script_name)
                if page_scripts:
                    logging.info(f"Fetched page {payload['pageNum']} with scripts: {', '.join(page_scripts)}")
                success = True

                payload['pageNum'] += 1
                payload['curShowSize'] += payload['pageSize']
                break

            except requests.exceptions.RequestException as e:
                if attempt == TIMEOUT_RETRY_LIMIT - 1:
                    logging.error(f"Failed after {TIMEOUT_RETRY_LIMIT} retries for pageNum={payload['pageNum']}: {e}")
                    return all_data
                logging.warning(f"Attempt {attempt+1} failed: {e}")

        if not success or not items:
            break

    return all_data

def fetch_script_details(script_ids):
    """Fetch details for given script_ids and return as list of dicts."""
    details = []
    url = HOST + PLAT_FORM_SCRIPT_INFO

    for i, script_id in enumerate(script_ids, 1):
        payload = {'scriptId': script_id}
        random_float = random.uniform(0, 1)
        nonce = f"{random_float:.16f}"
        serialized = serialize_data(payload)
        checksum_input = f"{nonce}{serialized}rytujfghjd#$%^$%^*#^2345thdghdfgWERTSFS356E6Ysssfgsyw5$&^*#%^^@%$TFgsfyew5yq465467456SFGDHERTYERTY#%$6yhdgh"
        checksum = hashlib.md5(checksum_input.encode('utf-8')).hexdigest()

        headers = HEADERS_TEMPLATE.copy()
        headers.update({"Checksum": checksum, "Nonce": nonce})

        for attempt in range(TIMEOUT_RETRY_LIMIT):
            logging.info(f"Fetching details for scriptId={script_id} [{i}/{len(script_ids)}], attempt {attempt+1}")
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                logging.debug(f"Response headers: {response.headers}")  # Debug logging
                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    logging.error(f"[{i}/{len(script_ids)}] Failed to decode JSON for scriptId={script_id}: {e}. Raw response: {response.text[:100]}")
                    break

                if response_data is None or not isinstance(response_data, dict):
                    logging.warning(f"[{i}/{len(script_ids)}] Invalid response data for scriptId={script_id}: {response.text[:100]}")
                    break

                data = response_data.get('data', {})
                if data:
                    detail = {
                        'scriptId': data.get('scriptId', ''),
                        'scriptName': data.get('scriptName', ''),
                        'scriptCoverUrl': data.get('scriptCoverUrl', ''),
                        'scriptImageContent': data.get('scriptImageContent', '')
                    }
                    details.append(detail)
                    logging.info(f"[{i}/{len(script_ids)}] Fetched details for scriptId={script_id}")
                break
            except requests.exceptions.RequestException as e:
                if attempt == TIMEOUT_RETRY_LIMIT - 1:
                    logging.error(f"[{i}/{len(script_ids)}] Failed to fetch scriptId={script_id} after {TIMEOUT_RETRY_LIMIT} retries: {e}")
                else:
                    logging.warning(f"[{i}/{len(script_ids)}] Attempt {attempt+1} failed: {e}")

    return details

def compress_image(image_path):
    """Compress image if it exceeds the threshold."""
    if os.path.getsize(image_path) > COMPRESSION_THRESHOLD:
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.save(image_path, "JPEG", quality=85)
            logging.info(f"Compressed {image_path}")
        except Exception as e:
            logging.error(f"Failed to compress {image_path}: {e}")

def download_images(scripts):
    """Download script cover and image content for each script into respective folders."""
    os.makedirs(SCRIPT_COVER_FOLDER, exist_ok=True)
    os.makedirs(SCRIPT_IMAGE_CONTENT_FOLDER, exist_ok=True)
    total_scripts = len(scripts)
    downloaded_images = 0
    total_size = 0

    for script_idx, script in enumerate(scripts, 1):
        script_id = script.get('scriptId', 'unknown')
        script_name = script.get('scriptName', 'unknown').replace('/', '_').replace('\\', '_')
        
        # Process script cover images
        cover_urls = script.get('scriptCoverUrl', '').split('@')
        if not cover_urls or cover_urls == ['']:
            logging.warning(f"[{script_idx}/{total_scripts}] No cover images for {script_name}")
        else:
            for img_idx, url in enumerate(cover_urls, 1):
                filename = f"{script_id}_{script_name}_{img_idx}_cover{os.path.splitext(url.split('/')[-1])[1]}"
                save_path = os.path.join(SCRIPT_COVER_FOLDER, filename)

                for attempt in range(TIMEOUT_RETRY_LIMIT):
                    try:
                        response = requests.get(url, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        with open(save_path, 'wb') as file:
                            file.write(response.content)
                        compress_image(save_path)
                        downloaded_images += 1
                        total_size += os.path.getsize(save_path)
                        logging.info(f"[{script_idx}/{total_scripts}] Downloaded cover {filename}")
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt == TIMEOUT_RETRY_LIMIT - 1:
                            logging.error(f"[{script_idx}/{total_scripts}] Failed to download cover {url}: {e}")
                        else:
                            logging.warning(f"[{script_idx}/{total_scripts}] Attempt {attempt+1} failed for cover {url}")

        # Process script image content
        content_urls = script.get('scriptImageContent', '').split('@')
        if not content_urls or content_urls == ['']:
            logging.warning(f"[{script_idx}/{total_scripts}] No image content for {script_name}")
        else:
            for img_idx, url in enumerate(content_urls, 1):
                filename = f"{script_id}_{script_name}_{img_idx}_content{os.path.splitext(url.split('/')[-1])[1]}"
                save_path = os.path.join(SCRIPT_IMAGE_CONTENT_FOLDER, filename)

                for attempt in range(TIMEOUT_RETRY_LIMIT):
                    try:
                        response = requests.get(url, timeout=REQUEST_TIMEOUT)
                        response.raise_for_status()
                        with open(save_path, 'wb') as file:
                            file.write(response.content)
                        compress_image(save_path)
                        downloaded_images += 1
                        total_size += os.path.getsize(save_path)
                        logging.info(f"[{script_idx}/{total_scripts}] Downloaded content {filename}")
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt == TIMEOUT_RETRY_LIMIT - 1:
                            logging.error(f"[{script_idx}/{total_scripts}] Failed to download content {url}: {e}")
                        else:
                            logging.warning(f"[{script_idx}/{total_scripts}] Attempt {attempt+1} failed for cover {url}")

    total_size_mb = total_size / (1024 * 1024)
    return downloaded_images, total_size_mb