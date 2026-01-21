import json
import uuid
from datetime import datetime
from typing import Dict, Any, List


class HumanReviewStore:
    """
    Persistent store for HUMAN_REVIEW cases.
    """

    def __init__(self, path: str = "data/human_reviews.json"):
        self.path = path

    def _load(self) -> List[Dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, records: List[Dict]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def create_review(
        self,
        invoice_id: str,
        invoice_number: str,
        confidence: float,
        validation: Dict[str, Any],
        resolution: Dict[str, Any],
        stateful: Dict[str, Any] | None,
    ) -> str:

        records = self._load()
        review_id = f"HR-{uuid.uuid4().hex[:8]}"

        records.append({
            "review_id": review_id,
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "route": "HUMAN_REVIEW",
            "confidence": confidence,
            "validation_snapshot": validation,
            "resolution_snapshot": resolution,
            "stateful_snapshot": stateful,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "human_decision": None,
        })

        self._save(records)
        return review_id
