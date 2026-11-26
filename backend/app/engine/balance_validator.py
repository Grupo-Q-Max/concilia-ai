"""
CONCILIA AI - Mathematical Audit & Balance Validator
Rigorous accounting validation:
- Validates: Final Balance = Initial Balance + Debits - Credits (respecting credit/debit sign nature)
- Explains mathematical origin of differences:
  * Monthly accumulator reset behavior (e.g., Q-MAX software convention)
  * Period net movement (Crédito - Débito)
  * Open invoices position vs Net Period movement
  * Deterministic breakdown
"""
from decimal import Decimal
from typing import Dict, Any, List

def audit_accounting_balance(initial_balance: Decimal, final_reported_balance: Decimal, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Audits the accounting ledger's mathematical integrity.
    """
    total_credits = sum((t['amount'] for t in transactions if t['trans_type'] == 'CREDIT'), Decimal('0.00'))
    total_debits = sum((t['amount'] for t in transactions if t['trans_type'] == 'DEBIT'), Decimal('0.00'))
    period_net_creditor = total_credits - total_debits
    period_net_debtor = total_debits - total_credits
    expected_final_balance = initial_balance + period_net_debtor
    is_exact_cumulative_match = final_reported_balance == expected_final_balance
    if not is_exact_cumulative_match and final_reported_balance == (initial_balance + period_net_creditor):
        expected_final_balance = initial_balance + period_net_creditor
        is_exact_cumulative_match = True
    monthly_groups: Dict[str, Dict[str, Decimal]] = {}
    for t in transactions:
        month = t['trans_date'][:7] if len(t['trans_date']) >= 7 else 'Geral'
        if month not in monthly_groups:
            monthly_groups[month] = {'credits': Decimal('0.00'), 'debits': Decimal('0.00'), 'first_balance': Decimal('0.00'), 'last_balance': Decimal('0.00')}
        if t['trans_type'] == 'CREDIT':
            monthly_groups[month]['credits'] += t['amount']
        else:
            monthly_groups[month]['debits'] += t['amount']
        if t.get('reported_balance') is not None:
            monthly_groups[month]['last_balance'] = t['reported_balance']
    last_month_key = sorted(monthly_groups.keys())[-1] if monthly_groups else None
    last_month_data = monthly_groups[last_month_key] if last_month_key else None
    is_monthly_reset_detected = False
    monthly_match_explanation = ''
    if last_month_data:
        last_month_net_deb_minus_cred = last_month_data['debits'] - last_month_data['credits']
        last_month_net_cred_minus_deb = last_month_data['credits'] - last_month_data['debits']
        if final_reported_balance in [last_month_net_deb_minus_cred, last_month_net_cred_minus_deb]:
            is_monthly_reset_detected = True
            monthly_match_explanation = f"O saldo informado na última linha (R$ {final_reported_balance:,.2f}) corresponde exatamente ao movimento líquido da competência final ({last_month_key}: Débitos R$ {last_month_data['debits']:,.2f} - Créditos R$ {last_month_data['credits']:,.2f} = R$ {last_month_net_deb_minus_cred:,.2f}). O software contábil de origem reinicia o acumulador analítico a cada mês civil."
    status = 'VALID' if is_exact_cumulative_match or is_monthly_reset_detected else 'DIVERGENT'
    explanation = {'status': status, 'is_exact_cumulative_match': is_exact_cumulative_match, 'is_monthly_reset_detected': is_monthly_reset_detected, 'total_credits': str(total_credits), 'total_debits': str(total_debits), 'initial_balance': str(initial_balance), 'final_reported_balance': str(final_reported_balance), 'expected_final_balance': str(expected_final_balance), 'period_net_creditor': str(period_net_creditor), 'period_net_debtor': str(period_net_debtor), 'monthly_match_explanation': monthly_match_explanation, 'audit_note': f'Auditoria Matemática Realizada com Sucesso. Total de Créditos: R$ {total_credits:,.2f} | Total de Débitos: R$ {total_debits:,.2f} | Variação Líquida do Período: R$ {period_net_debtor:,.2f}. ' + (monthly_match_explanation if is_monthly_reset_detected else '')}
    return explanation


# CONCILIA_V5_AUDIT_PRESENTATION_28

_original_audit_v5 = audit_accounting_balance

def audit_accounting_balance(
    initial_balance,
    final_reported_balance,
    transactions
):
    result = _original_audit_v5(
        initial_balance,
        final_reported_balance,
        transactions
    )

    movement = Decimal(str(result["period_net_debtor"]))

    note = (
        "Auditoria matematica: "
        + str(result["status"])
        + " | Total de debitos: R$ "
        + str(result["total_debits"])
        + " | Total de creditos: R$ "
        + str(result["total_credits"])
        + " | Movimentacao liquida D+/C-: R$ "
        + format(movement, ".2f")
        + " | Saldo final calculado: R$ "
        + str(result["expected_final_balance"])
    )

    if result.get("is_exact_cumulative_match"):
        result["is_monthly_reset_detected"] = False
        result["monthly_match_explanation"] = ""
    else:
        explanation = result.get("monthly_match_explanation")
        if explanation:
            note += " | " + explanation

    result["audit_note"] = note

    return result
