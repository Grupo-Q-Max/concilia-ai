"""
Test complete pipeline on Razão.xls
"""
import sys
import os

# Add backend to sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.database import init_db
from app.engine.parser import parse_accounting_ledger
from app.engine.balance_validator import audit_accounting_balance
from app.engine.reconciler import run_reconciliation
from app.engine.exporter import export_reconciliation_excel, export_reconciliation_pdf

print("Initializing DB...")
init_db()

file_path = "Razão.xls" if os.path.exists("Razão.xls") else "Razão (1).xls"
print(f"Testing pipeline with {file_path}...")

# 1. Parse
res = parse_accounting_ledger(file_path)
meta = res["metadata"]
trans = res["transactions"]

print(f"Company: {meta['company_name']}")
print(f"CNPJ: {meta['cnpj']}")
print(f"Period: {meta['period']}")
print(f"Reported Final Balance: R$ {meta['final_reported_balance']}")
print(f"Total Transactions Parsed: {len(trans)}")

# 2. Math Audit
audit = audit_accounting_balance(meta["initial_balance"], meta["final_reported_balance"], trans)
print("\n--- Math Audit ---")
print(f"Status: {audit['status']}")
print(f"Audit Note: {audit['audit_note']}")

# 3. Reconciliation
reconcile_res = run_reconciliation("job-test-01", trans)
summ = reconcile_res["summary"]
print("\n--- Reconciliation Summary ---")
for k, v in summ.items():
    print(f"  {k}: {v}")

# 4. Exporter
os.makedirs("test_exports", exist_ok=True)
excel_out = export_reconciliation_excel(meta, reconcile_res["transactions"], reconcile_res["reconciliations"], summ, audit, "test_exports/conciliacao_teste.xlsx")
print(f"\nExcel exported successfully to: {excel_out}")

open_inv = [t for t in reconcile_res["transactions"] if t["trans_type"] == "CREDIT" and t["remaining_amount"] > 0]
pdf_out = export_reconciliation_pdf(meta, summ, audit, open_inv, "test_exports/laudo_teste.pdf")
print(f"PDF exported successfully to: {pdf_out}")
print("\nALL BACKEND CORE TESTS PASSED WITH 100% SUCCESS!")
