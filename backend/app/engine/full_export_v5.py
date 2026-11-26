# CONCILIA_V5_FULL_EXPORT_25D

from decimal import Decimal
from datetime import datetime
from copy import deepcopy

from app.engine.composition import money


SHEET_NAMES = (
    "Resumo gerencial",
    "Validacao contabil",
    "Composicao do saldo",
    "Detalhamento das Baixas",
    "Saldo anterior original",
    "Saldo anterior residual",
    "Conciliados",
    "Notas em aberto",
    "Debitos pendentes",
    "Divergencias",
    "Sugestoes inteligentes",
    "Sugestoes saldo anterior",
    "Fornecedores",
    "Historico de desfazimentos",
    "Lancamentos originais",
)


def clean_records(records):

    return [
        {
            k: deepcopy(v)
            for k, v in dict(record).items()
            if k not in (
                "job_id",
                "opening_hash",
                "file_path",
                "metadata_json",
                "math_explanation",
            )
        }
        for record in (records or [])
    ]


def scalar_fields(data):

    return {
        k: v
        for k, v in (data or {}).items()
        if isinstance(
            v,
            (str, int, float, bool, Decimal)
        ) or v is None
    }


def build_full_sheets_v5(
    *,
    job,
    summary,
    composition,
    transactions,
    reconciliations,
    opening_original=None,
    opening_rows=None,
    current_suggestions=None,
    opening_suggestions=None,
    suppliers=None,
    undo_history=None,
    math_audit=None,
):

    zero = Decimal("0.00")

    tx = clean_records(transactions)

    active = [
        r for r in clean_records(reconciliations)
        if r.get("status") == "CONFIRMED"
    ]

    opened = [
        r for r in tx
        if r.get("trans_type") == "CREDIT"
        and money(r.get("remaining_amount")) > zero
    ]

    pending = [
        r for r in tx
        if r.get("trans_type") == "DEBIT"
        and money(r.get("remaining_amount")) > zero
    ]

    divergences = [
        r for r in active
        if r.get("match_type") in (
            "CENT_DIFFERENCE",
            "PARTIAL",
        )
    ]

    indicators = scalar_fields(
        summary.get("indicators_v5", {})
    )

    initial = money(job["initial_balance"])
    debits = money(job["total_debits"])
    credits = money(job["total_credits"])
    reported = money(job["final_reported_balance"])

    calculated = initial + debits - credits

    rows = clean_records(
        composition.get("rows", [])
    )

    composed = sum(
        (money(r["value"]) for r in rows),
        zero
    )

    opening_attached = opening_original is not None

    opening_documented = sum(
        (
            money(r["value"])
            for r in (opening_original or [])
        ),
        zero
    )

    opening_difference = (
        initial - opening_documented
    )

    details = clean_records(
        composition.get("payment_details", [])
    )

    current_items = clean_records(
        current_suggestions
    )

    previous_items = clean_records(
        opening_suggestions
    )

    for item in current_items + previous_items:

        item["suggestion_status"] = (
            "PENDENTE DE APROVACAO"
        )

    valid = (
        bool(composition.get("valid"))
        and calculated == reported
        and composed == reported
        and bool(tx)
    )

    managerial = {
        "Empresa": job.get("company_name"),
        "CNPJ": job.get("cnpj"),
        "Periodo": job.get("period"),
        "Documento": job.get("filename"),
        "Gerado em": datetime.now().isoformat(
            sep=" ",
            timespec="seconds"
        ),
        "initial_balance": str(initial),
        "total_debits": str(debits),
        "total_credits": str(credits),
        "final_reported_balance": str(reported),
        "composition_total": str(composed),
        "composition_difference": str(
            composed - reported
        ),
        "composition_valid": valid,
        "opening_attached": opening_attached,
        "opening_difference": str(
            opening_difference
        ),
        "opening_complete": (
            opening_attached
            and opening_difference == zero
        ),
        **indicators,
        "Total de lancamentos": len(tx),
        "Total de baixas detalhadas": len(details),
        "Sugestoes atuais": len(current_items),
        "Sugestoes anteriores": len(previous_items),
        "Observacao": (
            "Debitos positivos e creditos negativos "
            "nas colunas de saldo assinado. "
            "Sugestoes nao representam baixas realizadas."
        ),
    }

    def validation_row(
        name,
        actual,
        expected,
        observation=""
    ):

        actual = money(actual)
        expected = money(expected)

        difference = actual - expected

        return {
            "Verificacao": name,
            "validation_actual": str(actual),
            "validation_expected": str(expected),
            "difference": str(difference),
            "status": (
                "VALIDADO"
                if difference == zero
                else "DIVERGENTE"
            ),
            "Observacao": observation,
        }

    validation = [

        validation_row(
            "Equacao contabil",
            calculated,
            reported,
            "Saldo anterior + debitos - creditos."
        ),

        validation_row(
            "Composicao do saldo final",
            composed,
            reported,
            "Soma dos residuos assinados."
        ),

        validation_row(
            "Documentacao do saldo anterior",
            opening_documented,
            initial,
            "Diferenca nao comprovada permanece "
            "separada da conciliacao."
        ),
    ]

    validation[-1]["status"] = (
        "NAO ANEXADO"
        if not opening_attached
        else (
            "VALIDADO"
            if opening_difference == zero
            else "NAO COMPROVADO"
        )
    )

    validation.append({
        "Verificacao": "Resultado geral",
        "status": (
            "VALIDADO" if valid else "REVISAR"
        ),
        "Observacao": (
            "A validade matematica nao implica "
            "comprovacao integral do saldo anterior."
        ),
    })

    for key, value in scalar_fields(
        math_audit
    ).items():

        validation.append({
            "Verificacao": "Auditoria: " + key,
            "Observacao": str(value),
        })

    sheets = {
        "Resumo gerencial": [managerial],
        "Validacao contabil": validation,
        "Composicao do saldo": rows,
        "Detalhamento das Baixas": details,
        "Saldo anterior original": clean_records(
            opening_original
        ),
        "Saldo anterior residual": clean_records(
            opening_rows
        ),
        "Conciliados": active,
        "Notas em aberto": opened,
        "Debitos pendentes": pending,
        "Divergencias": divergences,
        "Sugestoes inteligentes": current_items,
        "Sugestoes saldo anterior": previous_items,
        "Fornecedores": clean_records(suppliers),
        "Historico de desfazimentos": clean_records(
            undo_history
        ),
        "Lancamentos originais": tx,
    }

    if tuple(sheets) != SHEET_NAMES:

        raise RuntimeError(
            "Estrutura do relatorio invalida."
        )

    return sheets
