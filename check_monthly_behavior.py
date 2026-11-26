import pandas as pd
from decimal import Decimal

file_path = "Razão.xls"
df = pd.read_excel(file_path, header=None)

# Parse valid transactions
records = []
for idx in range(9, 191):
    row = df.iloc[idx]
    date_val = str(row[0]).strip() if pd.notna(row[0]) else None
    if not date_val or date_val == 'nan':
        continue
    hist = str(row[1]).strip() if pd.notna(row[1]) else ""
    deb = Decimal(str(row[2]).strip()) if pd.notna(row[2]) and str(row[2]).strip() != "" else Decimal('0.00')
    cred = Decimal(str(row[3]).strip()) if pd.notna(row[3]) and str(row[3]).strip() != "" else Decimal('0.00')
    saldo = Decimal(str(row[4]).strip()) if pd.notna(row[4]) and str(row[4]).strip() != "" else None
    
    records.append({
        'idx': idx,
        'date': date_val,
        'month': date_val[:7],
        'hist': hist,
        'deb': deb,
        'cred': cred,
        'saldo': saldo
    })

print(f"Total valid transactions: {len(records)}")

# Group by month and check balance formula
from collections import defaultdict
by_month = defaultdict(list)
for r in records:
    by_month[r['month']].append(r)

for m, rows in by_month.items():
    print(f"\n=== Month {m} (Total rows: {len(rows)}) ===")
    tot_deb = sum(r['deb'] for r in rows)
    tot_cred = sum(r['cred'] for r in rows)
    first_saldo = rows[0]['saldo']
    last_saldo = rows[-1]['saldo']
    net_movement_deb_minus_cred = tot_deb - tot_cred
    net_movement_cred_minus_deb = tot_cred - tot_deb
    print(f"Total Débito:  {tot_deb}")
    print(f"Total Crédito: {tot_cred}")
    print(f"Tot Deb - Tot Cred: {net_movement_deb_minus_cred}")
    print(f"Tot Cred - Tot Deb: {net_movement_cred_minus_deb}")
    print(f"First Saldo: {first_saldo}")
    print(f"Last Saldo:  {last_saldo}")
    
    # Check within month running balance:
    # Notice: Credit produces negative saldo (-cred), Debit produces positive saldo (+deb)
    # running_saldo = - cred + deb
    running = Decimal('0.00')
    errors = 0
    for r in rows:
        running = running - r['cred'] + r['deb']
        if running != r['saldo']:
            errors += 1
            print(f"  Row {r['idx']} mismatch: calc={running}, reported={r['saldo']}")
    print(f"Errors against running = running - cred + deb: {errors}")

# Overall totals
total_debits = sum(r['deb'] for r in records)
total_credits = sum(r['cred'] for r in records)
print("\n=== OVERALL TOTALS ===")
print(f"Total Debits:  {total_debits}")
print(f"Total Credits: {total_credits}")
print(f"Difference (Cred - Deb): {total_credits - total_debits}")
print(f"Difference (Deb - Cred): {total_debits - total_credits}")
print(f"Last Row Saldo: {records[-1]['saldo']}")
print(f"Row 192 reported Deb: {df.iloc[192, 2]}, reported Cred: {df.iloc[192, 3]}")
