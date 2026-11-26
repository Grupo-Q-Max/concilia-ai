import pandas as pd
from decimal import Decimal
from test_parser import parsed

# Let's separate Credits (Provisions/Entradas) and Debits (Payments/Baixas)
credits = [p for p in parsed if p['type'] == 'CREDIT']
debits = [p for p in parsed if p['type'] == 'DEBIT']

print(f"Total Credits (Invoices): {len(credits)}, Total Sum: {sum(c['value'] for c in credits):.2f}")
print(f"Total Debits (Payments): {len(debits)}, Total Sum: {sum(d['value'] for d in debits):.2f}")

# Group by NF
from collections import defaultdict
credits_by_nf = defaultdict(list)
for c in credits:
    credits_by_nf[c['nf']].append(c)

debits_by_nf = defaultdict(list)
for d in debits:
    debits_by_nf[d['nf']].append(d)

all_nfs = set(credits_by_nf.keys()).union(set(debits_by_nf.keys()))
print(f"Total unique NFs: {len(all_nfs)}")

# Analyze each NF
fully_reconciled = []
partial_payments = []
fully_open = []
payments_without_provision = []
grouped_or_complex = []
value_mismatches = []

for nf in sorted(all_nfs):
    c_list = credits_by_nf.get(nf, [])
    d_list = debits_by_nf.get(nf, [])
    
    tot_c = sum(Decimal(str(c['value'])) for c in c_list)
    tot_d = sum(Decimal(str(d['value'])) for d in d_list)
    
    if not c_list and d_list:
        payments_without_provision.append((nf, d_list, tot_d))
    elif c_list and not d_list:
        fully_open.append((nf, c_list, tot_c))
    elif len(c_list) == 1 and len(d_list) == 1:
        if tot_c == tot_d:
            fully_reconciled.append((nf, c_list[0], d_list[0]))
        else:
            value_mismatches.append((nf, c_list[0], d_list[0], tot_c, tot_d, tot_c - tot_d))
    else:
        grouped_or_complex.append((nf, c_list, d_list, tot_c, tot_d, tot_c - tot_d))

print(f"\n1-to-1 Exact Reconciled: {len(fully_reconciled)}")
print(f"Fully Open (No Payment): {len(fully_open)}, Total Open Sum: {sum(x[2] for x in fully_open):.2f}")
print(f"Payments without Provision: {len(payments_without_provision)}")
print(f"Value Mismatches (1-to-1 different values): {len(value_mismatches)}")
print(f"Grouped / Multiple entries per NF: {len(grouped_or_complex)}")

if value_mismatches:
    print("\n--- Value Mismatches ---")
    for vm in value_mismatches:
        print(f"NF: {vm[0]} | Credit: {vm[3]} | Debit: {vm[4]} | Diff: {vm[5]}")

if grouped_or_complex:
    print("\n--- Grouped / Multiple entries per NF ---")
    for g in grouped_or_complex:
        print(f"NF: {g[0]} | #Cred: {len(g[1])} (sum {g[3]}) | #Deb: {len(g[2])} (sum {g[4]}) | Diff: {g[5]}")

if payments_without_provision:
    print("\n--- Payments without Provision ---")
    for p in payments_without_provision:
        print(f"NF: {p[0]} | Debits: {len(p[1])} | Total: {p[2]}")

print("\n--- Sample Fully Open Invoices ---")
for fo in fully_open[:10]:
    print(f"NF: {fo[0]} | Date: {fo[1][0]['date']} | Supplier: {fo[1][0]['supplier']} | Value: {fo[2]}")

total_open_amount = sum(x[2] for x in fully_open)
total_diff_grouped = sum(g[5] for g in grouped_or_complex)
total_diff_mismatch = sum(vm[5] for vm in value_mismatches)
print(f"\nTotal Open Amount: {total_open_amount}")
print(f"Total Grouped Diff: {total_diff_grouped}")
print(f"Total Mismatch Diff: {total_diff_mismatch}")
print(f"Sum of remaining open positions: {total_open_amount + total_diff_grouped + total_diff_mismatch}")
print(f"Expected Credit - Debit period difference: {sum(c['value'] for c in credits) - sum(d['value'] for d in debits):.2f}")
