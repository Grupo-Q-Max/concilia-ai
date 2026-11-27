"""
CONCILIA AI - Automatic Accounting Reconciliation Engine
Deterministic multi-pass reconciliation with Decimal precision, full traceability,
and configurable rules from settings.
"""
import uuid
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from app.config import load_settings
from app.engine.ai_matcher import are_suppliers_compatible, compute_similarity


# CONCILIA_INTELLIGENT_V5
import re
from app.engine.matching_v5 import normalize_nf, normalize_supplier
from app.engine.extractor import extract_fallback_number

def v5_reference(t):
    history = str(t.get("history") or "")

    raw_nf = str(t.get("extracted_nf") or "").strip()

    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw_nf):
        return raw_nf.replace(".", "").lstrip("0") or "0"

    nf = normalize_nf(t.get("extracted_nf"))

    if nf and nf.isdigit():
        return nf

    match = re.search(
        r"\b(?:NF-?E?|N\.F\.|NOTA\s+FISCAL|CRF|FATURA|DUPLICATA)"
        r"\s*[:.#-]?\s*(\d+)(?:\s*-\s*\d+/\d+)?",
        history,
        re.I
    )

    if match:
        return normalize_nf(match.group(1))

    # CONCILIA_V5_ASSISTIDA_FALLBACK_NF:
    # Na conciliacao assistida / ao nao encontrar NF, pegar numero do historico e utilizar como nota
    fallback = extract_fallback_number(history)
    if fallback:
        return normalize_nf(fallback)

    return nf

def v5_supplier(value):
    text = normalize_supplier(value)

    text = re.sub(
        r"\b(?:AQUISICAO|CONFORME|NOTA|FISCAL|"
        r"PAGAMENTO|PAGTO|PGTO|PAGO|VSP|OUTROS|"
        r"ENTRADA|PROVISAO|VALOR|RECOLHIDO|CRF|CSRF|IRRF|ISS|ISSQN|INSS|PIS|COFINS|CSLL|PCC|"
        r"CONTRATO|GERENCIAMENTO|ITENS|REF)\b",
        " ",
        text
    )

    text = re.sub(r"\bNF\s*\d+.*$", "", text)
    text = re.sub(r"\b\d+\b", " ", text)

    return " ".join(text.split())

def v5_supplier_match(a, b):
    sa = v5_supplier(a.get("cleaned_supplier"))
    sb = v5_supplier(b.get("cleaned_supplier"))

    if not sa or not sb:
        return False

    if sa == sb and len(sa) >= 5:
        return True

    ha = v5_supplier(a.get("history"))
    hb = v5_supplier(b.get("history"))

    for name, history in ((sa, hb), (sb, ha)):
        if len(name.split()) >= 3 and len(name) >= 12:
            if (" " + name + " ") in (" " + history + " "):
                return True

    return (
        len(sa.split()) >= 2
        and len(sb.split()) >= 2
        and (compute_similarity(sa, sb) >= 0.88 or are_suppliers_compatible(sa, sb, threshold=0.75))
    )


# CONCILIA_V5_FISCAL_REFERENCE_28

def v5_extended_alias(number, year):
    number = str(number or "")
    year = str(year or "")

    if not number.isdigit():
        return None

    if not re.fullmatch(r"20\d{2}", year):
        return None

    for prefix in (year, year[-2:]):
        if not number.startswith(prefix):
            continue

        suffix = number[len(prefix):]

        if len(suffix) < 9:
            continue

        if not suffix.startswith("0000"):
            continue

        alias = suffix.lstrip("0")

        if alias and len(alias) <= 7:
            return alias

    return None


def v5_fiscal_equivalent(a, b):
    x = v5_reference(a)
    y = v5_reference(b)

    if not x or not y or x == y:
        return False

    if not x.isdigit() or not y.isdigit():
        return False

    year_a = str(a.get("trans_date") or "")[:4]
    year_b = str(b.get("trans_date") or "")[:4]

    if not (
        v5_extended_alias(x, year_a) == y
        or v5_extended_alias(y, year_b) == x
    ):
        return False

    return v5_supplier_match(a, b)


def v5_exact_pass(job_id, transactions, reconciliations):
    # CONCILIA_V5_FISCAL_REVIEW_30A2A
    # Equivalencia fiscal exige aprovacao humana.
    for mode in ("NF", "SUPPLIER"):
        credits = [
            t for t in transactions
            if t["trans_type"] == "CREDIT"
            and t["remaining_amount"] > 0
            and not t.get("is_duplicate")
        ]

        debits = [
            t for t in transactions
            if t["trans_type"] == "DEBIT"
            and t["remaining_amount"] > 0
            and not t.get("is_duplicate")
        ]

        debits_by_amount = {}
        for d in debits:
            debits_by_amount.setdefault(d["remaining_amount"], []).append(d)

        candidates = {}
        reverse = {}

        for c in credits:
            for d in debits_by_amount.get(c["remaining_amount"], ()):
                a = v5_reference(c)
                b = v5_reference(d)

                if mode == "NF":
                    compatible = bool(a and b and a == b)
                elif mode == "FISCAL":
                    compatible = v5_fiscal_equivalent(c, d)
                else:
                    compatible = (
                        not (a and b)
                        and v5_supplier_match(c, d)
                    )

                if not compatible:
                    continue

                candidates.setdefault(c["id"], []).append(d)
                reverse.setdefault(d["id"], []).append(c)

        for c in credits:
            options = candidates.get(c["id"], [])

            if len(options) != 1:
                continue

            d = options[0]

            if len(reverse.get(d["id"], [])) != 1:
                continue

            if c["remaining_amount"] <= 0 or d["remaining_amount"] <= 0:
                continue

            value = c["remaining_amount"]

            for t in (c, d):
                t["matched_amount"] += value
                t["remaining_amount"] -= value
                t["status"] = "CONCILIADO"

            reason = (
                "NF normalizada e valor identico"
                if mode == "NF"
                else "Fornecedor compativel e valor identico; NF ausente"
            )

            if mode == "FISCAL":
                reason = (
                    "Equivalencia fiscal de numeracao; "
                    "fornecedor compativel e valor identico"
                )

            reconciliations.append({
                "id": str(uuid.uuid4()),
                "job_id": job_id,
                "match_type": "EXACT_1_TO_1",
                "invoice_trans_id": c["id"],
                "payment_trans_id": d["id"],
                "nf": v5_reference(c) or v5_reference(d),
                "supplier": c.get("extracted_supplier") or d.get("extracted_supplier"),
                "invoice_amount": str(c["amount"]),
                "payment_amount": str(d["amount"]),
                "reconciled_amount": str(value),
                "difference": "0.00",
                "confidence_score": 1.0 if mode == "NF" else 0.95,
                "status": "CONFIRMED",
                "match_notes": reason,
                "created_at": d["trans_date"]
            })



# CONCILIA_V5_AMBIGUITY_GUARD_28

def v5_partition_ambiguous(transactions):
    groups = {}

    for t in transactions:
        if t["remaining_amount"] <= 0:
            continue

        nf = v5_reference(t)

        if not nf:
            continue

        groups.setdefault(nf, []).append(t)

    blocked = set()

    for nf, items in groups.items():
        credits = [
            t for t in items
            if t["trans_type"] == "CREDIT"
        ]

        debits = [
            t for t in items
            if t["trans_type"] == "DEBIT"
        ]

        if not credits or not debits:
            continue

        # Multiple provisions for one reference require review.
        # One provision with several distinct payments remains valid.

        if len(credits) > 1:
            tot_c = sum(c["remaining_amount"] for c in credits)
            tot_d = sum(d["remaining_amount"] for d in debits)
            if tot_c == tot_d and len(debits) >= 1:
                continue
            blocked.update(t["id"] for t in items)
            continue

        amounts = {}

        for d in debits:
            value = d["remaining_amount"]
            amounts[value] = amounts.get(value, 0) + 1

        # Repeated identical payment amounts are ambiguous
        # when the available provision cannot cover all of them.

        total_debits = sum(
            (d["remaining_amount"] for d in debits),
            Decimal("0.00")
        )

        if (
            any(n > 1 for n in amounts.values())
            and total_debits > credits[0]["remaining_amount"]
        ):
            blocked.update(t["id"] for t in items)

    # Check competing fiscal references before automatic passes.

    fiscal_credits = [
        t for t in transactions
        if t["trans_type"] == "CREDIT"
        and t["remaining_amount"] > 0
    ]

    fiscal_debits = [
        t for t in transactions
        if t["trans_type"] == "DEBIT"
        and t["remaining_amount"] > 0
    ]

    fiscal_debits_by_amt = {}
    for d in fiscal_debits:
        fiscal_debits_by_amt.setdefault(d["remaining_amount"], []).append(d)

    fiscal_forward = {}
    fiscal_reverse = {}

    for c in fiscal_credits:
        for d in fiscal_debits_by_amt.get(c["remaining_amount"], ()):
            a = v5_reference(c)
            b = v5_reference(d)

            exact = bool(a and b and a == b)
            fiscal = v5_fiscal_equivalent(c, d)

            if not exact and not fiscal:
                continue

            fiscal_forward.setdefault(c["id"], []).append(d["id"])
            fiscal_reverse.setdefault(d["id"], []).append(c["id"])

    for credit_id, payment_ids in fiscal_forward.items():
        if len(payment_ids) > 1:
            blocked.add(credit_id)
            blocked.update(payment_ids)

    for payment_id, credit_ids in fiscal_reverse.items():
        if len(credit_ids) > 1:
            blocked.add(payment_id)
            blocked.update(credit_ids)

    active = [
        t for t in transactions
        if t["id"] not in blocked
    ]

    reserved = [
        t for t in transactions
        if t["id"] in blocked
    ]

    return active, reserved



# CONCILIA_V5_REVERSAL_SAFETY_30A2C1

def v5_has_reversal_marker(transaction):
    import re
    import unicodedata

    text = unicodedata.normalize(
        "NFKD",
        str(transaction.get("history") or "")
    ).encode(
        "ascii", "ignore"
    ).decode("ascii").upper()

    return bool(re.search(
        r"\b(?:ESTORNO|ESTORNADO|ESTORNADA|ESTORNAR|"
        r"CANCELA|CANCELADO|CANCELADA|CANCELAMENTO)\b",
        text
    ))


def v5_reversal_candidates(transactions):

    forward = {}
    reverse = {}
    marked = set()

    for t in transactions:

        if v5_has_reversal_marker(t):
            marked.add(t["id"])

    credits = [
        t for t in transactions
        if t["trans_type"] == "CREDIT"
        and t["remaining_amount"] > 0
        and not t.get("is_duplicate")
        and not t.get("is_reversal")
    ]

    debits = [
        t for t in transactions
        if t["trans_type"] == "DEBIT"
        and t["remaining_amount"] > 0
        and not t.get("is_duplicate")
        and not t.get("is_reversal")
    ]

    for c in credits:

        for d in debits:

            if (
                c["id"] not in marked
                and d["id"] not in marked
            ):
                continue

            if c["amount"] != d["amount"]:
                continue

            nf1 = v5_reference(c)
            nf2 = v5_reference(d)

            if nf1 and nf2:

                if nf1 != nf2:
                    continue

            elif not v5_supplier_match(c, d):
                continue

            forward.setdefault(
                c["id"], []
            ).append(d["id"])

            reverse.setdefault(
                d["id"], []
            ).append(c["id"])

    safe = set()
    reserved = set(marked)

    for cid, payment_ids in forward.items():

        reserved.add(cid)
        reserved.update(payment_ids)

        if len(payment_ids) != 1:
            continue

        did = payment_ids[0]

        if len(reverse.get(did, [])) != 1:
            continue

        safe.add((cid, did))

    return safe, reserved


def v5_safe_reversal_pair(t1, t2, safe_pairs):

    if t1["trans_type"] == t2["trans_type"]:
        return False

    if t1.get("is_duplicate") or t2.get("is_duplicate"):
        return False

    if t1["trans_type"] == "CREDIT":
        pair = (t1["id"], t2["id"])
    else:
        pair = (t2["id"], t1["id"])

    return pair in safe_pairs



# CONCILIA_V5_DUPLICATE_SAFETY_30A2C2

def v5_duplicate_groups(transactions):

    groups = {}

    for t in transactions:

        nf = v5_reference(t)
        supplier = v5_supplier(
            t.get("extracted_supplier")
        )

        history = " ".join(
            str(t.get("history") or "").upper().split()
        )

        if not nf or not supplier or not history:
            continue

        key = (
            t["trans_type"],
            t.get("trans_date"),
            t["amount"],
            nf,
            supplier,
            history
        )

        groups.setdefault(key, []).append(t)

    return [
        items for items in groups.values()
        if len(items) > 1
    ]


def v5_reserve_duplicates(transactions):

    reserved = set()

    for group in v5_duplicate_groups(transactions):

        for t in group:

            t["is_duplicate"] = 1
            reserved.add(t["id"])

    # Reserve potential counterparts as well.
    # No transaction is removed from accounting totals.

    duplicate_rows = [
        t for t in transactions
        if t["id"] in reserved
    ]

    # Index counterparts by NF, fiscal alias, and amount to avoid O(N^2) scan
    by_nf = {}
    by_amount_no_nf = {}
    for other in transactions:
        nf2 = v5_reference(other)
        if nf2:
            by_nf.setdefault(nf2, []).append(other)
            year2 = str(other.get("trans_date") or "")[:4]
            alias2 = v5_extended_alias(nf2, year2)
            if alias2:
                by_nf.setdefault(alias2, []).append(other)
        else:
            by_amount_no_nf.setdefault(other["amount"], []).append(other)

    for duplicate in duplicate_rows:
        nf1 = v5_reference(duplicate)
        year1 = str(duplicate.get("trans_date") or "")[:4]
        alias1 = v5_extended_alias(nf1, year1) if nf1 else None

        candidate_others = []
        if nf1:
            candidate_others.extend(by_nf.get(nf1, ()))
        if alias1:
            candidate_others.extend(by_nf.get(alias1, ()))
        if not nf1:
            candidate_others.extend(by_amount_no_nf.get(duplicate["amount"], ()))
            for other in transactions:
                if other["amount"] == duplicate["amount"]:
                    candidate_others.append(other)
        else:
            candidate_others.extend(by_amount_no_nf.get(duplicate["amount"], ()))

        for other in candidate_others:
            if duplicate["trans_type"] == other["trans_type"]:
                continue

            if other["id"] in reserved:
                continue

            nf2 = v5_reference(other)

            same_nf = bool(
                nf1 and nf2 and nf1 == nf2
            )

            fiscal = v5_fiscal_equivalent(
                duplicate, other
            )

            missing_nf_match = (
                not (nf1 and nf2)
                and duplicate["amount"] == other["amount"]
                and v5_supplier_match(duplicate, other)
            )

            if same_nf or fiscal or missing_nf_match:
                reserved.add(other["id"])

    return reserved



# CONCILIA_V5_ALLOCATION_SAFETY_30A2D

def v5_reserve_overallocated_groups(transactions):

    groups = {}

    for t in transactions:

        if t["remaining_amount"] <= 0:
            continue

        nf = v5_reference(t)

        if not nf:
            continue

        groups.setdefault(nf, []).append(t)

    reserved = set()

    for items in groups.values():

        credits = [
            t for t in items
            if t["trans_type"] == "CREDIT"
        ]

        debits = [
            t for t in items
            if t["trans_type"] == "DEBIT"
        ]

        if not credits or not debits:
            continue

        total_credit = sum(
            (t["remaining_amount"] for t in credits),
            Decimal("0.00")
        )

        total_debit = sum(
            (t["remaining_amount"] for t in debits),
            Decimal("0.00")
        )

        if (
            (len(credits) > 1 and total_credit != total_debit)
            or (
                len(debits) > 1
                and total_debit > total_credit
            )
        ):
            reserved.update(t["id"] for t in items)

    active = [
        t for t in transactions
        if t["id"] not in reserved
    ]

    pending = [
        t for t in transactions
        if t["id"] in reserved
    ]

    return active, pending


def v5_validate_allocations(transactions, reconciliations):

    from collections import defaultdict

    zero = Decimal("0.00")

    by_id = {}

    for t in transactions:

        if t["id"] in by_id:
            raise ValueError(
                "Duplicate transaction identifier"
            )

        by_id[t["id"]] = t

    totals = defaultdict(lambda: zero)

    pairs = set()
    record_ids = set()

    for r in reconciliations:

        if r.get("status") != "CONFIRMED":
            continue

        rid = r["id"]

        if rid in record_ids:
            raise ValueError(
                "Duplicate reconciliation identifier"
            )

        record_ids.add(rid)

        cid = r.get("invoice_trans_id")
        did = r.get("payment_trans_id")

        if cid not in by_id or did not in by_id:
            raise ValueError(
                "Reconciliation references missing transaction"
            )

        credit = by_id[cid]
        debit = by_id[did]

        if (
            credit["trans_type"] != "CREDIT"
            or debit["trans_type"] != "DEBIT"
        ):
            raise ValueError(
                "Invalid reconciliation direction"
            )

        if (
            credit.get("job_id") != debit.get("job_id")
            or r.get("job_id") != credit.get("job_id")
        ):
            raise ValueError(
                "Cross-document reconciliation"
            )

        pair = (cid, did)

        if pair in pairs:
            raise ValueError(
                "Duplicate reconciliation pair"
            )

        pairs.add(pair)

        amount = Decimal(str(r["reconciled_amount"]))

        if not amount.is_finite():
            raise ValueError(
                "Invalid reconciliation amount"
            )

        if amount <= zero:
            raise ValueError(
                "Non-positive reconciliation amount"
            )

        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError(
                "Invalid reconciliation precision"
            )

        totals[cid] += amount
        totals[did] += amount

    for t in transactions:

        original = Decimal(str(t["amount"]))
        matched = Decimal(str(t["matched_amount"]))

        allocated = totals[t["id"]]

        if allocated != matched:
            raise ValueError(
                "Reconciliation links do not match allocated amount"
            )

        if allocated > original:
            raise ValueError(
                "Reconciliation exceeds original transaction"
            )

    return True


def run_reconciliation(
    job_id: str,
    raw_transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Executes multi-pass deterministic reconciliation over raw transactions.
    Rules and tolerances are dynamically loaded from user settings.
    """
    settings = load_settings()
    cent_tol = Decimal(str(settings.get("cent_tolerance", 0.05)))
    min_similarity = float(settings.get("supplier_similarity_threshold", 0.55))
    
    enable_exact = settings.get("enable_exact_match", True)
    enable_cent = settings.get("enable_cent_difference", True)
    enable_partial = settings.get("enable_partial_payments", True)
    enable_grouped = settings.get("enable_grouped_payments", True)
    enable_reversals = settings.get("enable_reversals", True)
    enable_duplicates = settings.get("enable_duplicate_detection", True)

    # 1. Initialize transactions with tracking fields and unique IDs
    transactions: List[Dict[str, Any]] = []
    for i, t in enumerate(raw_transactions):
        trans_id = t.get("id") or str(uuid.uuid4())
        amt = Decimal(str(t["amount"])).quantize(Decimal('0.01'))
        transactions.append({
            "id": trans_id,
            "job_id": job_id,
            "row_index": t.get("row_index", i),
            "trans_date": t["trans_date"],
            "history": t["history"],
            "trans_type": t["trans_type"], # CREDIT (Invoice) or DEBIT (Payment)
            "amount": amt,
            "reported_balance": t.get("reported_balance"),
            "extracted_nf": t.get("extracted_nf"),
            "extracted_supplier": t.get("extracted_supplier"),
            "cleaned_supplier": t.get("cleaned_supplier"),
            "category": t.get("category"),
            "status": "EM_ABERTO" if t["trans_type"] == "CREDIT" else "SEM_PROVISAO",
            "matched_amount": Decimal('0.00'),
            "remaining_amount": amt,
            "is_reversal": 0,
            "is_duplicate": 0,
            "matched_pairs": []
        })

    reconciliations: List[Dict[str, Any]] = []

    for t in transactions:
        t["extracted_nf"] = v5_reference(t) or None

    v5_duplicate_reserved = (
        v5_reserve_duplicates(transactions)
        if enable_duplicates else set()
    )

    v5_safe_reversals, v5_reversal_reserved = (
        v5_reversal_candidates([
            t for t in transactions
            if t["id"] not in v5_duplicate_reserved
        ])
    )

    v5_reversal_reserved.update(v5_duplicate_reserved)

    # 2. PASS 0: Detect Estornos / Reversals & Duplicates
    if enable_reversals or enable_duplicates:
        for i, t1 in enumerate(transactions):
            if t1["remaining_amount"] == 0:
                continue
            for j, t2 in enumerate(transactions):
                if i >= j or t2["remaining_amount"] == 0:
                    continue
                # Duplicate detection within same type
                if t1["trans_type"] == t2["trans_type"]:
                    pass
                # Reversal detection between Credit and Debit
                elif enable_reversals and t1["trans_type"] != t2["trans_type"]:
                    hist_rev = v5_safe_reversal_pair(
                        t1, t2, v5_safe_reversals
                    )
                    if hist_rev and t1["amount"] == t2["amount"]:
                        if (
                            (v5_reference(t1) and v5_reference(t1) == v5_reference(t2))
                            or (
                                not (v5_reference(t1) and v5_reference(t2))
                                and v5_supplier_match(t1, t2)
                            )
                        ):
                            t1["is_reversal"] = 1
                            t2["is_reversal"] = 1
                            t1["status"] = "ESTORNO"
                            t2["status"] = "ESTORNO"
                            t1["matched_amount"] = t1["amount"]
                            t1["remaining_amount"] = Decimal('0.00')
                            t2["matched_amount"] = t2["amount"]
                            t2["remaining_amount"] = Decimal('0.00')
                            reconciliations.append({
                                "id": str(uuid.uuid4()),
                                "job_id": job_id,
                                "match_type": "REVERSAL",
                                "invoice_trans_id": t1["id"] if t1["trans_type"] == "CREDIT" else t2["id"],
                                "payment_trans_id": t2["id"] if t1["trans_type"] == "CREDIT" else t1["id"],
                                "nf": t1["extracted_nf"] or t2["extracted_nf"],
                                "supplier": t1["extracted_supplier"] or t2["extracted_supplier"],
                                "invoice_amount": str(t1["amount"] if t1["trans_type"] == "CREDIT" else t2["amount"]),
                                "payment_amount": str(t2["amount"] if t1["trans_type"] == "CREDIT" else t1["amount"]),
                                "reconciled_amount": str(t1["amount"]),
                                "difference": "0.00",
                                "confidence_score": 1.0,
                                "status": "CONFIRMED",
                                "match_notes": "Estorno identificado e compensado mutuamente.",
                                "created_at": t1["trans_date"]
                            })

    # Group active credits and debits by NF
    credits_by_nf: Dict[str, List[Dict[str, Any]]] = {}
    debits_by_nf: Dict[str, List[Dict[str, Any]]] = {}
    
    for t in transactions:
        nf = t["extracted_nf"]
        if not nf:
            continue
        if t["trans_type"] == "CREDIT":
            credits_by_nf.setdefault(nf, []).append(t)
        else:
            debits_by_nf.setdefault(nf, []).append(t)

    all_nfs = set(credits_by_nf.keys()).union(set(debits_by_nf.keys()))


    # Reserve ambiguous items before automatic matching.
    v5_original_order = {
        t["id"]: i for i, t in enumerate(transactions)
    }

    # Unresolved reversals cannot enter ordinary matching.
    v5_pending_reversals = [
        t for t in transactions
        if t["id"] in v5_reversal_reserved
        and t["remaining_amount"] > 0
    ]

    v5_pending_ids = {
        t["id"] for t in v5_pending_reversals
    }

    transactions = [
        t for t in transactions
        if t["id"] not in v5_pending_ids
    ]

    transactions, v5_reserved = v5_partition_ambiguous(
        transactions
    )

    v5_reserved.extend(v5_pending_reversals)

    transactions, v5_allocation_reserved = (
        v5_reserve_overallocated_groups(transactions)
    )

    v5_reserved.extend(v5_allocation_reserved)

    # 3. PASS 1: Intelligent exact matching V5
    if enable_exact:
        v5_exact_pass(job_id, transactions, reconciliations)

    credits_by_nf = {}
    debits_by_nf = {}

    for t in transactions:
        nf = v5_reference(t)

        if not nf or t["remaining_amount"] <= 0:
            continue

        if t.get("is_duplicate"):
            continue

        target = (
            credits_by_nf
            if t["trans_type"] == "CREDIT"
            else debits_by_nf
        )

        target.setdefault(nf, []).append(t)

    all_nfs = sorted(set(credits_by_nf) & set(debits_by_nf))

    # 4. PASS 2: Cent Difference Matching by NF (tolerance from settings)
    if enable_cent and cent_tol > Decimal('0.00'):
        for nf in all_nfs:
            c_list = [c for c in credits_by_nf.get(nf, []) if c["remaining_amount"] > 0]
            d_list = [d for d in debits_by_nf.get(nf, []) if d["remaining_amount"] > 0]
            
            if len(c_list) == 1 and len(d_list) == 1:
                cred = c_list[0]
                deb = d_list[0]
                
                diff = abs(cred["remaining_amount"] - deb["remaining_amount"])
                if Decimal('0.00') < diff <= cent_tol:
                    matched_val = min(cred["remaining_amount"], deb["remaining_amount"])
                    signed_diff = cred["remaining_amount"] - deb["remaining_amount"]
                    
                    cred["matched_amount"] += matched_val
                    cred["remaining_amount"] = Decimal('0.00')
                    cred["status"] = "DIVERGENCIA_CENTAVOS"
                    
                    deb["matched_amount"] += matched_val
                    deb["remaining_amount"] = Decimal('0.00')
                    deb["status"] = "DIVERGENCIA_CENTAVOS"
                    
                    reconciliations.append({
                        "id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "match_type": "CENT_DIFFERENCE",
                        "invoice_trans_id": cred["id"],
                        "payment_trans_id": deb["id"],
                        "nf": nf,
                        "supplier": cred["extracted_supplier"] or deb["extracted_supplier"],
                        "invoice_amount": str(cred["amount"]),
                        "payment_amount": str(deb["amount"]),
                        "reconciled_amount": str(matched_val),
                        "difference": str(signed_diff),
                        "confidence_score": 0.98,
                        "status": "CONFIRMED",
                        "match_notes": (
                            f"Conciliado com tolerância de centavos (Diferença: R$ {signed_diff:+.2f}). "
                            f"Crédito: R$ {cred['amount']} vs Débito: R$ {deb['amount']}."
                        ),
                        "created_at": deb["trans_date"]
                    })

    # 5. PASS 3: Partial and Grouped Payments for same NF
    for nf in all_nfs:
        c_list = [c for c in credits_by_nf.get(nf, []) if c["remaining_amount"] > 0]
        d_list = [d for d in debits_by_nf.get(nf, []) if d["remaining_amount"] > 0]
        
        if len(c_list) > 1 and len(d_list) > 1:
            continue

        if not c_list or not d_list:
            continue
            
        tot_c = sum(c["remaining_amount"] for c in c_list)
        tot_d = sum(d["remaining_amount"] for d in d_list)
        
        if enable_grouped and tot_c == tot_d and (len(c_list) > 1 or len(d_list) > 1):
            for cred in c_list:
                for deb in d_list:
                    if cred["remaining_amount"] == 0 or deb["remaining_amount"] == 0:
                        continue
                    alloc = min(cred["remaining_amount"], deb["remaining_amount"])
                    cred["matched_amount"] += alloc
                    cred["remaining_amount"] -= alloc
                    deb["matched_amount"] += alloc
                    deb["remaining_amount"] -= alloc
                    
                    cred["status"] = "CONCILIADO" if cred["remaining_amount"] == 0 else "PARCIAL"
                    deb["status"] = "CONCILIADO" if deb["remaining_amount"] == 0 else "PARCIAL"
                    
                    reconciliations.append({
                        "id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "match_type": "GROUPED",
                        "invoice_trans_id": cred["id"],
                        "payment_trans_id": deb["id"],
                        "nf": nf,
                        "supplier": cred["extracted_supplier"] or deb["extracted_supplier"],
                        "invoice_amount": str(cred["amount"]),
                        "payment_amount": str(deb["amount"]),
                        "reconciled_amount": str(alloc),
                        "difference": "0.00",
                        "confidence_score": 0.95,
                        "status": "CONFIRMED",
                        "match_notes": f"Baixa agrupada/parcial por NF {nf}.",
                        "created_at": deb["trans_date"]
                    })
        elif enable_partial:
            for cred in c_list:
                for deb in d_list:
                    if cred["remaining_amount"] == 0 or deb["remaining_amount"] == 0:
                        continue
                    alloc = min(cred["remaining_amount"], deb["remaining_amount"])
                    cred["matched_amount"] += alloc
                    cred["remaining_amount"] -= alloc
                    deb["matched_amount"] += alloc
                    deb["remaining_amount"] -= alloc
                    
                    cred["status"] = "CONCILIADO" if cred["remaining_amount"] == 0 else "PARCIAL"
                    deb["status"] = "CONCILIADO" if deb["remaining_amount"] == 0 else "PARCIAL"
                    
                    reconciliations.append({
                        "id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "match_type": "PARTIAL",
                        "invoice_trans_id": cred["id"],
                        "payment_trans_id": deb["id"],
                        "nf": nf,
                        "supplier": cred["extracted_supplier"] or deb["extracted_supplier"],
                        "invoice_amount": str(cred["amount"]),
                        "payment_amount": str(deb["amount"]),
                        "reconciled_amount": str(alloc),
                        "difference": str(cred["amount"] - deb["amount"]),
                        "confidence_score": 0.90,
                        "status": "CONFIRMED",
                        "match_notes": f"Amortização parcial de título via NF {nf}. Saldo restante: R$ {cred['remaining_amount']}.",
                        "created_at": deb["trans_date"]
                    })


    # 6. PASS 4: Reevaluate remaining exact candidates
    if enable_exact:
        v5_exact_pass(job_id, transactions, reconciliations)

    # Restore every reserved transaction to accounting totals.
    transactions.extend(v5_reserved)

    transactions.sort(
        key=lambda t: v5_original_order[t["id"]]
    )

    # 7. Final status updates for remaining open items
    for t in transactions:
        if t["remaining_amount"] > 0:
            if t["trans_type"] == "CREDIT":
                t["status"] = "PARCIAL" if t["matched_amount"] > 0 else "EM_ABERTO"
            else:
                t["status"] = "PARCIAL" if t["matched_amount"] > 0 else "SEM_PROVISAO"

    # CONCILIA_V5_INTEGRITY_28_TURBO
    zero = Decimal("0.00")

    for t in transactions:
        original_value = t["amount"]
        matched = t["matched_amount"]
        remaining = t["remaining_amount"]

        if min(original_value, matched, remaining) < zero:
            raise ValueError("Negative financial amount")

        if matched + remaining > original_value:
            raise ValueError("Allocation exceeds original amount")

        if t["status"] != "DIVERGENCIA_CENTAVOS":
            if matched + remaining != original_value:
                raise ValueError("Transaction balance mismatch")

    signed_original = sum(
        (
            t["amount"] if t["trans_type"] == "DEBIT"
            else -t["amount"]
            for t in transactions
        ),
        zero
    )

    signed_unsettled = sum(
        (
            (t["amount"] - t["matched_amount"])
            * (1 if t["trans_type"] == "DEBIT" else -1)
            for t in transactions
        ),
        zero
    )

    if signed_original != signed_unsettled:
        raise ValueError("Accounting conservation failed")

    v5_validate_allocations(
        transactions,
        reconciliations
    )

    # 8. Compute Summary KPIs
    tot_credits = sum((t["amount"] for t in transactions if t["trans_type"] == "CREDIT"), Decimal('0.00'))
    tot_debits = sum((t["amount"] for t in transactions if t["trans_type"] == "DEBIT"), Decimal('0.00'))
    tot_reconciled = sum((Decimal(r["reconciled_amount"]) for r in reconciliations), Decimal('0.00'))
    
    open_invoices = [t for t in transactions if t["trans_type"] == "CREDIT" and t["remaining_amount"] > 0]
    tot_open_val = sum((t["remaining_amount"] for t in open_invoices), Decimal('0.00'))
    
    divergences = [r for r in reconciliations if r["match_type"] == "CENT_DIFFERENCE"]
    tot_cent_diff = sum((Decimal(d["difference"]) for d in divergences), Decimal('0.00'))
    
    unmapped_debits = [
        t for t in transactions
        if t["trans_type"] == "DEBIT"
        and t["remaining_amount"] > 0
    ]
    tot_unmapped_debits = sum((t["remaining_amount"] for t in unmapped_debits), Decimal('0.00'))
    
    # Composição do Saldo Final
    # Na ausência de saldo anterior (ou quando saldo anterior = 0),
    # o saldo final exercido é rigorosamente composto por:
    # (+) Notas em Aberto
    # (+) Divergências de Centavos
    # (-) Débitos/Pagamentos sem provisão
    balance_composition = {
        "open_invoices_total": str(tot_open_val),
        "open_invoices_count": len(open_invoices),
        "cent_differences_total": str(tot_cent_diff),
        "cent_differences_count": len(divergences),
        "unmapped_debits_total": str(tot_unmapped_debits),
        "unmapped_debits_count": len(unmapped_debits),
        "composed_final_balance": str(tot_unmapped_debits - tot_open_val - tot_cent_diff),
        "period_net_movement": str(tot_debits - tot_credits)
    }
    
    summary = {
        "total_transactions": len(transactions),
        "total_invoices_count": len([t for t in transactions if t["trans_type"] == "CREDIT"]),
        "total_payments_count": len([t for t in transactions if t["trans_type"] == "DEBIT"]),
        "total_credits_value": str(tot_credits),
        "total_debits_value": str(tot_debits),
        "period_net_movement": str(tot_debits - tot_credits),
        "total_reconciled_value": str(tot_reconciled),
        "reconciled_count": len([r for r in reconciliations if r["match_type"] == "EXACT_1_TO_1"]),
        "cent_differences_count": len(divergences),
        "cent_differences_total": str(tot_cent_diff),
        "partial_count": len([t for t in transactions if t["status"] == "PARCIAL"]),
        "open_invoices_count": len(open_invoices),
        "total_open_value": str(tot_open_val),
        "unreconciled_payments_count": len(unmapped_debits),
        "reconciliation_rate_pct": round(float(tot_reconciled / tot_credits * 100) if tot_credits else 0.0, 2),
        "balance_composition": balance_composition
    }

    return {
        "transactions": transactions,
        "reconciliations": reconciliations,
        "summary": summary
    }
