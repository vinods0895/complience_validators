# tools/json_parser.py
import json

class JSONParser:
    def parse(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"raw_data": data}
        except Exception as e:
            return {"raw_data": {}, "error": str(e)}
