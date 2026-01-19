from flask import Flask, request, jsonify
from pathlib import Path
import json
import yaml
import csv
import re

app = Flask(__name__)

# -------------------------------------------------
# PATHS
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MASTER_DATA_DIR = BASE_DIR / "data" / "master_data"

# -------------------------------------------------
# SAFE LOADERS (NO CRASH GUARANTEE)
# -------------------------------------------------
def safe_load_json(path):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed loading {path}: {e}")
    return {}

def safe_load_yaml(path):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    except Exception as e:
        print(f"[WARN] Failed loading {path}: {e}")
    return {}

def safe_load_gst_rates_csv(path):
    rates = {}
    try:
        if not path.exists():
            return rates

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hsn = row.get("hsn_sac") or row.get("hsn")
                if not hsn:
                    continue

                if row.get("total_rate"):
                    rate = float(row["total_rate"])
                else:
                    cgst = float(row.get("cgst", 0) or 0)
                    sgst = float(row.get("sgst", 0) or 0)
                    igst = float(row.get("igst", 0) or 0)
                    rate = cgst + sgst + igst

                rates[hsn] = {"total_rate": round(rate, 2)}
    except Exception as e:
        print(f"[WARN] Failed loading GST rate CSV: {e}")

    return rates

# -------------------------------------------------
# LOAD MASTER DATA
# -------------------------------------------------
hsn_raw = safe_load_json(MASTER_DATA_DIR / "hsn_sac_codes.json")
HSN_MASTER = hsn_raw.get("hsn_codes", {})

GST_RATE_MASTER = safe_load_gst_rates_csv(
    MASTER_DATA_DIR / "gst_rates_schedule.csv"
)

company_policy = safe_load_yaml(
    MASTER_DATA_DIR / "company_policy.yaml"
)

GSTIN_REGEX = r"\b\d{2}[A-Z0-9]{13}\b"

# -------------------------------------------------
# GSTIN REGISTRY (NEVER FAILS HARD)
# -------------------------------------------------
@app.route("/api/gst/validate-gstin", methods=["POST"])
def validate_gstin():
    data = request.json or {}
    gstin = data.get("gstin")

    if not gstin:
        return jsonify({"status": "INVALID", "reason": "GSTIN missing"}), 200

    if not re.match(GSTIN_REGEX, gstin):
        return jsonify({"status": "INVALID", "reason": "Invalid GSTIN format"}), 200

    return jsonify({
        "gstin": gstin,
        "status": "ACTIVE",
        "trade_name": "Mock Vendor Pvt Ltd"
    }), 200

# -------------------------------------------------
# HSN / SAC MASTER LOOKUP
# -------------------------------------------------
@app.route("/api/gst/validate-hsn", methods=["POST"])
def validate_hsn():
    data = request.json or {}
    hsn = data.get("hsn_sac")

    if not hsn:
        return jsonify({"error": "HSN missing"}), 200

    master = HSN_MASTER.get(hsn)
    if not master:
        # IMPORTANT: not found ≠ invalid invoice
        return jsonify({"error": "HSN not found in master"}), 404

    return jsonify(master), 200

# -------------------------------------------------
# GST RATE LOOKUP (CSV DRIVEN)
# -------------------------------------------------
@app.route("/api/gst/rate-schedule", methods=["POST"])
def gst_rate_schedule():
    data = request.json or {}
    hsn = data.get("hsn_sac")

    if not hsn:
        return jsonify({"error": "HSN missing"}), 200

    rate = GST_RATE_MASTER.get(hsn)
    if not rate:
        return jsonify({"error": "GST rate not found"}), 404

    return jsonify(rate), 200

# -------------------------------------------------
# COMPANY POLICY (APPROVAL MATRIX ONLY)
# -------------------------------------------------
@app.route("/api/policy/check", methods=["POST"])
def check_policy():
    try:
        data = request.json or {}
        field = data.get("field")
        value = data.get("value")

        if field != "invoice_amount" or value is None:
            return jsonify({"compliant": True}), 200

        levels = (
            company_policy
            .get("approval_matrix", {})
            .get("levels", [])
        )

        for level in levels:
            max_amt = level.get("max_amount")
            if max_amt is None or value <= max_amt:
                return jsonify({
                    "compliant": True,
                    "approval_level": level.get("level"),
                    "approval_name": level.get("name"),
                }), 200

        return jsonify({"compliant": True}), 200

    except Exception as e:
        # NEVER fail validator because of policy infra
        return jsonify({
            "compliant": True,
            "warning": f"Policy evaluation skipped: {e}"
        }), 200

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "UP",
        "hsn_loaded": len(HSN_MASTER),
        "gst_rates_loaded": len(GST_RATE_MASTER),
        "policy_loaded": bool(company_policy),
    }), 200

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    print("🚀 Mock Compliance Server Starting...")
    print(f"📁 Master data path: {MASTER_DATA_DIR}")
    app.run(host="127.0.0.1", port=5000, debug=True)
