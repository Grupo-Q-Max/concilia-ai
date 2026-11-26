
import json
import uuid

from decimal import Decimal
from datetime import datetime
from app.engine.composition import money
from app.engine.opening_storage_v5 import opening_state


SAFE_TYPES = {
    "MANUAL",
    "EXACT_1_TO_1",
    "PARTIAL"
}


def get_transaction(conn, job_id, trans_id):

    row = conn.execute(
        "SELECT * FROM transactions WHERE job_id=? AND id=?",
        (job_id, trans_id)
    ).fetchone()

    if not row:
        raise ValueError("Lancamento original nao localizado.")

    return dict(row)


def validate_transaction(conn, job_id, t):

    if t.get("is_duplicate") or t.get("is_reversal"):
        raise ValueError("Duplicidade ou estorno exige revisao.")

    if t["status"] not in (
        "CONCILIADO", "PARCIAL", "EM_ABERTO", "SEM_PROVISAO"
    ):
        raise ValueError("Status do lancamento exige revisao.")

    original = money(t["amount"])
    matched = money(t["matched_amount"])
    remaining = money(t["remaining_amount"])

    if min(original, matched, remaining) < 0:
        raise ValueError("Valores negativos inconsistentes.")

    if matched + remaining != original:
        raise ValueError("Saldo do lancamento inconsistente.")

    recs = [
        dict(r) for r in conn.execute(
            """
            SELECT * FROM reconciliations
            WHERE job_id=? AND status='CONFIRMED'
            AND (invoice_trans_id=? OR payment_trans_id=?)
            """,
            (job_id, t["id"], t["id"])
        )
    ]

    total = Decimal("0.00")

    for r in recs:

        if r["match_type"] not in SAFE_TYPES:
            raise ValueError(
                "Existe baixa agrupada, estorno ou divergencia vinculada."
            )

        if not r["invoice_trans_id"] or not r["payment_trans_id"]:
            raise ValueError("Vinculo incompleto.")

        field = (
            "invoice_trans_id"
            if t["trans_type"] == "CREDIT"
            else "payment_trans_id"
        )

        if r[field] != t["id"]:
            raise ValueError("Natureza do vinculo inconsistente.")

        amount = money(r["reconciled_amount"])

        if amount <= 0:
            raise ValueError("Valor de baixa inconsistente.")

        total += amount

    opening_links = conn.execute(
        """
        SELECT amount FROM opening_matches_v5
        WHERE job_id=? AND payment_trans_id=?
        """,
        (job_id, t["id"])
    ).fetchall()

    for link in opening_links:

        if t["trans_type"] != "DEBIT":
            raise ValueError("Vinculo anterior inconsistente.")

        amount = money(link["amount"])

        if amount <= 0:
            raise ValueError("Baixa anterior inconsistente.")

        total += amount

    if total != matched:
        raise ValueError(
            "Total das baixas nao corresponde ao valor conciliado."
        )


def restore_transaction(conn, job_id, t, amount):

    matched = money(t["matched_amount"]) - amount
    remaining = money(t["remaining_amount"]) + amount
    original = money(t["amount"])

    if matched < 0 or remaining > original:
        raise ValueError("Desfazimento excede o saldo original.")

    if matched + remaining != original:
        raise ValueError("Saldo restaurado inconsistente.")

    if matched > 0:
        status = "PARCIAL"
    elif t["trans_type"] == "CREDIT":
        status = "EM_ABERTO"
    else:
        status = "SEM_PROVISAO"

    conn.execute(
        """
        UPDATE transactions
        SET matched_amount=?, remaining_amount=?, status=?
        WHERE id=? AND job_id=?
        """,
        (
            str(matched),
            str(remaining),
            status,
            t["id"],
            job_id
        )
    )

    return {
        "transaction_id": t["id"],
        "matched_amount": str(matched),
        "remaining_amount": str(remaining),
        "status": status
    }


def undo_match(conn, job_id, match_id, origin, reason):

    # Caller must own BEGIN IMMEDIATE and commit or rollback.

    if not conn.in_transaction:
        raise ValueError("Operacao exige transacao ativa.")

    reason = str(reason or "").strip()

    if not reason:
        raise ValueError("Informe o motivo do desfazimento.")

    if origin not in ("CURRENT", "OPENING"):
        raise ValueError("Origem da baixa invalida.")

    original, opening_rows, opening_links = opening_state(
        conn, job_id
    )

    restored = []
    opening_remaining = None

    if origin == "CURRENT":

        row = conn.execute(
            """
            SELECT * FROM reconciliations
            WHERE job_id=? AND id=?
            """,
            (job_id, match_id)
        ).fetchone()

        if not row:
            raise ValueError("Conciliacao nao localizada.")

        record = dict(row)

        if record["status"] != "CONFIRMED":
            raise ValueError("Baixa nao esta ativa ou ja foi desfeita.")

        if record["match_type"] not in SAFE_TYPES:
            raise ValueError(
                "Modalidade exige revisao especifica."
            )

        inv = get_transaction(
            conn, job_id, record["invoice_trans_id"]
        )

        pay = get_transaction(
            conn, job_id, record["payment_trans_id"]
        )

        if inv["trans_type"] != "CREDIT":
            raise ValueError("Credito invalido.")

        if pay["trans_type"] != "DEBIT":
            raise ValueError("Debito invalido.")

        validate_transaction(conn, job_id, inv)
        validate_transaction(conn, job_id, pay)

        amount = money(record["reconciled_amount"])

        if amount <= 0:
            raise ValueError("Valor de baixa invalido.")

        restored.append(
            restore_transaction(conn, job_id, inv, amount)
        )

        restored.append(
            restore_transaction(conn, job_id, pay, amount)
        )

        conn.execute(
            """
            UPDATE reconciliations SET status='UNDONE'
            WHERE job_id=? AND id=? AND status='CONFIRMED'
            """,
            (job_id, match_id)
        )

    else:

        record = next(
            (r for r in opening_links if r["id"] == match_id),
            None
        )

        if record is None:
            raise ValueError(
                "Baixa anterior inexistente ou ja desfeita."
            )

        pay = get_transaction(
            conn, job_id, record["payment_trans_id"]
        )

        if pay["trans_type"] != "DEBIT":
            raise ValueError("Pagamento invalido.")

        validate_transaction(conn, job_id, pay)

        amount = money(record["amount"])

        if amount <= 0:
            raise ValueError("Valor de baixa invalido.")

        restored.append(
            restore_transaction(conn, job_id, pay, amount)
        )

        conn.execute(
            """
            DELETE FROM opening_matches_v5
            WHERE job_id=? AND id=?
            """,
            (job_id, match_id)
        )

        _, rows_after, _ = opening_state(conn, job_id)

        opening_remaining = rows_after[
            record["opening_index"]
        ]["remaining_amount"]

    for item in restored:

        current = get_transaction(
            conn, job_id, item["transaction_id"]
        )

        validate_transaction(conn, job_id, current)

    audit_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO audit_logs (
            id, job_id, action, details, timestamp
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            job_id,
            "UNDO_MATCH_V5",
            json.dumps({
                "match_id": match_id,
                "origin": origin,
                "reason": reason,
                "amount": str(amount),
                "original_record": record,
                "restored_transactions": restored,
                "opening_remaining": opening_remaining
            }, ensure_ascii=False),
            datetime.now().isoformat()
        )
    )

    return {
        "success": True,
        "match_id": match_id,
        "origin": origin,
        "restored_amount": str(amount),
        "transactions": restored,
        "opening_remaining": opening_remaining,
        "audit_id": audit_id,
        "refresh_required": True
    }
