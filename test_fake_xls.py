import pandas as pd
import os
import shutil

# Test reading Razão.xls
file_xls = "Razão.xls"
print("Reading Razão.xls...")
df_xls = pd.read_excel(file_xls, header=None)
print("Razão.xls shape:", df_xls.shape)

# Create a dummy .xlsx renamed to .xls
test_xlsx_as_xls = "test_fake.xls"
df_xls.head(20).to_excel("temp.xlsx", index=False, header=False, engine="openpyxl")
shutil.copy("temp.xlsx", test_xlsx_as_xls)
os.remove("temp.xlsx")

print("\nTesting test_fake.xls (which is an xlsx with xls extension)...")
try:
    pd.read_excel(test_xlsx_as_xls, header=None)
    print("Normal read_excel succeeded")
except Exception as e:
    print("Normal read_excel failed as expected:", type(e).__name__, e)
    
    # Try openpyxl
    df_recovered = pd.read_excel(test_xlsx_as_xls, engine="openpyxl", header=None)
    print("Recovered with engine='openpyxl'! Shape:", df_recovered.shape)

if os.path.exists(test_xlsx_as_xls):
    os.remove(test_xlsx_as_xls)
