"""
CONCILIA AI - Persistent Configuration Module
Stores user-configurable settings in data/settings.json
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Determine base directory: if running as PyInstaller bundle, save data next to the .exe
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).parent
    DATA_DIR = EXE_DIR / "data"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "concilia_ai.db"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "cent_tolerance": 0.05,
    "supplier_similarity_threshold": 0.55,
    "enable_exact_match": True,
    "enable_cent_difference": True,
    "enable_partial_payments": True,
    "enable_grouped_payments": True,
    "enable_reversals": True,
    "enable_duplicate_detection": True,
    "balance_convention": "AUTO", # AUTO, MONTHLY_RESET, CUMULATIVE
    "ai_provider": "HEURISTIC", # HEURISTIC, OPENAI, GEMINI
    "ai_api_key": "",
    "ai_model": "gpt-4o-mini",
    "company_display_name": "CONCILIA AI Enterprise",
    "theme": "navy",
    "auto_open_browser": True
}

def load_settings() -> Dict[str, Any]:
    """Reads settings from disk without recursive calls."""
    if not SETTINGS_FILE.exists():
        # Write default file directly without calling save_settings
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return DEFAULT_SETTINGS.copy()
        
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:

    from app.operations_security_v5 import (
        SETTINGS_LOCK_V5,
        validate_settings_v5
    )

    import tempfile

    validated = validate_settings_v5(
        new_settings,
        DEFAULT_SETTINGS
    )

    with SETTINGS_LOCK_V5:

        current = DEFAULT_SETTINGS.copy()

        if SETTINGS_FILE.exists():

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as handle:

                stored = json.load(handle)

            if not isinstance(stored, dict):

                raise ValueError(
                    "Arquivo de configuracoes invalido."
                )

            current.update(stored)

        current.update(validated)

        current = validate_settings_v5(
            current,
            DEFAULT_SETTINGS
        )

        temporary = None

        try:

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(SETTINGS_FILE.parent),
                prefix=".settings_",
                suffix=".tmp",
                delete=False
            ) as handle:

                temporary = Path(handle.name)

                json.dump(
                    current,
                    handle,
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False
                )

                handle.flush()
                os.fsync(handle.fileno())

            os.replace(
                temporary,
                SETTINGS_FILE
            )

        finally:

            if temporary is not None:

                temporary.unlink(missing_ok=True)

        return current
