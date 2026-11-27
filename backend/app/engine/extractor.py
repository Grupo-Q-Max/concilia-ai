"""
CONCILIA AI - Intelligent Transaction Extractor
Extracts Invoice Numbers (NF), Supplier Names, Categories, and Descriptions from Brazilian Accounting Histories.
"""
import re
from typing import Dict, Any, Optional

def clean_supplier_name(raw_name: str) -> str:
    """
    Standardizes company names for fuzzy/AI matching:
    Removes legal suffixes (LTDA, EIRELI, S/A, ME, EPP), extra spaces, punctuation.
    """
    if not raw_name:
        return ""
    
    text = raw_name.upper().strip()
    
    # Remove common transaction & supplier prefixes
    text = re.sub(
        r'^(?:PAGAMENTO|PAGTO|PGTO|PAGO|ENTRADA|PROVISAO|VALOR\s+A\s+SER\s+RECOLHIDO|AQUISICAO|CONFORME|VR|VLR|CRF|CSRF|IRRF|IR|ISS|ISSQN|INSS|PIS|COFINS|CSLL|PCC|FORNECEDOR|FAVORECIDO|CLIENTE)[:\s\-\d,%]+',
        '',
        text
    )
    text = re.sub(
        r'^(?:CRF|CSRF|IRRF|IR|ISS|ISSQN|INSS|PIS|COFINS|CSLL|PCC)\b[:\s\-\d,%]*',
        '',
        text
    )
    
    # Collapse dotted initials (e.g. "A. G. M." -> "AGM")
    text = re.sub(
        r'\b([A-Z])\.\s*([A-Z])\.(?:\s*([A-Z])\.?)?',
        lambda m: "".join(g for g in m.groups() if g),
        text
    )

    # Remove corporate designations and types
    patterns = [
        r'\bLTDA\b\.?',
        r'\bME\b\.?',
        r'\bEPP\b\.?',
        r'\bEIRELI\b\.?',
        r'\bS[\.\/]?A\b\.?',
        r'\bSOCIEDADE ANONIMA\b\.?',
        r'\bSOCIEDADE DE ADVOGADOS\b\.?',
        r'\bCOMERCIO DE\b\.?',
        r'\bCOMERCIO\b\.?',
        r'\bCOMERCIAL\b\.?',
        r'\bINDUSTRIA E COMERCIO\b\.?',
        r'\bINDUSTRIA\b\.?',
        r'\bIND\b\.?',
        r'\bCOM\b\.?',
        r'\bSERVICOS?\b\.?',
        r'\bSERV\b\.?',
        r'\bCONSULTORIA\b\.?',
        r'\bASSESSORIA\b\.?',
        r'\bIMOBILIARIA\b\.?',
        r'\bIMOB\b\.?',
        r'\bPARTICIPACOES\b\.?',
        r'\bMATERIAIS\b\.?',
        r'\bEQUIPAMENTOS\b\.?',
        r'\bTECNOLOGIA\b\.?',
        r'\bDO BRASIL\b\.?'
    ]
    
    # Clean accents and special characters
    replacements = {
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C'
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    
    for pat in patterns:
        text = re.sub(pat, ' ', text, flags=re.IGNORECASE)
    
    # Remove symbols and punctuation
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    # Collapse multiple whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_fallback_number(history: str) -> Optional[str]:
    """
    Ao nao encontrar NF explicita, extrai o numero de identificacao/nota
    presente no historico contabil, ignorando datas, CNPJ/CPF, valores, etc.
    Exemplo: 'VALOR A SER RECOLHIDO CRF Servilimp Conservacao e Limpeza Eireli 186' -> '186'
    """
    if not history:
        return None
    text = str(history).strip()
    if not text:
        return None

    # 1. Ignora datas (ex: 2026-06-08, 08/06/2026, 08/06/26, 06/2026)
    cleaned = re.sub(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', ' ', text)
    cleaned = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', ' ', cleaned)
    cleaned = re.sub(r'\b\d{1,2}/\d{4}\b', ' ', cleaned)

    # 2. Ignora CNPJ e CPF (formatados ou sequencias longas)
    cleaned = re.sub(r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b', ' ', cleaned)
    cleaned = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', ' ', cleaned)
    cleaned = re.sub(r'\b\d{11,14}\b', ' ', cleaned)

    # 3. Ignora valores monetarios (ex: R$ 490,40, 1.234,56, 490,40)
    cleaned = re.sub(r'R\$\s*[\d\.,]+', ' ', cleaned, flags=re.I)
    cleaned = re.sub(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', ' ', cleaned)
    cleaned = re.sub(r'\b\d+,\d{2}\b', ' ', cleaned)

    # 4. Ignora horarios (ex: 14:30, 08:00:00)
    cleaned = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', ' ', cleaned)

    # 5. Ignora indicadores de parcela como /1, /01
    cleaned = re.sub(r'/\s*\d+\b', ' ', cleaned)

    # 6. Procura marcadores contabeis seguidos de numero (CRF, NF, NOTA, DOC, TITULO, DUPLICATA, FATURA, RECIBO, PEDIDO, GUIA)
    m_pref = re.search(r'\b(?:CRF|NF-?E?|N\.?F\.?|NOTA\s+FISCAL|DOC(?:UMENTO)?|TIT(?:ULO)?|DUPLICATA|FATURA|REC(?:IBO)?|PED(?:IDO)?|GUIA)\b.*?\b(\d{1,10})\b', cleaned, re.I)
    if m_pref:
        return str(int(m_pref.group(1)))

    # 6.1 Procura numero logo apos sufixos empresariais (LTDA, EIRELI, EPP, ME, S/A, SA, UNIPESSOAL)
    m_corp = re.search(r'\b(?:LTDA|EIRELI|EPP|ME|S/?A|SA|SOCIEDADE\s+ANONIMA|UNIPESSOAL)\b.*?\b(\d{1,10})\s*$', cleaned, re.I)
    if m_corp:
        return str(int(m_corp.group(1)))

    # 7. Procura numero no final do historico (padrao muito comum em sistemas contabeis)
    m_end = re.search(r'\b(\d{1,10})\s*$', cleaned)
    if m_end:
        return str(int(m_end.group(1)))

    # 8. Qualquer numero isolado restante no historico
    numbers = re.findall(r'\b(\d{1,10})\b', cleaned)
    if numbers:
        return str(int(numbers[-1]))

    return None

def extract_transaction_info(history: str, trans_type: str) -> Dict[str, Any]:
    """
    Intelligently extracts structured information from an accounting history string.
    Handles varied layouts:
    - "ENTRADA CONFORME NOTA FISCAL FORNECEDOR 12345"
    - "PAGAMENTO Categoria NF:12345 Fornecedor Itens: ..."
    - "PAGTO NF 1234 FORNECEDOR"
    - "DOC 1234 / NF 5678"
    """
    hist = str(history).strip() if history else ""
    hist_upper = hist.upper()
    
    nf: Optional[str] = None
    supplier: Optional[str] = None
    category: Optional[str] = None
    details: Optional[str] = None
    
    # Check if Entrada (Provision / Credit)
    if "ENTRADA" in hist_upper:
        # Pattern 1: ENTRADA CONFORME NOTA FISCAL <SUPPLIER> <NF>
        m_prov = re.search(r'(?i)ENTRADA\s+CONFORME\s+(?:NOTA\s+FISCAL|NF|DUPLICATA)?\s*(.*?)(?:\s+N[º°\.]?\s*|\s+)?(\d+[\w\-\./]*)\s*$', hist)
        if m_prov:
            supplier = m_prov.group(1).strip()
            nf = m_prov.group(2).strip()
        else:
            # Fallback search for any trailing digits
            clean_hist = re.sub(r'(?i)ENTRADA\s+CONFORME\s+(?:NOTA\s+FISCAL|NF)\s*', '', hist).strip()
            m_tail = re.search(r'^(.*?)\s+(\d+[\w\-\./]*)\s*$', clean_hist)
            if m_tail:
                supplier = m_tail.group(1).strip()
                nf = m_tail.group(2).strip()
            else:
                supplier = clean_hist
        category = "PROVISAO_NOTA_FISCAL"

    # Check if Valor a ser recolhido (Tax / Retention Provision - IRRF, CRF, CSRF, ISS, INSS, etc.)
    elif "VALOR A SER RECOLHIDO" in hist_upper:
        clean_hist = re.sub(
            r'(?i)^VALOR\s+A\s+SER\s+RECOLHIDO\s*(?:(?:IRRF|CRF|CSRF|ISSQN|ISS|INSS|PIS|COFINS|CSLL|PCC|IR)\b[:\s\-]*)?',
            '',
            hist
        ).strip()
        # Case A: <NF> <SUPPLIER> (e.g. "28102 GONÇALVES BASSE E BENETTI ADVOGADOS ASSOCIADOS")
        m_lead_nf = re.match(r'^(?:(?:NF|NOTA\s+FISCAL|DOC)[:\.\s]*)?(\d{1,10})\s+(.+)$', clean_hist, flags=re.I)
        # Case B: <SUPPLIER> <NF> (e.g. "Servilimp Conservacao e Limpeza Eireli 186")
        m_tail_nf = re.match(r'^(.+?)\s+(?:(?:NF|NOTA\s+FISCAL|DOC)[:\.\s]*)?(\d{1,10})\s*$', clean_hist, flags=re.I)
        if m_lead_nf:
            nf = m_lead_nf.group(1).strip()
            supplier = m_lead_nf.group(2).strip()
        elif m_tail_nf:
            supplier = m_tail_nf.group(1).strip()
            nf = m_tail_nf.group(2).strip()
        else:
            supplier = clean_hist
        category = "PROVISAO_IMPOSTO_RETIDO"

    # Check if Pagamento (Payment / Debit)
    elif "PAGAMENTO" in hist_upper or "PAGTO" in hist_upper:
        # Check category before NF: e.g. "PAGAMENTO Suprimentos e Materiais para escritório  NF:3048"
        m_cat = re.search(r'(?i)PAG(?:AMENTO|TO)\s+(.*?)\s+NF[:\s]', hist)
        if m_cat:
            category = m_cat.group(1).strip()
        else:
            category = "PAGAMENTO_FORNECEDOR"
            
        # Match NF
        m_nf = re.search(r'(?i)(?:NF|Nº|NOTA\s+FISCAL|DOC)[:\.\s]+(\d+[\w\-\./]*)', hist)
        if m_nf:
            nf = m_nf.group(1).strip()
            post_nf = hist[m_nf.end():].strip()
            
            # Extract details after "Itens:" or "Ref:"
            m_itens = re.search(r'(?i)\s+(Itens|Ref|Referente|Hist)[:\s]', post_nf)
            if m_itens:
                supplier = post_nf[:m_itens.start()].strip()
                details = post_nf[m_itens.start():].strip()
            else:
                supplier = post_nf
        else:
            supplier = hist
    else:
        # General pattern matching: look for any NF: xxx
        m_nf = re.search(r'(?i)(?:NF|NOTA\s+FISCAL|FATURA|DUPLICATA|DOC)[:\.\s]+(\d+[\w\-\./]*)', hist)
        if m_nf:
            nf = m_nf.group(1).strip()
        supplier = hist
        category = "OUTROS"

    # Ao nao encontrar NF, pegar numero do historico e utilizar como nota
    if not nf:
        fallback_nf = extract_fallback_number(hist)
        if fallback_nf:
            nf = fallback_nf
            if supplier:
                supplier = re.sub(rf'\s*\b{re.escape(fallback_nf)}\b\s*$', '', supplier).strip()

    # Clean extracted NF (remove trailing punctuation or spaces)
    if nf:
        nf = re.sub(r'[^\w\-\./]', '', nf)

    # Clean supplier
    cleaned = clean_supplier_name(supplier or "")

    return {
        "extracted_nf": nf,
        "extracted_supplier": supplier,
        "cleaned_supplier": cleaned,
        "category": category,
        "details": details
    }
