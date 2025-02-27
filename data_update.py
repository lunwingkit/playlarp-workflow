import csv
import os
from datetime import datetime
import config
import logging

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
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def sort_csv_by_script_id(file_path):
    """Sort CSV by scriptId in ascending order."""
    data = read_csv(file_path)
    if data:
        data.sort(key=lambda x: int(x['scriptId']) if x['scriptId'].isdigit() else x['scriptId'])
        write_csv(file_path, data, data[0].keys())
        logging.info(f"Sorted {file_path} by scriptId")

def update_script_list(new_data, mode='full'):
    """Update script_data.csv and return the number of new records inserted."""
    script_list_path = config.SCRIPT_LIST_PATH
    inserted_count = 0
    
    if not new_data:
        logging.info("No new script data to update.")
        return inserted_count
    
    if mode == 'incremental':
        existing_data = {row['scriptId'] for row in read_csv(script_list_path)}
        new_entries = [row for row in new_data if row['scriptId'] not in existing_data]
        inserted_count = len(new_entries)
        if new_entries:
            all_data = read_csv(script_list_path) + new_entries
            write_csv(script_list_path, all_data, new_data[0].keys())
            sort_csv_by_script_id(script_list_path)
            # Save incremental data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            incremental_dir = os.path.join(config.OUTPUT_FOLDER_PATH, timestamp)
            os.makedirs(incremental_dir, exist_ok=True)
            incremental_path = os.path.join(incremental_dir, 'script_data.csv')
            write_csv(incremental_path, new_entries, new_data[0].keys())
            logging.info(f"Incremental script list saved to {incremental_path}")
    else:
        write_csv(script_list_path, new_data, new_data[0].keys())
        sort_csv_by_script_id(script_list_path)
        inserted_count = len(new_data)  # In full mode, all records are "inserted"
    
    return inserted_count

def update_script_details(new_details, mode='full'):
    """Update script_data_detailed.csv and return the number of new records inserted."""
    detailed_csv_path = config.DETAILED_CSV_PATH
    inserted_count = 0
    
    if not new_details:
        logging.info("No new script details to update.")
        return inserted_count
    
    if mode == 'incremental':
        existing_data = {row['scriptId']: row for row in read_csv(detailed_csv_path)}
        new_entries = []
        for detail in new_details:
            script_id = detail['scriptId']
            if script_id not in existing_data:
                existing_data[script_id] = detail
                new_entries.append(detail)
                inserted_count += 1
        if existing_data:  # If there's existing data, use its keys
            write_csv(detailed_csv_path, list(existing_data.values()), list(existing_data.values())[0].keys())
        else:  # Otherwise, use new_details keys
            write_csv(detailed_csv_path, new_entries, new_details[0].keys())
        sort_csv_by_script_id(detailed_csv_path)
        if new_entries:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            incremental_dir = os.path.join(config.OUTPUT_FOLDER_PATH, timestamp)
            os.makedirs(incremental_dir, exist_ok=True)
            incremental_path = os.path.join(incremental_dir, 'script_data_detailed.csv')
            write_csv(incremental_path, new_entries, new_details[0].keys())
            logging.info(f"Incremental detailed data saved to {incremental_path}")
    else:
        write_csv(detailed_csv_path, new_details, new_details[0].keys())
        sort_csv_by_script_id(detailed_csv_path)
        inserted_count = len(new_details)  # In full mode, all records are "inserted"
    
    return inserted_count