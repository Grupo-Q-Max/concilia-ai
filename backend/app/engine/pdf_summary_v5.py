
# CONCILIA_V5_PDF_SUMMARY_26C2

from reportlab.platypus import Spacer

from app.engine.pdf_layout_v5 import (
    brl,
    percentage,
    paragraph,
    build_table,
    section_heading,
    create_styles,
)


FINANCIAL_FIELDS = (
    ("initial_balance", "Saldo anterior contabil"),
    ("total_debits", "Debitos do periodo"),
    ("total_credits", "Creditos do periodo"),
    ("final_reported_balance", "Saldo final do razao"),
    ("composition_total", "Saldo final composto"),
    ("composition_difference", "Diferenca contabil"),
    ("opening_difference", "Saldo anterior nao comprovado"),
)


CREDIT_GROUPS = (
    (
        "Creditos do periodo",
        "current_credit_original",
        "current_credit_matched",
        "current_credit_residual",
        "current_credit_rate_pct",
    ),
    (
        "Debitos do periodo",
        "current_debit_original",
        "current_debit_matched",
        "current_debit_residual",
        "current_debit_rate_pct",
    ),
    (
        "Creditos anteriores documentados",
        "opening_credit_original",
        "opening_credit_matched",
        "opening_credit_residual",
        "opening_rate_pct",
    ),
)


COUNT_FIELDS = (
    ("active_reconciliations_count",
        "Registros ativos de conciliacao"),
    ("active_opening_matches_count",
        "Baixas ativas do saldo anterior"),
    ("settled_invoices_count",
        "Notas integralmente quitadas"),
    ("partial_invoices_count",
        "Notas parcialmente baixadas"),
    ("untouched_invoices_count",
        "Notas sem baixa"),
    ("partial_payments_count",
        "Pagamentos parcialmente utilizados"),
    ("opening_settled_count",
        "Notas anteriores quitadas"),
    ("opening_partial_count",
        "Notas anteriores parciais"),
    ("undone_count",
        "Desfazimentos registrados"),
    ("Total de lancamentos",
        "Lancamentos originais"),
    ("Total de baixas detalhadas",
        "Baixas individuais detalhadas"),
    ("Sugestoes atuais",
        "Sugestoes do periodo"),
    ("Sugestoes anteriores",
        "Sugestoes do saldo anterior"),
)


def composition_status(summary):

    if summary.get("composition_valid") is True:
        return "VALIDADO"

    return "REVISAR"


def opening_status(summary):

    if summary.get("opening_attached") is not True:
        return "NAO ANEXADO"

    if summary.get("opening_complete") is True:
        return "VALIDADO"

    return "NAO COMPROVADO"


def financial_rows(summary):

    return [
        {
            "indicator": label,
            "value": summary.get(key),
        }
        for key, label in FINANCIAL_FIELDS
    ]


def credit_rows(summary):

    return [
        {
            "group": label,
            "original": summary.get(original),
            "matched": summary.get(matched),
            "residual": summary.get(residual),
            "rate": summary.get(rate),
        }
        for label, original, matched, residual, rate
        in CREDIT_GROUPS
    ]


def count_rows(summary):

    return [
        {
            "indicator": label,
            "count": summary.get(key),
        }
        for key, label in COUNT_FIELDS
    ]


def build_summary_section(sheets, styles=None):

    styles = styles or create_styles()

    records = sheets.get("Resumo gerencial", [])

    if len(records) != 1:
        raise ValueError(
            "Resumo gerencial ausente ou ambiguo."
        )

    summary = records[0]

    elements = [

        paragraph(
            "Relat\u00f3rio de Concilia\u00e7\u00e3o Cont\u00e1bil",
            styles["title"]
        ),

        paragraph(
            "Demonstrativo gerencial e anal\u00edtico",
            styles["subtitle"]
        ),

        section_heading(
            1,
            "Resumo gerencial",
            styles
        ),
    ]

    identification = [
        {
            "field": "Empresa",
            "value": summary.get("Empresa"),
        },
        {
            "field": "CNPJ",
            "value": summary.get("CNPJ"),
        },
        {
            "field": "Periodo",
            "value": summary.get("Periodo"),
        },
        {
            "field": "Documento",
            "value": summary.get("Documento"),
        },
        {
            "field": "Gerado em",
            "value": summary.get("Gerado em"),
        },
    ]

    elements.append(
        build_table(
            identification,
            [
                ("field", "Identificacao", 1, "text"),
                ("value", "Informacao", 4, "text"),
            ],
            styles
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(
        paragraph(
            "Posi\u00e7\u00e3o financeira e cont\u00e1bil",
            styles["section"]
        )
    )

    elements.append(
        build_table(
            financial_rows(summary),
            [
                ("indicator", "Indicador", 3, "text"),
                ("value", "Valor em reais", 2, "money"),
            ],
            styles
        )
    )

    elements.append(Spacer(1, 10))

    elements.append(
        paragraph(
            "Convencao contabil: debitos positivos "
            "e creditos negativos nos saldos assinados. "
            "Totais de movimentos e baixas sao "
            "apresentados por magnitude.",
            styles["body"]
        )
    )

    elements.append(
        paragraph(
            "Indicadores de baixas e valores residuais",
            styles["section"]
        )
    )

    elements.append(
        build_table(
            credit_rows(summary),
            [
                ("group", "Grupo", 2.8, "text"),
                ("original", "Original", 1.8, "money"),
                ("matched", "Baixado / utilizado", 1.8, "money"),
                ("residual", "Residual", 1.8, "money"),
                ("rate", "Percentual", 1.2, "percentage"),
            ],
            styles
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        paragraph(
            "Percentual consolidado de creditos baixados: "
            + percentage(
                summary.get("combined_credit_rate_pct")
            ),
            styles["body"]
        )
    )

    elements.append(
        paragraph(
            "Os indicadores de baixas consideram os "
            "lancamentos elegiveis. Podem diferir dos "
            "totais brutos do razao.",
            styles["body"]
        )
    )

    elements.append(
        paragraph(
            "Indicadores operacionais",
            styles["section"]
        )
    )

    elements.append(
        build_table(
            count_rows(summary),
            [
                ("indicator", "Indicador", 4, "text"),
                ("count", "Quantidade", 1, "text"),
            ],
            styles
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        paragraph(
            "Sugestoes inteligentes nao representam "
            "baixas confirmadas e podem se sobrepor.",
            styles["body"]
        )
    )

    return elements


def build_validation_section(sheets, styles=None):

    styles = styles or create_styles()

    summaries = sheets.get("Resumo gerencial", [])

    if len(summaries) != 1:
        raise ValueError("Resumo gerencial invalido.")

    summary = summaries[0]

    records = sheets.get("Validacao contabil", [])

    if not records:
        raise ValueError("Validacao contabil ausente.")

    math_status = composition_status(summary)
    previous_status = opening_status(summary)

    elements = [

        section_heading(
            2,
            "Valida\u00e7\u00e3o cont\u00e1bil",
            styles
        ),

        build_table(
            [
                {
                    "verification": "Composicao matematica",
                    "status": math_status,
                    "difference": summary.get(
                        "composition_difference"
                    ),
                },
                {
                    "verification": "Documentacao do saldo anterior",
                    "status": previous_status,
                    "difference": summary.get(
                        "opening_difference"
                    ),
                },
            ],
            [
                ("verification", "Verificacao", 3, "text"),
                ("status", "Situacao", 2, "status"),
                ("difference", "Diferenca", 2, "money"),
            ],
            styles
        ),

        Spacer(1, 10),
    ]

    if math_status == "VALIDADO":

        elements.append(
            paragraph(
                "A composicao matematica do saldo "
                "foi validada pelo snapshot contabil.",
                styles["success"]
            )
        )

    else:

        elements.append(
            paragraph(
                "ATENCAO: a composicao contabil "
                "requer revisao. Este documento nao "
                "deve ser interpretado como validado.",
                styles["danger"]
            )
        )

    elements.append(Spacer(1, 8))

    if previous_status == "NAO ANEXADO":

        elements.append(
            paragraph(
                "A composicao documental do saldo "
                "anterior nao foi anexada.",
                styles["warning"]
            )
        )

    elif previous_status == "NAO COMPROVADO":

        elements.append(
            paragraph(
                "Saldo anterior nao comprovado: "
                + brl(summary.get("opening_difference"))
                + ". A diferenca permanece separada "
                "das baixas confirmadas.",
                styles["warning"]
            )
        )

    else:

        elements.append(
            paragraph(
                "O total da composicao anterior anexada "
                "corresponde ao saldo anterior contabil.",
                styles["success"]
            )
        )

    elements.append(Spacer(1, 10))

    elements.append(
        paragraph(
            "A validade matematica nao implica "
            "comprovacao documental integral.",
            styles["body"]
        )
    )

    elements.append(
        build_table(
            records,
            [
                ("Verificacao", "Verificacao", 2.2, "text"),
                ("validation_actual", "Apurado", 1.5, "money"),
                ("validation_expected", "Esperado", 1.5, "money"),
                ("difference", "Diferenca", 1.3, "money"),
                ("status", "Situacao", 1.5, "status"),
                ("Observacao", "Observacao", 3, "text"),
            ],
            styles
        )
    )

    elements.append(Spacer(1, 8))

    elements.append(
        paragraph(
            "Na tabela analitica, a diferenca corresponde "
            "ao valor apurado menos o esperado. "
            "No resumo do saldo anterior nao comprovado, "
            "o sinal corresponde ao saldo contabil "
            "menos o saldo documentado.",
            styles["body"]
        )
    )

    return elements
