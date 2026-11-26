
from decimal import Decimal


def money(v):
    return Decimal(str(v or 0)).quantize(
        Decimal("0.01")
    )


def composition(job, transactions, opening=None):

    rows = []

    def add(kind, value, t, residual=None, matched=None):

        value = money(value)

        if value == 0:
            return

        original = money(
            t.get("amount", t.get("original", abs(value)))
        )

        matched = money(matched)

        if residual is None:
            residual = abs(value)

        residual = money(residual)

        row = {
            "kind": kind,
            "value": str(value),
            "date": t.get("trans_date", ""),
            "nf": t.get("extracted_nf", ""),
            "supplier": t.get("extracted_supplier", ""),
            "history": t.get("history", ""),
            "original": str(abs(original)),
            "matched_amount": str(matched),
            "remaining_amount": str(residual),
            "status": kind
        }

        if t.get("id"):
            row["transaction_id"] = t["id"]

        if kind in (
            "Nota em aberto",
            "D\u00e9bito residual",
            "Nota parcialmente baixada",
            "Pagamento parcialmente utilizado"
        ):
            row["status"] = (
                "PARCIALMENTE CONCILIADO"
                if matched > 0
                else "EM ABERTO"
            )

        rows.append(row)

    initial = money(job["initial_balance"])

    if opening is None:

        add(
            "Saldo anterior",
            initial,
            {
                "history": "Saldo anterior sem detalhamento"
            }
        )

        opening_difference = Decimal("0.00")

    else:

        for item in opening:

            add(
                "Saldo anterior detalhado",
                money(item["value"]),
                item
            )

        opening_difference = initial - sum(
            (money(item["value"]) for item in opening),
            Decimal("0.00")
        )

        if opening_difference:

            add(
                "Saldo anterior nao detalhado",
                opening_difference,
                {
                    "history": (
                        "Diferenca entre saldo anterior do razao "
                        "e planilha complementar; "
                        "pendente de comprovacao"
                    )
                }
            )

    for t in transactions:

        sign = 1 if t["trans_type"] == "DEBIT" else -1

        residual = money(t["remaining_amount"])
        matched = money(t["matched_amount"])

        if residual:

            if sign == 1:

                kind = (
                    "Pagamento parcialmente utilizado"
                    if matched > 0
                    else "D\u00e9bito residual"
                )

            else:

                kind = (
                    "Nota parcialmente baixada"
                    if matched > 0
                    else "Nota em aberto"
                )

            add(
                kind,
                sign * residual,
                t,
                residual=residual,
                matched=matched
            )

        if t["status"] == "DIVERGENCIA_CENTAVOS":

            difference = (
                money(t["amount"])
                - matched
                - residual
            )

            add(
                "Diverg\u00eancia de centavos",
                sign * difference,
                t,
                residual=abs(difference),
                matched=matched
            )

    total = sum(
        (money(r["value"]) for r in rows),
        Decimal("0.00")
    )

    reported = money(job["final_reported_balance"])

    return {
        "rows": rows,
        "total": str(total),
        "reported": str(reported),
        "difference": str(total - reported),
        "valid": total == reported and bool(transactions),
        "opening_attached": opening is not None,
        "opening_difference": str(opening_difference),
        "opening_complete": (
            opening is not None
            and opening_difference == 0
        )
    }
