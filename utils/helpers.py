# utils/helpers.py
import re
from datetime import datetime
from typing import Optional

def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Remove unwanted whitespace, normalize casing, and strip special characters.
    """
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize messy date formats into ISO YYYY-MM-DD.
    Handles dd/mm/yyyy, dd-mm-yyyy, mm/dd/yy, etc.
    """
    if not date_str:
        return None

    # Common separators
    for sep in ['/', '-', '.']:
        parts = date_str.split(sep)
        if len(parts) == 3:
            day, month, year = parts
            # Handle 2-digit year
            if len(year) == 2:
                year = "20" + year
            try:
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None  # fallback if parsing fails

def fuzzy_match(a: Optional[str], b: Optional[str]) -> bool:
    """
    Simple fuzzy string match for vendor names (can extend with Levenshtein).
    """
    if not a or not b:
        return False
    return a.lower().strip() in b.lower().strip() or b.lower().strip() in a.lower().strip()
