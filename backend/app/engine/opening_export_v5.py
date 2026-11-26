
from datetime import datetime
from decimal import Decimal
from app.engine.composition import money


def opening_sheets_v5(job, original, rows, links, items, composition):

    rows = [dict(r) for r in rows]
    items = [dict(s) for s in items]

    partial = [
        s for s in items
        if s.get("category") == "PARCIAL"
    ]

    divergences = [
        s for s in items
        if s.get("category") == "DIVERGENCIA_NF"
    ]

    ambiguous = [
        s for s in items
        if s.get("ambiguous")
        or s.get("current_conflict")
    ]

    eligible = [
        s for s in items
        if s.get("automatic_eligible")
        and not s.get("ambiguous")
        and not s.get("current_conflict")
    ]

    details = [
        dict(r)
        for r in composition.get("payment_details", [])
        if r.get("match_type") == "OPENING"
        or r.get("origin") == "SALDO_ANTERIOR"
    ]

    paid = sum(
        (money(r["amount"]) for r in links),
        Decimal("0.00")
    )

    original_total = sum(
        (money(r.get("value")) for r in (original or [])),
        Decimal("0.00")
    )

    residual_total = sum(
        (money(r.get("value")) for r in rows),
        Decimal("0.00")
    )

    initial = money(job["initial_balance"])
    unproven = initial - original_total

    summary = [{
        "Empresa": job.get("company_name"),
        "Periodo": job.get("period"),
        "Documento": job.get("filename"),
        "Gerado em": datetime.now().isoformat(
            sep=" ", timespec="seconds"
        ),
        "opening_attached": original is not None,
        "initial_balance": str(initial),
        "opening_original_signed": str(original_total),
        "opening_residual_signed": str(residual_total),
        "opening_matched_total": str(paid),
        "opening_difference": str(unproven),
        "opening_complete": (
            original is not None and unproven == 0
        ),
        "Total de sugestoes": len(items),
        "Parciais": len(partial),
        "Divergencias de NF": len(divergences),
        "Ambiguas ou conflitantes": len(ambiguous),
        "Elegiveis": len(eligible),
        "Baixas realizadas": len(links),
        "composition_total": composition.get("total"),
        "composition_reported": composition.get("reported"),
        "composition_difference": composition.get("difference"),
        "composition_valid": composition.get("valid"),
        "Observacao": (
            "Sugestoes nao representam baixas confirmadas. "
            "As classificacoes podem se sobrepor. "
            "Valores positivos representam debitos e "
            "negativos representam creditos. "
            "A exportacao nao altera conciliacoes."
        )
    }]

    def clean(records):
        return [
            {
                k: v for k, v in r.items()
                if k not in ("opening_hash", "job_id")
            }
            for r in records
        ]

    return {
        "Resumo gerencial": summary,
        "Composicao anterior": clean(rows),
        "Todas as sugestoes": clean(items),
        "Baixas parciais": clean(partial),
        "Divergencias de NF": clean(divergences),
        "Ambiguas e conflitos": clean(ambiguous),
        "Elegiveis": clean(eligible),
        "Detalhamento das Baixas": details
    }
