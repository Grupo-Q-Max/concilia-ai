import pandas as pd
import os

xml_content = """<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Sheet1">
  <Table>
   <Row>
    <Cell><Data ss:Type="String">Data</Data></Cell>
    <Cell><Data ss:Type="String">Histórico</Data></Cell>
    <Cell><Data ss:Type="String">Débito</Data></Cell>
    <Cell><Data ss:Type="String">Crédito</Data></Cell>
    <Cell><Data ss:Type="String">Saldo</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">2026-05-14</Data></Cell>
    <Cell><Data ss:Type="String">ENTRADA CONFORME NOTA FISCAL FORNECEDOR 123</Data></Cell>
    <Cell><Data ss:Type="String"></Data></Cell>
    <Cell><Data ss:Type="Number">1000</Data></Cell>
    <Cell><Data ss:Type="Number">-1000</Data></Cell>
   </Row>
  </Table>
 </Worksheet>
</Workbook>
"""

with open("test_xml.xls", "w", encoding="utf-8") as f:
    f.write(xml_content)

print("Testing test_xml.xls...")
try:
    pd.read_excel("test_xml.xls")
    print("read_excel succeeded")
except Exception as e:
    print("read_excel failed with:", type(e).__name__, e)

# How to parse XML SpreadsheetML?
# Beautiful soup or lxml or custom xml parser:
import xml.etree.ElementTree as ET
try:
    tree = ET.parse("test_xml.xls")
    root = tree.getroot()
    # Find all Row elements
    rows = []
    # Namespaces
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    for row in root.findall('.//ss:Row', ns):
        r_vals = []
        for cell in row.findall('ss:Cell', ns):
            data = cell.find('ss:Data', ns)
            r_vals.append(data.text if data is not None else "")
        rows.append(r_vals)
    df_xml = pd.DataFrame(rows)
    print("Recovered with XML SpreadsheetML parser! Shape:", df_xml.shape)
    print(df_xml)
except Exception as ex:
    print("XML error:", ex)

os.remove("test_xml.xls")
