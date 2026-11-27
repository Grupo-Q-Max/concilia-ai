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

    def test_composition_partial_shows_both_debit_and_credit(self):
        from app.engine.composition import composition
        job = {'initial_balance': '0.00', 'final_reported_balance': '-208.32'}
        tx = [
            {
                'id': 'tx1',
                'trans_date': '2026-01-02',
                'trans_type': 'CREDIT',
                'amount': '4480.00',
                'remaining_amount': '208.32',
                'matched_amount': '4271.68',
                'status': 'PARCIALMENTE_CONCILIADO',
                'extracted_nf': '3301',
                'extracted_supplier': 'SANTIFERR',
                'history': 'ENTRADA NOTA FISCAL SANTIFERR'
            }
        ]
        res = composition(job, tx)
        self.assertEqual(len(res['rows']), 2)
        kinds = [r['kind'] for r in res['rows']]
        self.assertIn("Nota parcialmente baixada (Crédito)", kinds)
        self.assertIn("Baixa parcial vinculada (Débito)", kinds)
        total = sum(Decimal(r['value']) for r in res['rows'])
        self.assertEqual(total, Decimal('-208.32'))
        self.assertTrue(res['valid'])

        from app.engine.closing_v5 import closing_summary_v5
        closing = closing_summary_v5(job, res)
        self.assertTrue(closing['valid'])
        self.assertEqual(closing['unknown_count'], 0)
        self.assertEqual(Decimal(closing['credit_residual']), Decimal('-208.32'))
        self.assertEqual(Decimal(closing['other_residual']), Decimal('0.00'))

    def test_tax_retention_extraction_and_supplier_consolidation(self):
        from app.engine.extractor import extract_transaction_info
        from app.engine.full_snapshot_v5 import supplier_summary_v5

        info = extract_transaction_info(
            "VALOR A SER RECOLHIDO IRRF 28102 GONÇALVES BASSE E BENETTI ADVOGADOS ASSOCIADOS",
            "CREDIT"
        )
        self.assertEqual(info["extracted_nf"], "28102")
        self.assertEqual(
            info["extracted_supplier"],
            "GONÇALVES BASSE E BENETTI ADVOGADOS ASSOCIADOS"
        )

        tx = [
            {
                "trans_type": "CREDIT",
                "amount": "1161.58",
                "matched_amount": "1029.08",
                "remaining_amount": "132.50",
                "extracted_supplier": "A. G. M. PRESTADORA DE SERVICOS LTDA",
                "cleaned_supplier": "",
            },
            {
                "trans_type": "DEBIT",
                "amount": "1029.08",
                "matched_amount": "1029.08",
                "remaining_amount": "0.00",
                "extracted_supplier": "AGM PRESTADORA DE SERVICO",
                "cleaned_supplier": "",
            },
        ]
        summary = supplier_summary_v5(tx)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["total_invoiced"], "1161.58")
        self.assertEqual(summary[0]["total_paid"], "1029.08")
        self.assertEqual(summary[0]["open_balance"], "132.50")

if __name__ == "__main__":
    unittest.main()
