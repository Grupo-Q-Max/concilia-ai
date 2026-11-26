
# CONCILIA_V5_MANUAL_SAFETY_30A3A

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def strict_money_v5(value):

    if value is None or isinstance(value, bool):
        raise ValueError("Valor financeiro ausente ou invalido.")

    try:

        result = Decimal(str(value))

        if not result.is_finite():
            raise ValueError("Valor financeiro nao finito.")

        if result != result.quantize(CENT):
            raise ValueError("Precisao financeira invalida.")

        return result.quantize(CENT)

    except (InvalidOperation, TypeError):

        raise ValueError("Valor financeiro invalido.")


def validate_manual_transaction_v5(transaction):

    from app.engine.reconciler import v5_has_reversal_marker

    t = dict(transaction)

    if t.get("is_duplicate") or t.get("is_reversal"):

        raise ValueError(
            "Duplicidade ou estorno exige revisao especifica."
        )

    if v5_has_reversal_marker(t):

        raise ValueError(
            "Estorno pendente exige revisao especifica."
        )

    allowed = {
        "EM_ABERTO",
        "SEM_PROVISAO",
        "PARCIAL"
    }

    if t.get("status") not in allowed:

        raise ValueError(
            "Situacao do lancamento nao permite baixa manual."
        )

    original = strict_money_v5(t.get("amount"))

    matched = strict_money_v5(t.get("matched_amount"))

    remaining = strict_money_v5(t.get("remaining_amount"))

    if original <= ZERO:

        raise ValueError(
            "Valor original deve ser positivo."
        )

    if matched < ZERO or remaining <= ZERO:

        raise ValueError(
            "Lancamento sem saldo disponivel ou inconsistente."
        )

    if matched + remaining != original:

        raise ValueError(
            "Valor original difere da soma baixada e residual."
        )

    if t["status"] == "PARCIAL" and matched <= ZERO:

        raise ValueError(
            "Lancamento parcial sem baixa registrada."
        )

    if t["status"] != "PARCIAL" and matched > ZERO:

        raise ValueError(
            "Lancamento aberto com baixa inconsistente."
        )

    return {
        "original": original,
        "matched": matched,
        "remaining": remaining
    }


def validate_manual_links_v5(conn, job_id, transaction):

    t = dict(transaction)

    financial = validate_manual_transaction_v5(t)

    tid = t["id"]

    if t.get("job_id") != job_id:

        raise ValueError(
            "Lancamento pertence a outro documento."
        )

    if t["trans_type"] == "CREDIT":

        field = "invoice_trans_id"
        opposite = "payment_trans_id"
        opposite_type = "DEBIT"

    elif t["trans_type"] == "DEBIT":

        field = "payment_trans_id"
        opposite = "invoice_trans_id"
        opposite_type = "CREDIT"

    else:

        raise ValueError("Natureza contabil invalida.")

    records = conn.execute(
        f"""
        SELECT * FROM reconciliations
        WHERE {field}=?
        AND status='CONFIRMED'
        """,
        (tid,)
    ).fetchall()

    total = ZERO
    seen = set()

    for record in records:

        r = dict(record)

        if r["job_id"] != job_id:

            raise ValueError(
                "Vinculo pertence a outro documento."
            )

        other_id = r.get(opposite)

        if not other_id or other_id in seen:

            raise ValueError(
                "Vinculo ausente ou repetido."
            )

        seen.add(other_id)

        other = conn.execute(
            """
            SELECT id, trans_type
            FROM transactions
            WHERE id=? AND job_id=?
            """,
            (other_id, job_id)
        ).fetchone()

        if not other or other["trans_type"] != opposite_type:

            raise ValueError(
                "Contraparte financeira invalida."
            )

        amount = strict_money_v5(
            r.get("reconciled_amount")
        )

        if amount <= ZERO:

            raise ValueError(
                "Vinculo financeiro nao positivo."
            )

        total += amount

    if t["trans_type"] == "DEBIT":

        opening_links = conn.execute(
            """
            SELECT job_id, amount
            FROM opening_matches_v5
            WHERE payment_trans_id=?
            """,
            (tid,)
        ).fetchall()

        for record in opening_links:

            if record["job_id"] != job_id:

                raise ValueError(
                    "Baixa anterior pertence a outro documento."
                )

            amount = strict_money_v5(record["amount"])

            if amount <= ZERO:

                raise ValueError(
                    "Baixa anterior com valor invalido."
                )

            total += amount

    if total != financial["matched"]:

        raise ValueError(
            "Total dos vinculos difere do valor baixado."
        )

    return financial


def validate_manual_composition_v5(composition):

    if not composition.get("valid"):

        raise ValueError(
            "Composicao contabil invalida."
        )

    total = strict_money_v5(
        composition.get("total")
    )

    difference = strict_money_v5(
        composition.get("difference")
    )

    if difference != ZERO:

        raise ValueError(
            "Composicao apresenta diferenca contabil."
        )

    opening_difference = strict_money_v5(
        composition.get("opening_difference", ZERO)
    )

    return total, opening_difference


def validate_manual_transition_v5(before, after):

    first = validate_manual_composition_v5(before)

    second = validate_manual_composition_v5(after)

    if first != second:

        raise ValueError(
            "Baixa alterou o saldo contabil ou a diferenca anterior."
        )

    return True


def validate_manual_result_v5(before, after, amount):

    amount = strict_money_v5(amount)

    original = strict_money_v5(after.get("amount"))

    matched = strict_money_v5(after.get("matched_amount"))

    remaining = strict_money_v5(after.get("remaining_amount"))

    if amount <= ZERO:

        raise ValueError("Baixa deve ser positiva.")

    if original != before["original"]:

        raise ValueError("Valor original foi alterado.")

    if matched != before["matched"] + amount:

        raise ValueError("Valor baixado incorreto.")

    if remaining != before["remaining"] - amount:

        raise ValueError("Saldo residual incorreto.")

    if remaining < ZERO or matched + remaining != original:

        raise ValueError("Resultado financeiro inconsistente.")

    expected_status = (
        "CONCILIADO" if remaining == ZERO else "PARCIAL"
    )

    if after.get("status") != expected_status:

        raise ValueError("Situacao financeira incorreta.")

    return True



# CONCILIA_V5_STALE_APPROVAL_30A3C1

def validate_expected_residuals_v5(
    payload,
    invoice_remaining,
    payment_remaining
):

    source = getattr(
        payload, "approval_source", "MANUAL"
    )

    if source not in {
        "MANUAL", "SUGGESTION", "BATCH"
    }:

        raise ValueError(
            "Origem da aprovacao invalida."
        )

    expected_invoice = getattr(
        payload,
        "expected_invoice_remaining",
        None
    )

    expected_payment = getattr(
        payload,
        "expected_payment_remaining",
        None
    )

    # CONCILIA_V5_MANDATORY_APPROVAL_30A3C4B
    if (
        expected_invoice is None
        or expected_payment is None
    ):

        raise ValueError(
            "Informe os dois saldos esperados."
        )

    expected_invoice = strict_money_v5(
        expected_invoice
    )

    expected_payment = strict_money_v5(
        expected_payment
    )

    current_invoice = strict_money_v5(
        invoice_remaining
    )

    current_payment = strict_money_v5(
        payment_remaining
    )

    if (
        expected_invoice <= ZERO
        or expected_payment <= ZERO
    ):

        raise ValueError(
            "Saldos esperados devem ser positivos."
        )

    if (
        expected_invoice != current_invoice
        or expected_payment != current_payment
    ):

        raise ValueError(
            "Os saldos foram alterados. "
            "Atualize os dados antes de aprovar."
        )

    if source == "MANUAL":

        if getattr(
            payload, "confirm_review", False
        ) is not True:

            raise ValueError(
                "Confirme a revisao individual "
                "antes de concluir a baixa manual."
            )

    return True



# CONCILIA_V5_SERVER_APPROVAL_30A3C3A

def validate_suggestion_approval_v5(
    payload,
    invoice,
    payment,
    suggestions
):

    source = getattr(
        payload, "approval_source", "MANUAL"
    )

    if source not in {
        "MANUAL", "SUGGESTION", "BATCH"
    }:

        raise ValueError(
            "Origem da aprovacao invalida."
        )

    if source == "MANUAL":

        return None

    validate_expected_residuals_v5(
        payload,
        invoice["remaining_amount"],
        payment["remaining_amount"]
    )

    matches = [
        s for s in suggestions
        if s.get("invoice_trans_id") == invoice["id"]
        and s.get("payment_trans_id") == payment["id"]
    ]

    if len(matches) != 1:

        raise ValueError(
            "Sugestao inexistente ou alterada. "
            "Atualize os candidatos."
        )

    candidate = matches[0]

    invoice_remaining = strict_money_v5(
        invoice["remaining_amount"]
    )

    payment_remaining = strict_money_v5(
        payment["remaining_amount"]
    )

    if (
        strict_money_v5(
            candidate.get("invoice_remaining")
        ) != invoice_remaining
        or strict_money_v5(
            candidate.get("payment_remaining")
        ) != payment_remaining
    ):

        raise ValueError(
            "Os saldos da sugestao foram alterados."
        )

    amount = strict_money_v5(
        candidate.get("suggested_amount")
    )

    if (
        amount <= ZERO
        or amount != min(
            invoice_remaining,
            payment_remaining
        )
    ):

        raise ValueError(
            "Valor sugerido inconsistente."
        )

    category = candidate.get("category")

    if category not in {
        "COMPATIVEL",
        "DIVERGENCIA_NF",
        "PARCIAL",
        "BAIXA_EVIDENCIA"
    }:

        raise ValueError(
            "Categoria de sugestao desconhecida."
        )

    score = candidate.get("score")

    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not 0 <= score <= 100
    ):

        raise ValueError(
            "Pontuacao da sugestao invalida."
        )

    requires_review = (
        category != "COMPATIVEL"
        or bool(candidate.get("ambiguous"))
        or bool(candidate.get("fiscal_equivalent"))
        or bool(candidate.get("requires_individual_review"))
        or score < 95
        or invoice_remaining != payment_remaining
    )

    if source == "BATCH":

        if (
            requires_review
            or candidate.get("batch_eligible") is not True
        ):

            raise ValueError(
                "Sugestao nao elegivel para aprovacao em lote. "
                "Realize a revisao individual."
            )

    elif requires_review:

        if getattr(
            payload, "confirm_review", False
        ) is not True:

            raise ValueError(
                "Esta sugestao exige confirmacao "
                "individual de revisao."
            )

    return {
        "approval_source": source,
        "category": category,
        "score": score,
        "reason": candidate.get("reason"),
        "ambiguous": bool(
            candidate.get("ambiguous")
        ),
        "fiscal_equivalent": bool(
            candidate.get("fiscal_equivalent")
        ),
        "review_confirmed": bool(
            getattr(payload, "confirm_review", False)
        ),
        "approved_amount": str(amount)
    }

