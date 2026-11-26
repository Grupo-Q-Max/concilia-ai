
# CONCILIA_V5_OPERATIONS_SECURITY_30A5B

import math
import zipfile
from pathlib import Path
from threading import RLock

from fastapi import HTTPException


MAX_UPLOAD_BYTES_V5 = 50 * 1024 * 1024

MAX_EXPANDED_BYTES_V5 = 256 * 1024 * 1024

MAX_ZIP_MEMBERS_V5 = 10000

ALLOWED_UPLOADS_V5 = {
    ".xls", ".xlsx", ".xlsm", ".xlsb",
    ".csv", ".html", ".htm", ".xml"
}

SETTINGS_LOCK_V5 = RLock()


def validate_settings_v5(payload, defaults):

    if not isinstance(payload, dict):
        raise ValueError("Configuracoes invalidas.")

    unknown = set(payload) - set(defaults)

    if unknown:
        raise ValueError("Parametro de configuracao desconhecido.")

    validated = {}

    for key, value in payload.items():

        default = defaults[key]

        if isinstance(default, bool):

            if type(value) is not bool:
                raise ValueError(
                    "Configuracao booleana invalida: " + key
                )

        elif key in (
            "cent_tolerance",
            "supplier_similarity_threshold"
        ):

            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
            ):
                raise ValueError(
                    "Configuracao numerica invalida: " + key
                )

            if key == "cent_tolerance":

                if not 0 <= value <= 1:
                    raise ValueError(
                        "Tolerancia deve estar entre 0 e 1 real."
                    )

            elif not 0 <= value <= 1:

                raise ValueError(
                    "Similaridade deve estar entre 0 e 1."
                )

        elif isinstance(default, str):

            if not isinstance(value, str):
                raise ValueError(
                    "Configuracao textual invalida: " + key
                )

            limit = 4096 if key == "ai_api_key" else 256

            if len(value) > limit:
                raise ValueError(
                    "Configuracao textual muito longa: " + key
                )

            if any(ord(char) < 32 for char in value):
                raise ValueError(
                    "Caracteres invalidos na configuracao."
                )

        if key == "balance_convention":

            if value not in (
                "AUTO", "MONTHLY_RESET", "CUMULATIVE"
            ):
                raise ValueError(
                    "Convencao contabil invalida."
                )

        if key == "ai_provider":

            if value not in (
                "HEURISTIC", "OPENAI", "GEMINI"
            ):
                raise ValueError(
                    "Provedor de IA invalido."
                )

        validated[key] = value

    return validated


def validate_uploaded_file_v5(
    upload,
    allowed=None,
    max_bytes=None
):

    allowed = (
        ALLOWED_UPLOADS_V5
        if allowed is None
        else set(allowed)
    )

    limit = (
        MAX_UPLOAD_BYTES_V5
        if max_bytes is None
        else max_bytes
    )

    filename = upload.filename or ""

    if (
        not filename
        or len(filename) > 255
        or "/" in filename
        or "\\" in filename
        or ":" in filename
        or any(ord(char) < 32 for char in filename)
    ):
        raise HTTPException(
            400, "Nome de arquivo invalido."
        )

    suffix = Path(filename).suffix.lower()

    if suffix not in allowed:

        raise HTTPException(
            400, "Formato de planilha nao suportado."
        )

    stream = upload.file

    try:

        stream.seek(0, 2)
        size = stream.tell()

        if size <= 0:

            raise HTTPException(
                400, "Arquivo vazio."
            )

        if size > limit:

            raise HTTPException(
                413, "Arquivo excede o limite de 50 MB."
            )

        stream.seek(0)
        header = stream.read(4096)
        stream.seek(0)

        if header.startswith(b"MZ") or header.startswith(b"\x7fELF"):

            raise HTTPException(
                400, "Arquivo executavel nao permitido."
            )

        if suffix in (".xlsx", ".xlsm", ".xlsb"):

            if not zipfile.is_zipfile(stream):

                raise HTTPException(
                    400, "Formato Excel invalido."
                )

            stream.seek(0)

            try:

                with zipfile.ZipFile(stream) as archive:

                    entries = archive.infolist()

                    if len(entries) > MAX_ZIP_MEMBERS_V5:

                        raise HTTPException(
                            400, "Planilha excessivamente complexa."
                        )

                    expanded = sum(
                        item.file_size for item in entries
                    )

                    if expanded > MAX_EXPANDED_BYTES_V5:

                        raise HTTPException(
                            413, "Planilha expandida muito grande."
                        )

                    names = set()

                    for item in entries:

                        name = item.filename

                        if (
                            name.startswith("/")
                            or "\\" in name
                            or ":" in name
                            or ".." in name.split("/")
                            or item.flag_bits & 1
                        ):

                            raise HTTPException(
                                400, "Estrutura de planilha invalida."
                            )

                        if name in names:

                            raise HTTPException(
                                400, "Entrada duplicada na planilha."
                            )

                        names.add(name)

                    workbook = (
                        "xl/workbook.bin"
                        if suffix == ".xlsb"
                        else "xl/workbook.xml"
                    )

                    if (
                        "[Content_Types].xml" not in names
                        or workbook not in names
                    ):

                        raise HTTPException(
                            400, "Arquivo Excel invalido."
                        )

            except zipfile.BadZipFile as exc:

                raise HTTPException(
                    400, "Planilha compactada invalida."
                ) from exc

        elif suffix == ".xls":

            ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

            # Accounting systems frequently export HTML/XML
            # tables with an XLS extension.

            text = (
                header.replace(b"\x00", b"")
                .decode("utf-8", errors="ignore")
                .lstrip("\ufeff \r\n\t")
                .lower()
            )

            if not (
                header.startswith(ole)
                or text.startswith("<")
            ):

                raise HTTPException(
                    400, "Formato XLS invalido."
                )

        elif suffix in (".html", ".htm", ".xml"):

            text = (
                header.replace(b"\x00", b"")
                .decode("utf-8", errors="ignore")
                .lstrip("\ufeff \r\n\t")
            )

            if not text.startswith("<"):

                raise HTTPException(
                    400, "Formato textual invalido."
                )

        return {
            "filename": filename,
            "suffix": suffix,
            "size": size
        }

    finally:

        stream.seek(0)
