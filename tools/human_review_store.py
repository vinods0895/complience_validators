import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import threading


class HumanReviewStore:
    """
    Persistent, audit-safe HUMAN_REVIEW store
    """

    _lock = threading.Lock()

    def __init__(self, path: str = "data/human_reviews.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write([])

    def _read(self) -> List[Dict]:
        try:
            if (not self.path.exists()) or self.path.stat().st_size == 0:
                return []
        except OSError:
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _write(self, records: List[Dict]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def create_review(
        self,
        invoice_id: str,
        invoice_number: str,
        confidence: float,
        validation: Dict[str, Any],
        resolution: Dict[str, Any],
        stateful: Optional[Dict[str, Any]],
    ) -> str:
        with self._lock:
            records = self._read()

            review_id = f"HR-{uuid.uuid4().hex[:8]}"

            records.append({
                "schema_version": "1.0",
                "review_id": review_id,
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "route": "HUMAN_REVIEW",
                "confidence": confidence,
                "validation_snapshot": validation,
                "resolution_snapshot": resolution,
                "stateful_snapshot": stateful,
                "status": "PENDING",
                "human_decision": None,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": None,
            })

            self._write(records)
            return review_id

    def submit_decision(
        self,
        review_id: str,
        decision: str,
        comments: Optional[str] = None,
    ) -> bool:
        with self._lock:
            records = self._read()
            for r in records:
                if r["review_id"] == review_id:
                    r["status"] = "COMPLETED"
                    r["human_decision"] = {
                        "decision": decision,
                        "comments": comments,
                        "decided_at": datetime.utcnow().isoformat() + "Z",
                    }
                    r["updated_at"] = datetime.utcnow().isoformat() + "Z"
                    self._write(records)
                    return True
            return False
    
    def list_reviews(
    self,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    ) -> List[Dict]:
        with self._lock:
            records = self._read()
            filtered_records = records
            if status:
                filtered_records = [r for r in filtered_records if r["status"] == status]
            if start_date:
                filtered_records = [r for r in filtered_records if r["created_at"] >= start_date]
            if end_date:
                filtered_records = [r for r in filtered_records if r["created_at"] <= end_date]
            return filtered_records[offset:offset+limit]
        if start_date:
            filtered_records = [
                r for r in filtered_records if r.get("created_at", "") >= start_date
            ]

        if end_date:
            filtered_records = [
                r for r in filtered_records if r.get("created_at", "") <= end_date
            ]

        return filtered_records[offset: offset + limit]
        
    def get_review(self, review_id: str) -> Optional[Dict]:
        with self._lock:
            records = self._read()
            for r in records:
                if r["review_id"] == review_id:
                    return r
            return None


