import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class ResultStore:
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
        data = self._read(self.results_file)
        data.append(result)
        self._write(self.results_file, data)

    def save_failure(self, invoice_id: str, error: str):
        failures = self._read(self.failures_file)
        failures.append({
            "invoice_id": invoice_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        self._write(self.failures_file, failures)

    def _read(self, path: Path) -> List[Dict]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path: Path, data: List[Dict]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
