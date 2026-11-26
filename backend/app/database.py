"""
CONCILIA AI - Database Module (SQLite with Decimal precision & JSON support)
"""
import sqlite3
import json
from decimal import Decimal
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            company_name TEXT,
            cnpj TEXT,
            period TEXT,
            account_code TEXT,
            initial_balance TEXT DEFAULT '0.00',
            final_reported_balance TEXT DEFAULT '0.00',
            total_credits TEXT DEFAULT '0.00',
            total_debits TEXT DEFAULT '0.00',
            period_net_movement TEXT DEFAULT '0.00',
            status TEXT NOT NULL DEFAULT 'PENDING',
            math_validation_status TEXT DEFAULT 'VALID',
            math_explanation TEXT,
            metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            trans_date TEXT NOT NULL,
            history TEXT NOT NULL,
            trans_type TEXT NOT NULL, -- CREDIT or DEBIT
            amount TEXT NOT NULL, -- Decimal as string
            reported_balance TEXT,
            extracted_nf TEXT,
            extracted_supplier TEXT,
            cleaned_supplier TEXT,
            category TEXT,
            status TEXT NOT NULL DEFAULT 'EM_ABERTO',
            matched_amount TEXT DEFAULT '0.00',
            remaining_amount TEXT NOT NULL,
            is_reversal INTEGER DEFAULT 0,
            is_duplicate INTEGER DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reconciliations (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            match_type TEXT NOT NULL, -- EXACT_1_TO_1, CENT_DIFFERENCE, PARTIAL, GROUPED, MANUAL, REVERSAL
            invoice_trans_id TEXT,
            payment_trans_id TEXT,
            nf TEXT,
            supplier TEXT,
            invoice_amount TEXT,
            payment_amount TEXT,
            reconciled_amount TEXT NOT NULL,
            difference TEXT DEFAULT '0.00',
            confidence_score REAL DEFAULT 1.0,
            status TEXT NOT NULL DEFAULT 'CONFIRMED', -- CONFIRMED, PENDING_REVIEW, REJECTED
            match_notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (invoice_trans_id) REFERENCES transactions(id) ON DELETE SET NULL,
            FOREIGN KEY (payment_trans_id) REFERENCES transactions(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS opening_compositions (job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
    # CONCILIA_V5_OPENING_MIGRATION
    from app.engine.opening_storage_v5 import (
        ensure_opening_storage
    )

    try:
        with conn:
            ensure_opening_storage(conn)
    finally:
        conn.close()
