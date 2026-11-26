import os
import io
import re
import xml.etree.ElementTree as ET
import pandas as pd

def universal_read_spreadsheet(file_path: str) -> pd.DataFrame:
    """
    Tries every known parser engine to read the tabular data:
    1. Standard pandas read_excel (default)
    2. openpyxl engine (.xlsx, even if named .xls)
    3. xlrd engine (.xls)
    4. Offset search for OLE magic / BIFF BOF (recovers files with leading junk bytes)
    5. HTML table parser (ERPs exporting HTML with .xls)
    6. XML Spreadsheet 2003 parser (Excel 2003 XML SpreadsheetML)
    7. CSV/TSV parser with auto delimiter and encodings
    """
    errors = []

    # 1. Default read_excel
    try:
        return pd.read_excel(file_path, header=None)
    except Exception as e:
        errors.append(f"read_excel default: {e}")

    # 2. openpyxl (in case it is an xlsx renamed to xls)
    try:
        return pd.read_excel(file_path, engine="openpyxl", header=None)
    except Exception as e:
        errors.append(f"openpyxl: {e}")

    # 3. Check for OLE header or BIFF BOF offset
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        ole_magic = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        biff8_bof = b'\x09\x08'
        biff5_bof = b'\x09\x04'

        # If OLE magic is present at an offset > 0
        ole_pos = raw_bytes.find(ole_magic)
        if ole_pos > 0:
            print(f"Found OLE header at offset {ole_pos}, attempting recovery...")
            cleaned = raw_bytes[ole_pos:]
            return pd.read_excel(io.BytesIO(cleaned), engine="xlrd", header=None)

        # If BIFF BOF is present at an offset > 0
        for bof in [biff8_bof, biff5_bof]:
            bof_pos = raw_bytes.find(bof)
            if bof_pos > 0 and bof_pos < 1024:
                print(f"Found BOF record at offset {bof_pos}, attempting recovery...")
                cleaned = raw_bytes[bof_pos:]
                try:
                    return pd.read_excel(io.BytesIO(cleaned), engine="xlrd", header=None)
                except Exception:
                    pass
    except Exception as e:
        errors.append(f"offset recovery: {e}")

    # 4. xlrd with ignore_workbook_corruption if available
    try:
        import xlrd
        book = xlrd.open_workbook(file_path, ignore_workbook_corruption=True)
        sheet = book.sheet_by_index(0)
        data = [sheet.row_values(r) for r in range(sheet.nrows)]
        return pd.DataFrame(data)
    except Exception as e:
        errors.append(f"xlrd corruption fallback: {e}")

    # 5. HTML table parser
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

    raise ValueError(f"Não foi possível abrir o arquivo. Erros reportados: {'; '.join(errors[:3])}")

print("Universal reader definition complete.")
