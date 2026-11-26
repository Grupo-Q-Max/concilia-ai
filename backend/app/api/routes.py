from pydantic import StrictBool
# CONCILIA_V5_OPERATIONS_SECURITY_30A5B
"""
CONCILIA AI - FastAPI Application Routes
"""
import os
import json
import uuid
import shutil
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from app.config import UPLOAD_DIR, EXPORT_DIR, load_settings, save_settings
from app.database import get_connection
from app.engine.parser import parse_accounting_ledger
from app.engine.balance_validator import audit_accounting_balance
from app.engine.reconciler import run_reconciliation
from app.engine.exporter import export_reconciliation_excel, export_reconciliation_pdf
from app.schemas import JobSummaryResponse, ManualMatchRequest

from app.engine.composition import composition, money


# CONCILIA_V5_PAYMENT_DETAILS
def payment_details(transactions, reconciliations):
    lookup = {t["id"]: t for t in transactions}
    details = []

    for r in reconciliations:
        if r.get("status") != "CONFIRMED":
            continue

        inv = lookup.get(r.get("invoice_trans_id"))
        pay = lookup.get(r.get("payment_trans_id"))

        if not inv or not pay:
            continue

        if inv["trans_type"] != "CREDIT" or pay["trans_type"] != "DEBIT":
            continue

        if inv.get("is_reversal") or pay.get("is_reversal"):
            continue

        residual = money(inv["remaining_amount"])

        details.append({
            "nf": inv.get("extracted_nf") or r.get("nf"),
            "supplier": inv.get("extracted_supplier"),
            "invoice_date": inv.get("trans_date"),
            "invoice_amount": str(money(inv["amount"])),
            "payment_date": pay.get("trans_date"),
            "payment_amount": str(money(pay["amount"])),
            "reconciled_amount": str(money(r["reconciled_amount"])),
            "matched_amount": str(money(inv["matched_amount"])),
            "remaining_amount": str(residual),
            "status": "PARCIAL" if residual > 0 else "QUITADO",
            "invoice_history": inv.get("history"),
            "payment_history": pay.get("history"),
            "invoice_row": inv.get("row_index"),
            "payment_row": pay.get("row_index"),
            "match_type": r.get("match_type"),
            "match_notes": r.get("match_notes"),
            "invoice_trans_id": inv["id"],
            "payment_trans_id": pay["id"],
            "reconciliation_id": r["id"]
        })

    return sorted(
        details,
        key=lambda r: (
            str(r["nf"] or ""),
            str(r["invoice_trans_id"]),
            str(r["payment_date"] or "")
        )
    )

# CONCILIA_V5_OPENING_INTEGRATION
def current_composition(conn, job):

    from app.engine.opening_storage_v5 import opening_state
    from app.engine.opening_matching_v5 import opening_audit

    job = dict(job)

    tx = [
        dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE job_id=? ORDER BY row_index",
            (job["id"],)
        )
    ]

    original, opening_rows, links = opening_state(
        conn, job["id"]
    )

    reconciliations = [
        dict(r) for r in conn.execute(
            "SELECT * FROM reconciliations WHERE job_id=?",
            (job["id"],)
        )
    ]

    result = composition(job, tx, original)

    result["payment_details"] = payment_details(
        tx, reconciliations
    )

    result["opening_rows"] = opening_rows
    result["opening_matches_count"] = len(links)
    result["opening_matched_total"] = "0.00"

    if original is None:
        return result

    audit = opening_audit(
        job["initial_balance"], original
    )

    result["opening_difference"] = audit["unproven_balance"]
    result["opening_complete"] = audit["fully_documented"]
    result["opening_audit"] = audit

    result["rows"] = [
        r for r in result["rows"]
        if r["kind"] != "Saldo anterior detalhado"
    ]

    residual_rows = []

    for item in opening_rows:

        value = money(item["value"])
        matched = money(item["matched_amount"])

        if value == 0:
            continue

        residual_rows.append({
            "kind": (
                "Saldo anterior parcialmente baixado"
                if matched > 0
                else "Saldo anterior detalhado"
            ),
            "value": str(value),
            "date": item.get("trans_date", ""),
            "nf": item.get("extracted_nf", ""),
            "supplier": item.get("extracted_supplier", ""),
            "history": item.get("history", ""),
            "original": item["original"],
            "matched_amount": item["matched_amount"],
            "remaining_amount": item["remaining_amount"],
            "status": item["status"],
            "transaction_id": (
                "OPENING:" + str(item["opening_index"])
            ),
            "origin": "SALDO_ANTERIOR"
        })

    result["rows"] = residual_rows + result["rows"]

    lookup = {t["id"]: t for t in tx}

    for link in links:

        item = opening_rows[link["opening_index"]]
        pay = lookup.get(link["payment_trans_id"])

        if pay is None:
            raise ValueError(
                "Pagamento do saldo anterior nao localizado."
            )

        result["payment_details"].append({
            "nf": item.get("extracted_nf"),
            "supplier": item.get("extracted_supplier"),
            "invoice_date": item.get("trans_date"),
            "invoice_amount": item["original"],
            "payment_date": pay.get("trans_date"),
            "payment_amount": str(money(pay["amount"])),
            "reconciled_amount": link["amount"],
            "matched_amount": item["matched_amount"],
            "remaining_amount": item["remaining_amount"],
            "status": item["status"],
            "invoice_history": item.get("history"),
            "payment_history": pay.get("history"),
            "invoice_row": link["opening_index"] + 1,
            "payment_row": pay.get("row_index"),
            "match_type": "OPENING",
            "match_notes": link["reason"],
            "invoice_trans_id": (
                "OPENING:" + str(link["opening_index"])
            ),
            "payment_trans_id": pay["id"],
            "reconciliation_id": link["id"],
            "origin": "SALDO_ANTERIOR"
        })

    result["opening_matched_total"] = str(sum(
        (money(r["amount"]) for r in links),
        Decimal("0.00")
    ))

    total = sum(
        (money(r["value"]) for r in result["rows"]),
        Decimal("0.00")
    )

    reported = money(job["final_reported_balance"])

    result["total"] = str(total)
    result["reported"] = str(reported)
    result["difference"] = str(total - reported)
    result["valid"] = total == reported and bool(tx)

    return result



# CONCILIA_V5_LIVE_SUMMARY
def refresh_live_summary(conn, job_id, summary):
    from decimal import Decimal

    tx = [dict(r) for r in conn.execute(
        "SELECT * FROM transactions WHERE job_id=?",
        (job_id,)
    )]

    rec = [dict(r) for r in conn.execute(
        "SELECT * FROM reconciliations WHERE job_id=? AND status='CONFIRMED'",
        (job_id,)
    )]

    def dec(v):
        return Decimal(str(v or 0))

    credits = [t for t in tx if t["trans_type"] == "CREDIT"]
    debits = [t for t in tx if t["trans_type"] == "DEBIT"]

    opened = [t for t in credits if dec(t["remaining_amount"]) > 0]
    pending = [t for t in debits if dec(t["remaining_amount"]) > 0]

    total_credits = sum((dec(t["amount"]) for t in credits), Decimal(0))
    total_debits = sum((dec(t["amount"]) for t in debits), Decimal(0))

    total_matched = sum(
        (dec(t["matched_amount"]) for t in credits),
        Decimal(0)
    )

    total_open = sum(
        (dec(t["remaining_amount"]) for t in opened),
        Decimal(0)
    )

    total_pending = sum(
        (dec(t["remaining_amount"]) for t in pending),
        Decimal(0)
    )

    cents = [r for r in rec if r["match_type"] == "CENT_DIFFERENCE"]

    total_cents = sum(
        (dec(r["difference"]) for r in cents),
        Decimal(0)
    )

    summary.update({
        "total_transactions": len(tx),
        "total_invoices_count": len(credits),
        "total_payments_count": len(debits),
        "total_credits_value": str(total_credits),
        "total_debits_value": str(total_debits),
        "total_reconciled_value": str(total_matched),
        "reconciled_count": len([
            r for r in rec
            if r["match_type"] in ("EXACT_1_TO_1", "MANUAL")
        ]),
        "open_invoices_count": len(opened),
        "total_open_value": str(total_open),
        "unreconciled_payments_count": len(pending),
        "partial_count": len([
            t for t in tx if t["status"] == "PARCIAL"
        ]),
        "cent_differences_count": len(cents),
        "cent_differences_total": str(total_cents),
        "reconciliation_rate_pct": round(
            float(total_matched / total_credits * 100)
            if total_credits else 0, 2
        )
    })

    summary.setdefault("balance_composition", {}).update({
        "open_invoices_total": str(total_open),
        "open_invoices_count": len(opened),
        "unmapped_debits_total": str(total_pending),
        "unmapped_debits_count": len(pending),
        "cent_differences_total": str(total_cents),
        "cent_differences_count": len(cents)
    })


    # CONCILIA_V5_INDICATORS_23B
    from app.engine.opening_storage_v5 import opening_state

    zero = Decimal("0.00")

    def amount(t, field):
        return dec(t.get(field)).quantize(Decimal("0.01"))

    def total(items, field):
        return sum(
            (amount(t, field) for t in items),
            zero
        )

    def rate(numerator, denominator):
        if denominator <= zero:
            return 0.0
        return float(
            (numerator / denominator * 100).quantize(
                Decimal("0.01")
            )
        )

    def eligible(t):
        return (
            not t.get("is_duplicate")
            and not t.get("is_reversal")
            and t.get("status") not in ("DIFERENCA_CENTAVOS", "DIVERGENCIA_CENTAVOS")
            and amount(t, "amount") > zero
        )

    def settled(t):
        return (
            amount(t, "remaining_amount") == zero
            and amount(t, "matched_amount") == amount(t, "amount")
        )

    def partial(t):
        return (
            amount(t, "matched_amount") > zero
            and amount(t, "remaining_amount") > zero
        )

    valid_credits = [t for t in credits if eligible(t)]
    valid_debits = [t for t in debits if eligible(t)]

    settled_credits = [
        t for t in valid_credits if settled(t)
    ]

    partial_credits = [
        t for t in valid_credits if partial(t)
    ]

    partial_debits = [
        t for t in valid_debits if partial(t)
    ]

    untouched_credits = [
        t for t in valid_credits
        if amount(t, "matched_amount") == zero
        and amount(t, "remaining_amount") > zero
    ]

    original, opening_rows, opening_links = opening_state(
        conn, job_id
    )

    opening_credits = [
        t for t in opening_rows
        if amount(t, "value") < zero
        or (
            amount(t, "remaining_amount") == zero
            and amount(t, "matched_amount") > zero
        )
    ]

    opening_paid = sum(
        (dec(r["amount"]) for r in opening_links),
        zero
    )

    opening_original = total(
        opening_credits, "original"
    )

    opening_residual = total(
        opening_credits, "remaining_amount"
    )

    current_matched = total(
        valid_credits, "matched_amount"
    )

    current_original = total(
        valid_credits, "amount"
    )

    debit_matched = total(
        valid_debits, "matched_amount"
    )

    debit_original = total(
        valid_debits, "amount"
    )

    by_type = {}

    for item in rec:
        key = item.get("match_type") or "UNKNOWN"
        by_type[key] = by_type.get(key, 0) + 1

    undone_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM audit_logs
        WHERE job_id=?
        AND action='UNDO_MATCH_V5'
        """,
        (job_id,)
    ).fetchone()[0]

    indicators = {
        "active_reconciliations_count": len(rec),
        "active_opening_matches_count": len(opening_links),
        "active_matches_total_count": (
            len(rec) + len(opening_links)
        ),
        "undone_count": undone_count,
        "reconciliations_by_type": by_type,

        "settled_invoices_count": len(settled_credits),
        "partial_invoices_count": len(partial_credits),
        "untouched_invoices_count": len(untouched_credits),
        "partial_payments_count": len(partial_debits),

        "current_credit_original": str(current_original),
        "current_credit_matched": str(current_matched),
        "current_credit_residual": str(total(valid_credits, "remaining_amount")),
        "current_debit_original": str(debit_original),
        "current_debit_matched": str(debit_matched),
        "current_debit_residual": str(total(valid_debits, "remaining_amount")),

        "current_credit_rate_pct": rate(
            current_matched, current_original
        ),
        "current_debit_rate_pct": rate(
            debit_matched, debit_original
        ),

        "opening_attached": original is not None,
        "opening_credit_original": str(opening_original),
        "opening_credit_matched": str(opening_paid),
        "opening_credit_residual": str(opening_residual),

        "opening_settled_count": len([
            t for t in opening_credits if (amount(t, "remaining_amount") == zero and amount(t, "matched_amount") == amount(t, "original") and amount(t, "original") > zero)
        ]),
        "opening_partial_count": len([
            t for t in opening_credits if partial(t)
        ]),
        "opening_rate_pct": rate(
            opening_paid, opening_original
        ),

        "combined_credit_original": str(
            current_original + opening_original
        ),
        "combined_credit_matched": str(
            current_matched + opening_paid
        ),
        "combined_credit_rate_pct": rate(
            current_matched + opening_paid,
            current_original + opening_original
        )
    }

    # CONCILIA_V5_INDICATORS_25A
    summary["indicators_v5"] = indicators

    return summary


router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "app": "CONCILIA AI", "version": "1.0.0"}

@router.get("/settings")
def get_system_settings():
    return load_settings()

@router.post("/settings")
def update_system_settings(payload: Dict[str, Any]):

    try:

        updated = save_settings(payload)

    except ValueError as exc:

        raise HTTPException(
            422,
            str(exc)
        ) from exc

    except Exception as exc:

        raise HTTPException(
            500,
            "Nao foi possivel salvar as configuracoes."
        ) from exc

    return {
        "success": True,
        "settings": updated
    }

@router.post("/reconciliation/{job_id}/reprocess")
def reprocess_job(job_id: str):
    # CONCILIA_V5_REPROCESS_SAFETY_30A4
    from decimal import Decimal
    import logging

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job_row:
            raise HTTPException(status_code=404, detail="Job não encontrado.")
        job_data = dict(job_row)


        from app.engine.opening_storage_v5 import (
            ensure_opening_storage
        )

        ensure_opening_storage(conn)

        if conn.execute(
            "SELECT 1 FROM opening_matches_v5 WHERE job_id=? LIMIT 1",
            (job_id,)
        ).fetchone():
            raise HTTPException(
                409,
                "Reprocessamento bloqueado: existem baixas "
                "registradas do saldo anterior."
            )

        if conn.execute(
            "SELECT 1 FROM reconciliations WHERE job_id=? "
            "AND match_type='MANUAL' AND status='CONFIRMED' LIMIT 1",
            (job_id,)
        ).fetchone():
            raise HTTPException(
                409,
                "Reprocessamento bloqueado: existem "
                "conciliacoes manuais aprovadas."
            )
        if conn.execute(
            "SELECT 1 FROM audit_logs WHERE job_id=? "
            "AND action='UNDO_MATCH_V5' LIMIT 1",
            (job_id,)
        ).fetchone():
            raise HTTPException(
                409,
                "Reprocessamento bloqueado: existem "
                "conciliacoes desfeitas pelo usuario."
            )


        file_path = str(UPLOAD_DIR / os.path.basename(job_data["file_path"]))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="Arquivo original não encontrado no servidor.")

        import hashlib
        from pathlib import Path

        source_hash_before = hashlib.sha256(
            Path(file_path).read_bytes()
        ).hexdigest()

        stored_metadata = json.loads(
            job_data.get("metadata_json") or "{}"
        )

        import_config = stored_metadata.get(
            "import_mapping_v5"
        )

        if import_config:
            from pathlib import Path

            digest = hashlib.sha256(
                Path(file_path).read_bytes()
            ).hexdigest()

            if digest != import_config["file_hash"]:

                raise HTTPException(
                    409,
                    "Arquivo original alterado. "
                    "Reprocessamento bloqueado."
                )

            parse_result = parse_accounting_ledger(
                file_path,
                header_row=import_config["header_row"],
                column_mapping=import_config["mapping"],
            )
        else:
            parse_result = parse_accounting_ledger(file_path)
        source_hash_after = hashlib.sha256(
            Path(file_path).read_bytes()
        ).hexdigest()

        if source_hash_before != source_hash_after:
            raise HTTPException(
                409,
                "Arquivo alterado durante a leitura."
            )

        metadata = parse_result["metadata"]
        raw_transactions = parse_result["transactions"]

        math_audit = audit_accounting_balance(
            metadata["initial_balance"],
            metadata["final_reported_balance"],
            raw_transactions
        )

        if math_audit["status"] != "VALID":
            raise HTTPException(
                422,
                "Reprocessamento com validacao invalida."
            )


        from app.engine.manual_safety_v5 import strict_money_v5

        if not raw_transactions:
            raise HTTPException(
                422,
                "Nenhum lancamento reconhecido."
            )

        for field in (
            "initial_balance",
            "final_reported_balance",
        ):
            if strict_money_v5(metadata[field]) != strict_money_v5(
                job_data[field]
            ):
                raise HTTPException(
                    409,
                    "Os saldos contabeis do arquivo diferem "
                    "do documento original. Importe como novo documento."
                )

        source_debits = sum(
            (
                strict_money_v5(t["amount"])
                for t in raw_transactions
                if t["trans_type"] == "DEBIT"
            ),
            Decimal("0.00")
        )

        source_credits = sum(
            (
                strict_money_v5(t["amount"])
                for t in raw_transactions
                if t["trans_type"] == "CREDIT"
            ),
            Decimal("0.00")
        )

        if (
            source_debits != strict_money_v5(job_data["total_debits"])
            or source_credits != strict_money_v5(job_data["total_credits"])
        ):
            raise HTTPException(
                409,
                "Os movimentos contabeis diferem do documento original."
            )

        if (
            strict_money_v5(metadata["initial_balance"])
            + source_debits
            - source_credits
            != strict_money_v5(metadata["final_reported_balance"])
        ):
            raise HTTPException(
                422,
                "A equacao contabil nao fecha."
            )


        def ledger_identity(t):
            balance = t.get("reported_balance")

            return (
                int(t["row_index"]),
                str(t["trans_date"]),
                str(t["history"]),
                str(t["trans_type"]),
                strict_money_v5(t["amount"]),
                (
                    strict_money_v5(balance)
                    if balance is not None and balance != ""
                    else None
                ),
            )

        previous_transactions = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM transactions WHERE job_id=?",
                (job_id,)
            )
        ]

        previous_identity = sorted(
            (ledger_identity(t) for t in previous_transactions),
            key=lambda item: item[0]
        )

        new_identity = sorted(
            (ledger_identity(t) for t in raw_transactions),
            key=lambda item: item[0]
        )

        if previous_identity != new_identity:
            raise HTTPException(
                409,
                "Os lancamentos originais foram alterados ou "
                "interpretados de forma diferente. "
                "Importe o arquivo como novo documento."
            )

        reconcile_result = run_reconciliation(job_id, raw_transactions)
        transactions = reconcile_result["transactions"]
        reconciliations = reconcile_result["reconciliations"]
        summary = reconcile_result["summary"]


        from app.engine.manual_safety_v5 import (
            validate_manual_composition_v5,
            validate_manual_transition_v5,
        )

        before_composition = current_composition(
            conn, job_data
        )

        validate_manual_composition_v5(
            before_composition
        )

        if not transactions:
            raise HTTPException(
                422,
                "O motor retornou uma lista vazia."
            )

        if len(transactions) != len(raw_transactions):
            raise HTTPException(
                409,
                "Quantidade de lancamentos alterada pelo motor."
            )

        if sorted(
            (ledger_identity(t) for t in transactions),
            key=lambda item: item[0]
        ) != new_identity:
            raise HTTPException(
                409,
                "O motor alterou os lancamentos originais."
            )

        conn.execute("DELETE FROM reconciliations WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM transactions WHERE job_id = ?", (job_id,))

        conn.execute("""
        UPDATE jobs SET
            total_credits = ?, total_debits = ?, period_net_movement = ?,
            math_validation_status = ?, math_explanation = ?, metadata_json = ?
        WHERE id = ?
        """, (
            str(summary["total_credits_value"]),
            str(summary["total_debits_value"]),
            str(summary["period_net_movement"]),
            math_audit["status"],
            json.dumps(math_audit, ensure_ascii=False),
            json.dumps(
                {
                    **stored_metadata,
                    "summary": summary,
                },
                ensure_ascii=False
            ),
            job_id
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

        conn.execute("""
        INSERT INTO audit_logs (id, job_id, action, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), job_id, "REPROCESS_WITH_SETTINGS",
            f"Reprocessado com novas configurações. {len(transactions)} lançamentos e {len(reconciliations)} conciliações.",
            datetime.now().isoformat()
        ))

        updated_job = conn.execute(
            "SELECT * FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not updated_job:
            raise RuntimeError(
                "Documento ausente apos reprocessamento."
            )

        after_composition = current_composition(
            conn, dict(updated_job)
        )

        validate_manual_composition_v5(
            after_composition
        )

        validate_manual_transition_v5(
            before_composition,
            after_composition
        )

        if strict_money_v5(
            after_composition["total"]
        ) != strict_money_v5(
            job_data["final_reported_balance"]
        ):
            raise HTTPException(
                409,
                "Composicao final diferente do saldo contabil."
            )

        if conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchone():
            raise RuntimeError(
                "Falha de integridade referencial."
            )

        if hashlib.sha256(
            Path(file_path).read_bytes()
        ).hexdigest() != source_hash_before:
            raise HTTPException(
                409,
                "Arquivo alterado durante o reprocessamento."
            )

        conn.commit()

        return {"success": True, "summary": summary, "math_audit": math_audit}
    except HTTPException:
        conn.rollback()
        raise

    except ValueError as exc:
        conn.rollback()
        raise HTTPException(
            409,
            str(exc)
        ) from exc

    except Exception as exc:
        conn.rollback()

        logging.getLogger(__name__).exception(
            "Falha no reprocessamento do documento %s",
            job_id
        )

        raise HTTPException(
            500,
            "Reprocessamento interrompido. "
            "Nenhuma alteracao foi confirmada."
        ) from exc

    finally:
        conn.close()

@router.post("/upload")
async def upload_and_process_ledger(
    file: UploadFile = File(...),
    header_row: Optional[int] = Form(None),
    column_mapping: Optional[str] = Form(None),
    mapping_fingerprint: Optional[str] = Form(None),
):
    """
    Receives an accounting ledger (.xls, .xlsx, .csv), parses transactions,
    performs mathematical audit, and runs automatic reconciliation.
    """
    # CONCILIA_V5_IMPORT_CONFIRM_29D32
    from app.operations_security_v5 import validate_uploaded_file_v5
    validate_uploaded_file_v5(file)
    import hashlib
    import re
    from pathlib import Path

    from app.engine.import_preview_v5 import (
        validate_upload_v5,
        ALLOWED_EXTENSIONS,
        MAX_BYTES,
    )

    job_id = str(uuid.uuid4())
    filename = Path(
        (file.filename or "ledger.xls")
        .replace("\\\\", "/")
    ).name

    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400, "Formato de planilha nao suportado."
        )

    safe_name = re.sub(
        r'[^A-Za-z0-9_.-]', '_', filename
    )[:120]

    saved_path = UPLOAD_DIR / (
        f"{job_id}_{safe_name}{suffix}"
    )

    mapped = any(
        value is not None
        for value in (
            header_row,
            column_mapping,
            mapping_fingerprint,
        )
    )

    import_config = None
    conn = None
    committed = False

    try:
        if mapped:
            if (
                header_row is None
                or not column_mapping
                or not mapping_fingerprint
            ):
                raise HTTPException(
                    400,
                    "Mapeamento ou confirmacao incompleta."
                )

            try:
                mapping = json.loads(column_mapping)

                if not isinstance(mapping, dict):
                    raise ValueError("Mapeamento invalido.")

                file.file.seek(0)

                validation = validate_upload_v5(
                    file, header_row, mapping
                )

            except HTTPException:
                raise

            except Exception as exc:
                raise HTTPException(
                    400,
                    "Mapeamento invalido: " + str(exc)
                ) from exc

            if not validation["valid"]:
                raise HTTPException(
                    422,
                    "Validacao contabil nao aprovada."
                )

            if (
                validation["mapping_fingerprint"]
                != mapping_fingerprint
            ):
                raise HTTPException(
                    409,
                    "Arquivo ou mapeamento alterado. "
                    "Valide novamente."
                )

            import_config = {
                "header_row": header_row,
                "mapping": mapping,
                "file_hash": validation["file_hash"],
                "mapping_fingerprint":
                    mapping_fingerprint,
            }

        file.file.seek(0)

        digest = hashlib.sha256()
        total = 0

        with saved_path.open("xb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)

                if not chunk:
                    break

                total += len(chunk)

                if total > MAX_BYTES:
                    raise HTTPException(
                        413, "Planilha acima de 50 MB."
                    )

                digest.update(chunk)
                buffer.write(chunk)

        if not total:
            raise HTTPException(400, "Planilha vazia.")

        if mapped:
            if (
                digest.hexdigest()
                != import_config["file_hash"]
            ):
                raise HTTPException(
                    409, "Arquivo alterado."
                )

            parse_result = parse_accounting_ledger(
                str(saved_path),
                header_row=header_row,
                column_mapping=mapping,
            )
        else:
            parse_result = parse_accounting_ledger(
                str(saved_path)
            )

        metadata = parse_result["metadata"]
        raw_transactions = parse_result["transactions"]
        
        # 2. Mathematical Audit
        math_audit = audit_accounting_balance(
            metadata["initial_balance"],
            metadata["final_reported_balance"],
            raw_transactions
        )
        
        if mapped and math_audit["status"] != "VALID":
            raise HTTPException(
                422,
                "A auditoria contabil final nao foi aprovada."
            )

        # 3. Reconciliation Engine
        reconcile_result = run_reconciliation(job_id, raw_transactions)
        transactions = reconcile_result["transactions"]
        reconciliations = reconcile_result["reconciliations"]
        summary = reconcile_result["summary"]
        
        # 4. Save into Database
        conn = get_connection()
        with conn:
            conn.execute("""
            INSERT INTO jobs (
                id, filename, file_path, created_at, company_name, cnpj, period, account_code,
                initial_balance, final_reported_balance, total_credits, total_debits,
                period_net_movement, status, math_validation_status, math_explanation, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                filename,
                str(saved_path),
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
                json.dumps(
                    {
                        "summary": summary,
                        "import_mapping_v5": import_config,
                    },
                    ensure_ascii=False
                )
            ))
            
            for t in transactions:
                conn.execute("""
                INSERT INTO transactions (
                    id, job_id, row_index, trans_date, history, trans_type, amount,
                    reported_balance, extracted_nf, extracted_supplier, cleaned_supplier,
                    category, status, matched_amount, remaining_amount, is_reversal, is_duplicate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["id"],
                    job_id,
                    t["row_index"],
                    t["trans_date"],
                    t["history"],
                    t["trans_type"],
                    str(t["amount"]),
                    str(t["reported_balance"]) if t["reported_balance"] is not None else None,
                    t["extracted_nf"],
                    t["extracted_supplier"],
                    t["cleaned_supplier"],
                    t["category"],
                    t["status"],
                    str(t["matched_amount"]),
                    str(t["remaining_amount"]),
                    t["is_reversal"],
                    t["is_duplicate"]
                ))
                
            for r in reconciliations:
                conn.execute("""
                INSERT INTO reconciliations (
                    id, job_id, match_type, invoice_trans_id, payment_trans_id, nf,
                    supplier, invoice_amount, payment_amount, reconciled_amount, difference,
                    confidence_score, status, match_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["id"],
                    job_id,
                    r["match_type"],
                    r["invoice_trans_id"],
                    r["payment_trans_id"],
                    r["nf"],
                    r["supplier"],
                    r["invoice_amount"],
                    r["payment_amount"],
                    r["reconciled_amount"],
                    r["difference"],
                    r["confidence_score"],
                    r["status"],
                    r["match_notes"],
                    r["created_at"]
                ))
                
            conn.execute("""
            INSERT INTO audit_logs (id, job_id, action, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                job_id,
                "INITIAL_PROCESSING",
                f"Processados {len(transactions)} lançamentos e {len(reconciliations)} conciliações.",
                datetime.now().isoformat()
            ))
        committed = True
        conn.close()
        conn = None
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Arquivo contábil processado e conciliado com sucesso!",
            "summary": summary,
            "math_audit": math_audit
        }
        
    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            400, str(exc)
        ) from exc

    except Exception as exc:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            500,
            "Nao foi possivel processar o documento."
        ) from exc

    finally:
        if conn is not None:
            conn.close()

        if not committed:
            saved_path.unlink(missing_ok=True)

@router.get("/jobs")
def list_jobs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    jobs = [dict(r) for r in rows]
    conn.close()
    return jobs

@router.get("/reconciliation/{job_id}/summary")
def get_job_summary(job_id: str):
    conn = get_connection()
    job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    job_data = dict(job_row)
    
    # Load summary & math audit
    math_explanation = json.loads(job_data["math_explanation"]) if job_data["math_explanation"] else {}
    meta = json.loads(job_data["metadata_json"]) if job_data["metadata_json"] else {}
    summary = refresh_live_summary(conn, job_id, meta.get("summary", {}))
    summary["composition_v3"] = current_composition(conn, job_data)

    # CONCILIA_V5_CLOSING_29E4
    from app.engine.closing_v5 import closing_summary_v5

    summary["closing_v5"] = closing_summary_v5(
        job_data, summary["composition_v3"]
    )

    
    # Get counts
    counts = conn.execute("""
    SELECT 
        status, COUNT(*) as cnt, SUM(CAST(amount AS REAL)) as total_amt
    FROM transactions 
    WHERE job_id = ?
    GROUP BY status
    """, (job_id,)).fetchall()
    
    # CONCILIA_V5_MONTHLY_29E3B
    from app.engine.monthly_v5 import monthly_evolution_v5
    monthly_evolution = monthly_evolution_v5(conn, job_id)
    status_distribution = [dict(c) for c in counts]
    
    conn.close()
    return {
        "job": job_data,
        "summary": summary,
        "math_audit": math_explanation,
        "status_distribution": status_distribution,
        "monthly_evolution": monthly_evolution
    }

@router.get("/reconciliation/{job_id}/transactions")
def get_transactions(
    job_id: str,
    trans_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_connection()
    query = "SELECT * FROM transactions WHERE job_id = ?"
    params = [job_id]
    
    if trans_type:
        query += " AND trans_type = ?"
        params.append(trans_type)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (extracted_nf LIKE ? OR extracted_supplier LIKE ? OR history LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
        
    query += " ORDER BY row_index ASC"
    rows = conn.execute(query, params).fetchall()
    items = [dict(r) for r in rows]
    conn.close()
    return items

@router.get("/reconciliation/{job_id}/reconciled")
def get_reconciled_pairs(job_id: str, match_type: Optional[str] = None):
    # CONCILIA_V5_REAL_STATUS
    conn = get_connection()

    try:
        query = """
            SELECT r.*,
                i.remaining_amount AS invoice_remaining,
                i.matched_amount AS invoice_total_matched,
                i.status AS invoice_status,
                p.remaining_amount AS payment_remaining,
                p.status AS payment_status
            FROM reconciliations r
            LEFT JOIN transactions i
                ON i.id = r.invoice_trans_id
                AND i.job_id = r.job_id
            LEFT JOIN transactions p
                ON p.id = r.payment_trans_id
                AND p.job_id = r.job_id
            WHERE r.job_id = ? AND r.status != 'UNDONE'
        """

        params = [job_id]

        if match_type:
            query += " AND r.match_type = ?"
            params.append(match_type)

        query += " ORDER BY r.nf ASC"

        items = []

        for row in conn.execute(query, params):

            item = dict(row)

            inv_rem = item.get("invoice_remaining")
            pay_rem = item.get("payment_remaining")

            if item["status"] != "CONFIRMED":
                status = {
                    "PENDING_REVIEW": "Pendente",
                    "REJECTED": "Rejeitado"
                }.get(item["status"], item["status"])

            elif item["match_type"] == "REVERSAL":
                status = "Estorno"

            elif item["match_type"] == "CENT_DIFFERENCE":
                status = "Divergencia de centavos"

            elif inv_rem is None or pay_rem is None:
                status = "Vinculo a revisar"

            elif (
                item.get("invoice_status") == "DIVERGENCIA_CENTAVOS"
                or item.get("payment_status") == "DIVERGENCIA_CENTAVOS"
            ):
                status = "Divergencia de centavos"

            elif money(inv_rem) > 0 or money(pay_rem) > 0:
                status = "Parcial"

            elif money(inv_rem) == 0 and money(pay_rem) == 0:
                status = "Quitado"

            else:
                status = "Revisar saldo"

            item["display_status"] = status

            original = money(item.get("invoice_amount"))
            accumulated = item.get("invoice_total_matched")

            item["paid_percentage"] = (
                round(float(money(accumulated) / original * 100), 2)
                if original > 0 and accumulated is not None
                else None
            )

            items.append(item)

        return items

    finally:
        conn.close()


@router.get("/reconciliation/{job_id}/open")
def get_open_invoices(job_id: str):
    from app.engine.reconciler import v5_reference
    conn = get_connection()
    rows = conn.execute("""
    SELECT * FROM transactions 
    WHERE job_id = ? AND trans_type = 'CREDIT' AND CAST(remaining_amount AS REAL) > 0
    ORDER BY trans_date ASC
    """, (job_id,)).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        if not d.get("extracted_nf") or str(d.get("extracted_nf")).strip() in ("S/N", "0", ""):
            ref = v5_reference(d)
            if ref and ref not in ("S/N", "0"):
                d["extracted_nf"] = ref
        items.append(d)
    conn.close()
    return items

@router.get("/reconciliation/{job_id}/divergences")
def get_divergences(job_id: str):
    from app.engine.reconciler import v5_reference
    conn = get_connection()
    # Cent differences and unmapped debits
    pairs = conn.execute("""
    SELECT * FROM reconciliations
    WHERE job_id = ? AND match_type IN ('CENT_DIFFERENCE', 'PARTIAL') AND status = 'CONFIRMED'
    ORDER BY nf ASC
    """, (job_id,)).fetchall()
    
    unmapped_debits = conn.execute("""
    SELECT * FROM transactions
    WHERE job_id = ? AND trans_type = 'DEBIT' AND CAST(remaining_amount AS REAL) > 0
    ORDER BY trans_date ASC
    """, (job_id,)).fetchall()
    
    debits = []
    for u in unmapped_debits:
        d = dict(u)
        if not d.get("extracted_nf") or str(d.get("extracted_nf")).strip() in ("S/N", "0", ""):
            ref = v5_reference(d)
            if ref and ref not in ("S/N", "0"):
                d["extracted_nf"] = ref
        debits.append(d)

    conn.close()
    return {
        "divergent_pairs": [dict(p) for p in pairs],
        "unmapped_debits": debits
    }

@router.get("/reconciliation/{job_id}/supplier-summary")
def get_supplier_summary(job_id: str):
    conn = get_connection()
    rows = conn.execute("""
    SELECT 
        extracted_supplier as supplier,
        SUM(CASE WHEN trans_type = 'CREDIT' THEN CAST(amount AS REAL) ELSE 0 END) as total_invoiced,
        SUM(CASE WHEN trans_type = 'DEBIT' THEN CAST(amount AS REAL) ELSE 0 END) as total_paid,
        SUM(CASE WHEN trans_type = 'CREDIT' THEN CAST(remaining_amount AS REAL) ELSE 0 END) as open_balance,
        COUNT(CASE WHEN trans_type = 'CREDIT' THEN 1 END) as invoices_count
    FROM transactions
    WHERE job_id = ?
    GROUP BY extracted_supplier
    ORDER BY open_balance DESC, total_invoiced DESC
    """, (job_id,)).fetchall()
    items = [dict(r) for r in rows]
    conn.close()
    return items

@router.post("/reconciliation/{job_id}/manual-match")
def manual_match(job_id: str, payload: ManualMatchRequest):
    from decimal import Decimal
    from fastapi import HTTPException
    from datetime import datetime
    import uuid
    import logging

    # CONCILIA_V5_MANUAL_SAFETY_30A3A
    from app.engine.manual_safety_v5 import (
        validate_manual_links_v5,
        validate_manual_composition_v5,
        validate_manual_transition_v5,
        validate_manual_result_v5,
    )

    def dec(value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01")
        )

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        job_row = conn.execute(
            "SELECT * FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not job_row:

            raise HTTPException(
                404, "Documento nao encontrado."
            )

        job = dict(job_row)

        inv_row = conn.execute(
            "SELECT * FROM transactions WHERE id=? AND job_id=?",
            (payload.invoice_trans_id, job_id)
        ).fetchone()

        pay_row = conn.execute(
            "SELECT * FROM transactions WHERE id=? AND job_id=?",
            (payload.payment_trans_id, job_id)
        ).fetchone()

        if not inv_row or not pay_row:
            raise HTTPException(
                404, "Lancamento nao encontrado."
            )

        inv = dict(inv_row)
        pay = dict(pay_row)

        if inv["trans_type"] != "CREDIT" or pay["trans_type"] != "DEBIT":
            raise HTTPException(
                400, "Selecione um credito e um debito."
            )

        if any(
            t.get("is_reversal") or t.get("is_duplicate")
            for t in (inv, pay)
        ):
            raise HTTPException(
                409, "Estorno ou duplicidade exige revisao."
            )

        try:

            invoice_before = validate_manual_links_v5(
                conn, job_id, inv
            )

            payment_before = validate_manual_links_v5(
                conn, job_id, pay
            )

            composition_before = current_composition(
                conn, job
            )

            validate_manual_composition_v5(
                composition_before
            )

        except ValueError as exc:

            raise HTTPException(409, str(exc))


        # CONCILIA_V5_STALE_APPROVAL_30A3C1
        from app.engine.manual_safety_v5 import (
            validate_expected_residuals_v5
        )

        try:

            validate_expected_residuals_v5(
                payload,
                inv["remaining_amount"],
                pay["remaining_amount"]
            )

        except ValueError as exc:

            raise HTTPException(409, str(exc))


        # CONCILIA_V5_SERVER_APPROVAL_30A3C3A
        from app.engine.manual_safety_v5 import (
            validate_suggestion_approval_v5
        )

        approval_metadata = None

        if payload.approval_source in (
            "SUGGESTION", "BATCH"
        ):

            current_transactions = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM transactions WHERE job_id=?",
                    (job_id,)
                )
            ]

            current_candidates = build_suggestions_v5(
                current_transactions
            )

            try:

                approval_metadata = (
                    validate_suggestion_approval_v5(
                        payload,
                        inv,
                        pay,
                        current_candidates
                    )
                )

            except ValueError as exc:

                raise HTTPException(409, str(exc))

        inv_rem = dec(inv["remaining_amount"])
        pay_rem = dec(pay["remaining_amount"])

        if inv_rem <= 0 or pay_rem <= 0:
            raise HTTPException(
                409, "Lancamento ja liquidado. Atualize a tela."
            )

        existing = conn.execute(
            """
            SELECT id FROM reconciliations
            WHERE job_id=?
            AND invoice_trans_id=?
            AND payment_trans_id=?
            AND status='CONFIRMED'
            """,
            (job_id, inv["id"], pay["id"])
        ).fetchone()

        if existing:
            raise HTTPException(
                409, "Esta baixa ja foi registrada."
            )

        matched = min(inv_rem, pay_rem)

        for t in (inv, pay):
            remaining = dec(t["remaining_amount"]) - matched
            accumulated = dec(t["matched_amount"]) + matched

            conn.execute(
                """
                UPDATE transactions
                SET matched_amount=?,
                    remaining_amount=?,
                    status=?
                WHERE id=? AND job_id=?
                """,
                (
                    str(accumulated),
                    str(remaining),
                    "CONCILIADO" if remaining == 0 else "PARCIAL",
                    t["id"],
                    job_id
                )
            )

        rec_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        from app.engine.reconciler import v5_reference
        from app.engine.extractor import extract_fallback_number

        match_nf = (
            v5_reference(inv)
            or v5_reference(pay)
            or extract_fallback_number(inv.get("history"))
            or extract_fallback_number(pay.get("history"))
            or inv.get("extracted_nf")
            or pay.get("extracted_nf")
            or "S/N"
        )

        conn.execute(
            """
            INSERT INTO reconciliations (
                id, job_id, match_type,
                invoice_trans_id, payment_trans_id,
                nf, supplier, invoice_amount,
                payment_amount, reconciled_amount,
                difference, confidence_score,
                status, match_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec_id,
                job_id,
                "MANUAL",
                inv["id"],
                pay["id"],
                match_nf,
                inv.get("extracted_supplier") or pay.get("extracted_supplier"),
                str(dec(inv["amount"])),
                str(dec(pay["amount"])),
                str(matched),
                str(inv_rem - pay_rem),
                1.0,
                "CONFIRMED",
                getattr(payload, "notes", None) or "Baixa aprovada pelo usuario.",
                now
            )
        )

        conn.execute(
            """
            UPDATE reconciliations
            SET status='REJECTED'
            WHERE job_id=?
            AND invoice_trans_id=?
            AND payment_trans_id=?
            AND status='PENDING_REVIEW'
            """,
            (job_id, inv["id"], pay["id"])
        )


        import json

        approval_audit = {
            "reconciliation_id": rec_id,
            "invoice_trans_id": inv["id"],
            "payment_trans_id": pay["id"],
            "amount": str(matched),
            "invoice_remaining_before": str(inv_rem),
            "payment_remaining_before": str(pay_rem),
            "invoice_remaining_after": str(inv_rem - matched),
            "payment_remaining_after": str(pay_rem - matched),
            "approval_source": payload.approval_source,
            # CONCILIA_V5_STRICT_APPROVAL_30A3C4D
            "review_confirmed": payload.confirm_review,
            "expected_invoice_remaining": payload.expected_invoice_remaining,
            "expected_payment_remaining": payload.expected_payment_remaining,
            "approval_metadata": approval_metadata,
            "notes": payload.notes
        }

        conn.execute(
            """
            INSERT INTO audit_logs (
                id, job_id, action, details, timestamp
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                job_id,
                "MANUAL_MATCH",
                json.dumps(approval_audit, ensure_ascii=False),
                now
            )
        )

        try:

            invoice_after = dict(conn.execute(
                "SELECT * FROM transactions WHERE id=? AND job_id=?",
                (inv["id"], job_id)
            ).fetchone())

            payment_after = dict(conn.execute(
                "SELECT * FROM transactions WHERE id=? AND job_id=?",
                (pay["id"], job_id)
            ).fetchone())

            validate_manual_result_v5(
                invoice_before,
                invoice_after,
                matched
            )

            validate_manual_result_v5(
                payment_before,
                payment_after,
                matched
            )

            composition_after = current_composition(
                conn, job
            )

            validate_manual_transition_v5(
                composition_before,
                composition_after
            )

        except ValueError as exc:

            raise HTTPException(409, str(exc))

        conn.commit()

        return {
            "success": True,
            "reconciliation_id": rec_id,
            "reconciled_amount": str(matched),
            "invoice_remaining": str(inv_rem - matched),
            "payment_remaining": str(pay_rem - matched),
            "refresh_required": True
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception:
        conn.rollback()
        logging.exception("Falha na conciliacao manual V5")
        raise HTTPException(
            500,
            "Nao foi possivel concluir a baixa. Nenhum valor foi alterado."
        )

    finally:
        conn.close()


@router.get("/reconciliation/{job_id}/export/excel")
def export_excel(job_id: str):

    # CONCILIA_V5_FULL_EXCEL_ROUTE_25G

    import logging
    import re
    import unicodedata

    from fastapi.responses import Response

    from app.engine.full_snapshot_v5 import (
        collect_full_snapshot_v5,
    )

    from app.engine.full_workbook_v5 import (
        build_full_workbook_v5,
    )

    logger = logging.getLogger(__name__)

    conn = None
    output = None

    try:

        conn = get_connection()

        try:

            sheets = collect_full_snapshot_v5(
                conn, job_id
            )

        except LookupError as exc:

            raise HTTPException(
                status_code=404,
                detail="Documento inexistente."
            ) from exc

        finally:

            conn.close()
            conn = None

        report = sheets["Resumo gerencial"][0]

        company = str(
            report.get("Empresa") or "Relatorio"
        )

        company = unicodedata.normalize(
            "NFKD", company
        ).encode(
            "ascii", "ignore"
        ).decode("ascii")

        company = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            company
        ).strip("_-")[:40]

        if not company:

            company = "Relatorio"

        safe_id = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            str(job_id)
        )[:12]

        filename = (
            f"CONCILIA_AI_V5_{company}_"
            f"{safe_id}.xlsx"
        )

        output = build_full_workbook_v5(
            sheets
        )

        content = output.getvalue()

        if not content.startswith(b"PK"):
            raise RuntimeError(
                "Arquivo Excel invalido."
            )

        return Response(
            content=content,
            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"',

                "Cache-Control":
                    "no-store, no-cache, must-revalidate",

                "Pragma":
                    "no-cache",

                "X-Content-Type-Options":
                    "nosniff",
            }
        )

    except HTTPException:

        raise

    except Exception as exc:

        logger.exception(
            "Falha na exportacao Excel V5. "
            "Documento: %s",
            job_id
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Nao foi possivel gerar o Excel completo. "
                "Consulte o log do sistema."
            )
        ) from exc

    finally:

        if output is not None:
            output.close()

        if conn is not None:
            conn.close()

@router.get("/reconciliation/{job_id}/export/pdf")
def export_pdf(job_id: str):

    # CONCILIA_V5_FULL_PDF_ROUTE_26_TURBO

    import logging
    import re
    import unicodedata

    from fastapi.responses import Response

    from app.engine.full_snapshot_v5 import (
        collect_full_snapshot_v5,
    )

    from app.engine.full_pdf_v5 import (
        build_full_pdf_v5,
    )

    logger = logging.getLogger(__name__)

    conn = None
    output = None

    try:

        conn = get_connection()

        try:

            sheets = collect_full_snapshot_v5(
                conn, job_id
            )

        except LookupError as exc:

            raise HTTPException(
                status_code=404,
                detail="Documento inexistente."
            ) from exc

        finally:

            conn.close()
            conn = None

        report = sheets["Resumo gerencial"][0]

        company = str(
            report.get("Empresa") or "Relatorio"
        )

        company = unicodedata.normalize(
            "NFKD", company
        ).encode(
            "ascii", "ignore"
        ).decode("ascii")

        company = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            company,
        ).strip("_-")[:40]

        company = company or "Relatorio"

        safe_id = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            str(job_id),
        )[:12]

        filename = (
            f"CONCILIA_AI_V5_{company}_{safe_id}.pdf"
        )

        output = build_full_pdf_v5(sheets)

        return Response(
            content=output.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"',

                "Cache-Control":
                    "no-store, no-cache, must-revalidate",

                "Pragma": "no-cache",

                "X-Content-Type-Options": "nosniff",
            }
        )

    except HTTPException:

        raise

    except Exception as exc:

        logger.exception(
            "Falha na exportacao PDF V5: %s",
            job_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Nao foi possivel gerar o PDF completo. "
                "Consulte o log do sistema."
            )
        ) from exc

    finally:

        if output is not None:
            output.close()

        if conn is not None:
            conn.close()


# CONCILIA AI V2 - History management
@router.delete("/history")
def delete_history_v2():
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM jobs")
        return {"success": True}
    finally:
        conn.close()


@router.delete("/history/{job_id}")
def delete_history_job_v2(job_id: str):
    conn = get_connection()
    try:
        with conn:
            result = conn.execute(
                "DELETE FROM jobs WHERE id = ?", (job_id,)
            )
            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Documento nao encontrado."
                )
        return {"success": True}
    finally:
        conn.close()

@router.post("/reconciliation/{job_id}/opening")
async def attach_opening(job_id: str, file: UploadFile = File(...)):
    from app.operations_security_v5 import validate_uploaded_file_v5
    validate_uploaded_file_v5(file, allowed={".xls", ".xlsx"})
    from app.engine.opening_import import read_opening
    from pathlib import Path
    import tempfile
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ('.xls','.xlsx'):
        raise HTTPException(400, "Use XLS ou XLSX")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/('opening'+suffix)
            path.write_bytes(await file.read())
            rows = read_opening(str(path), None)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"Erro ao importar planilha de saldo anterior: {exc}", exc_info=True)
        raise HTTPException(400, f"Planilha complementar invalida: {exc}") from exc
    conn=get_connection()
    try:
        job=conn.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not job: raise HTTPException(404,'Documento inexistente')
        # Preserve the original ledger balance; incomplete detail is shown separately.
        if not money(job['initial_balance']):
            raise HTTPException(400,'O documento nao possui saldo anterior.')
        with conn:
            conn.execute("BEGIN IMMEDIATE")

            from app.engine.opening_storage_v5 import (
                ensure_opening_storage
            )

            ensure_opening_storage(conn)

            if conn.execute(
                "SELECT 1 FROM opening_matches_v5 WHERE job_id=? LIMIT 1",
                (job_id,)
            ).fetchone():
                raise HTTPException(
                    409,
                    "Existem baixas do saldo anterior. "
                    "A substituicao da planilha foi bloqueada."
                )
            conn.execute('INSERT OR REPLACE INTO opening_compositions VALUES (?,?)',(job_id,json.dumps(rows,ensure_ascii=False)))
        return {'success':True}
    finally: conn.close()

@router.get('/reconciliation/{job_id}/export/tab/{tab}')
def export_tab(job_id: str, tab: str):
    from app.engine.tab_export import make_workbook
    from fastapi.responses import StreamingResponse
    conn=get_connection()
    try:
        job=conn.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not job: raise HTTPException(404,'Documento inexistente')
        job=dict(job)
    finally: conn.close()
    if tab=='dashboard':
        data=get_job_summary(job_id)
        summary=data['summary']
        sheets={'Resumo':[{'Empresa':job['company_name'],'Periodo':job['period'],'Saldo anterior':job['initial_balance'],'Debitos':job['total_debits'],'Creditos':job['total_credits'],'Saldo final':job['final_reported_balance'],**{k:v for k,v in summary.items() if not isinstance(v,(dict,list))}}], 'Evolucao mensal':data['monthly_evolution'],'Status':data['status_distribution']}
    elif tab=='composition':
        c=get_job_summary(job_id)['summary']['composition_v3']
        sheets={
            'Resumo': [{k:v for k,v in c.items()
                        if k not in ('rows','payment_details')}],
            'Composicao': c['rows'],
            'Detalhamento das Baixas': c['payment_details']
        }
    elif tab=='reconciled': sheets={'Conciliados':get_reconciled_pairs(job_id)}
    elif tab=='open': sheets={'Notas em aberto':get_open_invoices(job_id)}
    elif tab=='divergences':
        d=get_divergences(job_id); sheets={'Divergencias':d['divergent_pairs'],'Debitos sem provisao':d['unmapped_debits']}
    elif tab=='manual': sheets={'Notas pendentes':get_open_invoices(job_id),'Pagamentos pendentes':get_divergences(job_id)['unmapped_debits']}

    # CONCILIA_V5_SUGGESTION_EXPORT_24B
    elif tab == 'suggestions':
        from app.engine.suggestion_export_v5 import (
            suggestion_sheets_v5
        )

        read_conn = get_connection()

        try:
            read_conn.execute("PRAGMA query_only=ON")
            read_conn.execute("BEGIN")

            current_job = read_conn.execute(
                "SELECT * FROM jobs WHERE id=?",
                (job_id,)
            ).fetchone()

            if not current_job:
                raise HTTPException(
                    404, "Documento inexistente."
                )

            transactions = [
                dict(r) for r in read_conn.execute(
                    "SELECT * FROM transactions WHERE job_id=?",
                    (job_id,)
                )
            ]

            items = build_suggestions_v5(transactions)

            sheets = suggestion_sheets_v5(
                dict(current_job), items
            )
            # CONCILIA_V5_FINANCIAL_EXPORT_25C
            from app.engine.suggestion_financial_v5 import enrich_current_sheets
            sheets = enrich_current_sheets(
                sheets,
                transactions
            )

        finally:
            read_conn.close()


    # CONCILIA_V5_OPENING_EXPORT_24C
    elif tab == 'opening-suggestions':
        from app.engine.opening_export_v5 import (
            opening_sheets_v5
        )
        from app.engine.opening_storage_v5 import (
            opening_state,
            opening_suggestions
        )

        read_conn = get_connection()

        try:
            read_conn.execute("PRAGMA query_only=ON")
            read_conn.execute("BEGIN")

            current_job = read_conn.execute(
                "SELECT * FROM jobs WHERE id=?",
                (job_id,)
            ).fetchone()

            if not current_job:
                raise HTTPException(
                    404, "Documento inexistente."
                )

            current_job = dict(current_job)

            original, rows, links = opening_state(
                read_conn, job_id
            )

            items = opening_suggestions(
                read_conn, job_id
            ) if original is not None else []

            c = current_composition(
                read_conn, current_job
            )

            sheets = opening_sheets_v5(
                current_job,
                original,
                rows,
                links,
                items,
                c
            )
            # CONCILIA_V5_FINANCIAL_EXPORT_25C
            from app.engine.suggestion_financial_v5 import enrich_opening_sheets
            financial_tx_v5 = [
                dict(r) for r in read_conn.execute(
                    "SELECT * FROM transactions WHERE job_id=?",
                    (current_job["id"],)
                )
            ]
            sheets = enrich_opening_sheets(
                sheets,
                rows,
                financial_tx_v5
            )

        finally:
            read_conn.close()

    elif tab=='suppliers': sheets={'Fornecedores':get_supplier_summary(job_id)}
    elif tab=='history': sheets={'Historico':[{k:j.get(k) for k in ('filename','company_name','cnpj','period','created_at','status','initial_balance','final_reported_balance')} for j in list_jobs()]}
    else: raise HTTPException(400,'Aba desconhecida')
    return StreamingResponse(make_workbook(sheets),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f'attachment; filename="ConciliaAI_{tab}_{job_id[:8]}.xlsx"'})



# CONCILIA_V5_SUGGESTIONS

def build_suggestions_v5(transactions):
    from app.engine.reconciler import (
        v5_reference,
        v5_supplier_match,
        v5_fiscal_equivalent
    )
    from collections import Counter

    # CONCILIA_V5_SERVER_APPROVAL_30A3C3A
    from app.engine.reconciler import v5_has_reversal_marker

    active = [
        t for t in transactions
        if money(t["remaining_amount"]) > 0
        and not t.get("is_duplicate")
        and not t.get("is_reversal")
        and not v5_has_reversal_marker(t)
        and t.get("status") not in (
            "DIVERGENCIA_CENTAVOS",
            "CENT_DIFFERENCE"
        )
    ]

    credits = [
        t for t in active
        if t["trans_type"] == "CREDIT"
    ]

    debits = [
        t for t in active
        if t["trans_type"] == "DEBIT"
    ]

    # Pre-computa metadados de créditos
    from app.engine.extractor import extract_fallback_number
    from app.engine.reconciler import v5_extended_alias

    credit_meta = []
    for inv in credits:
        a = money(inv["remaining_amount"])
        nf1 = v5_reference(inv)
        if not nf1 or nf1 in ("S/N", "0"):
            fb1 = extract_fallback_number(inv.get("history"))
            if fb1:
                nf1 = fb1
        year_c = str(inv.get("trans_date") or "")[:4]
        alias1 = v5_extended_alias(nf1, year_c)
        credit_meta.append((inv, a, nf1, alias1))

    # Indexa débitos por valor e por NF para busca O(1) instantânea
    debits_by_amount = {}
    debits_by_nf = {}
    for pay in debits:
        b = money(pay["remaining_amount"])
        nf2 = v5_reference(pay)
        if not nf2 or nf2 in ("S/N", "0"):
            fb2 = extract_fallback_number(pay.get("history"))
            if fb2:
                nf2 = fb2
        year_d = str(pay.get("trans_date") or "")[:4]
        alias2 = v5_extended_alias(nf2, year_d)

        entry = (pay, b, nf2, alias2)
        debits_by_amount.setdefault(b, []).append(entry)
        if nf2 and nf2 not in ("S/N", "0"):
            debits_by_nf.setdefault(nf2, []).append(entry)
        if alias2:
            debits_by_nf.setdefault(alias2, []).append(entry)

    suggestions = []

    for inv, a, nf1, alias1 in credit_meta:
        # Busca apenas débitos candidatos relevantes (mesmo valor, mesma NF ou alias fiscal)
        candidates_seen = set()
        candidates = []

        for entry in debits_by_amount.get(a, []):
            p = entry[0]
            if p["id"] not in candidates_seen:
                candidates_seen.add(p["id"])
                candidates.append(entry)

        if nf1 and nf1 not in ("S/N", "0"):
            for entry in debits_by_nf.get(nf1, []):
                p = entry[0]
                if p["id"] not in candidates_seen:
                    candidates_seen.add(p["id"])
                    candidates.append(entry)

        if alias1:
            for entry in debits_by_nf.get(alias1, []):
                p = entry[0]
                if p["id"] not in candidates_seen:
                    candidates_seen.add(p["id"])
                    candidates.append(entry)

        for pay, b, nf2, alias2 in candidates:
            same_nf = bool(nf1 and nf2 and nf1 == nf2)
            different_nf = bool(nf1 and nf2 and nf1 != nf2)
            same_supplier = v5_supplier_match(inv, pay)
            same_value = a == b

            # CONCILIA_V5_FISCAL_SUGGESTIONS_30A2B
            fiscal_equivalent = (
                different_nf
                and same_supplier
                and v5_fiscal_equivalent(inv, pay)
            )

            if same_value and same_nf:
                score = 100
                reason = "Mesma NF e mesmo valor"
                category = "COMPATIVEL"

            elif fiscal_equivalent:
                score = 95 if same_value else 90

                reason = (
                    "Possivel equivalencia de numeracao fiscal; "
                    "fornecedor compativel; "
                    + (
                        "valor identico"
                        if same_value
                        else "valores diferentes, possivel baixa parcial"
                    )
                    + ". Exige aprovacao individual."
                )

                category = "DIVERGENCIA_NF"

            elif same_value and different_nf:
                score = 85 if same_supplier else 60
                reason = "Valores iguais com NFs diferentes"
                category = "DIVERGENCIA_NF"

            elif same_value and same_supplier:
                score = 95
                reason = "Mesmo fornecedor e valor"
                category = "COMPATIVEL"

            elif same_nf:
                score = 90
                reason = "Mesma NF com possibilidade de baixa parcial"
                category = "PARCIAL"

            elif same_value:
                score = 40
                reason = "Mesmo valor sem outra evidencia"
                category = "BAIXA_EVIDENCIA"

            else:
                continue

            suggestions.append({
                "id": inv["id"] + ":" + pay["id"],
                "invoice_trans_id": inv["id"],
                "payment_trans_id": pay["id"],
                "invoice_nf": nf1 or "S/N",
                "payment_nf": nf2 or "S/N",
                "invoice_supplier": inv.get("extracted_supplier"),
                "payment_supplier": pay.get("extracted_supplier"),
                "invoice_date": inv.get("trans_date"),
                "payment_date": pay.get("trans_date"),
                "invoice_history": inv.get("history"),
                "payment_history": pay.get("history"),
                "invoice_remaining": str(a),
                "payment_remaining": str(b),
                "suggested_amount": str(min(a,b)),
                "invoice_after": str(a-min(a,b)),
                "payment_after": str(b-min(a,b)),
                "score": score,
                "reason": reason,
                "category": category,
                "fiscal_equivalent": bool(fiscal_equivalent),
                "requires_individual_review": (
                    category != "COMPATIVEL"
                )
            })

    inv_counts = Counter(
        s["invoice_trans_id"] for s in suggestions
    )

    pay_counts = Counter(
        s["payment_trans_id"] for s in suggestions
    )

    for s in suggestions:
        s["ambiguous"] = (
            inv_counts[s["invoice_trans_id"]] > 1
            or pay_counts[s["payment_trans_id"]] > 1
        )

        s["batch_eligible"] = (
            not s["ambiguous"]
            and s["category"] == "COMPATIVEL"
            and not s["requires_individual_review"]
            and not s["fiscal_equivalent"]
            and s["score"] >= 95
        )

    for s in suggestions:
        if s["ambiguous"]:
            s["requires_individual_review"] = True

    return sorted(
        suggestions,
        key=lambda s: (
            -s["score"],
            s["ambiguous"],
            s["invoice_date"] or "",
            s["id"]
        )
    )


@router.get("/reconciliation/{job_id}/suggestions")
def get_suggestions_v5(job_id: str):
    conn = get_connection()

    try:
        job = conn.execute(
            "SELECT id FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not job:
            raise HTTPException(404, "Documento inexistente.")

        transactions = [
            dict(r) for r in conn.execute(
                "SELECT * FROM transactions WHERE job_id=?",
                (job_id,)
            )
        ]

        items = build_suggestions_v5(transactions)

        return {
            "items": items,
            "total": len(items),
            "compatible": sum(
                s["category"] == "COMPATIVEL"
                for s in items
            ),
            "divergences": sum(
                s["category"] == "DIVERGENCIA_NF"
                for s in items
            ),
            "partial": sum(
                s["category"] == "PARCIAL"
                for s in items
            ),
            "ambiguous": sum(
                s["ambiguous"] for s in items
            ),
            "batch_eligible": sum(
                s["batch_eligible"] for s in items
            )
        }

    finally:
        conn.close()



# CONCILIA_V5_OPENING_API

from pydantic import BaseModel, Field
from decimal import Decimal


class OpeningApprovalV5(BaseModel):

    opening_index: int = Field(ge=0)
    payment_trans_id: str
    opening_hash: str
    expected_opening: Decimal = Field(gt=0)
    expected_payment: Decimal = Field(gt=0)
    confirm_review: StrictBool = False


@router.get("/reconciliation/{job_id}/opening-suggestions")
def get_opening_suggestions_v5(job_id: str):

    from app.engine.opening_storage_v5 import (
        opening_suggestions,
        opening_state
    )

    conn = get_connection()

    try:

        conn.execute("BEGIN")

        job = conn.execute(
            "SELECT * FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not job:
            raise HTTPException(
                404, "Documento inexistente."
            )

        original, rows, links = opening_state(
            conn, job_id
        )

        items = opening_suggestions(
            conn, job_id
        )

        return {
            "opening_attached": original is not None,
            "items": items,
            "total": len(items),
            "eligible": sum(
                s["automatic_eligible"] for s in items
            ),
            "ambiguous": sum(
                s["ambiguous"] for s in items
            ),
            "partial": sum(
                s["category"] == "PARCIAL" for s in items
            ),
            "approved_count": len(links),
            "approved_amount": str(sum(
                (money(r["amount"]) for r in links),
                Decimal("0.00")
            )),
            "opening_rows": rows
        }

    except ValueError as exc:

        raise HTTPException(409, str(exc))

    finally:

        conn.close()


@router.post("/reconciliation/{job_id}/opening-approve")
def approve_opening_v5(
    job_id: str,
    payload: OpeningApprovalV5
):

    import logging

    from app.engine.opening_storage_v5 import (
        register_opening_match
    )

    conn = get_connection()

    try:

        conn.execute("BEGIN IMMEDIATE")

        job = conn.execute(
            "SELECT * FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not job:

            raise HTTPException(
                404, "Documento inexistente."
            )

        before = current_composition(
            conn, dict(job)
        )

        if not before["valid"]:

            raise HTTPException(
                409,
                "Composicao inconsistente antes da baixa."
            )

        result = register_opening_match(
            conn,
            job_id,
            payload.opening_index,
            payload.payment_trans_id,
            payload.opening_hash,
            payload.expected_opening,
            payload.expected_payment,
            allow_review=payload.confirm_review
        )

        after = current_composition(
            conn, dict(job)
        )

        if (
            not after["valid"]
            or money(before["total"]) != money(after["total"])
            or money(before["opening_difference"])
                != money(after["opening_difference"])
        ):

            raise HTTPException(
                409,
                "Baixa bloqueada por inconsistencia contabil."
            )

        conn.commit()

        return {
            **result,
            "composition_total": after["total"],
            "composition_difference": after["difference"],
            "opening_difference": after["opening_difference"],
            "refresh_required": True
        }

    except HTTPException:

        conn.rollback()
        raise

    except ValueError as exc:

        conn.rollback()
        raise HTTPException(409, str(exc))

    except Exception:

        conn.rollback()

        logging.exception(
            "Falha na aprovacao do saldo anterior"
        )

        raise HTTPException(
            500,
            "Nao foi possivel registrar a baixa. "
            "Nenhum valor foi alterado."
        )

    finally:

        conn.close()



# CONCILIA_V5_UNDO_API

from typing import Literal
from pydantic import BaseModel, Field


class UndoMatchV5Request(BaseModel):

    match_id: str = Field(min_length=1)
    origin: Literal["CURRENT", "OPENING"]
    reason: str = Field(min_length=3, max_length=1000)
    confirm: StrictBool = False


@router.post("/reconciliation/{job_id}/undo-match")
def undo_match_v5(job_id: str, payload: UndoMatchV5Request):

    import logging

    from app.engine.undo_v5 import undo_match

    if not payload.confirm:
        raise HTTPException(
            400,
            "Confirme expressamente o desfazimento."
        )

    if len(payload.reason.strip()) < 3:
        raise HTTPException(
            400,
            "Informe o motivo do desfazimento."
        )

    conn = get_connection()

    try:

        conn.execute("BEGIN IMMEDIATE")

        job = conn.execute(
            "SELECT * FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not job:
            raise HTTPException(
                404,
                "Documento inexistente."
            )

        before = current_composition(
            conn, dict(job)
        )

        if not before["valid"]:
            raise HTTPException(
                409,
                "Composicao inconsistente antes do desfazimento."
            )

        result = undo_match(
            conn,
            job_id,
            payload.match_id,
            payload.origin,
            payload.reason
        )

        after = current_composition(
            conn, dict(job)
        )

        if not after["valid"]:
            raise HTTPException(
                409,
                "Desfazimento bloqueado: composicao divergente."
            )

        if money(before["total"]) != money(after["total"]):
            raise HTTPException(
                409,
                "Desfazimento alteraria o saldo contabil."
            )

        if (
            money(before["opening_difference"])
            != money(after["opening_difference"])
        ):
            raise HTTPException(
                409,
                "Diferenca do saldo anterior alterada."
            )

        if conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchone():

            raise HTTPException(
                409,
                "Inconsistencia nos vinculos do banco."
            )

        conn.commit()

        return {
            **result,
            "composition_total": after["total"],
            "composition_difference": after["difference"],
            "opening_difference": after["opening_difference"],
            "composition_valid": after["valid"],
            "refresh_required": True
        }

    except HTTPException:

        conn.rollback()
        raise

    except ValueError as exc:

        conn.rollback()

        raise HTTPException(
            409,
            str(exc)
        )

    except Exception:

        conn.rollback()

        logging.exception(
            "Falha no desfazimento V5"
        )

        raise HTTPException(
            500,
            "Nao foi possivel desfazer a baixa. "
            "A operacao nao foi confirmada."
        )

    finally:

        conn.close()


@router.get("/reconciliation/{job_id}/undo-history")
def get_undo_history_v5(job_id: str):

    import json

    conn = get_connection()

    try:

        job = conn.execute(
            "SELECT id FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if not job:
            raise HTTPException(
                404,
                "Documento inexistente."
            )

        items = []

        for row in conn.execute(
            """
            SELECT id, action, details, timestamp
            FROM audit_logs
            WHERE job_id=?
            AND action='UNDO_MATCH_V5'
            ORDER BY timestamp DESC, id DESC
            """,
            (job_id,)
        ):

            item = dict(row)

            try:
                item["details"] = json.loads(
                    item["details"]
                )
            except (TypeError, ValueError):
                pass

            items.append(item)

        return {
            "total": len(items),
            "items": items
        }

    finally:

        conn.close()



# CONCILIA_V5_IMPORT_PREVIEW_API_29D31

@router.post("/import/preview")
def import_preview_v5(
    file: UploadFile = File(...),
    header_row: Optional[int] = Form(None)
):
    from app.operations_security_v5 import validate_uploaded_file_v5
    validate_uploaded_file_v5(file)
    from app.engine.import_preview_v5 import (
        preview_upload_v5
    )

    try:
        return preview_upload_v5(
            file, header_row
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    finally:
        file.file.close()


@router.post("/import/validate")
def import_validate_v5(
    file: UploadFile = File(...),
    header_row: int = Form(...),
    mapping_json: str = Form(...)
):
    from app.operations_security_v5 import validate_uploaded_file_v5
    validate_uploaded_file_v5(file)
    from app.engine.import_preview_v5 import (
        validate_upload_v5
    )

    try:
        mapping = json.loads(mapping_json)

        if not isinstance(mapping, dict):
            raise ValueError("Mapeamento invalido.")

        return validate_upload_v5(
            file, header_row, mapping
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    finally:
        file.file.close()

