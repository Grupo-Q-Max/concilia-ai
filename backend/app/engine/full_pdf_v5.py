
# CONCILIA_V5_FULL_PDF_26_TURBO

import json

from io import BytesIO
from decimal import Decimal

from reportlab.platypus import (
    SimpleDocTemplate,
    PageBreak,
    Spacer,
)

from app.engine.full_export_v5 import SHEET_NAMES

from app.engine.full_workbook_v5 import (
    FULL_MONEY,
    FULL_LABELS,
    PERCENT_FIELDS,
)

from app.engine.tab_export import MONEY, LABELS

from app.engine.pdf_layout_v5 import (
    PAGE_SIZE,
    MARGIN,
    create_styles,
    paragraph,
    build_table,
    section_heading,
    draw_page,
)

from app.engine.pdf_summary_v5 import (
    build_summary_section,
    build_validation_section,
)

from app.engine.pdf_details_v5 import (
    build_composition_section,
    build_payment_section,
)

EXCLUDED = {
    "job_id",
    "opening_hash",
    "file_path",
    "metadata_json",
    "math_explanation",
}

MONEY_FIELDS = set(MONEY) | set(FULL_MONEY) | {
    "original",
    "amount",
    "value",
    "remaining",
    "opening_amount",
    "opening_original",
    "opening_remaining",
    "opening_after",
    "payment_after",
    "invoice_after",
    "payment_remaining",
    "invoice_remaining",
    "suggested_amount",
    "reconciled_amount",
    "restored_amount",
}

FIELD_LABELS = {
    **LABELS,
    **FULL_LABELS,
    "id": "Identificador",
    "nf": "NF",
    "date": "Data",
    "trans_date": "Data",
    "extracted_nf": "NF",
    "extracted_supplier": "Fornecedor",
    "supplier": "Fornecedor",
    "history": "Historico",
    "amount": "Valor original",
    "value": "Saldo D+/C-",
    "original": "Valor original",
    "matched_amount": "Total baixado",
    "remaining_amount": "Saldo residual",
    "status": "Situacao",
    "trans_type": "Natureza",
    "row_index": "Linha original",
    "invoice_nf": "NF da provisao",
    "payment_nf": "NF do pagamento",
    "opening_nf": "NF anterior",
    "score": "Pontuacao",
    "reason": "Motivo",
    "category": "Categoria",
    "suggested_amount": "Baixa sugerida",
    "reconciled_amount": "Baixa confirmada",
    "match_type": "Tipo de conciliacao",
    "match_notes": "Motivo da conciliacao",
    "invoice_trans_id": "ID da provisao",
    "payment_trans_id": "ID do pagamento",
    "reconciliation_id": "ID da conciliacao",
}

TITLES = (
    "Resumo gerencial",
    "Validacao contabil",
    "Composicao do saldo final",
    "Detalhamento individual das baixas",
    "Saldo anterior original",
    "Saldo anterior residual",
    "Conciliacoes realizadas",
    "Notas fiscais em aberto",
    "Debitos pendentes",
    "Divergencias",
    "Sugestoes inteligentes",
    "Sugestoes do saldo anterior",
    "Resumo por fornecedor",
    "Historico de desfazimentos",
    "Lancamentos originais",
)

TX_FIELDS = (
    "row_index",
    "trans_date",
    "extracted_nf",
    "extracted_supplier",
    "trans_type",
    "amount",
    "matched_amount",
    "remaining_amount",
    "status",
)

REC_FIELDS = (
    "nf",
    "supplier",
    "invoice_original_amount",
    "invoice_amount",
    "payment_amount",
    "reconciled_amount",
    "invoice_remaining",
    "difference",
    "display_status",
    "match_type",
)

PREFERRED = {
    "Saldo anterior original": (
        "date", "nf", "supplier", "history", "value",
    ),

    "Saldo anterior residual": (
        "date", "nf", "supplier", "original",
        "matched_amount", "remaining_amount",
        "value", "status",
    ),

    "Conciliados": REC_FIELDS,
    "Divergencias": REC_FIELDS,

    "Notas em aberto": TX_FIELDS,
    "Debitos pendentes": TX_FIELDS,
    "Lancamentos originais": TX_FIELDS,

    "Sugestoes inteligentes": (
        "invoice_nf",
        "invoice_supplier",
        "payment_nf",
        "payment_supplier",
        "invoice_remaining",
        "payment_remaining",
        "suggested_amount",
        "category",
        "score",
        "suggestion_status",
    ),

    "Sugestoes saldo anterior": (
        "opening_nf",
        "opening_supplier",
        "payment_nf",
        "payment_supplier",
        "opening_remaining",
        "payment_remaining",
        "suggested_amount",
        "category",
        "score",
        "suggestion_status",
    ),

    "Fornecedores": (
        "supplier",
        "total_invoiced",
        "total_paid",
        "open_balance",
        "supplier_credit_matched",
        "supplier_debit_matched",
        "supplier_debit_residual",
        "invoices_count",
    ),

    "Historico de desfazimentos": (
        "timestamp",
        "origin",
        "nf",
        "supplier",
        "restored_amount",
        "reason",
        "audit_parse_status",
    ),
}

NOTES = {
    "Saldo anterior original":
        "Composicao documental original, antes das baixas.",

    "Saldo anterior residual":
        "Posicao atual do saldo anterior apos baixas confirmadas.",

    "Conciliados":
        "Registros ativos. Uma conciliacao parcial nao significa "
        "quitacao integral da nota fiscal.",

    "Notas em aberto":
        "Creditos com valor residual positivo. Consulte a situacao "
        "de cada lancamento para identificar excecoes.",

    "Debitos pendentes":
        "Debitos com saldo residual ainda disponivel.",

    "Divergencias":
        "Registros de diferencas e conciliacoes parciais.",

    "Sugestoes inteligentes":
        "PENDENTE DE APROVACAO. Sugestoes podem se sobrepor "
        "e nao representam baixas realizadas.",

    "Sugestoes saldo anterior":
        "PENDENTE DE APROVACAO. A elegibilidade nao representa "
        "uma baixa confirmada.",

    "Fornecedores":
        "Total pago representa movimentos de debito. "
        "Debitos efetivamente utilizados sao apresentados "
        "em coluna separada.",

    "Historico de desfazimentos":
        "Registro de auditoria. Valores restaurados historicos "
        "nao devem ser somados ao saldo atual.",

    "Lancamentos originais":
        "Todos os lancamentos disponibilizados pelo snapshot, "
        "sem limite artificial de quantidade.",
}


def redact(value):

    if isinstance(value, dict):
        return {
            k: redact(v)
            for k, v in value.items()
            if k not in EXCLUDED
        }

    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]

    return value


def normalize_records(records):

    result = []

    for record in records:

        row = redact(dict(record))

        for key, value in row.items():

            if isinstance(value, (dict, list, tuple)):
                row[key] = json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                    indent=2,
                )

        result.append(row)

    return result


def field_kind(key):

    if key in PERCENT_FIELDS:
        return "percentage"

    if key in MONEY_FIELDS or key.endswith("_value"):
        return "money"

    if key == "date" or key.endswith("_date"):
        return "date"

    if key in {
        "status",
        "display_status",
        "suggestion_status",
        "invoice_status",
        "payment_status",
        "category",
    }:
        return "status"

    return "text"


def field_label(key):

    return FIELD_LABELS.get(
        key,
        key.replace("_", " ").capitalize()
    )


def field_weight(key):

    kind = field_kind(key)

    if kind in {"money", "percentage"}:
        return 1.6

    if kind == "date":
        return 1.2

    if key in {
        "history",
        "reason",
        "match_notes",
        "invoice_history",
        "payment_history",
        "opening_history",
        "original_record",
        "restored_transactions",
    }:
        return 3.5

    if "supplier" in key:
        return 2.6

    return 1.5


def available_fields(records):

    return list(dict.fromkeys(
        key
        for row in records
        for key in row
        if key not in EXCLUDED
    ))


def prepare_section(name, records):

    rows = normalize_records(records)

    for index, row in enumerate(rows, 1):

        row["pdf_record_number"] = index

        if name.startswith("Sugestoes"):
            row["suggestion_status"] = (
                "PENDENTE DE APROVACAO"
            )

    keys = available_fields(rows)

    preferred = [
        key for key in PREFERRED.get(name, ())
        if key in keys
    ]

    remaining = [
        key for key in keys
        if key not in preferred
        and key != "pdf_record_number"
    ]

    return rows, preferred, remaining


def make_columns(keys):

    columns = [
        (
            "pdf_record_number",
            "Registro",
            0.8,
            "text",
        )
    ]

    for key in keys:

        columns.append((
            key,
            field_label(key),
            field_weight(key),
            field_kind(key),
        ))

    return columns


def partition_fields(keys, max_columns=7):

    return [
        keys[i:i + max_columns]
        for i in range(0, len(keys), max_columns)
    ]


def build_generic_section(number, name, records, styles):

    rows, preferred, remaining = prepare_section(
        name, records
    )

    elements = [
        section_heading(
            number,
            TITLES[number - 1],
            styles,
        ),

        paragraph(
            NOTES.get(name, ""),
            styles["body"],
        ),

        paragraph(
            "Quantidade de registros: " + str(len(rows)),
            styles["body"],
        ),
    ]

    if not rows:

        elements.append(
            paragraph(
                "Nenhum registro nesta secao.",
                styles["body"],
            )
        )

        return elements

    groups = partition_fields(preferred)

    groups.extend(
        partition_fields(remaining)
    )

    if not groups:
        groups = [[]]

    elements.append(
        paragraph(
            "Os numeros de registro permitem relacionar "
            "as tabelas complementares desta secao. "
            "Nao representam numeros de notas fiscais.",
            styles["body"],
        )
    )

    for index, keys in enumerate(groups, 1):

        elements.append(Spacer(1, 8))

        elements.append(
            paragraph(
                "Quadro "
                + str(index)
                + " de "
                + str(len(groups)),
                styles["section"],
            )
        )

        elements.append(
            build_table(
                rows,
                make_columns(keys),
                styles,
            )
        )

    return elements


def build_full_pdf_v5(sheets):

    if tuple(sheets) != SHEET_NAMES:
        raise ValueError(
            "Estrutura inesperada do relatorio PDF."
        )

    styles = create_styles()

    elements = []

    builders = (
        build_summary_section,
        build_validation_section,
        build_composition_section,
        build_payment_section,
    )

    for index, name in enumerate(SHEET_NAMES):

        if index:
            elements.append(PageBreak())

        if index < len(builders):

            elements.extend(
                builders[index](sheets, styles)
            )

        else:

            elements.extend(
                build_generic_section(
                    index + 1,
                    name,
                    sheets[name],
                    styles,
                )
            )

    output = BytesIO()

    try:

        doc = SimpleDocTemplate(
            output,
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=48,
            bottomMargin=48,
            title="Concilia AI V5 - Relatorio Completo",
            author="Concilia AI V5 Intelligent",
            subject="Conciliacao e auditoria contabil",
        )

        doc.build(
            elements,
            onFirstPage=draw_page,
            onLaterPages=draw_page,
        )

        output.seek(0)

        content = output.getvalue()

        if not (
            content.startswith(b"%PDF-")
            and content.rstrip().endswith(b"%%EOF")
        ):
            raise RuntimeError("PDF invalido.")

        return output

    except Exception:

        output.close()

        raise
