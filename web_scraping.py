import asyncio
import aiohttp
import config
import hashlib
import json
import random
import os
import time
from PIL import Image
import logging
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

async def fetch_page(session, url, payload, page_num):
    """Fetch a single page asynchronously with retries."""
    random_float = random.uniform(0, 1)
    nonce = f"{random_float:.16f}"
    serialized = serialize_data(payload)
    checksum_input = f"{nonce}{serialized}rytujfghjd#$%^$%^*#^2345thdghdfgWERTSFS356E6Ysssfgsyw5$&^*#%^^@%$TFgsfyew5yq465467456SFGDHERTYERTY#%$6yhdgh"
    checksum = hashlib.md5(checksum_input.encode('utf-8')).hexdigest()

    headers = HEADERS_TEMPLATE.copy()
    headers.update({"Checksum": checksum, "Nonce": nonce})

    for attempt in range(TIMEOUT_RETRY_LIMIT):
        try:
            logging.info(f"Fetching script list page {page_num}, attempt {attempt+1}")
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' not in content_type:
                    logging.error(f"Unexpected content type for pageNum={page_num}: {content_type}")
                    return None

                data = await response.json()
                if not isinstance(data, dict) or 'head' not in data or data['head'].get('code') != 200:
                    if isinstance(data, dict) and data.get('head', {}).get('code') == 500 and data.get('data') is None:
                        logging.info(f"Server returned 500 with null data for pageNum={page_num}, treating as end of pagination")
                        return []  # Treat specific 500 error with null data as end of list
                    logging.warning(f"Server error for pageNum={page_num}: {json.dumps(data, ensure_ascii=False)}")
                    return None

                return data.get('data', {}).get('items', [])
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.warning(f"Attempt {attempt+1} failed for pageNum={page_num}: {str(e)}")
            if attempt == TIMEOUT_RETRY_LIMIT - 1:
                logging.error(f"Failed after {TIMEOUT_RETRY_LIMIT} retries for pageNum={page_num}: {str(e)}")
                return None
            await asyncio.sleep(2 ** attempt)  # Backoff before retry

async def fetch_script_list():
    """Fetch script list with pagination asynchronously in batches of 50 pages."""
    url = HOST + SCRIPT_SEARCH_PAGE
    base_payload = {
        'scriptPlotTagType': '0', 'scriptLabelType': '0', 'pageNum': 0,
        'scriptDifficultyDegreeTagType': '0', 'sceneType': 0,
        'scriptDurationTagType': '0', 'scriptThemeTagType': '0',
        'scriptBackgroundTagType': '0', 'scriptSaleModeTagType': '0',
        'scriptPlayWayTagType': '0', 'personType': '0', 'cityCode': '810000',
        'curShowSize': 0, 'pageSize': 20
    }
    
    async with aiohttp.ClientSession() as session:
        # Fetch page 0 to initialize
        initial_payload = base_payload.copy()
        initial_items = await fetch_page(session, url, initial_payload, 0)
        if not initial_items:
            logging.info("No items found on page 0, returning empty list")
            return []

        all_data = []
        current_time = int(time.time())
        for item in initial_items:
            script_id = str(item.get('scriptId', ''))
            script_name = item.get('scriptName', '')
            if script_id:
                all_data.append({
                    'scriptId': script_id,
                    'scriptName': script_name,
                    'firstFetchAt': current_time,
                    'lastModifiedAt': current_time,
                    'coverImageDownloaded': False,
                    'imageContentDownloaded': False,
                    'coverImageUploaded': False,
                    'imageContentUploaded': False,
                    'databaseInserted': False  # New flag
                })

        # Fetch pages in batches of 50
        batch_size = 50
        page_offset = 1
        while True:
            tasks = []
            for page in range(page_offset, page_offset + batch_size):
                payload = base_payload.copy()
                payload['pageNum'] = page
                payload['curShowSize'] = page * base_payload['pageSize']
                tasks.append(fetch_page(session, url, payload, page))

            logging.debug(f"Fetching batch of pages {page_offset} to {page_offset + batch_size - 1}")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process batch results
            batch_has_items = False
            end_of_list = False
            for page_num, result in enumerate(results, page_offset):
                if isinstance(result, list):
                    if result:
                        batch_has_items = True
                        for item in result:
                            script_id = str(item.get('scriptId', ''))
                            script_name = item.get('scriptName', '')
                            if script_id:
                                all_data.append({
                                    'scriptId': script_id,
                                    'scriptName': script_name,
                                    'firstFetchAt': current_time,
                                    'lastModifiedAt': current_time,
                                    'coverImageDownloaded': False,
                                    'imageContentDownloaded': False,
                                    'coverImageUploaded': False,
                                    'imageContentUploaded': False,
                                    'databaseInserted': False  # New flag
                                })
                    else:
                        logging.info(f"Empty list at pageNum={page_num}, checking if end of pagination")
                        end_of_list = True
                elif result is None:
                    logging.warning(f"Page {page_num} returned None due to error, continuing with batch")
                else:
                    logging.error(f"Unexpected result type for pageNum={page_num}: {type(result)}")

            if end_of_list and not batch_has_items:
                logging.info(f"Confirmed end of pagination at batch starting page {page_offset}")
                break
            elif not batch_has_items:
                logging.info(f"No items in batch starting at page {page_offset}, but no empty list confirmed, continuing")
            page_offset += batch_size

        logging.info(f"Fetched {len(all_data)} scripts across multiple pages")
        return all_data

async def fetch_script_detail(session, url, script_id, index, total):
    """Fetch details for a single scriptId asynchronously with retries."""
    payload = {'scriptId': script_id}
    random_float = random.uniform(0, 1)
    nonce = f"{random_float:.16f}"
    serialized = serialize_data(payload)
    checksum_input = f"{nonce}{serialized}rytujfghjd#$%^$%^*#^2345thdghdfgWERTSFS356E6Ysssfgsyw5$&^*#%^^@%$TFgsfyew5yq465467456SFGDHERTYERTY#%$6yhdgh"
    checksum = hashlib.md5(checksum_input.encode('utf-8')).hexdigest()

    headers = HEADERS_TEMPLATE.copy()
    headers.update({"Checksum": checksum, "Nonce": nonce})

    for attempt in range(TIMEOUT_RETRY_LIMIT):
        try:
            logging.info(f"Fetching details for scriptId={script_id} [{index}/{total}], attempt {attempt+1}")
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                response.raise_for_status()
                data = await response.json()
                if data and isinstance(data, dict) and 'data' in data:
                    current_time = int(time.time())
                    detail = data['data'].copy()  # Copy all fields from the API response
                    detail['lastModifiedAt'] = current_time  # Add local timestamp
                    return detail
                else:
                    logging.warning(f"[{index}/{total}] Invalid response for scriptId={script_id}")
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.warning(f"Attempt {attempt+1} failed for scriptId={script_id} [{index}/{total}]: {str(e)}")
            if attempt == TIMEOUT_RETRY_LIMIT - 1:
                logging.error(f"Failed after {TIMEOUT_RETRY_LIMIT} retries for scriptId={script_id} [{index}/{total}]: {str(e)}")
                return None
            await asyncio.sleep(2 ** attempt)

async def fetch_script_details(script_ids):
    """Fetch details for given script_ids concurrently."""
    url = HOST + PLAT_FORM_SCRIPT_INFO
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_script_detail(session, url, script_id, i + 1, len(script_ids))
            for i, script_id in enumerate(script_ids)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        details = [result for result in results if result is not None]
        logging.info(f"Fetched details for {len(details)} out of {len(script_ids)} scripts")
        return details

async def download_image(session, url, save_path, script_idx, total_scripts, image_idx, total_images_for_script, image_type):
    """Download a single image asynchronously with retries."""
    for attempt in range(TIMEOUT_RETRY_LIMIT):
        try:
            logging.info(f"Attempt {attempt+1} to download {image_type} {url} [Script {script_idx}/{total_scripts}, Image {image_idx}/{total_images_for_script}]")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                response.raise_for_status()
                content = await response.read()
                with open(save_path, 'wb') as file:
                    file.write(content)
                compress_image(save_path)
                logging.info(f"[Script {script_idx}/{total_scripts}, Image {image_idx}/{total_images_for_script}] Downloaded {image_type} {os.path.basename(save_path)}")
                return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.warning(f"Attempt {attempt+1} failed for {image_type} {url} [Script {script_idx}/{total_scripts}, Image {image_idx}/{total_images_for_script}]: {str(e)}")
            if attempt == TIMEOUT_RETRY_LIMIT - 1:
                logging.error(f"Failed after {TIMEOUT_RETRY_LIMIT} retries for {image_type} {url} [Script {script_idx}/{total_scripts}, Image {image_idx}/{total_images_for_script}]: {str(e)}")
                return False
            await asyncio.sleep(2 ** attempt)
    return False

def compress_image(image_path):
    """Compress image if it exceeds the threshold."""
    if os.path.getsize(image_path) > COMPRESSION_THRESHOLD:
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
                img.save(image_path, "JPEG", quality=85)
            logging.info(f"Compressed {image_path}")
        except Exception as e:
            logging.error(f"Failed to compress {image_path}: {str(e)}")

async def download_images(scripts):
    """Download script cover and image content for each script into respective folders asynchronously."""
    os.makedirs(SCRIPT_COVER_FOLDER, exist_ok=True)
    os.makedirs(SCRIPT_IMAGE_CONTENT_FOLDER, exist_ok=True)
    total_scripts = len(scripts)
    downloaded_images = 0
    total_size = 0
    downloaded_status = {}  # Track download status per scriptId
    failed_covers = []  # Track failed cover downloads
    failed_contents = []  # Track failed content downloads

    async with aiohttp.ClientSession() as session:
        tasks = []
        for script_idx, script in enumerate(scripts, 1):
            script_id = script.get('scriptId', 'unknown')
            script_name = script.get('scriptName', 'unknown').replace('/', '_').replace('\\', '_')
            # Log script details for debugging
            logging.debug(f"Processing scriptId={script_id}: coverDownloaded={script.get('coverImageDownloaded', 'False')}, contentDownloaded={script.get('imageContentDownloaded', 'False')}, coverUrl={script.get('scriptCoverUrl', 'None')}, contentUrl={script.get('scriptImageContent', 'None')}")
            
            # Preserve existing flags if already set
            downloaded_status[script_id] = {
                'cover': script.get('coverImageDownloaded', 'False') == 'True',
                'content': script.get('imageContentDownloaded', 'False') == 'True'
            }

            # Process script cover images only if not already downloaded
            if not downloaded_status[script_id]['cover']:
                cover_urls = script.get('scriptCoverUrl', '').split('@')
                total_covers_for_script = len(cover_urls) if cover_urls and cover_urls[0] else 0
                if total_covers_for_script > 0:
                    logging.debug(f"Adding {total_covers_for_script} cover download tasks for scriptId={script_id}")
                    for img_idx, url in enumerate(cover_urls, 1):
                        filename = get_image_filename(url, script_id, script_name, img_idx, "cover")
                        save_path = os.path.join(SCRIPT_COVER_FOLDER, filename)
                        tasks.append(download_image(session, url, save_path, script_idx, total_scripts, img_idx, total_covers_for_script, "cover"))

            # Process script image content only if not already downloaded
            if not downloaded_status[script_id]['content']:
                content_urls = script.get('scriptImageContent', '').split('@')
                total_contents_for_script = len(content_urls) if content_urls and content_urls[0] else 0
                if total_contents_for_script > 0:
                    logging.debug(f"Adding {total_contents_for_script} content download tasks for scriptId={script_id}")
                    for img_idx, url in enumerate(content_urls, 1):
                        filename = get_image_filename(url, script_id, script_name, img_idx, "image_content")
                        save_path = os.path.join(SCRIPT_IMAGE_CONTENT_FOLDER, filename)
                        tasks.append(download_image(session, url, save_path, script_idx, total_scripts, img_idx, total_contents_for_script, "content"))

        # Log total tasks created
        logging.debug(f"Total download tasks created: {len(tasks)}")

        # Execute all download tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            logging.warning("No download tasks were created")

        # Process results and update status
        task_index = 0
        for script_idx, script in enumerate(scripts, 1):
            script_id = script.get('scriptId', 'unknown')
            script_name = script.get('scriptName', 'unknown')
            cover_urls = script.get('scriptCoverUrl', '').split('@')
            content_urls = script.get('scriptImageContent', '').split('@')

            # Reset status to False unless downloads succeed
            if not downloaded_status[script_id]['cover']:
                downloaded_status[script_id]['cover'] = False
            if not downloaded_status[script_id]['content']:
                downloaded_status[script_id]['content'] = False

            # Process cover downloads
            if cover_urls and cover_urls[0] and not downloaded_status[script_id]['cover']:
                for _ in range(len(cover_urls)):
                    result = results[task_index]
                    logging.debug(f"Cover result for scriptId={script_id}, idx={_ + 1}: {result}")
                    if result is True:
                        downloaded_status[script_id]['cover'] = True
                        downloaded_images += 1
                        total_size += os.path.getsize(os.path.join(SCRIPT_COVER_FOLDER, get_image_filename(cover_urls[_], script_id, script_name, _+1, "cover")))
                    else:
                        downloaded_status[script_id]['cover'] = False
                        failed_covers.append({'scriptId': script_id, 'scriptName': script_name})
                    task_index += 1
                script['coverImageDownloaded'] = downloaded_status[script_id]['cover']

            # Process content downloads
            if content_urls and content_urls[0] and not downloaded_status[script_id]['content']:
                for _ in range(len(content_urls)):
                    result = results[task_index]
                    logging.debug(f"Content result for scriptId={script_id}, idx={_ + 1}: {result}")
                    if result is True:
                        downloaded_status[script_id]['content'] = True
                        downloaded_images += 1
                        total_size += os.path.getsize(os.path.join(SCRIPT_IMAGE_CONTENT_FOLDER, get_image_filename(content_urls[_], script_id, script_name, _+1, "image_content")))
                    else:
                        downloaded_status[script_id]['content'] = False
                        failed_contents.append({'scriptId': script_id, 'scriptName': script_name})
                    task_index += 1
                script['imageContentDownloaded'] = downloaded_status[script_id]['content']

            # lastModifiedAt not updated here; handled in fetch_script_detail
            # firstFetchAt not touched here; preserved from SCRIPT_LIST_PATH

        # Calculate totals
        total_covers = sum(len(script.get('scriptCoverUrl', '').split('@')) for script in scripts if script.get('scriptCoverUrl', '') and not downloaded_status[script['scriptId']]['cover'])
        total_contents = sum(len(script.get('scriptImageContent', '').split('@')) for script in scripts if script.get('scriptImageContent', '') and not downloaded_status[script['scriptId']]['content'])
        successful_covers = total_covers - len(failed_covers)
        successful_contents = total_contents - len(failed_contents)

        # Logging summary
        total_size_mb = total_size / (1024 * 1024)
        logging.info(f"Download Summary:")
        logging.info(f"  Total Covers: {total_covers}, Successful: {successful_covers}, Failed: {len(failed_covers)}")
        if failed_covers:
            logging.info("  Failed Covers:")
            for fail in failed_covers:
                logging.info(f"    scriptId: {fail['scriptId']}, scriptName: {fail['scriptName']}")
        logging.info(f"  Total Image Contents: {total_contents}, Successful: {successful_contents}, Failed: {len(failed_contents)}")
        if failed_contents:
            logging.info("  Failed Image Contents:")
            for fail in failed_contents:
                logging.info(f"    scriptId: {fail['scriptId']}, scriptName: {fail['scriptName']}")
        logging.info(f"Downloaded {downloaded_images} images, total size: {total_size_mb:.2f} MB")

    return downloaded_images, total_size_mb

def get_image_filename(url, script_id, script_name, idx, image_type):
    """Generate a structured filename for images following the new naming logic."""
    url_parts = url.split('/')
    script_name = script_name.replace("/", "_").replace("\\", "_")
    
    if "platformScriptImg" in url:
        folder_name = url_parts[-2]
        file_name = url_parts[-1]
        original_filename, file_extension = os.path.splitext(file_name)
        return f"{folder_name}_{script_id}_{script_name}_{idx}_{image_type}_{original_filename}{file_extension}"
    elif "officialActivity" in url or "script" in url:
        activity_date = url_parts[-2]
        file_name = url_parts[-1]
        original_filename, file_extension = os.path.splitext(file_name)
        return f"{activity_date}_{script_id}_{script_name}_{idx}_{image_type}_{original_filename}{file_extension}"
    elif "shopScriptImg" in url:
        shop_id = url_parts[-2]
        file_name = url_parts[-1]
        original_filename, file_extension = os.path.splitext(file_name)
        return f"{shop_id}_{script_id}_{script_name}_{idx}_{image_type}_{original_filename}{file_extension}"
    else:
        file_name = url_parts[-1]
        original_filename, file_extension = os.path.splitext(file_name)
        return f"{script_id}_{script_name}_{idx}_{image_type}_{original_filename}{file_extension}"

# Synchronous wrappers for compatibility
def run_fetch_script_list():
    logging.debug("Calling run_fetch_script_list")
    return asyncio.run(fetch_script_list())

def run_fetch_script_details(script_ids):
    logging.debug("Calling run_fetch_script_details")
    return asyncio.run(fetch_script_details(script_ids))

def run_download_images(scripts):
    logging.debug("Calling run_download_images")
    return asyncio.run(download_images(scripts))

# Assign wrappers to match expected names in main.py
fetch_script_list_sync = run_fetch_script_list
fetch_script_details_sync = run_fetch_script_details
download_images_sync = run_download_images