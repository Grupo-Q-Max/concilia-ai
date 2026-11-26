"""
CONCILIA AI - Pre-seed script for Razão.xls (Safe Demo Loader)
If a sample Razão.xls exists, it loads it as a demo. If not, it skips safely.
"""
import sys
import os
import uuid
import json
from datetime import datetime
from pathlib import Path

def find_sample_file():
    candidates = [
        "Razão.xls",
        "Razão (1).xls",
        os.path.join(os.getcwd(), "Razão.xls"),
        os.path.join(os.getcwd(), "Razão (1).xls"),
    ]
    if getattr(sys, 'frozen', False):
        exe_dir = str(Path(sys.executable).parent)
        candidates.extend([
            os.path.join(exe_dir, "Razão.xls"),
            os.path.join(exe_dir, "Razão (1).xls"),
        ])
        if hasattr(sys, '_MEIPASS'):
            candidates.extend([
                os.path.join(sys._MEIPASS, "Razão.xls"),
                os.path.join(sys._MEIPASS, "Razão (1).xls"),
            ])
            
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return c
    return None

def seed_razao():
    # Lazy imports so backend path is resolved
    from app.database import init_db, get_connection
    from app.engine.parser import parse_accounting_ledger
    from app.engine.balance_validator import audit_accounting_balance
    from app.engine.reconciler import run_reconciliation

    init_db()
    
    file_path = find_sample_file()
    if not file_path:
        # Perfectly normal: no initial demo file, user will upload via UI
        return
        
    try:
        res = parse_accounting_ledger(file_path)
        metadata = res["metadata"]
        raw_transactions = res["transactions"]
        
        math_audit = audit_accounting_balance(
            metadata["initial_balance"],
            metadata["final_reported_balance"],
            raw_transactions
        )
        
        job_id = "job-razao-demo-01"
        reconcile_result = run_reconciliation(job_id, raw_transactions)
        transactions = reconcile_result["transactions"]
        reconciliations = reconcile_result["reconciliations"]
        summary = reconcile_result["summary"]
        
        conn = get_connection()
        with conn:
            # Only seed if no job exists
            count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            if count == 0:
                conn.execute("""
                INSERT INTO jobs (
                    id, filename, file_path, created_at, company_name, cnpj, period, account_code,
                    initial_balance, final_reported_balance, total_credits, total_debits,
                    period_net_movement, status, math_validation_status, math_explanation, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    os.path.basename(file_path),
                    os.path.abspath(file_path),
                    datetime.now().isoformat(),
                    metadata["company_name"],
                    metadata["cnpj"],
                    metadata["period"],
                    metadata["account_code"],
                    str(metadata["initial_balance"]),
                    str(metadata["final_reported_balance"]),
                    str(summary["total_credits_value"]),
                    str(summary["total_debits_value"]),
                    str(summary["period_net_movement"]),
                    "PROCESSED",
                    math_audit["status"],
                    json.dumps(math_audit, ensure_ascii=False),
                    json.dumps({"summary": summary}, ensure_ascii=False)
                ))
                
                for t in transactions:
                    conn.execute("""
                    INSERT INTO transactions (
                        id, job_id, row_index, trans_date, history, trans_type, amount,
                        reported_balance, extracted_nf, extracted_supplier, cleaned_supplier,
                        category, status, matched_amount, remaining_amount, is_reversal, is_duplicate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        t["id"], job_id, t["row_index"], t["trans_date"], t["history"],
                        t["trans_type"], str(t["amount"]),
                        str(t["reported_balance"]) if t["reported_balance"] is not None else None,
                        t["extracted_nf"], t["extracted_supplier"], t["cleaned_supplier"],
                        t["category"], t["status"], str(t["matched_amount"]),
                        str(t["remaining_amount"]), t["is_reversal"], t["is_duplicate"]
                    ))
                    
                for r in reconciliations:
                    conn.execute("""
                    INSERT INTO reconciliations (
                        id, job_id, match_type, invoice_trans_id, payment_trans_id, nf,
                        supplier, invoice_amount, payment_amount, reconciled_amount, difference,
                        confidence_score, status, match_notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r["id"], job_id, r["match_type"], r["invoice_trans_id"],
                        r["payment_trans_id"], r["nf"], r["supplier"],
                        r["invoice_amount"], r["payment_amount"], r["reconciled_amount"],
                        r["difference"], r["confidence_score"], r["status"],
                        r["match_notes"], r["created_at"]
                    ))
        conn.close()
    except Exception as e:
        print(f"Nota: carga inicial de demonstração pulada: {e}")

if __name__ == "__main__":
    seed_razao()
