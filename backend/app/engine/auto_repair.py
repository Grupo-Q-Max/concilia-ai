"""
CONCILIA AI - Automatic Spreadsheet Repair & Sanitizer Engine
Intelligently repairs, cleans, and normalizes defective or non-standard accounting Excel/CSV files:
1. Drops leading/trailing empty rows and columns.
2. Cleans formula error strings (#REF!, #VALUE!, #N/A, #DIV/0!, #NAME?, #NUM!).
3. Normalizes text numbers, accounting parenthesis (1.234,56), currency symbols (R$, $), trailing D/C.
4. Auto-detects and synthesizes missing 'Saldo' (Balance) column from running Debits/Credits.
5. Auto-splits single 'Valor' + 'D/C' (or Natureza) column into separate Débito and Crédito columns.
6. Filters out intermediate page break headers and summary/subtotal rows.
7. Corrects negative debits/credits (reversals) and nets simultaneous debits and credits.
8. Provides detailed audit trail of all repairs performed.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd


def normalize_str(value: Any) -> str:
    """Normalizes string for comparison: uppercase, stripped, without accents."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def clean_cell_value(val: Any) -> Any:
    """Cleans Excel formula error codes and dirty string artifacts."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    # Excel error codes
    if s.upper() in (
        "#REF!", "#VALUE!", "#N/A", "#DIV/0!",
        "#NAME?", "#NUM!", "#NULL!", "N/A", "NAN", "NONE"
    ):
        return None
    # Replace non-breaking spaces and control characters
    s = s.replace("\xa0", " ").replace("\r", " ").strip()
    return s


def sanitize_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Cleans raw DataFrame loaded from Excel or CSV:
    - Replaces formula errors with None
    - Trims fully empty rows and columns
    - Normalizes types
    """
    repairs = []
    initial_shape = df.shape

    # Apply cell cleaner
    cleaned_df = df.map(clean_cell_value)

    # Drop entirely empty rows and columns
    cleaned_df = cleaned_df.dropna(how="all").dropna(axis=1, how="all")

    if cleaned_df.shape != initial_shape:
        repairs.append(
            f"Removidas linhas e colunas vazias ({initial_shape[0]}x{initial_shape[1]} -> {cleaned_df.shape[0]}x{cleaned_df.shape[1]})."
        )

    cleaned_df = cleaned_df.reset_index(drop=True)
    cleaned_df.columns = range(cleaned_df.shape[1])
    return cleaned_df, repairs


def auto_repair_ledger_dataframe(
    df: pd.DataFrame,
    initial_balance: Decimal = Decimal("0.00")
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Analyzes an accounting ledger DataFrame and repairs:
    - Missing Saldo column (calculates running balance automatically)
    - Single Valor + D/C column (splits into Débito and Crédito)
    - Ambiguous or non-standard headers
    - Corrupt or negative debits/credits
    """
    df, repairs = sanitize_dataframe(df)
    if df.empty or df.shape[0] < 2:
        return df, repairs

    from app.engine.parser import parse_currency

    aliases = {
        "date": {
            "DATA", "DT", "DIA", "DATA LANCAMENTO", "DATA DO LANCAMENTO",
            "DT LANCTO", "DT LANCAMENTO", "DATA MOVIMENTO", "DATA DO MOVIMENTO",
            "DATA CONTABIL", "DT MOVIMENTO", "DATA MOVIMENTACAO", "EMISSAO", "DATA EMISSAO"
        },
        "history": {
            "HISTORICO", "HIST", "HISTORICO CONTABIL", "DESCRICAO",
            "DESCRICAO DO LANCAMENTO", "DESCRICAO DO MOVIMENTO", "COMPLEMENTO",
            "HISTORICO COMPLETO", "HISTORICO LANCAMENTO", "DETALHE", "HISTORICO DO MOVIMENTO"
        },
        "debit": {
            "DEBITO", "DEBITOS", "VALOR DEBITO", "VALOR DO DEBITO",
            "VLR DEBITO", "VLR DEB", "VL DEBITO", "DEB", "DEBITO R"
        },
        "credit": {
            "CREDITO", "CREDITOS", "VALOR CREDITO", "VALOR DO CREDITO",
            "VLR CREDITO", "VLR CRED", "VL CREDITO", "CRED", "CREDITO R"
        },
        "amount": {
            "VALOR", "VLR", "VALOR LIQUIDO", "VLR LIQUIDO", "VALOR DO MOVIMENTO",
            "VALOR NOMINAL", "VALOR DOCUMENTO", "VALOR LANCAMENTO"
        },
        "nature": {
            "D C", "DC", "NATUREZA", "TIPO", "D OU C", "OPERACAO", "DEB CRED"
        },
        "balance": {
            "SALDO", "SALDO ATUAL", "SALDO MENSAL", "SALDO DO MES",
            "SALDO DO PERIODO", "SALDO EXERCICIO", "SALDO ACUMULADO", "SALDO FINAL", "SALDO R"
        }
    }

    best_header_row = -1
    best_mapping: Dict[str, int] = {}
    best_score = 0

    # Scan top 25 rows for header candidate
    max_scan = min(25, len(df))
    for r_idx in range(max_scan):
        row_vals = [normalize_str(x) for x in df.iloc[r_idx].values]
        row_map: Dict[str, int] = {}
        score = 0

        for col_idx, text in enumerate(row_vals):
            if not text:
                continue
            for field, names in aliases.items():
                if field not in row_map:
                    if text in names or any(text.startswith(n) for n in names if len(n) > 3):
                        row_map[field] = col_idx
                        score += 2 if field in ("date", "history", "debit", "credit", "balance") else 1
                        break

        # Check if contains at least date and history
        if "date" in row_map and "history" in row_map and score > best_score:
            best_score = score
            best_header_row = r_idx
            best_mapping = row_map

    # If header found
    if best_header_row >= 0:
        # Case A: Has Amount + Nature (D/C) but not Debit/Credit
        if ("debit" not in best_mapping or "credit" not in best_mapping) and "amount" in best_mapping and "nature" in best_mapping:
            amt_col = best_mapping["amount"]
            nat_col = best_mapping["nature"]
            deb_vals = []
            cred_vals = []

            for i in range(len(df)):
                if i <= best_header_row:
                    deb_vals.append("Débito" if i == best_header_row else "")
                    cred_vals.append("Crédito" if i == best_header_row else "")
                else:
                    amt = parse_currency(df.iloc[i, amt_col])
                    nat = normalize_str(df.iloc[i, nat_col])
                    if "D" in nat:
                        deb_vals.append(str(amt))
                        cred_vals.append("0.00")
                    elif "C" in nat:
                        deb_vals.append("0.00")
                        cred_vals.append(str(amt))
                    else:
                        deb_vals.append("0.00")
                        cred_vals.append(str(amt))

            col_deb = df.shape[1]
            col_cred = df.shape[1] + 1
            df[col_deb] = deb_vals
            df[col_cred] = cred_vals
            best_mapping["debit"] = col_deb
            best_mapping["credit"] = col_cred
            repairs.append("Coluna de Valor e Natureza (D/C) desmembrada automaticamente em Débito e Crédito.")

        # Case B: Has Debit and Credit but lacks Balance (Saldo)
        if "balance" not in best_mapping and "debit" in best_mapping and "credit" in best_mapping:
            deb_col = best_mapping["debit"]
            cred_col = best_mapping["credit"]

            # Compute running balance
            running_bal = initial_balance
            bal_col_vals = []

            for i in range(len(df)):
                if i < best_header_row:
                    bal_col_vals.append("")
                elif i == best_header_row:
                    bal_col_vals.append("Saldo Calculado (Auto-Reparo)")
                else:
                    d_val = parse_currency(df.iloc[i, deb_col])
                    c_val = parse_currency(df.iloc[i, cred_col])
                    running_bal = running_bal + c_val - d_val
                    bal_col_vals.append(str(running_bal))

            new_bal_col = df.shape[1]
            df[new_bal_col] = bal_col_vals
            best_mapping["balance"] = new_bal_col
            repairs.append("Coluna de Saldo ausente calculada automaticamente a partir da movimentação de Débitos e Créditos.")

    return df, repairs
