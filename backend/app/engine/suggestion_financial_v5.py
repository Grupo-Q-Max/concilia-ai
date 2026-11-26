
from decimal import Decimal

# CONCILIA_V5_FINANCIAL_EXPORT_25C


def money(value):

    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )


def financial_fields(record, prefix, original_key="amount"):

    original = money(record[original_key])
    matched = money(record["matched_amount"])
    residual = money(record["remaining_amount"])

    if min(original, matched, residual) < 0:
        raise ValueError(
            "Valores financeiros negativos."
        )

    return {
        prefix + "_original_amount": str(original),
        prefix + "_already_matched": str(matched),
        prefix + "_financial_difference": str(
            original - matched - residual
        )
    }


def enrich_current_sheets(sheets, transactions):

    lookup = {
        t["id"]: dict(t)
        for t in transactions
    }

    result = {}

    for name, records in sheets.items():

        enriched = []

        for source in records:

            row = dict(source)

            if (
                "invoice_trans_id" in row
                and "payment_trans_id" in row
                and "suggested_amount" in row
            ):

                invoice = lookup[
                    row["invoice_trans_id"]
                ]

                payment = lookup[
                    row["payment_trans_id"]
                ]

                row.update(
                    financial_fields(
                        invoice, "invoice"
                    )
                )

                row.update(
                    financial_fields(
                        payment, "payment"
                    )
                )

                row["suggestion_status"] = (
                    "PENDENTE DE APROVACAO"
                )

            enriched.append(row)

        result[name] = enriched

    return result


def enrich_opening_sheets(sheets, rows, transactions):

    opening_lookup = {
        int(r["opening_index"]): dict(r)
        for r in rows
    }

    payment_lookup = {
        t["id"]: dict(t)
        for t in transactions
    }

    result = {}

    for name, records in sheets.items():

        enriched = []

        for source in records:

            row = dict(source)

            if (
                "opening_index" in row
                and "payment_trans_id" in row
                and "suggested_amount" in row
            ):

                invoice = opening_lookup[
                    int(row["opening_index"])
                ]

                payment = payment_lookup[
                    row["payment_trans_id"]
                ]

                row.update(
                    financial_fields(
                        invoice,
                        "opening",
                        "original"
                    )
                )

                row.update(
                    financial_fields(
                        payment,
                        "payment"
                    )
                )

                row["suggestion_status"] = (
                    "PENDENTE DE APROVACAO"
                )

            enriched.append(row)

        result[name] = enriched

    return result
