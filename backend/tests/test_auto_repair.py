import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from decimal import Decimal
import pandas as pd
from app.engine.auto_repair import auto_repair_ledger_dataframe, clean_cell_value, sanitize_dataframe
from app.engine.parser import parse_currency, find_header_row, parse_accounting_ledger
import tempfile
import os

class TestAutoRepairAndMultiFile(unittest.TestCase):

    def test_parse_currency_edge_cases(self):
        self.assertEqual(parse_currency("- 1.500,00"), Decimal("-1500.00"))
        self.assertEqual(parse_currency("(1.500,00)"), Decimal("-1500.00"))
        self.assertEqual(parse_currency("1.500,00-"), Decimal("-1500.00"))
        self.assertEqual(parse_currency("1.500,00 D"), Decimal("1500.00"))
        self.assertEqual(parse_currency("R$ 1.500,00"), Decimal("1500.00"))
        self.assertEqual(parse_currency("1234.56"), Decimal("1234.56"))
        self.assertEqual(parse_currency("1234,56"), Decimal("1234.56"))
        self.assertEqual(parse_currency("#REF!"), Decimal("0.00"))
        self.assertEqual(parse_currency("#VALUE!"), Decimal("0.00"))

    def test_clean_cell_value(self):
        self.assertIsNone(clean_cell_value("#REF!"))
        self.assertIsNone(clean_cell_value("#N/A"))
        self.assertEqual(clean_cell_value("Texto\xa0Normal"), "Texto Normal")

    def test_auto_repair_missing_balance(self):
        data = [
            ["Data", "Histórico", "Débito", "Crédito"],
            ["01/10/2026", "NF 101 - FORNECEDOR A", None, "1000.00"],
            ["02/10/2026", "PGTO NF 101", "1000.00", None],
        ]
        df = pd.DataFrame(data)
        repaired_df, repairs = auto_repair_ledger_dataframe(df)
        self.assertTrue(len(repairs) > 0)
        self.assertEqual(repaired_df.shape[1], 5) # Added Saldo column
        hdr_idx, mapping = find_header_row(repaired_df)
        self.assertEqual(hdr_idx, 0)
        self.assertIn("balance", mapping)

    def test_parse_accounting_ledger_auto_repairs_missing_balance_file(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            df = pd.DataFrame([
                ["Data", "Histórico", "Débito", "Crédito"],
                ["01/10/2026", "NF 201 - FORNECEDOR XYZ", 0, 500.00],
                ["05/10/2026", "PGTO NF 201", 500.00, 0],
            ])
            df.to_excel(temp_path, index=False, header=False)

            result = parse_accounting_ledger(temp_path)
            self.assertEqual(len(result["transactions"]), 2)
            self.assertEqual(result["metadata"]["final_reported_balance"], Decimal("0.00"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
