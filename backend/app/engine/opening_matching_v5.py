
from decimal import Decimal
from collections import Counter
from app.engine.reconciler import v5_reference, v5_supplier_match
from app.engine.extractor import extract_transaction_info


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def opening_candidates(opening, transactions):

    credits = []
    payments = []
    current_credits = []

    for index, row in enumerate(opening):

        value = money(row.get("value"))

        if value >= 0:
            continue

        history = str(row.get("history") or "")
        info = extract_transaction_info(history, "CREDIT")

        item = {
            **info,
            **row,
            "history": history,
            "opening_index": index,
            "remaining_amount": str(abs(value))
        }

        raw_nf = row.get("extracted_nf") or info.get("extracted_nf")
        if not raw_nf or str(raw_nf).strip() in ("S/N", "0"):
            from app.engine.extractor import extract_fallback_number
            fb = extract_fallback_number(history)
            if fb:
                raw_nf = fb

        item["extracted_nf"] = raw_nf or "S/N"

        credits.append(item)

    # Pre-computa débitos e indexa por valor e por NF para busca O(1)
    payment_meta = []
    payments_by_amount = {}
    payments_by_nf = {}

    for t in transactions:
        if t.get("is_duplicate") or t.get("is_reversal"):
            continue

        if money(t.get("remaining_amount")) <= 0:
            continue

        if t["trans_type"] == "DEBIT":
            b = money(t["remaining_amount"])
            nf2 = v5_reference(t)
            entry = (t, b, nf2)
            payment_meta.append(entry)
            payments_by_amount.setdefault(b, []).append(entry)
            if nf2 and nf2 not in ("S/N", "0"):
                payments_by_nf.setdefault(nf2, []).append(entry)

        elif t["trans_type"] == "CREDIT":
            current_credits.append(t)

    # Pre-indexa créditos do período para verificação rápida de conflitos
    curr_cred_nfs = set()
    curr_cred_by_amt = {}
    for t in current_credits:
        c_nf = v5_reference(t)
        if c_nf and c_nf not in ("S/N", "0"):
            curr_cred_nfs.add(c_nf)
        c_amt = money(t["remaining_amount"])
        curr_cred_by_amt.setdefault(c_amt, []).append(t)

    candidates = []

    for inv in credits:

        a = money(inv["remaining_amount"])
        nf1 = v5_reference(inv)

        # Seleciona apenas pagamentos com mesmo valor ou mesma NF
        seen_pays = set()
        cand_pays = []

        for entry in payments_by_amount.get(a, []):
            p = entry[0]
            if p["id"] not in seen_pays:
                seen_pays.add(p["id"])
                cand_pays.append(entry)

        if nf1 and nf1 not in ("S/N", "0"):
            for entry in payments_by_nf.get(nf1, []):
                p = entry[0]
                if p["id"] not in seen_pays:
                    seen_pays.add(p["id"])
                    cand_pays.append(entry)

        for pay, b, nf2 in cand_pays:

            same_nf = bool(nf1 and nf2 and nf1 == nf2)
            different_nf = bool(nf1 and nf2 and nf1 != nf2)
            same_supplier = v5_supplier_match(inv, pay)
            same_value = a == b

            if same_nf and same_value:
                category = "EXATO"
                score = 100
                reason = "Mesma NF e mesmo valor do saldo anterior"

            elif same_nf:
                category = "PARCIAL"
                score = 90
                reason = "Possivel baixa parcial de exercicio anterior"

            elif same_value and different_nf:
                category = "DIVERGENCIA_NF"
                score = 60
                reason = "Valores iguais com NFs diferentes"

            elif same_value and same_supplier:
                category = "FORNECEDOR"
                score = 95
                reason = "Mesmo fornecedor e valor"

            else:
                continue

            current_conflict = bool(
                (nf2 and nf2 in curr_cred_nfs)
                or any(
                    v5_supplier_match(t, pay)
                    for t in curr_cred_by_amt.get(b, [])
                )
            )

            matched = min(a, b)

            candidates.append({
                "opening_index": inv["opening_index"],
                "payment_trans_id": pay["id"],
                "opening_nf": nf1 or "S/N",
                "payment_nf": nf2 or "S/N",
                "opening_history": inv.get("history"),
                "payment_history": pay.get("history"),
                "opening_date": inv.get("trans_date"),
                "payment_date": pay.get("trans_date"),
                "opening_amount": str(a),
                "payment_amount": str(b),
                "suggested_amount": str(matched),
                "opening_after": str(a - matched),
                "payment_after": str(b - matched),
                "category": category,
                "score": score,
                "reason": reason,
                "current_conflict": current_conflict
            })

    opening_counts = Counter(
        s["opening_index"] for s in candidates
    )

    payment_counts = Counter(
        s["payment_trans_id"] for s in candidates
    )

    for s in candidates:

        s["ambiguous"] = (
            opening_counts[s["opening_index"]] > 1
            or payment_counts[s["payment_trans_id"]] > 1
            or s["current_conflict"]
        )

        s["automatic_eligible"] = (
            not s["ambiguous"]
            and s["category"] in ("EXATO", "FORNECEDOR")
        )

    return sorted(
        candidates,
        key=lambda s: (-s["score"], s["ambiguous"])
    )


def opening_audit(initial_balance, opening):

    initial = money(initial_balance)

    detailed = sum(
        (money(r["value"]) for r in opening),
        Decimal("0.00")
    )

    difference = initial - detailed

    return {
        "initial_balance": str(initial),
        "detailed_balance": str(detailed),
        "unproven_balance": str(difference),
        "fully_documented": difference == 0,
        "mathematical_difference": str(
            initial - detailed - difference
        )
    }
