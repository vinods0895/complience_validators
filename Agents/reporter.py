from typing import Dict, Any, Optional
from datetime import datetime


class ReporterAgent:
    """
    Deterministic compliance reporter.
    No LLM usage.
    """

    def run(
        self,
        data: Dict[str, Any],
        validation: Dict[str, Any],
        resolution: Dict[str, Any],
        stateful: Optional[Dict[str, Any]],
        route: str,
        confidence: float,
        human_review_id: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "invoice_id": data.get("invoice_id"),
            "invoice_number": data.get("invoice_number"),
            "route": route,
            "confidence": confidence,
            "human_review_id": human_review_id,
            "final_status": validation.get("summary", {}).get("final_status"),
            "validation": validation,
            "resolution": resolution,
            "stateful": stateful,
            "generated_at": datetime.utcnow().isoformat(),
        }
