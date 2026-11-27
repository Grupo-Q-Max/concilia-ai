"""
CONCILIA AI - Multi-Layout Intelligent Excel, XML, HTML & CSV Parser
Robustly parses any accounting ledger (Razão Contábil):
- Multi-engine universal reader (handles mismatched extensions, HTML tables, XML SpreadsheetML, CSV, corrupt headers)
- Dynamically detects headers (never assumes row 0)
- Detects metadata (Company, CNPJ, Period, Account, Initial Balance)
- Parses transaction rows (Date, History, Debit, Credit, Balance)
- Converts currency to exact Decimal
"""
import os
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from app.engine.extractor import extract_transaction_info

def parse_currency(val: Any) -> Decimal:
    """Safely converts Brazilian or international currency representations to Decimal."""
    if val is None or pd.isna(val):
        return Decimal('0.00')
    if isinstance(val, (int, float)):
        return Decimal(str(val)).quantize(Decimal('0.01'))
    
    s = str(val).strip().replace('\xa0', ' ')
    if not s or s.lower() in ('nan', 'none', '-', 'x'):
        return Decimal('0.00')
    
    # Handle currency symbols and whitespace
    s = s.replace('R$', '').replace('$', '').strip()
    s = re.sub(r'-\s+', '-', s)
    if s.endswith('-'):
        s = '-' + s[:-1]
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    s = re.sub(r'\s*[DCdc]$', '', s).strip()
    
    # Check if standard BR format: 1.234,56
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # 1.234,56 -> 1234.56
            s = s.replace('.', '').replace(',', '.')
        else:
            # 1,234.56 -> 1234.56
            s = s.replace(',', '')
    elif ',' in s:
        # 1234,56 -> 1234.56
        s = s.replace(',', '.')
        
    s = re.sub(r'[^\d.-]', '', s)
    try:
        return Decimal(s).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return Decimal('0.00')

def universal_read_spreadsheet(file_path: str) -> pd.DataFrame:
    """
    Universally loads any spreadsheet or tabular file, even if:
    - An .xlsx file was saved with .xls extension
    - A .xls file was saved with .xlsx extension
    - An HTML table was saved with .xls extension (common in ERPs)
    - An XML Spreadsheet was saved with .xls extension
    - A CSV or TSV was saved with .xls extension
    - A file is encoded in utf-8, latin-1, cp1252, or utf-16
    - A file has leading junk bytes before OLE header or BOF record
    """
    errors = []

    # CONCILIA_CALAMINE_FALLBACK
    try:
        return pd.read_excel(
            file_path,
            engine="calamine",
            header=None
        )
    except Exception as e:
        errors.append(f"calamine: {e}")



    # 1. Default read_excel
    try:
        return pd.read_excel(file_path, header=None)
    except Exception as e:
        errors.append(f"read_excel default: {e}")

    # 2. openpyxl engine (handles .xlsx, even if named .xls)
    try:
        return pd.read_excel(file_path, engine="openpyxl", header=None)
    except Exception as e:
        errors.append(f"openpyxl: {e}")

    # 3. Check for OLE header or BIFF BOF offset recovery
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        ole_magic = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        biff8_bof = b'\x09\x08'
        biff5_bof = b'\x09\x04'

        ole_pos = raw_bytes.find(ole_magic)
        if ole_pos > 0:
            cleaned = raw_bytes[ole_pos:]
            return pd.read_excel(io.BytesIO(cleaned), engine="xlrd", header=None)

        for bof in [biff8_bof, biff5_bof]:
            bof_pos = raw_bytes.find(bof)
            if bof_pos > 0 and bof_pos < 2048:
                cleaned = raw_bytes[bof_pos:]
                try:
                    return pd.read_excel(io.BytesIO(cleaned), engine="xlrd", header=None)
                except Exception:
                    pass
    except Exception as e:
        errors.append(f"offset recovery: {e}")

    # 4. xlrd with ignore_workbook_corruption
    try:
        import xlrd
        book = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
        sheet = book.sheet_by_index(0)
        data = [sheet.row_values(r) for r in range(sheet.nrows)]
        if data:
            return pd.DataFrame(data)
    except Exception as e:
        errors.append(f"xlrd corruption fallback: {e}")

    # 5. HTML table parser (ERPs exporting HTML tables with .xls)
    try:
        dfs = pd.read_html(file_path, header=None)
        if dfs:
            return max(dfs, key=lambda d: d.shape[0] * d.shape[1])
    except Exception as e:
        errors.append(f"read_html: {e}")

    # 6. XML SpreadsheetML parser
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "<Workbook" in content and "<Table" in content:
            tree = ET.fromstring(content)
            rows = []
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            for row in tree.findall('.//ss:Row', ns) or tree.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Row'):
                r_vals = []
                for cell in row.findall('.//ss:Cell', ns) or row.findall('.//{urn:schemas-microsoft-com:office:spreadsheet}Cell'):
                    data = cell.find('.//ss:Data', ns) or cell.find('.//{urn:schemas-microsoft-com:office:spreadsheet}Data')
                    r_vals.append(data.text if data is not None else "")
                rows.append(r_vals)
            if rows:
                return pd.DataFrame(rows)
    except Exception as e:
        errors.append(f"xml spreadsheetml: {e}")

    # 7. CSV / TSV with multiple encodings
    for encoding in ['utf-8', 'latin1', 'cp1252', 'utf-16', 'utf-16-le', 'iso-8859-1']:
        for sep in [';', ',', '\t', '|']:
            try:
                df = pd.read_csv(file_path, sep=sep, header=None, encoding=encoding)
                if df.shape[1] >= 3 and df.shape[0] >= 1:
                    return df
            except Exception:
                pass

    raise ValueError(f"Não foi possível abrir o arquivo. O formato pode estar incompatível ou corrompido: {' | '.join(errors) if errors else 'formato desconhecido'}")

def find_header_row(df: pd.DataFrame) -> Tuple[int, Dict[str, int]]:
    import unicodedata
    import re

    def normalize(value):
        text = str(value).strip().upper()

        text = unicodedata.normalize("NFKD", text)

        text = "".join(
            c for c in text
            if not unicodedata.combining(c)
        )

        return re.sub(r"[^A-Z0-9]+", " ", text).strip()

    aliases = {
        "date": {
            "DATA", "DT", "DIA",
            "DATA LANCAMENTO",
            "DATA DO LANCAMENTO",
            "DT LANCTO",
            "DT LANCAMENTO",
            "DATA MOVIMENTO",
            "DATA DO MOVIMENTO",
            "DATA CONTABIL",
            "DT MOVIMENTO",
            "DATA MOVIMENTACAO",
            "DATA DA MOVIMENTACAO",
        },
        "history": {
            "HISTORICO",
            "HIST",
            "HISTORICO CONTABIL",
            "DESCRICAO",
            "DESCRICAO DO LANCAMENTO",
            "DESCRICAO DO MOVIMENTO",
            "COMPLEMENTO",
            "HISTORICO COMPLETO",
            "HISTORICO LANCAMENTO",
        },
        "debit": {
            "DEBITO", "DEBITOS",
            "VALOR DEBITO",
            "VALOR DO DEBITO",
            "VLR DEBITO",
            "VLR DEB",
            "VL DEBITO",
            "DEB",
        },
        "credit": {
            "CREDITO", "CREDITOS",
            "VALOR CREDITO",
            "VALOR DO CREDITO",
            "VLR CREDITO",
            "VLR CRED",
            "VL CREDITO",
            "CRED",
        },
        "document": {
            "NUMERO", "DOCUMENTO",
            "NRO", "NF", "NOTA FISCAL",
            "N DOCUMENTO",
            "NO DOCUMENTO",
            "NUMERO DOCUMENTO",
            "NUMERO DO DOCUMENTO",
            "NRO DOCUMENTO",
            "NUMERO NF",
        },
    }

    required = {
        "date", "history", "debit", "credit"
    }

    for idx, row in df.iterrows():
        found = {}

        for col_idx, cell in enumerate(row.values):
            if pd.isna(cell):
                continue

            key = normalize(cell)
            field = None

            for name, values in aliases.items():
                if key in values:
                    field = name
                    break

            if field is None:
                if key.startswith(("HIST", "DESCR")):
                    field = "history"

                elif key.startswith("DEB"):
                    field = "debit"

                elif key.startswith("CRED"):
                    field = "credit"

                elif key.startswith("SALDO") or "SALDO" in key:
                    if any(
                        word in key for word in (
                            "EXERCICIO",
                            "ACUMULADO",
                            "FINAL",
                        )
                    ):
                        field = "balance_exercise"
                    else:
                        field = "balance_monthly"

            if field:
                found.setdefault(field, []).append(col_idx)

        if not required.issubset(found):
            continue

        for field in required:
            if len(found[field]) > 1:
                # Auto-repair: select first unambiguous column match
                found[field] = [found[field][0]]

        mapping = {
            key: values[0]
            for key, values in found.items()
            if len(values) >= 1
        }

        if "balance_exercise" in found:
            mapping["balance"] = found["balance_exercise"][0]

        elif "balance_monthly" in found:
            mapping["balance"] = found["balance_monthly"][0]

        elif "balance" in found:
            mapping["balance"] = found["balance"][0]

        else:
            # Auto-repair: synthesize running balance column
            deb_col = mapping["debit"]
            cred_col = mapping["credit"]
            running_bal = Decimal("0.00")
            bal_vals = []
            for r in range(len(df)):
                if r < idx:
                    bal_vals.append("")
                elif r == idx:
                    bal_vals.append("Saldo Acumulado (Calculado)")
                else:
                    d = parse_currency(df.iloc[r, deb_col])
                    c = parse_currency(df.iloc[r, cred_col])
                    running_bal = running_bal + c - d
                    bal_vals.append(str(running_bal))
            new_col = df.shape[1]
            df[new_col] = bal_vals
            mapping["balance"] = new_col

        selected = [
            mapping[k]
            for k in (
                "date", "history",
                "debit", "credit", "balance"
            )
        ]

        if len(selected) != len(set(selected)):
            raise ValueError(
                "Colunas contabeis conflitantes."
            )

        return idx, mapping

    raise ValueError(
        "Cabecalho contabil nao identificado. "
        "Verifique Data, Historico, Debito, Credito e Saldo."
    )


def parse_accounting_ledger(
    file_path: str,
    *,
    header_row=None,
    column_mapping=None
) -> Dict[str, Any]:
    """
    Comprehensive parser for Razão Contábil.
    Uses universal multi-engine reader to support any Excel, HTML, XML, CSV layout.
    """
    df = universal_read_spreadsheet(file_path)
    from app.engine.auto_repair import auto_repair_ledger_dataframe
    df, repairs_applied = auto_repair_ledger_dataframe(df)

    # 1. Extract Metadata from Top Rows
    company_name = ""
    cnpj = ""
    period = ""
    account_code = ""
    initial_balance = Decimal('0.00')
    has_explicit_initial_balance = False
    

    # CONCILIA_V5_MANUAL_IMPORT_29D2
    if header_row is None and column_mapping is None:
        header_idx, col_map = find_header_row(df)

    elif header_row is None or column_mapping is None:
        raise ValueError(
            "Informe o cabecalho e o mapeamento completo."
        )

    else:
        from app.engine.import_mapping_v5 import (
            validate_mapping_v5
        )

        header_idx = header_row

        col_map = validate_mapping_v5(
            df,
            header_idx,
            column_mapping
        )
    
    for i in range(min(header_idx + 5, len(df))):
        row_cells = [str(x).strip() for x in df.iloc[i].values if pd.notna(x)]
        row_text = " ".join(row_cells)
        
        # Company
        m_emp = re.search(r'(?i)(?:Empresa|Razão Social)[:\s]+(.*?)(?:C\.N|CNPJ|$)', row_text)
        if m_emp and not company_name:
            company_name = m_emp.group(1).strip()
        elif 'ASSOCIACAO' in row_text.upper() and not company_name:
            company_name = row_text.strip()
            
        # CNPJ
        m_cnpj = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', row_text)
        if m_cnpj and not cnpj:
            cnpj = m_cnpj.group(0)
            
        # Period
        m_per = re.search(r'(?i)(?:Per[íi]odo)[:\s]+(\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4})', row_text)
        if m_per and not period:
            period = m_per.group(1).strip()
            
        # Account
        m_acc = re.search(r'(?i)(?:Conta)[:\s]+([\d\.]+)', row_text)
        if m_acc and not account_code:
            account_code = m_acc.group(1).strip()
            
        # Initial Balance
        if 'SALDO ANTERIOR' in row_text.upper():
            has_explicit_initial_balance = True
            for cell in df.iloc[i].values:
                if pd.notna(cell) and str(cell).strip() not in ['', 'SALDO ANTERIOR']:
                    initial_balance = parse_currency(cell)
                    break


    # CONCILIA_METADATA_V2
    company_name = re.split(
        r"\s+Folha\s*:",
        company_name,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()

    for i in range(min(header_idx + 5, len(df))):
        cells = [
            str(x).strip()
            for x in df.iloc[i].values
            if pd.notna(x)
        ]

        text = " ".join(cells)

        if re.search(r"\bConta\s*:", text, re.I):
            match = re.search(
                r"\b\d+(?:\.\d+){2,}\b", text
            )
            if match:
                account_code = match.group(0)

    # 2. Extract Transactions
    transactions = []
    final_reported_balance: Optional[Decimal] = None
    
    date_col = col_map.get('date', 0)
    hist_col = col_map.get('history', 1)
    deb_col = col_map.get('debit', 2)
    cred_col = col_map.get('credit', 3)
    bal_col = col_map.get('balance', 4)
    
    df_values = df.values
    num_cols = df_values.shape[1] if df_values.ndim > 1 else 0

    for row_idx in range(header_idx + 1, len(df_values)):
        row = df_values[row_idx]
        
        cell_date = row[date_col] if date_col < num_cols else None
        cell_hist = row[hist_col] if hist_col < num_cols else None
        cell_deb = row[deb_col] if deb_col < num_cols else None
        cell_cred = row[cred_col] if cred_col < num_cols else None
        cell_bal = row[bal_col] if bal_col < num_cols else None
        
        # Check if empty row
        if pd.isna(cell_date) and pd.isna(cell_hist) and pd.isna(cell_deb) and pd.isna(cell_cred):
            continue
            
        date_str = str(cell_date).strip() if pd.notna(cell_date) else ""
        hist_str = str(cell_hist).strip() if pd.notna(cell_hist) else ""
        
        # Skip header-like or metadata repeats (e.g. "Conta:", "SALDO ANTERIOR", license notices)
        if 'CONTA:' in date_str.upper() or 'SALDO ANTERIOR' in hist_str.upper() or 'SISTEMA LICENCIADO' in date_str.upper():
            continue
            
        # Parse debits and credits
        deb_val = parse_currency(cell_deb)
        cred_val = parse_currency(cell_cred)

        # CONCILIA_V5_IMPORT_SAFETY_30A1 - Auto-repair negative or simultaneous debits/credits
        if date_str:
            if deb_val < 0:
                cred_val = abs(deb_val)
                deb_val = Decimal('0.00')
            elif cred_val < 0:
                deb_val = abs(cred_val)
                cred_val = Decimal('0.00')

            if deb_val > 0 and cred_val > 0:
                if deb_val > cred_val:
                    deb_val = deb_val - cred_val
                    cred_val = Decimal('0.00')
                else:
                    cred_val = cred_val - deb_val
                    deb_val = Decimal('0.00')
        
        # Skip summary total row (e.g. row with no date but large debits/credits at the end)
        if not date_str and (deb_val > 0 or cred_val > 0):
            continue
            
        if deb_val == 0 and cred_val == 0:
            continue
            
        # Format date string
        clean_date = date_str[:10] if len(date_str) >= 10 else date_str
        
        # Parse reported balance
        rep_balance: Optional[Decimal] = None
        if pd.notna(cell_bal) and str(cell_bal).strip() != "":
            rep_balance = parse_currency(cell_bal)
            final_reported_balance = rep_balance
            
        trans_type = "CREDIT" if cred_val > 0 else "DEBIT"
        amount = cred_val if cred_val > 0 else deb_val
        
        # Extract NF & Supplier using extractor
        ext_info = extract_transaction_info(hist_str, trans_type)
        
        transactions.append({
            "row_index": row_idx,
            "trans_date": clean_date,
            "history": hist_str,
            "trans_type": trans_type,
            "amount": amount,
            "reported_balance": rep_balance,
            "extracted_nf": ext_info["extracted_nf"],
            "extracted_supplier": ext_info["extracted_supplier"],
            "cleaned_supplier": ext_info["cleaned_supplier"],
            "category": ext_info["category"],
            "details": ext_info["details"]
        })


    if final_reported_balance is None:
        total_creds = sum((t["amount"] for t in transactions if t["trans_type"] == "CREDIT"), Decimal("0.00"))
        total_debs = sum((t["amount"] for t in transactions if t["trans_type"] == "DEBIT"), Decimal("0.00"))
        final_reported_balance = initial_balance + total_creds - total_debs

    # CONCILIA_EMPTY_GUARD_V2
    if not transactions:
        raise ValueError(
            "Nenhum lancamento contabil reconhecido. "
            "A importacao nao pode ser validada."
        )

    return {
        "metadata": {
            "company_name": company_name or "EMPRESA NÃO IDENTIFICADA",
            "cnpj": cnpj or "N/D",
            "period": period or "N/D",
            "account_code": account_code or "2.1.30.100.000 (Fornecedores)",
            "initial_balance": initial_balance,
            "has_explicit_initial_balance": has_explicit_initial_balance,
            "final_reported_balance": final_reported_balance
        },
        "transactions": transactions
    }
