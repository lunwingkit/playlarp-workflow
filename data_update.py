import csv
import os
import config
import logging
import time

def read_csv(file_path):
    """Read CSV into a list of dictionaries."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_csv(file_path, data, fieldnames):
    """Write data to CSV with given fieldnames."""
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)

def sort_csv_by_script_id(file_path):
    """Sort CSV by scriptId in ascending order."""
    data = read_csv(file_path)
    if data:
        data.sort(key=lambda x: int(x['scriptId']) if x['scriptId'].isdigit() else x['scriptId'])
        fieldnames = ['scriptId', 'scriptName'] + [key for key in data[0].keys() if key not in ['scriptId', 'scriptName']]
        write_csv(file_path, data, fieldnames)
        logging.info(f"Sorted {file_path} by scriptId")

def update_script_list(new_data, mode='full'):
    script_list_path = config.SCRIPT_LIST_PATH
    inserted_count = 0
    
    if not new_data:
        logging.info("No new script data to update.")
        return inserted_count
    
    current_time = int(time.time())
    if mode == 'incremental':
        existing_data = {row['scriptId']: row for row in read_csv(script_list_path)}
        new_entries = []
        for row in new_data:
            script_id = row['scriptId']
            if script_id not in existing_data:
                row['databaseInserted'] = 'False'  # Set for new entries
                new_entries.append(row)
                inserted_count += 1
            else:
                existing_row = existing_data[script_id]
                existing_row['scriptName'] = row['scriptName']
                # Preserve flags including databaseInserted
        all_data = list(existing_data.values()) + [row for row in new_entries if row['scriptId'] not in existing_data]
    else:
        all_data = [dict(row, databaseInserted='False') for row in new_data]  # All new with False
        inserted_count = len(new_data)
    
    if all_data:
        fieldnames = ['scriptId', 'scriptName', 'firstFetchAt', 'lastModifiedAt',
                      'coverImageDownloaded', 'imageContentDownloaded',
                      'coverImageUploaded', 'imageContentUploaded', 'databaseInserted']
        write_csv(script_list_path, all_data, fieldnames)
        sort_csv_by_script_id(script_list_path)
    return inserted_count

def update_script_details(new_details, mode='full'):
    detailed_csv_path = config.DETAILED_CSV_PATH
    inserted_count = 0
    
    if not new_details:
        logging.info("No new script details to update.")
        return inserted_count
    
    current_time = int(time.time())
    if mode == 'incremental':
        existing_data = {row['scriptId']: row for row in read_csv(detailed_csv_path)}
        new_entries = []
        for detail in new_details:
            script_id = detail['scriptId']
            if script_id not in existing_data:
                detail['firstFetchAt'] = current_time
                new_entries.append(detail)
                inserted_count += 1
            else:
                existing_row = existing_data[script_id]
                existing_row.update(detail)
                existing_row['lastModifiedAt'] = current_time
                existing_row['firstFetchAt'] = existing_row.get('firstFetchAt', current_time)
        all_data = list(existing_data.values()) + [row for row in new_entries if row['scriptId'] not in existing_data]
    else:
        all_data = new_details
        inserted_count = len(new_details)
    
    if all_data:
        fieldnames = ['scriptId', 'scriptName', 'firstFetchAt', 'lastModifiedAt', 'scriptCoverUrl', 'scriptImageContent']
        write_csv(detailed_csv_path, all_data, fieldnames)
        sort_csv_by_script_id(detailed_csv_path)
    return inserted_count

def update_script_list_flags(updated_data):
    script_list_path = config.SCRIPT_LIST_PATH
    current_data = {row['scriptId']: row for row in read_csv(script_list_path)}
    
    flag_fields = ['coverImageDownloaded', 'imageContentDownloaded', 'coverImageUploaded', 'imageContentUploaded', 'databaseInserted']
    
    for item in updated_data:
        script_id = item['scriptId']
        if script_id in current_data:
            current_row = current_data[script_id]
            for field in flag_fields:
                if field in item and current_row.get(field) != 'True':
                    current_row[field] = str(item[field])
            # Preserve firstFetchAt, lastModifiedAt unchanged here

    all_data = list(current_data.values())
    if all_data:
        fieldnames = ['scriptId', 'scriptName', 'firstFetchAt', 'lastModifiedAt',
                      'coverImageDownloaded', 'imageContentDownloaded',
                      'coverImageUploaded', 'imageContentUploaded', 'databaseInserted']
        write_csv(script_list_path, all_data, fieldnames)
        sort_csv_by_script_id(script_list_path)
    logging.info(f"Updated flags in {script_list_path}")