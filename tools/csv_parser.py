# tools/csv_parser.py
import csv

class CSVParser:
    def parse(self, file_path: str) -> dict:
        try:
            rows = []
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
            return {"raw_data": rows}
        except Exception as e:
            return {"raw_data": [], "error": str(e)}
