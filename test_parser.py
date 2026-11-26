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
    records.append((idx, date_val, hist, deb, cred))

def parse_record(idx, date_str, hist, deb, cred):
    # Determine type
    trans_type = "CREDIT" if cred > 0 else "DEBIT"
    val = cred if cred > 0 else deb
    
    nf = None
    supplier = None
    details = None
    
    # Check Entrada: "ENTRADA CONFORME NOTA FISCAL <FORNECEDOR> <NF>"
    # Or "ENTRADA CONFORME NF..." or similar
    if "ENTRADA CONFORME NOTA FISCAL" in hist.upper() or "ENTRADA CONFORME NF" in hist.upper():
        clean_hist = re.sub(r'(?i)ENTRADA\s+CONFORME\s+(?:NOTA\s+FISCAL|NF)\s*', '', hist).strip()
        # Look for trailing number (the NF)
        m = re.search(r'^(.*?)\s+(\d+[\w\-\./]*)\s*$', clean_hist)
        if m:
            supplier = m.group(1).strip()
            nf = m.group(2).strip()
        else:
            supplier = clean_hist
    
    # Check Pagamento: "PAGAMENTO ... NF:\s*(\w+) ... Itens: ..."
    elif "PAGAMENTO" in hist.upper():
        # Match NF
        m_nf = re.search(r'(?i)NF[:\s]+(\d+[\w\-\./]*)', hist)
        if m_nf:
            nf = m_nf.group(1).strip()
            # Everything after NF: <nf> up to "Itens:" or end
            post_nf = hist[m_nf.end():].strip()
            m_itens = re.search(r'(?i)\s+Itens:', post_nf)
            if m_itens:
                supplier = post_nf[:m_itens.start()].strip()
                details = post_nf[m_itens.end():].strip()
            else:
                supplier = post_nf
        else:
            # Maybe NF is formatted differently
            supplier = hist
    else:
        # Other type of entry
        supplier = hist

    return {
        'idx': idx,
        'type': trans_type,
        'date': date_str[:10],
        'value': val,
        'nf': nf,
        'supplier': supplier,
        'hist': hist
    }

parsed = [parse_record(*r) for r in records]

unmatched_nf = [p for p in parsed if not p['nf']]
print(f"Total parsed: {len(parsed)}")
print(f"Parsed with NF: {len(parsed) - len(unmatched_nf)}")
print(f"Parsed without NF: {len(unmatched_nf)}")

if unmatched_nf:
    print("\n--- Rows without NF ---")
    for u in unmatched_nf:
        print(f"Row {u['idx']} | Type: {u['type']} | Val: {u['value']} | Hist: {u['hist']}")
