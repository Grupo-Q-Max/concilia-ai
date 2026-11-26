import pandas as pd
from decimal import Decimal

file_path = "Razão.xls"
df = pd.read_excel(file_path, header=None)

# Let's inspect rows around the jumps:
# Row 8: SALDO ANTERIOR
# Row 13, 14
# Row 27, 28
# Row 61, 62
# Row 116, 117
# Row 190, 191, 192

print("Rows 6 to 15:")
print(df.iloc[6:15])

print("\nRows 26 to 30:")
print(df.iloc[26:30])

print("\nRows 60 to 64:")
print(df.iloc[60:64])

print("\nRows 115 to 119:")
print(df.iloc[115:119])

print("\nRows 188 to 194:")
print(df.iloc[188:195])
