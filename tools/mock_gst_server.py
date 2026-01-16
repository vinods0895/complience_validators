from flask import Flask, request, jsonify
from datetime import datetime
import json
from pathlib import Path

app = Flask(__name__)

# Load mock data
BASE_DIR = Path(__file__).resolve().parent.parent  # D:\complience_validators
VENDOR_REGISTRY_PATH = BASE_DIR / "data" / "master_data" / "vendor_registry.json"

with open(VENDOR_REGISTRY_PATH, "r") as f:
    vendors = {
        v["gstin"]: v
        for v in json.load(f)["vendors"]
        if v.get("gstin")
    }
@app.route('/api/gst/validate-gstin', methods=['POST'])
def validate_gstin():
    data = request.json
    gstin = data.get('gstin', '').upper().strip()
    
    # Basic format validation
    if len(gstin) != 15 or not gstin.isalnum():
        return jsonify({
            'valid': False,
            'error': 'INVALID_FORMAT',
            'message': 'GSTIN must be 15 characters alphanumeric'
        }), 400
    
    # Look up in mock data
    vendor = vendors.get(gstin)
    if not vendor:
        return jsonify({
            'valid': False,
            'error': 'NOT_FOUND',
            'message': 'GSTIN not registered in GST system'
        }), 404
    
    response = {
        'valid': True,
        'gstin': gstin,
        'legal_name': vendor['legal_name'],
        'trade_name': vendor.get('trade_name'),
        'status': vendor['status'],
        'state_code': vendor['state_code'],
        'state': vendor['state'],
        'taxpayer_type': vendor.get('gst_filing_status', 'Regular')
    }
    
    if vendor['status'] == 'SUSPENDED':
        response['suspension_date'] = vendor.get('suspension_date')
        response['suspension_reason'] = vendor.get('suspension_reason')
    
    return jsonify(response)

# Add other endpoints...

if __name__ == '__main__':
    app.run(port=8080, debug=True)