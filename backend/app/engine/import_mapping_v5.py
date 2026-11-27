
"""CONCILIA_V5_IMPORT_MAPPING_29D1"""

import pandas as pd

from app.engine.parser import (
    universal_read_spreadsheet,
    find_header_row
)

REQUIRED_FIELDS = (
    "date",
    "history",
    "debit",
    "credit",
    "balance"
)

OPTIONAL_FIELDS = ("document",)


def validate_mapping_v5(df, header_row, mapping):

    if type(header_row) is not int:
        raise ValueError("Linha de cabecalho invalida.")

    if not 0 <= header_row < len(df) - 1:
        raise ValueError(
            "Cabecalho fora da area de lancamentos."
        )

    if not isinstance(mapping, dict):
        raise ValueError("Mapeamento invalido.")

    allowed = set(REQUIRED_FIELDS + OPTIONAL_FIELDS)

    if set(mapping) - allowed:
        raise ValueError("Campo desconhecido.")

    missing = set(REQUIRED_FIELDS) - set(mapping)

    if missing:
        raise ValueError(
            "Campos obrigatorios ausentes: " +
            ", ".join(sorted(missing))
        )

    selected = []

    for field, index in mapping.items():

        if type(index) is not int:
            raise ValueError(
                "Indice invalido: " + field
            )

        if not 0 <= index < df.shape[1]:
            raise ValueError(
                "Coluna inexistente: " + field
            )

        selected.append(index)

    if len(selected) != len(set(selected)):
        raise ValueError(
            "Uma coluna nao pode representar dois campos."
        )

    return dict(mapping)


def column_letter_v5(index):

    result = ""
    number = index + 1

    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result

    return result


def cell_text_v5(value):

    if pd.isna(value):
        return ""

    return str(value)


def inspect_ledger_v5(file_path, header_row=None):

    df = universal_read_spreadsheet(str(file_path))

    if df.empty:
        raise ValueError("Planilha vazia.")

    from app.engine.auto_repair import auto_repair_ledger_dataframe
    df, repairs = auto_repair_ledger_dataframe(df)

    detected = None
    warning = None

    try:
        index, mapping = find_header_row(df)

        detected = {
            "header_row": int(index),
            "mapping": {
                key: int(value)
                for key, value in mapping.items()
                if key in REQUIRED_FIELDS + OPTIONAL_FIELDS
            }
        }

    except ValueError as exc:
        warning = str(exc)

    if header_row is None:
        header_row = (
            detected["header_row"]
            if detected is not None
            else 0
        )

    if type(header_row) is not int:
        raise ValueError("Linha invalida.")

    if not 0 <= header_row < len(df):
        raise ValueError("Linha inexistente.")

    columns = [
        {
            "index": i,
            "letter": column_letter_v5(i),
            "header": cell_text_v5(
                df.iloc[header_row, i]
            )
        }
        for i in range(df.shape[1])
    ]

    sample = []

    for i in range(
        header_row + 1,
        min(header_row + 11, len(df))
    ):
        sample.append({
            "row": i + 1,
            "values": [
                cell_text_v5(v)
                for v in df.iloc[i].tolist()
            ]
        })

    return {
        "row_count": len(df),
        "column_count": df.shape[1],
        "header_row": header_row,
        "columns": columns,
        "sample": sample,
        "automatic_mapping": detected,
        "requires_manual_mapping": detected is None,
        "warning": warning,
        "repairs": repairs
    }
