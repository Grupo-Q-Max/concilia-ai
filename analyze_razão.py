import pandas as pd
from decimal import Decimal

file_path = "Razão.xls"
df = pd.read_excel(file_path, header=None)

rows = []
for idx in range(6, len(df)):
    r = df.iloc[idx].tolist()
    rows.append((idx, r))

# Let's inspect header and rows
header = rows[0]
print("Header at row 6:", header)

# Find data rows
data_rows = []
for idx, r in rows[1:]:
    data = r[0]
    hist = r[1]
    deb = r[2]
    cred = r[3]
    saldo = r[4]
    
    # Check if this is a transaction
    if pd.notna(data) and str(data).strip() != "":
        data_rows.append({
            'row_idx': idx,
            'date': str(data).strip(),
            'history': str(hist).strip() if pd.notna(hist) else "",
            'debit': Decimal(str(deb).strip()) if pd.notna(deb) and str(deb).strip() != "" else Decimal('0.00'),
            'credit': Decimal(str(cred).strip()) if pd.notna(cred) and str(cred).strip() != "" else Decimal('0.00'),
            'reported_balance': Decimal(str(saldo).strip()) if pd.notna(saldo) and str(saldo).strip() != "" else None
        })
    else:
        print(f"Non-transaction row {idx}: {r}")

print(f"\nTotal transaction rows: {len(data_rows)}")

# Let's inspect balance formula row by row
prev_balance = Decimal('0.00')
print("\n--- Examining balance changes ---")
for i, row in enumerate(data_rows):
    deb = row['debit']
    cred = row['credit']
    rep_bal = row['reported_balance']
    
    # If standard: new_bal = prev - cred + deb OR prev + cred - deb OR prev - deb + cred?
    # Let's see: row 0: cred 5282.11 -> saldo -5282.11. So saldo = prev - cred + deb? Or is saldo negative when credit?
    # Wait, row 14: row 13 saldo was -29890.11.
    # What was row 14? Let's check row 13 vs row 14!
    if i < 20 or i > len(data_rows) - 10:
        print(f"Row {row['row_idx']} ({row['date'][:10]}): Deb={deb:10.2f} Cred={cred:10.2f} RepSaldo={rep_bal} | Prev={prev_balance}")
    
    # Check if rep_bal != prev + X
    diff_minus_cred = (prev_balance - cred + deb) - (rep_bal if rep_bal is not None else Decimal('0'))
    diff_plus_cred = (prev_balance + cred - deb) - (rep_bal if rep_bal is not None else Decimal('0'))
    
    # Let's check when rep_bal jumps!
    expected_if_deb_minus_cred = prev_balance + deb - cred
    expected_if_cred_minus_deb = prev_balance + cred - deb
    expected_if_minus_cred_plus_deb = prev_balance - cred + deb
    
    if rep_bal is not None:
        if rep_bal != expected_if_minus_cred_plus_deb and rep_bal != expected_if_cred_minus_deb and rep_bal != expected_if_deb_minus_cred:
            print(f"--> JUMP at row {row['row_idx']} ({row['date'][:10]}): Prev={prev_balance}, Deb={deb}, Cred={cred}, RepSaldo={rep_bal}, diff={rep_bal - prev_balance}")
        prev_balance = rep_bal

print("\nLast reported balance:", data_rows[-1]['reported_balance'])
