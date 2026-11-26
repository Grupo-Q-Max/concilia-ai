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
    s = str(val).strip()
    if not s or s.upper() in ('X', '-', 'NAN', 'NONE', ''):
        return None
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

    if has_date and has_hist:
        m = {'type': 'table'}
        for idx, c in enumerate(norm_cells):
            if c in ('data', 'emissao', 'dt', 'data emissao', 'dt emissao') and 'date' not in m:
                m['date'] = idx
            elif c in ('lt', 'lote', 'documento', 'doc') and 'doc' not in m:
                m['doc'] = idx
            elif c in ('historico', 'descricao', 'hist') and 'history' not in m:
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


def read_opening(path, initial=None):
    dfs = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            excel_file = pd.ExcelFile(path)
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
        current_map = None

        if len(df.columns) == 4:
            first_cells = [norm(v) for v in df.iloc[0]]
            has_header = first_cells[0] in ('data', 'emissao', 'data emissao') and first_cells[2] in ('historico', 'descricao')
            if not has_header:
                first_date = parse_date_safely(df.iloc[0, 0])
                if first_date:
                    current_map = {'type': 'simple_4', 'date': 0, 'doc': 1, 'history': 2, 'value': 3}

        for r_idx in range(len(df)):
            row = df.iloc[r_idx]
            cells = [str(c).strip() if pd.notna(c) else '' for c in row]
            if not any(cells):
                continue
            norm_cells = [norm(c) for c in cells]

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
                raw_date = cells[cmap['date']] if 'date' in cmap and cmap['date'] < len(cells) else ''
                raw_hist = cells[cmap['history']] if 'history' in cmap and cmap['history'] < len(cells) else ''
                raw_doc = cells[cmap['doc']] if 'doc' in cmap and cmap['doc'] < len(cells) else ''
                raw_nf = cells[cmap['nf']] if 'nf' in cmap and cmap['nf'] < len(cells) else ''
                raw_sup = cells[cmap['supplier']] if 'supplier' in cmap and cmap['supplier'] < len(cells) else ''
                raw_nat = norm(cells[cmap['nature']]) if 'nature' in cmap and cmap['nature'] < len(cells) else ''

                raw_val = cells[cmap['value']] if 'value' in cmap and cmap['value'] < len(cells) else ''
                raw_deb = cells[cmap['debit']] if 'debit' in cmap and cmap['debit'] < len(cells) else ''
                raw_cred = cells[cmap['credit']] if 'credit' in cmap and cmap['credit'] < len(cells) else ''

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
                supplier_val = re.sub(r'^(?:ENTRADA|AQUISICAO|DEVOLUCAO|PGTO|PAGAMENTO)\s+(?:CONFORME\s+)?(?:NOTA\s+FISCAL|NF)?\s*', '', supplier_val, flags=re.I).strip()

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
