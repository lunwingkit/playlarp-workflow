import pandas as pd
import time

# Load the CSV file
df = pd.read_csv("data/script_data_simple.csv")

# Convert scriptId to integer for comparison
df["scriptId"] = df["scriptId"].astype(int)

# Define threshold scriptId
threshold_script_id = 531164785958528512

# Apply conditions for coverImageUploaded and imageContentUploaded
df["databaseInserted"] = df["scriptId"] < threshold_script_id

# Save the modified CSV
df.to_csv("data/script_data_simple.csv", index=False)

print("CSV file updated and saved as XXX_modified.csv")
