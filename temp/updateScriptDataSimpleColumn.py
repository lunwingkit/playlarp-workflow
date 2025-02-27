import pandas as pd
import time

# Load the CSV file
df = pd.read_csv("data/script_data_simple.csv")

# Get current epoch time
current_epoch = int(time.time())

# Add new columns
df["firstFetchAt"] = current_epoch

# Convert scriptId to integer for comparison
df["scriptId"] = df["scriptId"].astype(int)

# Save the modified CSV
df.to_csv("data/script_data_simple.csv", index=False)

print("CSV file updated and saved as XXX_modified.csv")
