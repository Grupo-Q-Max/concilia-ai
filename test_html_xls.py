import pandas as pd
import os

html_content = """
<html><body>
<table>
<tr><td>Data</td><td>Histórico</td><td>Débito</td><td>Crédito</td><td>Saldo</td></tr>
<tr><td>2026-05-14</td><td>ENTRADA CONFORME NOTA FISCAL FORNECEDOR 123</td><td></td><td>1000</td><td>-1000</td></tr>
</table>
</body></html>
"""
with open("test_html.xls", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Testing test_html.xls...")
try:
    pd.read_excel("test_html.xls")
    print("read_excel succeeded")
except Exception as e:
    print("read_excel failed with:", type(e).__name__, e)
    # Recover with read_html
    dfs = pd.read_html("test_html.xls")
    print("Recovered with read_html! Shape:", dfs[0].shape)

os.remove("test_html.xls")
