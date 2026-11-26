import sys
import os
import shutil
import pandas as pd

if os.path.exists("Razão (1).xls") and not os.path.exists("Razão.xls"):
    shutil.copy("Razão (1).xls", "Razão.xls")

file_path = "Razão.xls" if os.path.exists("Razão.xls") else "Razão (1).xls"
print(f"Reading {file_path}...")

# Check sheets
excel_file = pd.ExcelFile(file_path)
print("Sheet names:", excel_file.sheet_names)

df = pd.read_excel(file_path, sheet_name=0, header=None)
print("Shape:", df.shape)
print("\n--- First 30 rows ---")
for idx, row in df.head(30).iterrows():
    vals = [str(x) if pd.notna(x) else "" for x in row.values]
    if any(vals):
        print(f"Row {idx:2d}: {vals}")

print("\n--- Last 30 rows ---")
for idx, row in df.tail(30).iterrows():
    vals = [str(x) if pd.notna(x) else "" for x in row.values]
    if any(vals):
        print(f"Row {idx:2d}: {vals}")
