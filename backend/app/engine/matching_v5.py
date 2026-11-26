import re
import unicodedata
from decimal import Decimal

def normalize_nf(value):
    text = str(value or "").upper().strip()
    text = re.sub(r"\s+", "", text)

    if text in ("", "SN", "S/N", "NONE", "NAN", "0", "-"):
        return ""

    text = re.sub(r"^(?:NF|NFE|NF-E)[:.]?", "", text)
    text = re.sub(r"-\d+/\d+$", "", text)

    if text.isdigit():
        return str(int(text))

    return text

def normalize_supplier(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()

    text = re.sub(r"\b(?:LTDA|EIRELI|ME|EPP)\b", " ", text)
    text = re.sub(r"[^A-Z0-9 ]", " ", text)

    return " ".join(text.split())

def classify_match(nf1, nf2, supplier1, supplier2, value1, value2):
    a = normalize_nf(nf1)
    b = normalize_nf(nf2)

    s1 = normalize_supplier(supplier1)
    s2 = normalize_supplier(supplier2)

    if Decimal(str(value1)) != Decimal(str(value2)):
        return "VALOR_DIFERENTE"

    if a and b:
        if a == b:
            return "AUTOMATICO"
        return "APROVACAO"

    if s1 and s2 and s1 == s2:
        return "AUTOMATICO"

    return "SEM_CONFIRMACAO"

if __name__ == "__main__":
    assert normalize_nf("1176-1/1") == "1176"
    assert normalize_nf("1176 - 1/1") == "1176"
    assert normalize_nf("001176") == "1176"
    assert normalize_nf("S/N") == ""

    assert classify_match(
        "1176", "1176-1/1",
        "EMPRESA A", "EMPRESA B",
        "28.64", "28.64"
    ) == "AUTOMATICO"

    assert classify_match(
        "S/N", "1176-1/1",
        "LL COMERCIO DE PAPEIS ESPECIAIS",
        "LL COMERCIO DE PAPEIS ESPECIAIS LTDA",
        "28.64", "28.64"
    ) == "AUTOMATICO"

    assert classify_match(
        "1176", "1177",
        "EMPRESA A", "EMPRESA A",
        "28.64", "28.64"
    ) == "APROVACAO"

    print("TODOS OS TESTES APROVADOS!")
