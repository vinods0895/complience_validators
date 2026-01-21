from typing import Dict, Any, Optional
from pydantic import BaseModel


class ComplianceState(BaseModel):
    # Input
    file_path: str
    financial_year: str

    # Core data
    invoice: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    stateful: Optional[Dict[str, Any]] = None
    resolution: Optional[Dict[str, Any]] = None

    # Routing
    route: Optional[str] = None
    confidence: Optional[float] = None
    human_review_id: Optional[str] = None

    # Output
    report: Optional[Dict[str, Any]] = None
