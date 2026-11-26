"""
CONCILIA AI - Automated Unit & Integration Tests
Covers:
- Partial payments
- Grouped payments
- Cent differences
- Duplicates
- Reversals (Estornos)
- Initial balance variations
- Mathematical audit
"""
import unittest
from decimal import Decimal
import sys
import os

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.reconciler import run_reconciliation
from app.engine.balance_validator import audit_accounting_balance
from app.engine.extractor import extract_transaction_info, clean_supplier_name
from app.engine.ai_matcher import compute_similarity, are_suppliers_compatible

class TestReconcilerEdgeCases(unittest.TestCase):
    
    def test_exact_1_to_1_matching(self):
        transactions = [
            {
                "row_index": 1,
                "trans_date": "2026-06-01",
                "history": "ENTRADA CONFORME NOTA FISCAL FORNECEDOR ALFA LTDA 1001",
                "trans_type": "CREDIT",
                "amount": Decimal("1500.00"),
                "extracted_nf": "1001",
                "extracted_supplier": "FORNECEDOR ALFA LTDA",
                "cleaned_supplier": clean_supplier_name("FORNECEDOR ALFA LTDA"),
                "category": "PROVISAO_NOTA_FISCAL"
            },
            {
                "row_index": 2,
                "trans_date": "2026-06-15",
                "history": "PAGAMENTO NF:1001 Fornecedor Alfa Itens: Servicos",
                "trans_type": "DEBIT",
                "amount": Decimal("1500.00"),
                "extracted_nf": "1001",
                "extracted_supplier": "Fornecedor Alfa",
                "cleaned_supplier": clean_supplier_name("Fornecedor Alfa"),
                "category": "PAGAMENTO_FORNECEDOR"
            }
        ]
        res = run_reconciliation("job-test", transactions)
        self.assertEqual(res["summary"]["reconciled_count"], 1)
        self.assertEqual(Decimal(res["summary"]["total_open_value"]), Decimal("0.00"))
        self.assertEqual(res["transactions"][0]["status"], "CONCILIADO")
        self.assertEqual(res["transactions"][1]["status"], "CONCILIADO")

    def test_cent_difference_matching(self):
        # 1 cent divergence (e.g. Credit 6492.96 vs Debit 6492.95)
        transactions = [
            {
                "row_index": 1,
                "trans_date": "2026-07-01",
                "history": "ENTRADA CONFORME NOTA FISCAL EMPRESA BETA 54994",
                "trans_type": "CREDIT",
                "amount": Decimal("6492.96"),
                "extracted_nf": "54994",
                "extracted_supplier": "EMPRESA BETA",
                "cleaned_supplier": clean_supplier_name("EMPRESA BETA"),
                "category": "PROVISAO_NOTA_FISCAL"
            },
            {
                "row_index": 2,
                "trans_date": "2026-07-10",
                "history": "PAGAMENTO NF:54994 Empresa Beta Itens: Manutencao",
                "trans_type": "DEBIT",
                "amount": Decimal("6492.95"),
                "extracted_nf": "54994",
                "extracted_supplier": "Empresa Beta",
                "cleaned_supplier": clean_supplier_name("Empresa Beta"),
                "category": "PAGAMENTO_FORNECEDOR"
            }
        ]
        res = run_reconciliation("job-test-cent", transactions)
        self.assertEqual(res["summary"]["cent_differences_count"], 1)
        self.assertEqual(Decimal(res["summary"]["cent_differences_total"]), Decimal("0.01"))
        self.assertEqual(res["transactions"][0]["status"], "DIVERGENCIA_CENTAVOS")
        self.assertEqual(res["transactions"][1]["status"], "DIVERGENCIA_CENTAVOS")

    def test_partial_payment(self):
        # Invoice of 10,000 paid with 4,000 first, 6,000 remaining
        transactions = [
            {
                "row_index": 1,
                "trans_date": "2026-08-01",
                "history": "ENTRADA CONFORME NOTA FISCAL CONSTRUTORA GAMA 8800",
                "trans_type": "CREDIT",
                "amount": Decimal("10000.00"),
                "extracted_nf": "8800",
                "extracted_supplier": "CONSTRUTORA GAMA",
                "cleaned_supplier": clean_supplier_name("CONSTRUTORA GAMA"),
                "category": "PROVISAO_NOTA_FISCAL"
            },
            {
                "row_index": 2,
                "trans_date": "2026-08-15",
                "history": "PAGAMENTO Parcela 1 NF:8800 Construtora Gama Itens: Obra",
                "trans_type": "DEBIT",
                "amount": Decimal("4000.00"),
                "extracted_nf": "8800",
                "extracted_supplier": "Construtora Gama",
                "cleaned_supplier": clean_supplier_name("Construtora Gama"),
                "category": "PAGAMENTO_FORNECEDOR"
            }
        ]
        res = run_reconciliation("job-test-partial", transactions)
        t_inv = res["transactions"][0]
        t_pay = res["transactions"][1]
        
        self.assertEqual(t_inv["status"], "PARCIAL")
        self.assertEqual(t_inv["matched_amount"], Decimal("4000.00"))
        self.assertEqual(t_inv["remaining_amount"], Decimal("6000.00"))
        self.assertEqual(t_pay["status"], "CONCILIADO")
        self.assertEqual(res["summary"]["partial_count"], 1)
        self.assertEqual(Decimal(res["summary"]["total_open_value"]), Decimal("6000.00"))

    def test_grouped_payment(self):
        # 2 invoices (300 + 700) paid in 1 single payment of 1,000
        transactions = [
            {
                "row_index": 1,
                "trans_date": "2026-08-01",
                "history": "ENTRADA CONFORME NOTA FISCAL FORNECEDOR DELTA 7701",
                "trans_type": "CREDIT",
                "amount": Decimal("300.00"),
                "extracted_nf": "7701",
                "extracted_supplier": "FORNECEDOR DELTA",
                "cleaned_supplier": clean_supplier_name("FORNECEDOR DELTA"),
                "category": "PROVISAO_NOTA_FISCAL"
            },
            {
                "row_index": 2,
                "trans_date": "2026-08-01",
                "history": "ENTRADA CONFORME NOTA FISCAL FORNECEDOR DELTA 7701", # Same NF grouped billing
                "trans_type": "CREDIT",
                "amount": Decimal("700.00"),
                "extracted_nf": "7701",
                "extracted_supplier": "FORNECEDOR DELTA",
                "cleaned_supplier": clean_supplier_name("FORNECEDOR DELTA"),
                "category": "PROVISAO_NOTA_FISCAL"
            },
            {
                "row_index": 3,
                "trans_date": "2026-08-20",
                "history": "PAGAMENTO Agrupado NF:7701 Fornecedor Delta Itens: Lote",
                "trans_type": "DEBIT",
                "amount": Decimal("1000.00"),
                "extracted_nf": "7701",
                "extracted_supplier": "Fornecedor Delta",
                "cleaned_supplier": clean_supplier_name("Fornecedor Delta"),
                "category": "PAGAMENTO_FORNECEDOR"
            }
        ]
        res = run_reconciliation("job-test-grouped", transactions)
        self.assertEqual(Decimal(res["summary"]["total_open_value"]), Decimal("0.00"))
        self.assertEqual(res["transactions"][0]["status"], "CONCILIADO")
        self.assertEqual(res["transactions"][1]["status"], "CONCILIADO")
        self.assertEqual(res["transactions"][2]["status"], "CONCILIADO")

    def test_reversal_estorno(self):
        # Entry followed by its exact Estorno
        transactions = [
            {
                "row_index": 1,
                "trans_date": "2026-09-01",
                "history": "ENTRADA NOTA FISCAL EPSILON 9999",
                "trans_type": "CREDIT",
                "amount": Decimal("2500.00"),
                "extracted_nf": "9999",
                "extracted_supplier": "EPSILON",
                "cleaned_supplier": clean_supplier_name("EPSILON"),
                "category": "PROVISAO_NOTA_FISCAL"
            },
            {
                "row_index": 2,
                "trans_date": "2026-09-02",
                "history": "ESTORNO DE LANCAMENTO NOTA FISCAL EPSILON 9999",
                "trans_type": "DEBIT",
                "amount": Decimal("2500.00"),
                "extracted_nf": "9999",
                "extracted_supplier": "EPSILON",
                "cleaned_supplier": clean_supplier_name("EPSILON"),
                "category": "ESTORNO"
            }
        ]
        res = run_reconciliation("job-test-reversal", transactions)
        self.assertEqual(res["transactions"][0]["status"], "ESTORNO")
        self.assertEqual(res["transactions"][1]["status"], "ESTORNO")
        self.assertEqual(Decimal(res["summary"]["total_open_value"]), Decimal("0.00"))

    def test_balance_validator_math(self):
        # Validates accounting balance formula: Final = Initial + Credits - Debits
        trans = [
            {"trans_date": "2026-01-10", "trans_type": "CREDIT", "amount": Decimal("5000.00")},
            {"trans_date": "2026-01-20", "trans_type": "DEBIT", "amount": Decimal("3000.00")},
        ]
        initial = Decimal("1000.00")
        expected_final = Decimal("3000.00") # 1000 + 5000 - 3000 = 3000
        audit = audit_accounting_balance(initial, expected_final, trans)
        self.assertEqual(audit["status"], "VALID")
        self.assertTrue(audit["is_exact_cumulative_match"])

    def test_fallback_nf_extraction_and_matching(self):
        from app.engine.extractor import extract_fallback_number
        from app.engine.reconciler import v5_reference, v5_supplier_match

        # Case 1: Servilimp 186
        h_serv = "VALOR A SER RECOLHIDO CRF Servilimp Conservacao e Limpeza Eireli 186"
        self.assertEqual(extract_fallback_number(h_serv), "186")
        info_serv = extract_transaction_info(h_serv, "C")
        self.assertEqual(info_serv["extracted_nf"], "186")

        # Case 2: Cushman & Wakefield 128456
        h_cush_c = "PAGAMENTO CUSHMAN & WAKEFIELD CONSULTORIA IMOBILIARIA LTDA 128456"
        h_cush_d = "PAGAMENTO Contrato Gerenciamento NF:128456 Cushman & Wakefield Consultoria Imob. Ltda. Itens: Gerenciamento de propriedade ref.03/2026"
        self.assertEqual(extract_fallback_number(h_cush_c), "128456")
        info_c = extract_transaction_info(h_cush_c, "C")
        info_d = extract_transaction_info(h_cush_d, "D")
        self.assertEqual(info_c["extracted_nf"], "128456")
        self.assertEqual(info_d["extracted_nf"], "128456")

        inv = {"history": h_cush_c, "extracted_nf": info_c["extracted_nf"], "extracted_supplier": info_c["extracted_supplier"], "cleaned_supplier": info_c["cleaned_supplier"]}
        pay = {"history": h_cush_d, "extracted_nf": info_d["extracted_nf"], "extracted_supplier": info_d["extracted_supplier"], "cleaned_supplier": info_d["cleaned_supplier"]}
        self.assertEqual(v5_reference(inv), "128456")
        self.assertEqual(v5_reference(pay), "128456")
        self.assertTrue(v5_supplier_match(inv, pay))

if __name__ == "__main__":
    unittest.main()
