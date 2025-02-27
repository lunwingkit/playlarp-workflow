import pandas as pd
import zhconv
import csv
import os
import logging

def translate_csv(input_csv, output_csv):
    if not os.path.exists(input_csv):
        logging.error(f"Input file {input_csv} not found.")
        return

    df = pd.read_csv(input_csv, quoting=csv.QUOTE_ALL)
    df_translated = df.apply(lambda col: col.map(lambda x: zhconv.convert(str(x), 'zh-hant') if isinstance(x, str) else x))
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_translated.to_csv(output_csv, index=False, quoting=csv.QUOTE_ALL)
    logging.info(f"Translated {input_csv} to {output_csv}")
    
def sort_csv_by_script_id(csv_path):
    """Sort CSV by scriptId in ascending order."""
    if not os.path.exists(csv_path):
        logging.error(f"File not found: {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) <= 1:
        return

    header = rows[0]
    data_rows = rows[1:]
    data_rows.sort(key=lambda row: int(row[0]) if row[0].isdigit() else row[0])

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data_rows)
    logging.info(f"Sorted {csv_path} by scriptId")