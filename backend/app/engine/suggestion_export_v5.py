
from datetime import datetime
from decimal import Decimal


def suggestion_sheets_v5(job, items):

    items = [dict(item) for item in items]

    compatible = [
        s for s in items
        if s["category"] == "COMPATIVEL"
    ]

    partial = [
        s for s in items
        if s["category"] == "PARCIAL"
    ]

    divergences = [
        s for s in items
        if s["category"] == "DIVERGENCIA_NF"
    ]

    ambiguous = [
        s for s in items
        if s.get("ambiguous")
    ]

    low_evidence = [
        s for s in items
        if s["category"] == "BAIXA_EVIDENCIA"
    ]

    eligible = [
        s for s in items
        if s.get("batch_eligible")
        and not s.get("ambiguous")
        and s["category"] == "COMPATIVEL"
        and s["score"] >= 95
    ]

    inv_ids = [
        s["invoice_trans_id"] for s in eligible
    ]

    pay_ids = [
        s["payment_trans_id"] for s in eligible
    ]

    if (
        len(inv_ids) != len(set(inv_ids))
        or len(pay_ids) != len(set(pay_ids))
    ):
        raise ValueError(
            "Sugestoes elegiveis possuem vinculos repetidos."
        )

    eligible_value = sum(
        (
            Decimal(str(s["suggested_amount"]))
            for s in eligible
        ),
        Decimal("0.00")
    )

    def rows(records):
        result = []

        for s in records:
            result.append({
                "category": s["category"],
                "score": s["score"],
                "ambiguous": bool(s.get("ambiguous")),
                "batch_eligible": bool(
                    s.get("batch_eligible")
                ),
                "invoice_nf": s.get("invoice_nf"),
                "invoice_supplier": s.get("invoice_supplier"),
                "invoice_date": s.get("invoice_date"),
                "invoice_remaining": s["invoice_remaining"],
                "payment_nf": s.get("payment_nf"),
                "payment_supplier": s.get("payment_supplier"),
                "payment_date": s.get("payment_date"),
                "payment_remaining": s["payment_remaining"],
                "suggested_amount": s["suggested_amount"],
                "invoice_after": s["invoice_after"],
                "payment_after": s["payment_after"],
                "reason": s.get("reason"),
                "invoice_history": s.get("invoice_history"),
                "payment_history": s.get("payment_history"),
                "invoice_trans_id": s["invoice_trans_id"],
                "payment_trans_id": s["payment_trans_id"],
                "suggestion_status": "PENDENTE DE APROVACAO"
            })

        return result

    summary = [{
        "Empresa": job.get("company_name"),
        "Periodo": job.get("period"),
        "Documento": job.get("filename"),
        "Gerado em": datetime.now().isoformat(
            sep=" ", timespec="seconds"
        ),
        "Total de sugestoes": len(items),
        "Compativeis": len(compatible),
        "Parciais": len(partial),
        "Divergencias de NF": len(divergences),
        "Ambiguas": len(ambiguous),
        "Baixa evidencia": len(low_evidence),
        "Elegiveis em lote": len(eligible),
        "eligible_value": str(eligible_value),
        "Situacao": "RELATORIO INFORMATIVO",
        "Observacao": (
            "As abas podem compartilhar sugestoes. "
            "Valores projetados nao representam baixas "
            "confirmadas. Nenhuma conciliacao foi aprovada "
            "pela exportacao."
        )
    }]

    return {
        "Resumo gerencial": summary,
        "Todas as sugestoes": rows(items),
        "Compativeis": rows(compatible),
        "Baixas parciais": rows(partial),
        "Divergencias de NF": rows(divergences),
        "Ambiguas": rows(ambiguous),
        "Baixa evidencia": rows(low_evidence),
        "Elegiveis em lote": rows(eligible)
    }
