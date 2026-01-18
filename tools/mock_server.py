from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path
import json
import csv
import yaml

app = Flask(__name__)

# -------------------------------------------------------------------
# BASE PATHS
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MASTER_DATA_DIR = BASE_DIR / "data" / "master_data"

# -------------------------------------------------------------------
# LOAD VENDOR REGISTRY (GSTIN)
# -------------------------------------------------------------------
VENDOR_REGISTRY_PATH = MASTER_DATA_DIR / "vendor_registry.json"

with open(VENDOR_REGISTRY_PATH, "r", encoding="utf-8") as f:
    vendors = {
        v["gstin"]: v
        for v in json.load(f).get("vendors", [])
        if v.get("gstin")
    }

# -------------------------------------------------------------------
# LOAD HSN / SAC MASTER
# -------------------------------------------------------------------
HSN_CODES_PATH = MASTER_DATA_DIR / "hsn_sac_codes.json"

with open(HSN_CODES_PATH, "r", encoding="utf-8") as f:
    hsn_master = {
        item["code"]: item
        for item in json.load(f).get("codes", [])
    }

# -------------------------------------------------------------------
# LOAD GST RATES SCHEDULE
# -------------------------------------------------------------------
GST_RATE_PATH = MASTER_DATA_DIR / "gst_rates_schedule.csv"

gst_rates = {}

with open(GST_RATE_PATH, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        hsn = row.get("hsn_sac_code")
        if not hsn:
            continue

        cgst = float(row.get("rate_cgst") or 0)
        sgst = float(row.get("rate_sgst") or 0)
        igst = float(row.get("rate_igst") or 0)

        gst_rates[hsn.strip()] = {
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "total_rate": (cgst + sgst) if (cgst or sgst) else igst,
            "effective_from": row.get("effective_from"),
            "effective_to": row.get("effective_to"),
            "category": row.get("category"),
            "special_conditions": row.get("special_conditions"),
        }

print(f"✅ Loaded GST rates for {len(gst_rates)} HSN/SAC codes")

# -------------------------------------------------------------------
# LOAD COMPANY POLICY
# -------------------------------------------------------------------
POLICY_PATH = MASTER_DATA_DIR / "company_policy.yaml"

with open(POLICY_PATH, "r", encoding="utf-8") as f:
    company_policy = yaml.safe_load(f)

# -------------------------------------------------------------------
# GSTIN VALIDATION
# -------------------------------------------------------------------
@app.route("/api/gst/validate-gstin", methods=["POST"])
def validate_gstin():
    data = request.get_json(force=True)
    gstin = data.get("gstin", "").upper().strip()

    if len(gstin) != 15 or not gstin.isalnum():
        return jsonify({
            "valid": False,
            "error": "INVALID_FORMAT",
            "message": "GSTIN must be 15 characters alphanumeric"
        }), 400

    vendor = vendors.get(gstin)
    if not vendor:
        return jsonify({
            "valid": False,
            "error": "NOT_FOUND",
            "message": "GSTIN not found in vendor registry"
        }), 404

    return jsonify({
        "valid": True,
        "gstin": gstin,
        "legal_name": vendor.get("legal_name"),
        "trade_name": vendor.get("trade_name"),
        "status": vendor.get("status"),
        "state_code": vendor.get("state_code"),
        "state": vendor.get("state"),
        "taxpayer_type": vendor.get("gst_filing_status", "Regular")
    }), 200

# -------------------------------------------------------------------
# IRN VERIFICATION (MOCK)
# -------------------------------------------------------------------
@app.route("/api/gst/verify-irn", methods=["POST"])
def verify_irn():
    data = request.get_json(force=True)
    irn = data.get("irn", "").strip()

    if not irn:
        return jsonify({"error": "IRN_REQUIRED"}), 400

    return jsonify({
        "valid": True,
        "irn": irn,
        "status": "ACTIVE",
        "ack_date": datetime.utcnow().strftime("%Y-%m-%d")
    }), 200

# -------------------------------------------------------------------
# TDS 206AB CHECK (MOCK)
# -------------------------------------------------------------------
@app.route("/api/tds/check-206ab", methods=["POST"])
def check_206ab():
    data = request.get_json(force=True)
    pan = data.get("pan", "").upper().strip()

    if not pan:
        return jsonify({"error": "PAN_REQUIRED"}), 400

    return jsonify({
        "pan": pan,
        "is_206ab_applicable": False,
        "reason": "Filed returns in last 2 financial years"
    }), 200

# -------------------------------------------------------------------
# HSN / SAC VALIDATION
# -------------------------------------------------------------------
@app.route("/api/gst/validate-hsn", methods=["POST"])
def validate_hsn():
    data = request.get_json(force=True)
    hsn = data.get("hsn_sac", "").strip()

    if not hsn:
        return jsonify({"error": "HSN_REQUIRED"}), 400

    record = hsn_master.get(hsn)
    if not record:
        return jsonify({
            "valid": False,
            "error": "INVALID_HSN",
            "message": "HSN/SAC not found in master data"
        }), 404

    return jsonify({
        "valid": True,
        "hsn_sac": hsn,
        "description": record.get("description"),
        "type": record.get("type", "HSN")
    }), 200

# -------------------------------------------------------------------
# GST RATE LOOKUP
# -------------------------------------------------------------------
@app.route("/api/gst/rate-schedule", methods=["POST"])
def gst_rate_schedule():
    data = request.get_json(force=True)
    hsn = data.get("hsn_sac", "").strip()

    if not hsn:
        return jsonify({"error": "HSN_REQUIRED"}), 400

    record = gst_rates.get(hsn)
    if not record:
        return jsonify({
            "error": "RATE_NOT_FOUND",
            "message": "GST rate not available for given HSN/SAC"
        }), 404

    return jsonify({
        "hsn_sac": hsn,
        "cgst": record["cgst"],
        "sgst": record["sgst"],
        "igst": record["igst"],
        "total_rate": record["total_rate"],
        "effective_from": record["effective_from"],
        "effective_to": record["effective_to"],
        "category": record["category"],
        "special_conditions": record["special_conditions"],
    }), 200

# -------------------------------------------------------------------
# COMPANY POLICY CHECK
# -------------------------------------------------------------------
@app.route("/api/policy/check", methods=["POST"])
def check_policy():
    data = request.get_json(force=True)
    field = data.get("field")
    value = data.get("value")

    if field == "invoice_amount":
        max_amt = company_policy["invoice"]["max_amount"]
        return jsonify({
            "compliant": value <= max_amt,
            "rule": f"Invoice amount must be ≤ {max_amt}"
        }), 200

    if field == "vendor_state":
        blocked = company_policy["vendors"]["blocked_states"]
        return jsonify({
            "compliant": value not in blocked,
            "blocked_states": blocked
        }), 200

    return jsonify({
        "compliant": True,
        "message": "No applicable policy rule"
    }), 200

# -------------------------------------------------------------------
# HISTORICAL DECISION LOOKUP (MOCK)
# -------------------------------------------------------------------
@app.route("/api/decisions/lookup", methods=["POST"])
def lookup_decision():
    return jsonify({
        "decision": "Approved",
        "reason": "Matches prior vendor invoices"
    }), 200

# -------------------------------------------------------------------
# APP ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
