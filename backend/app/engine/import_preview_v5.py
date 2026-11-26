
"""CONCILIA_V5_IMPORT_PREVIEW_29D31"""

from pathlib import Path
from tempfile import TemporaryDirectory
from decimal import Decimal
import hashlib
import json

from fastapi import UploadFile, HTTPException

from app.engine.parser import parse_accounting_ledger
from app.engine.import_mapping_v5 import inspect_ledger_v5
from app.engine.balance_validator import audit_accounting_balance

MAX_BYTES = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".xls", ".xlsx", ".xlsm", ".xlsb",
    ".csv", ".html", ".htm", ".xml"
}


def money_v5(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )


def receive_preview_file_v5(file, folder):

    suffix = Path(
        file.filename or ""
    ).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato de planilha nao suportado."
        )

    path = Path(folder) / ("preview" + suffix)

    digest = hashlib.sha256()
    total = 0

    with path.open("wb") as output:

        while True:

            chunk = file.file.read(1024 * 1024)

            if not chunk:
                break

            total += len(chunk)

            if total > MAX_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Planilha acima de 50 MB."
                )

            digest.update(chunk)
            output.write(chunk)

    if total == 0:
        raise HTTPException(
            status_code=400,
            detail="Planilha vazia."
        )

    return path, digest.hexdigest()


def mapping_fingerprint_v5(
    file_hash, header_row, mapping
):

    payload = json.dumps(
        {
            "file_hash": file_hash,
            "header_row": header_row,
            "mapping": mapping
        },
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def preview_upload_v5(file, header_row=None):

    with TemporaryDirectory(
        prefix="concilia_preview_"
    ) as folder:

        path, digest = receive_preview_file_v5(
            file, folder
        )

        result = inspect_ledger_v5(
            path,
            header_row=header_row
        )

        result["file_hash"] = digest
        result["filename"] = file.filename

        return result


def validate_upload_v5(
    file, header_row, mapping
):

    with TemporaryDirectory(
        prefix="concilia_validate_"
    ) as folder:

        path, digest = receive_preview_file_v5(
            file, folder
        )

        parsed = parse_accounting_ledger(
            str(path),
            header_row=header_row,
            column_mapping=mapping
        )

        meta = parsed["metadata"]
        tx = parsed["transactions"]

        initial = money_v5(
            meta["initial_balance"]
        )

        reported = money_v5(
            meta["final_reported_balance"]
        )

        debits = sum(
            (
                money_v5(t["amount"])
                for t in tx
                if t["trans_type"] == "DEBIT"
            ),
            Decimal("0.00")
        )

        credits = sum(
            (
                money_v5(t["amount"])
                for t in tx
                if t["trans_type"] == "CREDIT"
            ),
            Decimal("0.00")
        )

        calculated = initial + debits - credits

        difference = calculated - reported

        audit = audit_accounting_balance(
            initial,
            reported,
            tx
        )

        valid = (
            bool(tx)
            and difference == 0
            and audit["status"] == "VALID"
        )

        return {
            "valid": valid,
            "transaction_count": len(tx),
            "initial_balance": str(initial),
            "total_debits": str(debits),
            "total_credits": str(credits),
            "calculated_balance": str(calculated),
            "reported_balance": str(reported),
            "difference": str(difference),
            "audit_status": audit["status"],
            "file_hash": digest,
            "mapping_fingerprint":
                mapping_fingerprint_v5(
                    digest, header_row, mapping
                ),
            "header_row": header_row,
            "mapping": mapping,
            "sample": tx[:10],
            "preview_only": True
        }
