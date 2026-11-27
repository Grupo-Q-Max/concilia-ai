from io import BytesIO
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

MONEY={'amount','matched_amount','remaining_amount','reported_balance','invoice_amount','payment_amount','reconciled_amount','difference','total_invoiced','total_paid','open_balance','original','value','total','reported','opening_difference','initial_balance','final_reported_balance','Saldo anterior','Debitos','Creditos','Saldo final','credits','debits','total_amt'}
LABELS={'trans_date':'Data','extracted_nf':'NF','extracted_supplier':'Fornecedor','history':'Historico','amount':'Valor original','remaining_amount':'Saldo residual','matched_amount':'Valor conciliado','kind':'Origem','value':'Residual D+/C-','original':'Valor original','supplier':'Fornecedor','nf':'NF','date':'Data','difference':'Diferenca','opening_difference':'Saldo anterior nao detalhado'}


# CONCILIA_V5_EXPORT_LABELS
LABELS.update({
    "matched_amount": "Valor baixado",
    "remaining_amount": "Saldo em aberto",
    "status": "Situacao",
    "original": "Valor original",
    "value": "Saldo contabil D+/C-",
    "transaction_id": "Identificador do lancamento"
})


# CONCILIA_V5_PAYMENT_LABELS
LABELS.update({
    "invoice_date": "Data da provisao",
    "payment_date": "Data do pagamento",
    "invoice_amount": "Valor original da NF",
    "payment_amount": "Valor original do pagamento",
    "reconciled_amount": "Valor desta baixa",
    "matched_amount": "Total baixado da NF",
    "remaining_amount": "Saldo residual da NF",
    "invoice_history": "Historico da provisao",
    "payment_history": "Historico do pagamento",
    "invoice_row": "Linha de origem da NF",
    "payment_row": "Linha de origem do pagamento",
    "match_type": "Tipo de conciliacao",
    "match_notes": "Observacoes"
})


# CONCILIA_V5_PROFESSIONAL_EXCEL_24E

def make_workbook(sheets):

    import json
    import math
    import textwrap

    from decimal import Decimal
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side
    )
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    wb = Workbook()
    wb.remove(wb.active)

    wb.properties.creator = "Concilia AI V5"
    wb.properties.title = "Relatorio de conciliacao contabil"

    navy = "17365D"
    white = "FFFFFF"
    slate = "334155"
    light = "F1F5F9"

    money_format = '#,##0.00;[Red]-#,##0.00;0.00'

    excluded = {
        "job_id",
        "file_path",
        "metadata_json",
        "math_explanation"
    }

    status_colors = {
        "COMPATIVEL": ("DCFCE7", "166534"),
        "EXATO": ("DCFCE7", "166534"),
        "FORNECEDOR": ("DCFCE7", "166534"),
        "QUITADO": ("DCFCE7", "166534"),
        "CONCILIADO": ("DCFCE7", "166534"),
        "CONFIRMED": ("DCFCE7", "166534"),
        "PARCIAL": ("FEF3C7", "92400E"),
        "PARTIAL": ("FEF3C7", "92400E"),
        "PARCIALMENTE CONCILIADO": ("FEF3C7", "92400E"),
        "BAIXA PARCIAL REGISTRADA": ("DCFCE7", "166534"),
        "DIVERGENCIA_NF": ("FEE2E2", "991B1B"),
        "BAIXA_EVIDENCIA": ("FEE2E2", "991B1B"),
        "EM ABERTO": ("E0F2FE", "075985"),
        "EM_ABERTO": ("E0F2FE", "075985"),
        "SEM_PROVISAO": ("FEE2E2", "991B1B"),
        "UNDONE": ("E2E8F0", "475569"),
        "REJECTED": ("E2E8F0", "475569"),
        "PENDENTE DE APROVACAO": ("FEF3C7", "92400E")
    }

    status_fields = {
        "status", "category", "display_status",
        "suggestion_status", "invoice_status",
        "payment_status"
    }

    flag_fields = {
        "ambiguous", "current_conflict",
        "batch_eligible", "automatic_eligible",
        "opening_attached", "opening_complete",
        "composition_valid", "valid"
    }

    long_fields = {
        "history", "invoice_history",
        "payment_history", "opening_history",
        "reason", "match_notes", "Observacao",
        "details"
    }

    id_fields = {
        "id", "nf", "extracted_nf",
        "invoice_nf", "payment_nf", "opening_nf",
        "cnpj", "account_code", "transaction_id",
        "invoice_trans_id", "payment_trans_id",
        "reconciliation_id"
    }

    def fill(color):
        return PatternFill("solid", fgColor=color)

    def is_money(key):
        return key in MONEY or key.endswith("_value")

    def set_text(cell, value):

        text = str(value)

        if len(text) > 32767:
            raise ValueError(
                "Texto excede o limite de uma celula Excel."
            )

        cell.value = text
        cell.data_type = "s"

    for name, records in sheets.items():

        rows = list(records)
        ws = wb.create_sheet(name)

        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 90

        ws.sheet_properties.pageSetUpPr.fitToPage = True

        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        ws.page_margins = PageMargins(
            left=0.3,
            right=0.3,
            top=0.5,
            bottom=0.5,
            header=0.2,
            footer=0.2
        )

        ws.oddFooter.left.text = "Concilia AI V5"
        ws.oddFooter.right.text = "Pagina &P de &N"

        ws.sheet_properties.tabColor = navy

        keys = list(dict.fromkeys(
            k
            for row in rows
            for k in row
            if k not in excluded
        ))

        if not keys:

            ws.append(["Nenhum registro"])

            ws["A1"].fill = fill(navy)

            ws["A1"].font = Font(
                name="Calibri",
                size=11,
                bold=True,
                color=white
            )

            ws.column_dimensions["A"].width = 35
            ws.row_dimensions[1].height = 30
            ws.freeze_panes = "A2"

            continue

        ws.append([
            LABELS.get(k, k)
            for k in keys
        ])

        ws.freeze_panes = "A2"
        ws.print_title_rows = "1:1"
        ws.row_dimensions[1].height = 34

        widths = {}

        for i, key in enumerate(keys, 1):

            cell = ws.cell(1, i)

            cell.fill = fill(navy)

            cell.font = Font(
                name="Calibri",
                size=11,
                bold=True,
                color=white
            )

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )

            widths[i] = max(
                14,
                min(34, len(str(cell.value)) + 4)
            )

            if is_money(key):
                widths[i] = max(widths[i], 22)

            if key in long_fields:
                widths[i] = 58

            if key in id_fields:
                widths[i] = max(widths[i], 18)

        for row_index, row in enumerate(rows, 2):

            row_color = (
                white if row_index % 2 == 0 else light
            )

            for i, key in enumerate(keys, 1):

                value = row.get(key)
                cell = ws.cell(row_index, i)

                cell.fill = fill(row_color)

                cell.font = Font(
                    name="Calibri",
                    size=10,
                    color=slate
                )

                cell.border = Border(
                    bottom=Side(
                        style="hair",
                        color="E2E8F0"
                    )
                )

                cell.alignment = Alignment(
                    vertical="center",
                    wrap_text=True
                )

                if value is None:
                    continue

                if isinstance(value, bool):

                    cell.value = value

                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center"
                    )

                    if key in flag_fields:

                        warning = (
                            value
                            if key in {
                                "ambiguous",
                                "current_conflict"
                            }
                            else not value
                        )

                        cell.fill = fill(
                            "FEF3C7"
                            if warning
                            else "DCFCE7"
                        )

                elif key in id_fields or key.endswith("_id"):

                    set_text(cell, value)
                    cell.number_format = "@"

                elif is_money(key):

                    if isinstance(value, str) and not value.strip():
                        continue

                    try:
                        amount = Decimal(str(value))
                    except Exception as e:
                        raise ValueError(
                            "Valor monetario invalido: "
                            + str(key)
                        ) from e

                    if not amount.is_finite():
                        raise ValueError(
                            "Valor monetario nao finito."
                        )

                    numeric = float(amount)

                    if not math.isfinite(numeric):
                        raise ValueError(
                            "Valor excede capacidade numerica."
                        )

                    if Decimal(str(numeric)) != amount:
                        raise ValueError(
                            "Conversao Excel perderia precisao: "
                            + str(key)
                        )

                    if len(amount.normalize().as_tuple().digits) > 15:
                        raise ValueError(
                            "Valor excede precisao do Excel: "
                            + str(key)
                        )

                    cell.value = numeric
                    cell.number_format = money_format

                    cell.alignment = Alignment(
                        horizontal="right",
                        vertical="center"
                    )

                elif isinstance(value, (int, float)):

                    cell.value = value

                elif isinstance(value, Decimal):

                    cell.value = float(value)

                elif isinstance(value, (dict, list, tuple)):

                    set_text(
                        cell,
                        json.dumps(
                            value,
                            ensure_ascii=False,
                            default=str
                        )
                    )

                else:

                    set_text(cell, value)

                if key in status_fields:

                    status = str(value).strip().upper()

                    if status in status_colors:

                        bg, fg = status_colors[status]

                        cell.fill = fill(bg)

                        cell.font = Font(
                            name="Calibri",
                            size=10,
                            bold=True,
                            color=fg
                        )

                if key not in long_fields:

                    length = max(
                        (
                            len(part)
                            for part in str(cell.value).splitlines()
                        ),
                        default=0
                    )

                    widths[i] = max(
                        widths[i],
                        min(44, length + 3)
                    )

        for i, width in widths.items():

            ws.column_dimensions[
                get_column_letter(i)
            ].width = width

        for row_index in range(2, ws.max_row + 1):

            line_count = 1

            for i in range(1, len(keys) + 1):

                cell = ws.cell(row_index, i)

                if isinstance(cell.value, str):

                    width = max(8, int(widths[i]) - 3)

                    lines = sum(
                        max(1, len(textwrap.wrap(
                            part,
                            width=width
                        )))
                        for part in cell.value.splitlines()
                    )

                    line_count = max(line_count, lines)

            ws.row_dimensions[row_index].height = min(
                409,
                max(23, line_count * 15 + 8)
            )

        ws.auto_filter.ref = ws.dimensions
        ws.print_area = ws.dimensions

    if not wb.worksheets:
        wb.create_sheet("Sem registros")

    output = BytesIO()

    wb.save(output)
    wb.close()

    output.seek(0)

    return output



# CONCILIA_V5_STATUS_EXPORT
MONEY.update({
    "invoice_remaining",
    "payment_remaining",
    "invoice_total_matched"
})

LABELS.update({
    "display_status": "Situacao atual da baixa",
    "invoice_remaining": "Saldo residual da NF",
    "payment_remaining": "Saldo residual do pagamento",
    "invoice_total_matched": "Total baixado da NF",
    "paid_percentage": "Percentual baixado (%)",
    "confidence_score": "Confianca da conciliacao",
    "invoice_status": "Status da NF",
    "payment_status": "Status do pagamento"
})


# CONCILIA_V5_SUGGESTION_EXPORT_24B

MONEY.update({
    "invoice_remaining",
    "payment_remaining",
    "suggested_amount",
    "invoice_after",
    "payment_after",
    "eligible_value"
})

LABELS.update({
    "category": "Classificacao",
    "score": "Confianca (0 a 100)",
    "ambiguous": "Ambigua",
    "batch_eligible": "Elegivel em lote",
    "invoice_nf": "NF da provisao",
    "payment_nf": "NF do pagamento",
    "invoice_supplier": "Fornecedor da provisao",
    "payment_supplier": "Fornecedor do pagamento",
    "invoice_remaining": "Saldo atual da provisao",
    "payment_remaining": "Saldo atual do pagamento",
    "suggested_amount": "Valor sugerido para baixa",
    "invoice_after": "Residual projetado da provisao",
    "payment_after": "Residual projetado do pagamento",
    "eligible_value": "Valor potencial elegivel em lote",
    "reason": "Justificativa",
    "suggestion_status": "Situacao da sugestao",
    "invoice_trans_id": "ID da provisao",
    "payment_trans_id": "ID do pagamento"
})


# CONCILIA_V5_OPENING_EXPORT_24C

MONEY.update({
    "opening_original_signed",
    "opening_residual_signed",
    "opening_matched_total",
    "opening_remaining",
    "opening_original",
    "opening_after",
    "opening_amount",
    "payment_amount",
    "payment_remaining",
    "payment_after",
    "suggested_amount",
    "composition_total",
    "composition_reported",
    "composition_difference"
})

LABELS.update({
    "opening_attached": "Planilha anterior anexada",
    "initial_balance": "Saldo anterior contabil",
    "opening_original_signed": "Saldo anterior detalhado D+/C-",
    "opening_residual_signed": "Saldo anterior residual D+/C-",
    "opening_matched_total": "Total baixado do saldo anterior",
    "opening_difference": "Saldo anterior nao comprovado",
    "opening_complete": "Saldo anterior integralmente comprovado",
    "opening_index": "Indice do lancamento anterior",
    "opening_nf": "NF do saldo anterior",
    "opening_supplier": "Fornecedor anterior",
    "opening_date": "Data da provisao anterior",
    "opening_history": "Historico anterior",
    "opening_remaining": "Residual anterior disponivel",
    "opening_after": "Residual anterior projetado",
    "automatic_eligible": "Elegivel para aprovacao",
    "current_conflict": "Conflito com provisao atual",
    "composition_total": "Saldo final composto",
    "composition_reported": "Saldo final contabil",
    "composition_difference": "Diferenca da composicao",
    "composition_valid": "Composicao validada"
})

# CONCILIA_V5_FINANCIAL_EXPORT_25C
MONEY.update(['invoice_already_matched', 'invoice_financial_difference', 'invoice_original_amount', 'opening_already_matched', 'opening_financial_difference', 'opening_original_amount', 'payment_already_matched', 'payment_financial_difference', 'payment_original_amount'])
LABELS.update({'invoice_original_amount': 'Valor original da NF', 'invoice_already_matched': 'Total ja baixado da NF', 'invoice_financial_difference': 'Diferenca financeira da NF', 'payment_original_amount': 'Valor original do pagamento', 'payment_already_matched': 'Total ja utilizado do pagamento', 'payment_financial_difference': 'Diferenca financeira do pagamento', 'opening_original_amount': 'Valor original da NF anterior', 'opening_already_matched': 'Total ja baixado da NF anterior', 'opening_financial_difference': 'Diferenca financeira da NF anterior', 'suggestion_status': 'Situacao da sugestao'})
