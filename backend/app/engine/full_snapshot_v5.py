# CONCILIA_V5_FULL_SNAPSHOT_25E

import json

from decimal import Decimal

from app.engine.composition import money

from app.engine.full_export_v5 import (
    build_full_sheets_v5,
)

from app.engine.opening_storage_v5 import (
    opening_state,
    opening_suggestions,
)

from app.engine.suggestion_export_v5 import (
    suggestion_sheets_v5,
)

from app.engine.opening_export_v5 import (
    opening_sheets_v5,
)

from app.engine.suggestion_financial_v5 import (
    enrich_current_sheets,
    enrich_opening_sheets,
)


def supplier_summary_v5(transactions):

    zero = Decimal("0.00")

    groups = {}

    for t in transactions:

        supplier = t.get("extracted_supplier")

        if supplier not in groups:

            groups[supplier] = {
                "supplier": supplier,
                "total_invoiced": zero,
                "total_paid": zero,
                "open_balance": zero,
                "invoices_count": 0,
                "supplier_credit_matched": zero,
                "supplier_debit_matched": zero,
                "supplier_debit_residual": zero,
            }

        item = groups[supplier]

        original = money(t["amount"])
        matched = money(t["matched_amount"])
        residual = money(t["remaining_amount"])

        if t["trans_type"] == "CREDIT":

            item["total_invoiced"] += original
            item["open_balance"] += residual
            item["invoices_count"] += 1
            item["supplier_credit_matched"] += matched

        elif t["trans_type"] == "DEBIT":

            item["total_paid"] += original
            item["supplier_debit_matched"] += matched
            item["supplier_debit_residual"] += residual

    result = sorted(
        groups.values(),
        key=lambda r: (
            -r["open_balance"],
            -r["total_invoiced"],
            str(r["supplier"] or "")
        )
    )

    for item in result:

        for key, value in item.items():

            if isinstance(value, Decimal):
                item[key] = str(value)

    return result


def reconciliation_rows_v5(
    reconciliations,
    transactions
):

    lookup = {
        t["id"]: t
        for t in transactions
    }

    result = []

    for source in reconciliations:

        if source.get("status") != "CONFIRMED":
            continue

        item = dict(source)

        inv = lookup.get(
            item.get("invoice_trans_id")
        )

        pay = lookup.get(
            item.get("payment_trans_id")
        )

        if inv is not None:

            item.update({
                "invoice_remaining":
                    inv["remaining_amount"],

                "invoice_total_matched":
                    inv["matched_amount"],

                "invoice_original_amount":
                    inv["amount"],

                "invoice_status":
                    inv["status"],

                "invoice_date":
                    inv.get("trans_date"),

                "invoice_history":
                    inv.get("history"),
            })

            original = money(inv["amount"])

            item["paid_percentage"] = (
                round(
                    float(
                        money(inv["matched_amount"])
                        / original * 100
                    ),
                    2
                )
                if original > 0
                else None
            )

        if pay is not None:

            item.update({
                "payment_remaining":
                    pay["remaining_amount"],

                "payment_already_matched":
                    pay["matched_amount"],

                "payment_original_amount":
                    pay["amount"],

                "payment_status":
                    pay["status"],

                "payment_date":
                    pay.get("trans_date"),

                "payment_history":
                    pay.get("history"),
            })

        if item["match_type"] == "REVERSAL":

            status = "Estorno"

        elif item["match_type"] == "CENT_DIFFERENCE":

            status = "Divergencia de centavos"

        elif inv is None or pay is None:

            status = "Vinculo a revisar"

        elif (
            inv["status"] in (
                "DIFERENCA_CENTAVOS",
                "DIVERGENCIA_CENTAVOS"
            )
            or pay["status"] in (
                "DIFERENCA_CENTAVOS",
                "DIVERGENCIA_CENTAVOS"
            )
        ):

            status = "Divergencia de centavos"

        elif (
            money(inv["remaining_amount"]) < 0
            or money(pay["remaining_amount"]) < 0
        ):

            status = "Revisar saldo"

        elif (
            money(inv["remaining_amount"]) > 0
            or money(pay["remaining_amount"]) > 0
        ):

            status = "Parcial"

        elif (
            money(inv["matched_amount"])
            == money(inv["amount"])
            and money(pay["matched_amount"])
            == money(pay["amount"])
        ):

            status = "Quitado"

        else:

            status = "Revisar saldo"

        item["display_status"] = status

        result.append(item)

    return result


def undo_history_rows_v5(conn, job_id):

    rows = conn.execute(
        """
        SELECT id, action, details, timestamp
        FROM audit_logs
        WHERE job_id=?
        AND action='UNDO_MATCH_V5'
        ORDER BY timestamp DESC, id DESC
        """,
        (job_id,)
    )

    result = []

    for source in rows:

        item = dict(source)

        raw = item.get("details")

        try:

            details = json.loads(raw or "{}")

            if not isinstance(details, dict):
                raise ValueError(
                    "Auditoria fora do formato esperado."
                )

        except (ValueError, TypeError):

            item["audit_parse_status"] = "REVISAR"
            item["audit_raw_details"] = raw

            result.append(item)

            continue

        original = details.get("original_record") or {}

        if not isinstance(original, dict):
            original = {}

        result.append({
            "id": item["id"],
            "timestamp": item["timestamp"],
            "action": item["action"],
            "origin": details.get("origin"),
            "match_id": details.get("match_id"),
            "reason": details.get("reason"),
            "restored_amount": details.get("amount"),
            "nf": original.get("nf"),
            "supplier": original.get("supplier"),
            "invoice_trans_id":
                original.get("invoice_trans_id"),
            "payment_trans_id":
                original.get("payment_trans_id"),
            "opening_remaining":
                details.get("opening_remaining"),
            "restored_transactions":
                details.get("restored_transactions"),
            "original_record": original,
            "audit_parse_status": "OK",
        })

    return result


def collect_full_snapshot_v5(conn, job_id):

    # Importacao local para evitar dependencia circular.
    from app.api.routes import (
        current_composition,
        refresh_live_summary,
        build_suggestions_v5,
    )

    if conn.in_transaction:

        raise RuntimeError(
            "A exportacao exige uma conexao exclusiva."
        )

    conn.execute("PRAGMA query_only=ON")
    conn.execute("BEGIN")

    try:

        row = conn.execute(
            "SELECT * FROM jobs WHERE id=?",
            (job_id,)
        ).fetchone()

        if row is None:

            raise LookupError(
                "Documento inexistente."
            )

        job = dict(row)

        transactions = [
            dict(r)
            for r in conn.execute(
                """
                SELECT * FROM transactions
                WHERE job_id=?
                ORDER BY row_index ASC, id ASC
                """,
                (job_id,)
            )
        ]

        reconciliations = [
            dict(r)
            for r in conn.execute(
                """
                SELECT * FROM reconciliations
                WHERE job_id=?
                AND status='CONFIRMED'
                ORDER BY nf ASC, id ASC
                """,
                (job_id,)
            )
        ]

        metadata = json.loads(
            job.get("metadata_json") or "{}"
        )

        math_audit = json.loads(
            job.get("math_explanation") or "{}"
        )

        summary = refresh_live_summary(
            conn,
            job_id,
            metadata.get("summary", {})
        )

        composition = current_composition(
            conn, job
        )

        original, opening_rows, links = (
            opening_state(conn, job_id)
        )

        current_items = build_suggestions_v5(
            transactions
        )

        current_sheets = suggestion_sheets_v5(
            job, current_items
        )

        current_sheets = enrich_current_sheets(
            current_sheets,
            transactions
        )

        previous_items = (
            opening_suggestions(conn, job_id)
            if original is not None
            else []
        )

        previous_sheets = opening_sheets_v5(
            job,
            original,
            opening_rows,
            links,
            previous_items,
            composition
        )

        previous_sheets = enrich_opening_sheets(
            previous_sheets,
            opening_rows,
            transactions
        )

        suppliers = supplier_summary_v5(
            transactions
        )

        history = undo_history_rows_v5(
            conn, job_id
        )

        active = reconciliation_rows_v5(
            reconciliations,
            transactions
        )

        sheets = build_full_sheets_v5(
            job=job,
            summary=summary,
            composition=composition,
            transactions=transactions,
            reconciliations=active,
            opening_original=original,
            opening_rows=opening_rows,
            current_suggestions=current_sheets[
                "Todas as sugestoes"
            ],
            opening_suggestions=previous_sheets[
                "Todas as sugestoes"
            ],
            suppliers=suppliers,
            undo_history=history,
            math_audit=math_audit,
        )

        return sheets

    finally:

        # Encerrar a leitura sem gravar dados.
        conn.rollback()
