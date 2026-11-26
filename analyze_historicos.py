import pandas as pd
import re

file_path = "Razão.xls"
df = pd.read_excel(file_path, header=None)

records = []
for idx in range(9, 191):
    row = df.iloc[idx]
    date_val = str(row[0]).strip() if pd.notna(row[0]) else None
    if not date_val or date_val == 'nan':
        continue
    hist = str(row[1]).strip() if pd.notna(row[1]) else ""
    deb = float(row[2]) if pd.notna(row[2]) and str(row[2]).strip() != "" else 0.0
    cred = float(row[3]) if pd.notna(row[3]) and str(row[3]).strip() != "" else 0.0
    saldo = float(row[4]) if pd.notna(row[4]) and str(row[4]).strip() != "" else 0.0
    records.append((idx, date_val, hist, deb, cred, saldo))

print(f"Total transactions: {len(records)}")

# Let's inspect types of transactions:
entradas = [r for r in records if r[4] > 0] # Credits = Entradas / Provisões
pagamentos = [r for r in records if r[3] > 0] # Debits = Pagamentos / Baixas

print(f"Total Entradas (Créditos): {len(entradas)}")
print(f"Total Pagamentos (Débitos): {len(pagamentos)}")

print("\n--- First 10 Entradas ---")
for r in entradas[:10]:
    print(f"Row {r[0]} | Date: {r[1][:10]} | Val: {r[4]:10.2f} | Hist: {r[2]}")

print("\n--- First 10 Pagamentos ---")
for r in pagamentos[:10]:
    print(f"Row {r[0]} | Date: {r[1][:10]} | Val: {r[3]:10.2f} | Hist: {r[2]}")
