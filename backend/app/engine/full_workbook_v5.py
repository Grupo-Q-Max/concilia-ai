# CONCILIA_V5_FULL_WORKBOOK_25F

from io import BytesIO
from decimal import Decimal

from openpyxl import load_workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
)
from openpyxl.utils import get_column_letter

from app.engine.full_export_v5 import SHEET_NAMES

from app.engine.tab_export import (
    make_workbook,
    MONEY,
    LABELS,
)


FULL_MONEY = {
    "amount",
    "original",
    "value",
    "matched_amount",
    "remaining_amount",
    "reported_balance",
    "initial_balance",
    "total_debits",
    "total_credits",
    "final_reported_balance",
    "composition_total",
    "composition_difference",
    "opening_difference",
    "validation_actual",
    "validation_expected",
    "difference",
    "current_credit_original",
    "current_credit_matched",
    "current_credit_residual",
    "current_debit_original",
    "current_debit_matched",
    "current_debit_residual",
    "opening_credit_original",
    "opening_credit_matched",
    "opening_credit_residual",
    "combined_credit_original",
    "combined_credit_matched",
    "invoice_total_matched",
    "invoice_original_amount",
    "invoice_remaining",
    "invoice_already_matched",
    "invoice_financial_difference",
    "payment_original_amount",
    "payment_already_matched",
    "payment_remaining",
    "payment_financial_difference",
    "opening_original_amount",
    "opening_already_matched",
    "opening_financial_difference",
    "opening_remaining",
    "opening_after",
    "invoice_after",
    "payment_after",
    "suggested_amount",
    "invoice_amount",
    "payment_amount",
    "reconciled_amount",
    "total_invoiced",
    "total_paid",
    "open_balance",
    "supplier_credit_matched",
    "supplier_debit_matched",
    "supplier_debit_residual",
    "restored_amount",
}


FULL_LABELS = {
    "validation_actual":
        "Valor apurado",

    "validation_expected":
        "Valor esperado",

    "composition_total":
        "Saldo final composto",

    "composition_difference":
        "Diferenca contabil",

    "composition_valid":
        "Composicao validada",

    "opening_difference":
        "Saldo anterior nao comprovado",

    "opening_complete":
        "Saldo anterior comprovado",

    "opening_attached":
        "Saldo anterior anexado",

    "original":
        "Valor original",

    "matched_amount":
        "Total baixado",

    "remaining_amount":
        "Saldo residual",

    "value":
        "Saldo assinado",

    "current_credit_original":
        "Creditos originais do periodo",

    "current_credit_matched":
        "Creditos baixados do periodo",

    "current_credit_residual":
        "Creditos residuais do periodo",

    "current_debit_original":
        "Debitos originais do periodo",

    "current_debit_matched":
        "Debitos utilizados do periodo",

    "current_debit_residual":
        "Debitos residuais do periodo",

    "opening_credit_original":
        "Creditos originais anteriores",

    "opening_credit_matched":
        "Creditos anteriores baixados",

    "opening_credit_residual":
        "Creditos anteriores residuais",

    "combined_credit_original":
        "Creditos originais consolidados",

    "combined_credit_matched":
        "Creditos baixados consolidados",

    "current_credit_rate_pct":
        "Percentual de creditos baixados",

    "current_debit_rate_pct":
        "Percentual de debitos utilizados",

    "opening_rate_pct":
        "Percentual baixado do saldo anterior",

    "combined_credit_rate_pct":
        "Percentual consolidado de baixas",

    "paid_percentage":
        "Percentual baixado da NF",

    "invoice_total_matched":
        "Total acumulado baixado da NF",

    "supplier_credit_matched":
        "Creditos efetivamente baixados",

    "supplier_debit_matched":
        "Debitos efetivamente utilizados",

    "supplier_debit_residual":
        "Debitos ainda disponiveis",

    "restored_amount":
        "Valor restaurado",

    "display_status":
        "Situacao da conciliacao",

    "suggestion_status":
        "Situacao da sugestao",

    "audit_parse_status":
        "Integridade da auditoria",

    "restored_transactions":
        "Lancamentos restaurados",

    "original_record":
        "Registro original da baixa",

    "reason":
        "Motivo",

    "origin":
        "Origem",

    "match_id":
        "Identificador da baixa",

    "timestamp":
        "Data e hora da auditoria",
}


PERCENT_FIELDS = {
    "current_credit_rate_pct",
    "current_debit_rate_pct",
    "opening_rate_pct",
    "combined_credit_rate_pct",
    "paid_percentage",
}


BOOLEAN_FIELDS = {
    "composition_valid",
    "opening_complete",
    "opening_attached",
    "ambiguous",
    "batch_eligible",
    "automatic_eligible",
    "current_conflict",
}


TAB_COLORS = {
    "Resumo gerencial": "17365D",
    "Validacao contabil": "17365D",
    "Composicao do saldo": "2563EB",
    "Detalhamento das Baixas": "2563EB",
    "Saldo anterior original": "64748B",
    "Saldo anterior residual": "64748B",
    "Conciliados": "15803D",
    "Notas em aberto": "B45309",
    "Debitos pendentes": "B45309",
    "Divergencias": "B91C1C",
    "Sugestoes inteligentes": "7C3AED",
    "Sugestoes saldo anterior": "7C3AED",
    "Fornecedores": "0369A1",
    "Historico de desfazimentos": "475569",
    "Lancamentos originais": "475569",
}


# Reutilizar as regras do exportador existente.
MONEY.update(FULL_MONEY)
LABELS.update(FULL_LABELS)


def build_full_workbook_v5(sheets):

    if tuple(sheets) != SHEET_NAMES:

        raise ValueError(
            "Estrutura inesperada do Excel completo."
        )

    base = make_workbook(sheets)

    try:

        base.seek(0)

        wb = load_workbook(base)

    finally:

        base.close()

    try:

        wb.properties.title = (
            "Concilia AI V5 - Relatorio Completo"
        )

        wb.properties.subject = (
            "Conciliacao e auditoria contabil"
        )

        wb.properties.creator = "Concilia AI V5"

        for ws in wb.worksheets:

            ws.sheet_properties.tabColor = (
                TAB_COLORS[ws.title]
            )

            ws.sheet_view.showGridLines = False
            ws.freeze_panes = "A2"

            headers = {
                cell.column: cell.value
                for cell in ws[1]
            }

            records = sheets[ws.title]

            keys = list(dict.fromkeys(
                key
                for record in records
                for key in record
                if key not in (
                    "job_id",
                    "file_path",
                    "metadata_json",
                    "math_explanation",
                )
            ))

            for key in keys:

                label = LABELS.get(key, key)

                columns = [
                    col
                    for col, header in headers.items()
                    if header == label
                ]

                if len(columns) != 1:

                    if key in PERCENT_FIELDS:

                        raise ValueError(
                            "Coluna percentual ambigua: "
                            + key
                        )

                    continue

                column = columns[0]

                if key in PERCENT_FIELDS:

                    for index, record in enumerate(
                        records, start=2
                    ):

                        value = record.get(key)

                        if value is None or value == "":
                            continue

                        number = Decimal(str(value))

                        if not number.is_finite():

                            raise ValueError(
                                "Percentual invalido."
                            )

                        cell = ws.cell(index, column)

                        # Origem usa 49.00 para 49%.
                        cell.value = float(number / 100)

                        cell.number_format = "0.00%"

                if key in BOOLEAN_FIELDS:

                    for index, record in enumerate(
                        records, start=2
                    ):

                        value = record.get(key)

                        if not isinstance(value, bool):
                            continue

                        cell = ws.cell(index, column)

                        cell.value = (
                            "SIM" if value else "NAO"
                        )

                        cell.font = Font(
                            name="Calibri",
                            bold=True,
                            color=(
                                "166534"
                                if value
                                else "92400E"
                            )
                        )

                        cell.fill = PatternFill(
                            "solid",
                            fgColor=(
                                "DCFCE7"
                                if value
                                else "FEF3C7"
                            )
                        )

                        cell.alignment = Alignment(
                            horizontal="center"
                        )

                if key in FULL_MONEY:

                    for index, record in enumerate(
                        records, start=2
                    ):

                        value = record.get(key)

                        if value is None or value == "":
                            continue

                        cell = ws.cell(index, column)

                        if cell.data_type != "n":

                            raise ValueError(
                                "Campo monetario nao numerico: "
                                + ws.title + " / " + key
                            )

                        cell.number_format = (
                            "#,##0.00;"
                            "[Red]-#,##0.00;"
                            "0.00"
                        )

                    letter = get_column_letter(column)

                    ws.column_dimensions[letter].width = max(
                        ws.column_dimensions[letter].width,
                        18
                    )

            if ws.title == "Validacao contabil":

                for row in ws.iter_rows(min_row=2):

                    for cell in row:

                        if cell.value in (
                            "DIVERGENTE",
                            "REVISAR",
                            "NAO COMPROVADO",
                            "NAO ANEXADO",
                        ):

                            cell.font = Font(
                                bold=True,
                                color="92400E"
                            )

                            cell.fill = PatternFill(
                                "solid",
                                fgColor="FEF3C7"
                            )

                        elif cell.value == "VALIDADO":

                            cell.font = Font(
                                bold=True,
                                color="166534"
                            )

                            cell.fill = PatternFill(
                                "solid",
                                fgColor="DCFCE7"
                            )

        wb.active = 0

        output = BytesIO()

        wb.save(output)

        output.seek(0)

        return output

    finally:

        wb.close()
