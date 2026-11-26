
# CONCILIA_V5_PDF_DETAILS_26C3

from decimal import Decimal

from reportlab.platypus import Spacer

from app.engine.pdf_layout_v5 import (
    brl,
    paragraph,
    build_table,
    section_heading,
    create_styles,
)

ZERO = Decimal("0.00")


def money(value):

    if value is None or value == "":
        raise ValueError("Valor financeiro ausente.")

    number = Decimal(str(value))

    if not number.is_finite():
        raise ValueError("Valor financeiro invalido.")

    return number.quantize(Decimal("0.01"))


def total_field(records, field):

    return sum(
        (money(r.get(field)) for r in records),
        ZERO
    )


def get_summary(sheets):

    records = sheets.get("Resumo gerencial", [])

    if len(records) != 1:
        raise ValueError("Resumo gerencial invalido.")

    return records[0]


def composition_totals(records):

    debit = ZERO
    credit = ZERO

    for record in records:

        value = money(record.get("value"))

        if value > ZERO:
            debit += value

        elif value < ZERO:
            credit += value

    return {
        "debit": debit,
        "credit": credit,
        "total": debit + credit,
        "count": len(records),
    }


def payment_totals(records):

    current = ZERO
    opening = ZERO

    for record in records:

        amount = money(
            record.get("reconciled_amount")
        )

        if amount < ZERO:
            raise ValueError(
                "Valor de baixa individual negativo."
            )

        if (
            record.get("origin") == "SALDO_ANTERIOR"
            or record.get("match_type") == "OPENING"
        ):

            opening += amount

        else:

            current += amount

    return {
        "current": current,
        "opening": opening,
        "total": current + opening,
        "count": len(records),
    }


def combine_fields(*values):

    return "\n".join(
        str(value)
        for value in values
        if value is not None and value != ""
    )


def composition_display_rows(records):

    result = []

    for record in records:

        row = dict(record)

        row["identification"] = combine_fields(
            record.get("nf"),
            record.get("supplier"),
        )

        row["description"] = combine_fields(
            record.get("kind"),
            record.get("history"),
        )

        row["trace"] = combine_fields(
            record.get("status"),
            record.get("transaction_id"),
        )

        result.append(row)

    return result


def payment_display_rows(records):

    result = []

    for record in records:

        row = dict(record)

        previous = (
            record.get("origin") == "SALDO_ANTERIOR"
            or record.get("match_type") == "OPENING"
        )

        row["display_origin"] = (
            "Saldo anterior"
            if previous
            else "Periodo atual"
        )

        row["identification"] = combine_fields(
            record.get("nf"),
            record.get("supplier"),
        )

        row["trace"] = combine_fields(
            row["display_origin"],
            record.get("match_type"),
            record.get("reconciliation_id"),
        )

        result.append(row)

    return result


def build_composition_section(sheets, styles=None):

    styles = styles or create_styles()

    summary = get_summary(sheets)

    if "Composicao do saldo" not in sheets:
        raise ValueError("Composicao ausente.")

    records = sheets["Composicao do saldo"]

    totals = composition_totals(records)

    expected = money(
        summary.get("composition_total")
    )

    reported = money(
        summary.get("final_reported_balance")
    )

    difference = totals["total"] - reported

    snapshot_consistent = (
        totals["total"] == expected
        and difference == money(
            summary.get("composition_difference")
        )
    )

    elements = [

        section_heading(
            3,
            "Composi\u00e7\u00e3o do saldo final",
            styles
        ),

        paragraph(
            "Demonstrativo analitico de todos os "
            "residuos que compoem o saldo contabil.",
            styles["body"]
        ),

        build_table(
            [
                {
                    "indicator": "Residuos devedores",
                    "amount": totals["debit"],
                },
                {
                    "indicator": "Residuos credores",
                    "amount": totals["credit"],
                },
                {
                    "indicator": "Saldo final composto",
                    "amount": totals["total"],
                },
                {
                    "indicator": "Saldo final do razao",
                    "amount": reported,
                },
                {
                    "indicator": "Diferenca contabil",
                    "amount": difference,
                },
            ],
            [
                ("indicator", "Indicador", 3, "text"),
                ("amount", "Valor D+/C-", 2, "money"),
            ],
            styles
        ),

        Spacer(1, 10),
    ]

    if not snapshot_consistent:

        elements.append(
            paragraph(
                "ATENCAO: os residuos apresentados "
                "divergem dos totais do snapshot. "
                "Revisao obrigatoria.",
                styles["danger"]
            )
        )

    elif (
        difference == ZERO
        and summary.get("composition_valid") is True
    ):

        elements.append(
            paragraph(
                "Composicao matematica validada.",
                styles["success"]
            )
        )

    else:

        elements.append(
            paragraph(
                "Composicao contabil requer revisao.",
                styles["warning"]
            )
        )

    elements.append(Spacer(1, 8))

    elements.append(
        paragraph(
            "Quantidade de componentes: "
            + str(totals["count"]),
            styles["body"]
        )
    )

    elements.append(
        paragraph(
            "A coluna Saldo D+/C- representa o "
            "valor efetivamente integrante do saldo. "
            "Valores originais e baixados sao "
            "informativos e nao devem ser somados "
            "para calcular o saldo final.",
            styles["body"]
        )
    )

    elements.append(
        build_table(
            composition_display_rows(records),
            [
                ("date", "Data", 1.1, "date"),
                ("identification", "NF / Fornecedor", 2.1, "text"),
                ("description", "Origem / Historico", 3.0, "text"),
                ("original", "Original", 1.5, "money"),
                ("matched_amount", "Baixado", 1.5, "money"),
                ("remaining_amount", "Residual", 1.5, "money"),
                ("value", "Saldo D+/C-", 1.6, "money"),
                ("trace", "Situacao / ID", 1.8, "text"),
            ],
            styles
        )
    )

    return elements


def build_payment_section(sheets, styles=None):

    styles = styles or create_styles()

    if "Detalhamento das Baixas" not in sheets:
        raise ValueError("Detalhamento ausente.")

    records = sheets["Detalhamento das Baixas"]

    totals = payment_totals(records)

    elements = [

        section_heading(
            4,
            "Detalhamento individual das baixas",
            styles
        ),

        paragraph(
            "Cada registro representa uma baixa "
            "individual disponibilizada pelo motor "
            "de conciliacao.",
            styles["body"]
        ),

        build_table(
            [
                {
                    "indicator": "Baixas do periodo atual",
                    "amount": totals["current"],
                },
                {
                    "indicator": "Baixas do saldo anterior",
                    "amount": totals["opening"],
                },
                {
                    "indicator": "Total das baixas detalhadas",
                    "amount": totals["total"],
                },
            ],
            [
                ("indicator", "Origem", 3, "text"),
                ("amount", "Valor aplicado", 2, "money"),
            ],
            styles
        ),

        Spacer(1, 8),

        paragraph(
            "Quantidade de baixas individuais: "
            + str(totals["count"]),
            styles["body"]
        ),

        paragraph(
            "Somente a coluna Baixa individual deve "
            "ser somada para obter o total aplicado. "
            "O valor original, o total acumulado e "
            "o residual da NF podem se repetir em "
            "varios pagamentos vinculados a mesma NF.",
            styles["body"]
        ),

        paragraph(
            "Os saldos apresentados representam "
            "a posicao atual do documento, e nao "
            "o saldo historico apos cada pagamento.",
            styles["body"]
        ),

        build_table(
            payment_display_rows(records),
            [
                ("identification", "NF / Fornecedor", 2.1, "text"),
                ("invoice_date", "Data NF", 1.0, "date"),
                ("invoice_amount", "Original NF", 1.5, "money"),
                ("payment_date", "Data baixa", 1.0, "date"),
                ("payment_amount", "Pagamento", 1.5, "money"),
                ("reconciled_amount", "Baixa individual", 1.5, "money"),
                ("matched_amount", "Baixado acumulado", 1.5, "money"),
                ("remaining_amount", "Residual atual", 1.5, "money"),
                ("status", "Situacao", 1.0, "status"),
                ("display_origin", "Origem", 1.2, "text"),
            ],
            styles
        ),
    ]

    elements.append(Spacer(1, 12))

    elements.append(
        paragraph(
            "Historicos e rastreabilidade das baixas",
            styles["section"]
        )
    )

    elements.append(
        build_table(
            payment_display_rows(records),
            [
                ("identification", "NF / Fornecedor", 2.0, "text"),
                ("invoice_history", "Historico da provisao", 2.7, "text"),
                ("payment_history", "Historico do pagamento", 2.7, "text"),
                ("reconciled_amount", "Valor aplicado", 1.4, "money"),
                ("invoice_row", "Linha NF", 0.7, "text"),
                ("payment_row", "Linha baixa", 0.7, "text"),
                ("trace", "Origem / Tipo / ID", 2.0, "text"),
                ("match_notes", "Motivo", 2.0, "text"),
            ],
            styles
        )
    )

    return elements
