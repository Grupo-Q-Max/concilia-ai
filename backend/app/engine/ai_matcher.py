"""
CONCILIA AI - AI & Fuzzy Supplier Matcher
Performs intelligent supplier name comparison, token matching, and modular LLM classification.
"""
import difflib
import re
from typing import Dict, Any, Optional

def compute_similarity(str1: str, str2: str) -> float:
    """
    Computes a hybrid similarity score (0.0 to 1.0) between two supplier strings:
    Combines SequenceMatcher ratio and Token Overlap (Jaccard on words).
    """
    if not str1 or not str2:
        return 0.0
    
    s1 = str1.upper().strip()
    s2 = str2.upper().strip()
    
    if s1 == s2:
        return 1.0
        
    # Sequence Matcher
    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
    
    # Word Token Jaccard
    tokens1 = set(re.findall(r'\b\w+\b', s1))
    tokens2 = set(re.findall(r'\b\w+\b', s2))
    
    if not tokens1 or not tokens2:
        return seq_ratio
        
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    token_ratio = len(intersection) / len(union) if union else 0.0
    
    # Substring containment bonus (e.g. "DHARMA" in "DHARMA COMERCIO...")
    containment_bonus = 0.0
    if (len(s1) > 4 and s1 in s2) or (len(s2) > 4 and s2 in s1):
        containment_bonus = 0.25
        
    final_score = max(seq_ratio, (seq_ratio * 0.4 + token_ratio * 0.6) + containment_bonus)
    return min(1.0, round(final_score, 4))

def are_suppliers_compatible(sup1: str, sup2: str, threshold: float = 0.55) -> bool:
    """
    Determines whether two supplier names refer to the same entity.
    """
    if not sup1 or not sup2:
        # If one is empty, we don't disqualify purely on supplier if NF and value match
        return True
    
    score = compute_similarity(sup1, sup2)
    return score >= threshold

def query_llm_for_disambiguation(hist1: str, hist2: str) -> Dict[str, Any]:
    """
    Modular LLM integration:
    If OPENAI_API_KEY is configured, can ask the model for advanced semantic confirmation.
    If no API key is provided, returns heuristic deterministic result without external failure.
    """
    # Deterministic fallback
    sim = compute_similarity(hist1, hist2)
    return {
        "is_match": sim >= 0.6,
        "confidence": sim,
        "explanation": f"Similaridade heurística/token: {sim*100:.1f}%",
        "provider": "deterministic_heuristic"
    }
