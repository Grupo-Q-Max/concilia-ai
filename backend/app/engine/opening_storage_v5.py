
import json
import uuid
import hashlib

from datetime import datetime
from decimal import Decimal
from app.engine.opening_matching_v5 import (
    money, opening_candidates, opening_audit
)


def ensure_opening_storage(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS opening_matches_v5 (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            opening_index INTEGER NOT NULL,
            opening_hash TEXT NOT NULL,
            payment_trans_id TEXT NOT NULL,
            amount TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(job_id, opening_index, payment_trans_id),
            FOREIGN KEY(job_id)
                REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY(payment_trans_id)
                REFERENCES transactions(id) ON DELETE CASCADE
        )
    """)


def opening_hash(rows):

    payload = json.dumps(
        rows,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def opening_state(conn, job_id):

    ensure_opening_storage(conn)

    record = conn.execute(
        "SELECT payload FROM opening_compositions WHERE job_id=?",
        (job_id,)
    ).fetchone()

    if not record:
        return None, [], []

    original = json.loads(record[0])
    digest = opening_hash(original)

    links = [
        dict(r) for r in conn.execute(
            "SELECT * FROM opening_matches_v5 WHERE job_id=?",
            (job_id,)
        )
    ]

    totals = {}

    for link in links:

        if link["opening_hash"] != digest:
            raise ValueError(
                "Planilha complementar alterada apos conciliacao."
            )

        index = link["opening_index"]

        if not 0 <= index < len(original):
            raise ValueError("Vinculo de saldo anterior invalido.")

        amount = money(link["amount"])

        if amount <= 0:
            raise ValueError("Valor de baixa invalido.")

        totals[index] = totals.get(
            index, Decimal("0.00")
        ) + amount

    rows = []

    for index, item in enumerate(original):

        value = money(item["value"])
        matched = totals.get(index, Decimal("0.00"))

        if matched and (value >= 0 or matched > abs(value)):
            raise ValueError(
                "Baixas excedem o saldo original da nota."
            )

        residual = value + matched

        raw_nf = item.get("extracted_nf")
        if not raw_nf or str(raw_nf).strip() in ("S/N", "0"):
            from app.engine.extractor import extract_fallback_number
            fb = extract_fallback_number(item.get("history"))
            if fb:
                raw_nf = fb

        rows.append({
            **item,
            "extracted_nf": raw_nf or "S/N",
            "opening_index": index,
            "opening_hash": digest,
            "original": str(abs(value)),
            "matched_amount": str(matched),
            "remaining_amount": str(abs(residual)),
            "value": str(residual),
            "status": (
                "QUITADO" if residual == 0
                else "PARCIAL" if matched > 0
                else "EM ABERTO"
            )
        })

    return original, rows, links


def opening_suggestions(conn, job_id):

    original, rows, links = opening_state(conn, job_id)

    if original is None:
        return []

    transactions = [
        dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE job_id=?",
            (job_id,)
        )
    ]

    suggestions = opening_candidates(rows, transactions)

    existing = {
        (r["opening_index"], r["payment_trans_id"])
        for r in links
    }

    result = []

    for item in suggestions:

        key = (
            item["opening_index"],
            item["payment_trans_id"]
        )

        if key in existing:
            continue

        item["opening_hash"] = opening_hash(original)

        result.append(item)

    return result


def register_opening_match(
    conn,
    job_id,
    opening_index,
    payment_id,
    expected_hash,
    expected_opening,
    expected_payment,
    allow_review=False
):

    # Caller owns the transaction and must commit or rollback.

    original, rows, links = opening_state(conn, job_id)

    if original is None:
        raise ValueError("Planilha complementar nao anexada.")

    if opening_hash(original) != expected_hash:
        raise ValueError("Planilha alterada. Atualize os dados.")

    if not 0 <= opening_index < len(rows):
        raise ValueError("Nota anterior inexistente.")

    inv = rows[opening_index]

    if money(inv["value"]) >= 0:
        raise ValueError("Nota anterior sem saldo credor.")

    pay_row = conn.execute(
        """
        SELECT * FROM transactions
        WHERE id=? AND job_id=?
        """,
        (payment_id, job_id)
    ).fetchone()

    if not pay_row:
        raise ValueError("Pagamento inexistente.")

    pay = dict(pay_row)

    if pay["trans_type"] != "DEBIT":
        raise ValueError("Lancamento nao e pagamento.")

    if pay.get("is_duplicate") or pay.get("is_reversal"):
        raise ValueError("Pagamento exige revisao.")

    if pay.get("status") == "DIVERGENCIA_CENTAVOS":
        raise ValueError("Pagamento com divergencia exige revisao.")

    a = abs(money(inv["value"]))
    b = money(pay["remaining_amount"])

    if a <= 0 or b <= 0:
        raise ValueError("Lancamento ja liquidado.")

    if a != money(expected_opening) or b != money(expected_payment):
        raise ValueError("Saldos alterados. Atualize as sugestoes.")

    if money(pay["matched_amount"]) + b != money(pay["amount"]):
        raise ValueError("Pagamento com saldo inconsistente.")

    if any(
        r["opening_index"] == opening_index
        and r["payment_trans_id"] == payment_id
        for r in links
    ):
        raise ValueError("Baixa ja registrada.")

    candidate = next(
        (
            s for s in opening_suggestions(conn, job_id)
            if s["opening_index"] == opening_index
            and s["payment_trans_id"] == payment_id
        ),
        None
    )

    if candidate is None:
        raise ValueError("Sugestao nao encontrada.")

    if not candidate["automatic_eligible"] and not allow_review:
        raise ValueError("Sugestao exige aprovacao individual.")

    matched = min(a, b)
    residual = b - matched
    accumulated = money(pay["matched_amount"]) + matched

    match_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn.execute(
        """
        INSERT INTO opening_matches_v5 (
            id, job_id, opening_index, opening_hash,
            payment_trans_id, amount, reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            match_id, job_id, opening_index,
            expected_hash, payment_id, str(matched),
            candidate["reason"], now
        )
    )

    conn.execute(
        """
        UPDATE transactions
        SET matched_amount=?, remaining_amount=?, status=?
        WHERE id=? AND job_id=?
        """,
        (
            str(accumulated),
            str(residual),
            "CONCILIADO" if residual == 0 else "PARCIAL",
            payment_id, job_id
        )
    )

    conn.execute(
        """
        INSERT INTO audit_logs (
            id, job_id, action, details, timestamp
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            job_id,
            "OPENING_MATCH_V5",
            json.dumps({
                "match_id": match_id,
                "opening_index": opening_index,
                "payment_id": payment_id,
                "amount": str(matched)
            }),
            now
        )
    )

    return {
        "success": True,
        "match_id": match_id,
        "reconciled_amount": str(matched),
        "opening_remaining": str(a - matched),
        "payment_remaining": str(residual)
    }
