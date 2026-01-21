# graph/state.py

from typing import Optional, Dict, Any
from pydantic import BaseModel


class ComplianceState(BaseModel):
    # -------- INPUTS --------
    file_path: Optional[str] = None
    invoice: Optional[Dict[str, Any]] = None
    financial_year: Optional[str] = None

    # -------- VALIDATION --------
    validation: Optional[Dict[str, Any]] = None

    # -------- STATEFUL --------
    stateful: Optional[Dict[str, Any]] = None

    # -------- RESOLUTION --------
    resolution: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    route: Optional[str] = None

    # -------- HUMAN REVIEW --------
    human_review_id: Optional[str] = None

    # -------- FINAL REPORT --------
    report: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"
