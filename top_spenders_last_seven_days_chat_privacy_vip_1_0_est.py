import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Define the directory path
directory = r"G:\Meu Drive\Sexting - Histórico"

# Get today's date (use datetime.now() for real execution, but hardcoded for simulation)
today = datetime.now().date()
# For the given context: today = datetime(2026, 2, 6).date()

# Calculate the date 7 days ago
seven_days_ago = today - timedelta(days=7)

# List all files in the directory
files = os.listdir(directory)

# Filter files that match the pattern and are within the last 7 days
relevant_files = []
for file in files:
    if file.endswith("_top_spenders_privacy_vip.xlsx"):
        # Extract date from filename (assuming format dd_mm_yyyy_...)
        date_str = file[:10]  # dd_mm_yyyy is 10 characters (2+1+2+1+4)
        try:
            file_date = datetime.strptime(date_str, "%d_%m_%Y").date()
            if seven_days_ago <= file_date <= today:
                relevant_files.append(os.path.join(directory, file))
        except ValueError:
            # Skip if date parsing fails
            continue

# Initialize an empty DataFrame to hold consolidated data
consolidated_df = pd.DataFrame(columns=["Comprador", "Valor gasto"])

# Read and concatenate data from relevant files
for file_path in relevant_files:
    df = pd.read_excel(file_path)
    # Ensure columns are present
    if "Comprador" in df.columns and "Valor gasto" in df.columns:
        consolidated_df = pd.concat([consolidated_df, df[["Comprador", "Valor gasto"]]], ignore_index=True)

# Group by "Comprador" and sum "Valor gasto"
if not consolidated_df.empty:
    grouped_df = consolidated_df.groupby("Comprador", as_index=False)["Valor gasto"].sum()
    # Sort by "Valor gasto" in descending order
    grouped_df = grouped_df.sort_values(by="Valor gasto", ascending=False)
else:
    grouped_df = pd.DataFrame(columns=["Comprador", "Valor gasto"])

# Define the output file path
output_path = os.path.join(directory, "last_week_top_spenders_privacy_vip.xlsx")

# Save the result to Excel, overwriting if exists
grouped_df.to_excel(output_path, index=False)

print(f"Weekly ranking generated and saved to: {output_path}")

sys.exit()