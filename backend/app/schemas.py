"""
CONCILIA AI - Pydantic Schemas for API
"""
from pydantic import BaseModel, Field
from pydantic import StrictBool
from typing import List, Dict, Any, Optional

class JobSummaryResponse(BaseModel):
    id: str
    filename: str
    company_name: str
    cnpj: str
    period: str
    account_code: str
    initial_balance: str
    final_reported_balance: str
    total_credits: str
    total_debits: str
    period_net_movement: str
    status: str
    math_validation_status: str
    math_explanation: Optional[Dict[str, Any]] = None
    summary: Dict[str, Any]

class TransactionResponse(BaseModel):
    id: str
    job_id: str
    row_index: int
    trans_date: str
    history: str
    trans_type: str
    amount: str
    reported_balance: Optional[str] = None
    extracted_nf: Optional[str] = None
    extracted_supplier: Optional[str] = None
    cleaned_supplier: Optional[str] = None
    category: Optional[str] = None
    status: str
    matched_amount: str
    remaining_amount: str
    is_reversal: int = 0
    is_duplicate: int = 0

class ReconciliationResponse(BaseModel):
    id: str
    job_id: str
    match_type: str
    invoice_trans_id: Optional[str] = None
    payment_trans_id: Optional[str] = None
    nf: Optional[str] = None
    supplier: Optional[str] = None
    invoice_amount: Optional[str] = None
    payment_amount: Optional[str] = None
    reconciled_amount: str
    difference: str
    confidence_score: float
    status: str
    match_notes: Optional[str] = None
    created_at: str

class ManualMatchRequest(BaseModel):
    invoice_trans_id: str
    payment_trans_id: str
    notes: Optional[str] = "Conciliação manual aprovada pelo usuário."

    # CONCILIA_V5_STALE_APPROVAL_30A3C1
    expected_invoice_remaining: Optional[str] = None
    expected_payment_remaining: Optional[str] = None
    approval_source: str = "MANUAL"
    # CONCILIA_V5_STRICT_APPROVAL_30A3C4D
    confirm_review: StrictBool = False


class SupplierSummaryItem(BaseModel):
    supplier: str
    total_invoiced: str
    total_paid: str
    open_balance: str
    invoices_count: int
    status: str
