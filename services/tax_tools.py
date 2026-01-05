"""Tax tools for RAG-powered compliance agent."""
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any

def parse_statement_row(row: str) -> Dict[str, Any]:
    """Strictly parse date and amount from a bank statement row."""
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", row)
    amount_match = re.search(r"([+-]?\d+[\.,]?\d*)", row)
    return {
        "date": date_match.group(1) if date_match else None,
        "amount": float(amount_match.group(1).replace(",", "")) if amount_match else None,
        "raw": row
    }

def fuzzy_match_receipt(statement_row: Dict[str, Any], receipts: List[Dict[str, Any]], day_buffer: int = 3) -> Any:
    """Fuzzy match a statement row to receipts within ±3 days and similar amount."""
    from datetime import datetime, timedelta
    stmt_date = statement_row.get("date")
    stmt_amount = statement_row.get("amount")
    if not stmt_date or stmt_amount is None:
        return None
    stmt_date_obj = datetime.strptime(stmt_date, "%Y-%m-%d")
    best_match = None
    best_score = 0.0
    for r in receipts:
        r_date = r.get("date")
        r_amount = r.get("amount")
        if not r_date or r_amount is None:
            continue
        r_date_obj = datetime.strptime(r_date, "%Y-%m-%d")
        if abs((stmt_date_obj - r_date_obj).days) > day_buffer:
            continue
        amt_ratio = min(stmt_amount, r_amount) / max(stmt_amount, r_amount) if max(stmt_amount, r_amount) > 0 else 0
        meta_score = SequenceMatcher(None, statement_row["raw"], r.get("raw", "")).ratio()
        score = 0.7 * amt_ratio + 0.3 * meta_score
        if score > best_score:
            best_score = score
            best_match = r
    return best_match if best_score > 0.7 else None

def reconcile_transaction(statement_row: Dict[str, Any], receipts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reconcile a statement row with receipts, flagging uncategorized if no match."""
    match = fuzzy_match_receipt(statement_row, receipts)
    if match:
        return {"status": "MATCHED", "statement": statement_row, "receipt": match}
    else:
        return {"status": "UNCATEGORIZED", "statement": statement_row, "receipt": None}