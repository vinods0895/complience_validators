import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading


class ResultStore:
    _lock = threading.Lock()

    def __init__(self, base_dir: str = "output"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.results_file = self.base_dir / "invoice_results.json"
        self.failures_file = self.base_dir / "failed_invoices.json"

        if not self.results_file.exists():
            self._write(self.results_file, [])

        if not self.failures_file.exists():
            self._write(self.failures_file, [])

    def save_result(self, result: Dict[str, Any]):
        with self._lock:
            data = self._read(self.results_file)
            data.append(result)
            self._write(self.results_file, data)

    def save_failure(self, invoice_id: str, error: str):
        with self._lock:
            failures = self._read(self.failures_file)
            failures.append({
                "invoice_id": invoice_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            self._write(self.failures_file, failures)

    def _read(self, path: Path) -> List[Dict]:
        try:
            if (not path.exists()) or path.stat().st_size == 0:
                return []
        except OSError:
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _write(self, path: Path, data: List[Dict]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Dict]:
        with self._lock:
            records = self._read(self.results_file)
            for r in records:
                if r.get("invoice_number") == invoice_number:
                    return r
            return None

    def filter_results(
        self,
        vendor_gstin: Optional[str] = None,
        route: Optional[str] = None,
        max_confidence: Optional[float] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict]:
        with self._lock:
            records = self._read(self.results_file)

            # Stable ordering (newest first)
            records = sorted(
                records,
                key=lambda r: r.get("generated_at", ""),
                reverse=True
            )

            filtered_records = records

            if vendor_gstin:
                filtered_records = [
                    r for r in filtered_records
                    if r.get("vendor_gstin") == vendor_gstin
                ]

            if route:
                filtered_records = [
                    r for r in filtered_records
                    if r.get("route") == route
                ]

            if max_confidence is not None:
                filtered_records = [
                    r for r in filtered_records
                    if r.get("confidence", 1.0) <= max_confidence
                ]

            return filtered_records[offset: offset + limit]
