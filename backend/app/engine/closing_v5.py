# CONCILIA_V5_CLOSING_29E4

from decimal import Decimal
import unicodedata

ZERO = Decimal("0.00")

def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )

def normalize(value):
    return unicodedata.normalize(
        "NFKD", str(value)
    ).encode(
        "ascii", "ignore"
    ).decode("ascii").lower().strip()

def closing_summary_v5(job, composition):

    groups = {
        "opening_residual": ZERO,
        "opening_unproven": ZERO,
        "credit_residual": ZERO,
        "debit_residual": ZERO,
        "cent_differences": ZERO,
        "other_residual": ZERO,
    }

    unknown_count = 0

    for row in composition["rows"]:

        kind = normalize(row["kind"])
        value = money(row["value"])

        if kind == "saldo anterior nao detalhado":
            key = "opening_unproven"

        elif kind in (
            "saldo anterior",
            "saldo anterior detalhado",
            "saldo anterior parcialmente baixado",
            "saldo anterior parcialmente baixado (credito)",
            "baixa parcial do saldo anterior (debito)",
        ):
            key = "opening_residual"

        elif kind in (
            "nota em aberto",
            "nota parcialmente baixada",
            "nota parcialmente baixada (credito)",
            "baixa parcial vinculada (debito)",
        ):
            key = "credit_residual"

        elif kind in (
            "debito residual",
            "pagamento parcialmente utilizado",
            "pagamento parcialmente utilizado (debito)",
            "provisao vinculada a baixa (credito)",
        ):
            key = "debit_residual"

        elif kind == "divergencia de centavos":
            key = "cent_differences"

        else:
            key = "other_residual"
            unknown_count += 1

        groups[key] += value

    total = sum(groups.values(), ZERO)

    reported = money(job["final_reported_balance"])
    initial = money(job["initial_balance"])

    opening_paid = money(
        composition.get("opening_matched_total", "0.00")
    )

    difference = total - reported

    agrees = (
        total == money(composition["total"])
        and reported == money(composition["reported"])
        and difference == money(composition["difference"])
    )

    opening_consistent = (
        groups["opening_residual"]
        + groups["opening_unproven"]
        == initial + opening_paid
    )

    valid = (
        composition["valid"] is True
        and difference == ZERO
        and agrees
        and opening_consistent
        and unknown_count == 0
        and groups["credit_residual"] <= ZERO
        and groups["debit_residual"] >= ZERO
    )

    return {
        **{k: str(v) for k, v in groups.items()},
        "opening_original": str(initial),
        "opening_paid": str(opening_paid),
        "opening_attached": bool(
            composition.get("opening_attached")
        ),
        "opening_complete": bool(
            composition.get("opening_complete")
        ),
        "total": str(total),
        "reported": str(reported),
        "difference": str(difference),
        "agrees_with_composition": agrees,
        "opening_consistent": opening_consistent,
        "unknown_count": unknown_count,
        "valid": valid,
    }
