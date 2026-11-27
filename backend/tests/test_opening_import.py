import unittest
import sys
import os
import tempfile
import pandas as pd
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.opening_import import read_opening, infer_headerless_mapping, detect_column_mapping, norm


class TestOpeningImport(unittest.TestCase):

    def test_headerless_3_columns_excel(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            df = pd.DataFrame([
                ["2024-12-31", "entrada conforme NOTA FISCAL 1", 1.0],
                ["2024-12-31", "NOTA FISCAL 2", 2.0],
                ["2024-12-31", "NOTA FISCAL 3", 5.0],
                ["2024-12-31", "NOTA FISCAL 4", 10.0],
                ["2024-12-31", "NOTA FISCAL 5", 51200.0],
            ])
            df.to_excel(temp_path, index=False, header=False)

            rows = read_opening(temp_path)
            self.assertEqual(len(rows), 5)
            self.assertEqual(rows[0]["extracted_nf"], "1")
            self.assertEqual(rows[0]["value"], "-1.00")
            self.assertEqual(rows[0]["trans_date"], "2024-12-31")
            self.assertEqual(rows[4]["extracted_nf"], "5")
            self.assertEqual(rows[4]["value"], "-51200.00")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_headerless_3_columns_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
            f.write("2024-12-31,entrada conforme NOTA FISCAL 1,1\n")
            f.write("2024-12-31,NOTA FISCAL 2,2\n")
            f.write("2024-12-31,NOTA FISCAL 5,51200\n")
            temp_path = f.name

        try:
            rows = read_opening(temp_path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["extracted_nf"], "1")
            self.assertEqual(rows[0]["value"], "-1.00")
            self.assertEqual(rows[2]["extracted_nf"], "5")
            self.assertEqual(rows[2]["value"], "-51200.00")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_with_headers_3_columns(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name

        try:
            df = pd.DataFrame([
                ["Data", "Histórico", "Valor"],
                ["2024-12-31", "NF 100 - FORNECEDOR ABC", 1500.50],
                ["2024-12-31", "NF 101 - FORNECEDOR XYZ", 3200.00],
            ])
            df.to_excel(temp_path, index=False, header=False)

            rows = read_opening(temp_path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["extracted_nf"], "100")
            self.assertEqual(rows[0]["value"], "-1500.50")
            self.assertEqual(rows[1]["extracted_nf"], "101")
            self.assertEqual(rows[1]["value"], "-3200.00")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == '__main__':
    unittest.main()
