import re
import unicodedata
import warnings
from decimal import Decimal
from datetime import datetime, date
import pandas as pd
from app.engine.parser import universal_read_spreadsheet, parse_currency
from app.engine.extractor import extract_transaction_info, extract_fallback_number


def norm(v):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(v or '').strip().lower()) if not unicodedata.combining(c))


def parse_date_safely(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime('%Y-%m-%d')
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if 30000 <= val <= 60000:
            dt = pd.to_datetime(val, unit='D', origin='1899-12-30')
            return dt.strftime('%Y-%m-%d')
    s = str(val).strip()
    if not s or s.upper() in ('X', '-', 'NAN', 'NONE', ''):
        return None
    if re.match(r'^\d{5}\.\d+$', s):
        try:
            f = float(s)
            if 30000 <= f <= 60000:
                dt = pd.to_datetime(f, unit='D', origin='1899-12-30')
                return dt.strftime('%Y-%m-%d')
        except (ValueError, OverflowError):
            pass
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if re.search(r'[\/\.\-]', s) or (len(s) == 8 and s.isdigit()):
                dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
                if pd.notna(dt):
                    return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return None


def detect_column_mapping(norm_cells):
    # Template 5: Fornecedor, NF, Emissao, Saldo Anterior, Natureza (D/C)
    if any('fornecedor' in c for c in norm_cells) and any('natureza' in c or 'd/c' in c for c in norm_cells):
        m = {'type': 'template_5'}
        for idx, c in enumerate(norm_cells):
            if 'fornecedor' in c and 'supplier' not in m: m['supplier'] = idx
            elif ('nf' in c or 'nota' in c) and 'nf' not in m: m['nf'] = idx
            elif ('emissao' in c or 'data' in c) and 'date' not in m: m['date'] = idx
            elif ('saldo' in c or 'valor' in c) and 'amount' not in m: m['amount'] = idx
            elif ('natureza' in c or 'd/c' in c) and 'nature' not in m: m['nature'] = idx
        if len(m) >= 5:
            return m

    # Tabular layout with Date, History, Amounts (like Razão / Conciliação de Fornecedores)
    has_date = any(c in ('data', 'emissao', 'dt', 'data emissao', 'dt emissao', 'vencimento') for c in norm_cells)
    has_hist = any(c in ('historico', 'descricao', 'hist', 'detalhe', 'complemento') for c in norm_cells)
    has_doc_or_nf = any(c in ('nota', 'nf', 'numero', 'nota fiscal', 'titulo', 'documento', 'doc', 'fornecedor') for c in norm_cells)
    has_amount = any(c in ('valor', 'debito', 'credito', 'saldo', 'total', 'debito/valor', 'saldo anterior', 'valor nominal', 'formula') for c in norm_cells)

    if (has_date and has_hist) or (has_date and has_doc_or_nf) or (has_date and has_amount) or (has_hist and has_amount) or (has_doc_or_nf and has_amount):
        m = {'type': 'table'}
        for idx, c in enumerate(norm_cells):
            if c in ('data', 'emissao', 'dt', 'data emissao', 'dt emissao', 'vencimento') and 'date' not in m:
                m['date'] = idx
            elif c in ('lt', 'lote', 'documento', 'doc') and 'doc' not in m:
                m['doc'] = idx
            elif c in ('historico', 'descricao', 'hist', 'detalhe', 'complemento') and 'history' not in m:
                m['history'] = idx
            elif c in ('nota', 'nf', 'numero', 'nota fiscal', 'titulo') and 'nf' not in m:
                m['nf'] = idx
            elif c in ('debito', 'deb', 'debitos') and 'debit' not in m:
                m['debit'] = idx
            elif c in ('credito', 'cred', 'creditos') and 'credit' not in m:
                m['credit'] = idx
            elif c in ('valor', 'debito/valor', 'saldo', 'saldo anterior', 'valor nominal', 'formula') and 'value' not in m:
                m['value'] = idx
            elif c in ('fornecedor', 'razao social', 'nome') and 'supplier' not in m:
                m['supplier'] = idx
            elif c in ('natureza', 'd/c', 'dc') and 'nature' not in m:
                m['nature'] = idx
        return m

    return None


def is_numeric_cell(val):
    if pd.isna(val) or val is None:
        return False
    s = str(val).strip()
    s_clean = re.sub(r'^(?:R\$|USD|\$)\s*', '', s, flags=re.I).strip()
    return bool(re.match(r'^-?[\d\.,\s]+$', s_clean)) and any(c.isdigit() for c in s_clean)


def infer_headerless_mapping(df):
    if df.empty:
        return None
    sample_rows = []
    for r_idx in range(min(10, len(df))):
        row = df.iloc[r_idx]
        cells = [str(c).strip() if pd.notna(c) else '' for c in row]
        if any(cells):
            if detect_column_mapping([norm(c) for c in cells]):
                return None
            sample_rows.append(cells)
            if len(sample_rows) >= 3:
                break
    if not sample_rows:
        return None

    num_cols = len(df.columns)
    date_cols = [
        c for c in range(num_cols)
        if all(parse_date_safely(r[c]) for r in sample_rows if c < len(r) and r[c])
        and any(parse_date_safely(r[c]) for r in sample_rows if c < len(r) and r[c])
    ]
    val_cols = [c for c in range(num_cols) if c not in date_cols and any(is_numeric_cell(r[c]) and parse_currency(r[c]) > 0 for r in sample_rows if c < len(r) and r[c])]

    if not val_cols and not date_cols:
        return None

    if num_cols == 3:
        if 0 in date_cols:
            if 2 in val_cols:
                return {'type': 'table', 'date': 0, 'history': 1, 'value': 2}
            elif 1 in val_cols:
                return {'type': 'table', 'date': 0, 'value': 1, 'history': 2}
        elif 1 in date_cols and 2 in val_cols:
            return {'type': 'table', 'history': 0, 'date': 1, 'value': 2}
        elif 2 in val_cols:
            return {'type': 'table', 'doc': 0, 'history': 1, 'value': 2}

    elif num_cols == 4:
        if 0 in date_cols:
            if 3 in val_cols:
                return {'type': 'simple_4', 'date': 0, 'doc': 1, 'history': 2, 'value': 3}
            elif 2 in val_cols and 3 in val_cols:
                return {'type': 'table', 'date': 0, 'history': 1, 'debit': 2, 'credit': 3}
        elif 3 in val_cols:
            return {'type': 'simple_4', 'date': 0 if 0 in date_cols else None, 'doc': 1, 'history': 2, 'value': 3}

    elif num_cols == 2:
        if 1 in val_cols:
            if 0 in date_cols:
                return {'type': 'table', 'date': 0, 'value': 1}
            else:
                return {'type': 'table', 'history': 0, 'value': 1}

    if val_cols:
        best_val = val_cols[-1]
        best_date = date_cols[0] if date_cols else None
        remaining = [c for c in range(num_cols) if c != best_val and c != best_date]
        m = {'type': 'table', 'value': best_val}
        if best_date is not None:
            m['date'] = best_date
        if len(remaining) == 1:
            m['history'] = remaining[0]
        elif len(remaining) >= 2:
            m['doc'] = remaining[0]
            m['history'] = remaining[1]
        return m

    return None


def read_opening(path, initial=None, column_mapping=None, header_row=None):
    dfs = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pd.ExcelFile(path) as excel_file:
                for sname in excel_file.sheet_names:
                    try:
                        sheet_df = pd.read_excel(excel_file, sheet_name=sname, header=None).dropna(how='all').dropna(axis=1, how='all')
                        if not sheet_df.empty and len(sheet_df) >= 1:
                            dfs.append((sname, sheet_df))
                    except Exception:
                        pass
    except Exception:
        pass

    if not dfs:
        base_df = universal_read_spreadsheet(path).dropna(how='all').dropna(axis=1, how='all')
        if base_df.empty:
            raise ValueError('Planilha vazia.')
        dfs.append(('default', base_df))

    best_rows = []

    for sheet_name, df in dfs:
        rows = []
        if column_mapping:
            current_map = {'type': 'table'}
            for k, v in column_mapping.items():
                if v is not None and str(v).strip() != '' and str(v).isdigit():
                    current_map[k] = int(v)
            start_row = header_row if (header_row is not None and header_row > 0) else 0
        else:
            current_map = infer_headerless_mapping(df)
            start_row = 0

        for r_idx in range(start_row, len(df)):
            row = df.iloc[r_idx]
            cells = [str(c).strip() if pd.notna(c) else '' for c in row]
            if not any(cells):
                continue
            norm_cells = [norm(c) for c in cells]

            if not column_mapping:
                detected = detect_column_mapping(norm_cells)
                if detected:
                    current_map = detected
                    continue

            if not current_map:
                continue

            cmap = current_map

            if cmap['type'] == 'template_5':
                raw_sup = cells[cmap['supplier']] if cmap.get('supplier', -1) < len(cells) else ''
                raw_nf = cells[cmap['nf']] if cmap.get('nf', -1) < len(cells) else ''
                raw_date = cells[cmap['date']] if cmap.get('date', -1) < len(cells) else ''
                raw_amt = cells[cmap['amount']] if cmap.get('amount', -1) < len(cells) else ''
                raw_nat = norm(cells[cmap['nature']]) if cmap.get('nature', -1) < len(cells) else ''

                if not raw_sup and not raw_nf and not raw_amt:
                    continue
                if raw_nat not in ('d', 'c', 'debito', 'credito'):
                    continue

                val = parse_currency(raw_amt)
                if val <= 0:
                    continue
                sign = 1 if raw_nat in ('d', 'debito') else -1
                date_str = parse_date_safely(raw_date) or '2025-12-31'

                rows.append({
                    'extracted_supplier': str(raw_sup),
                    'extracted_nf': str(raw_nf),
                    'trans_date': date_str,
                    'history': 'Composicao anterior importada',
                    'document_number': str(raw_nf),
                    'value': str(sign * val)
                })

            elif cmap['type'] in ('table', 'simple_4'):
                raw_date = cells[cmap['date']] if cmap.get('date') is not None and cmap['date'] < len(cells) else ''
                raw_hist = cells[cmap['history']] if cmap.get('history') is not None and cmap['history'] < len(cells) else ''
                raw_doc = cells[cmap['doc']] if cmap.get('doc') is not None and cmap['doc'] < len(cells) else ''
                raw_nf = cells[cmap['nf']] if cmap.get('nf') is not None and cmap['nf'] < len(cells) else ''
                raw_sup = cells[cmap['supplier']] if cmap.get('supplier') is not None and cmap['supplier'] < len(cells) else ''
                raw_nat = norm(cells[cmap['nature']]) if cmap.get('nature') is not None and cmap['nature'] < len(cells) else ''

                raw_val = cells[cmap['value']] if cmap.get('value') is not None and cmap['value'] < len(cells) else ''
                raw_deb = cells[cmap['debit']] if cmap.get('debit') is not None and cmap['debit'] < len(cells) else ''
                raw_cred = cells[cmap['credit']] if cmap.get('credit') is not None and cmap['credit'] < len(cells) else ''

                if not raw_hist and not raw_val and not raw_deb and not raw_cred:
                    continue

                d_norm = norm(raw_date)
                h_norm = norm(raw_hist)
                if d_norm in ('total', 'totais', 'subtotal', 'dif', 'diferenca') or h_norm in ('total', 'totais', 'saldo', 'total deb', 'total cre', 'diferenca'):
                    continue

                val_deb = parse_currency(raw_deb)
                val_cred = parse_currency(raw_cred)
                val_num = parse_currency(raw_val)

                sign = 0
                final_val = Decimal('0.00')

                if raw_nat in ('c', 'credito'):
                    sign = -1
                    final_val = val_cred if val_cred > 0 else (val_num if val_num > 0 else abs(val_num))
                elif raw_nat in ('d', 'debito'):
                    sign = 1
                    final_val = val_deb if val_deb > 0 else (val_num if val_num > 0 else abs(val_num))
                elif val_cred > 0 and (val_deb == 0 or val_deb is None):
                    sign = -1
                    final_val = val_cred
                elif val_deb > 0 and (val_cred == 0 or val_cred is None):
                    sign = 1
                    final_val = val_deb
                elif val_num > 0:
                    final_val = val_num
                    is_entrada = bool(re.search(r'\b(?:entrada|aquisicao|provisao|fatura|duplicata|compra)\b', h_norm))
                    is_pagto = bool(re.search(r'\b(?:pagto|pgto|pagamento|pago|devolucao|debito|estorno)\b', h_norm))
                    if is_entrada and not is_pagto:
                        sign = -1
                    elif is_pagto:
                        sign = 1
                    else:
                        sign = -1
                elif val_num < 0:
                    final_val = abs(val_num)
                    sign = -1
                else:
                    continue

                if final_val <= 0:
                    continue

                date_str = parse_date_safely(raw_date) or '2025-12-31'

                info = extract_transaction_info(raw_hist, 'CREDIT' if sign == -1 else 'DEBIT')

                nf_val = raw_nf if raw_nf and raw_nf.upper() != 'X' else (info.get('extracted_nf') or '')
                if not nf_val or nf_val in ('S/N', '0'):
                    fb = extract_fallback_number(raw_hist)
                    if fb:
                        nf_val = fb

                supplier_val = raw_sup if raw_sup else (info.get('extracted_supplier') or raw_hist)
                supplier_cleaned = re.sub(r'^(?:ENTRADA|AQUISICAO|DEVOLUCAO|PGTO|PAGAMENTO)\s+(?:CONFORME\s+)?(?:NOTA\s+FISCAL|NF)?\s*', '', supplier_val, flags=re.I).strip()
                if not raw_sup:
                    if not supplier_cleaned or supplier_cleaned == nf_val or supplier_cleaned.isdigit() or norm(supplier_cleaned) in ('', 'sn', '0', 's/n'):
                        supplier_val = raw_hist
                    else:
                        supplier_val = supplier_cleaned
                else:
                    supplier_val = supplier_cleaned or raw_sup

                rows.append({
                    'extracted_supplier': str(supplier_val),
                    'extracted_nf': str(nf_val),
                    'trans_date': date_str,
                    'history': str(raw_hist),
                    'document_number': str(raw_doc or raw_nf or ''),
                    'value': str(sign * final_val)
                })

        if len(rows) > len(best_rows):
            best_rows = rows

    if not best_rows:
        raise ValueError('Nenhum lancamento valido encontrado na planilha complementar.')

    return best_rows


def inspect_opening_spreadsheet(path, custom_header_row=None):
    base_df = universal_read_spreadsheet(path).dropna(how='all').dropna(axis=1, how='all')
    if base_df.empty:
        raise ValueError('Planilha vazia.')

    num_rows, num_cols = base_df.shape

    # Determine header row (1-based index, or 0 for headerless)
    header_row_idx = -1
    if custom_header_row is not None:
        header_row_idx = custom_header_row - 1 if custom_header_row > 0 else -1
    else:
        for idx in range(min(5, num_rows)):
            row_cells = [norm(base_df.iloc[idx, c]) for c in range(num_cols)]
            if detect_column_mapping(row_cells):
                header_row_idx = idx
                break

    from openpyxl.utils import get_column_letter
    columns = []
    for c in range(num_cols):
        hdr = ''
        if header_row_idx >= 0 and header_row_idx < num_rows:
            val = base_df.iloc[header_row_idx, c]
            hdr = str(val).strip() if pd.notna(val) else ''
        letter = get_column_letter(c + 1)
        columns.append({
            'index': c,
            'letter': letter,
            'header': hdr
        })

    if header_row_idx >= 0:
        row_cells = [norm(base_df.iloc[header_row_idx, c]) for c in range(num_cols)]
        detected = detect_column_mapping(row_cells) or {}
    else:
        detected = infer_headerless_mapping(base_df) or {}

    mapping = {}
    for key in ('date', 'value', 'history', 'doc', 'nf', 'supplier', 'debit', 'credit', 'nature', 'amount'):
        if key in detected and detected[key] is not None:
            mapping[key] = detected[key]

    start_data = header_row_idx + 1 if header_row_idx >= 0 else 0
    sample_rows = []
    for r in range(start_data, min(start_data + 6, num_rows)):
        row_vals = [str(base_df.iloc[r, c]).strip() if pd.notna(base_df.iloc[r, c]) else '' for c in range(num_cols)]
        sample_rows.append(row_vals)

    return {
        'row_count': num_rows,
        'column_count': num_cols,
        'header_row': header_row_idx + 1 if header_row_idx >= 0 else 0,
        'columns': columns,
        'mapping': mapping,
        'sample_rows': sample_rows
    }


def validate_opening_spreadsheet(path, header_row, column_mapping, job_initial_balance='0.00'):
    rows = read_opening(path, column_mapping=column_mapping, header_row=header_row)
    if not rows:
        raise ValueError('Nenhum lançamento válido encontrado com o mapeamento informado.')

    total_amount = sum(abs(Decimal(r['value'])) for r in rows)
    initial_dec = abs(Decimal(str(job_initial_balance or 0)))
    difference = abs(initial_dec - total_amount)

    return {
        'valid': True,
        'count': len(rows),
        'total_amount': str(total_amount.quantize(Decimal('0.01'))),
        'job_initial_balance': str(initial_dec.quantize(Decimal('0.01'))),
        'difference': str(difference.quantize(Decimal('0.01'))),
        'sample': rows[:10],
        'header_row': header_row,
        'mapping': column_mapping
    }
