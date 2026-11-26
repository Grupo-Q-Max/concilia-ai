
# CONCILIA_V5_MONTHLY_29E3B

from datetime import date
from decimal import Decimal
import re

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def month_key_v5(value):
    text = str(value or "").strip()

    iso = re.fullmatch(
        r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?",
        text
    )

    br = re.fullmatch(
        r"(\d{1,2})/(\d{1,2})/(\d{4})(?:[ T].*)?",
        text
    )

    try:
        if iso:
            y, m, d = map(int, iso.groups())
        elif br:
            d, m, y = map(int, br.groups())
        else:
            return None

        parsed = date(y, m, d)

        return f"{parsed.year:04d}-{parsed.month:02d}"

    except ValueError:
        return None


def monthly_evolution_v5(conn, job_id):
    rows = conn.execute(
        """
        SELECT trans_date, trans_type, amount
        FROM transactions
        WHERE job_id = ?
        """,
        (job_id,)
    ).fetchall()

    grouped = {}

    for row in rows:
        key = month_key_v5(row["trans_date"]) or "SEM_DATA"

        if key not in grouped:
            grouped[key] = {
                "month": key,
                "credits": ZERO,
                "debits": ZERO,
                "transaction_count": 0
            }

        item = grouped[key]
        amount = Decimal(str(row["amount"]))

        if row["trans_type"] == "CREDIT":
            item["credits"] += amount

        elif row["trans_type"] == "DEBIT":
            item["debits"] += amount

        item["transaction_count"] += 1

    return [
        {
            "month": key,
            "credits": float(
                grouped[key]["credits"].quantize(CENT)
            ),
            "debits": float(
                grouped[key]["debits"].quantize(CENT)
            ),
            "transaction_count": grouped[key]["transaction_count"]
        }
        for key in sorted(grouped)
    ]
