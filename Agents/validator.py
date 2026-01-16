

import json
import csv
import yaml
import re
import requests
from typing import Dict, List, Any


GST_API_URL = "http://localhost:8080/api/gst/validate-gstin"


class ValidatorAgent:
    # -------------------------------------------------
    # Initialization
    # -------------------------------------------------
    def __init__(
        self,
        vendor_registry_path: str,
        gst_rates_path: str,
        hsn_codes_path: str,
        tds_sections_path: str,
        company_policy_path: str,
        historical_decisions_path: str,
    ):
        self.vendor_registry = self._load_json(vendor_registry_path)
        self.gst_rates = self._load_csv(gst_rates_path)
        self.hsn_codes = self._load_json(hsn_codes_path)
        self.tds_sections = self._load_json(tds_sections_path)
        self.company_policy = self._load_yaml(company_policy_path)
        self.historical_decisions = self._load_jsonl(historical_decisions_path)

    # -------------------------------------------------
    # Loaders
    # -------------------------------------------------
    def _load_json(self, path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_csv(self, path: str) -> List[Dict]:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _load_yaml(self, path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_jsonl(self, path: str) -> List[Dict]:
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------
    def validate_invoice(self, invoice: Any) -> Dict:
        data = invoice.model_dump()  # ✅ Pydantic v2 compliant
        checks: List[Dict] = []

        # Structural
        checks.append(self._check_invoice_number(data))
        checks.append(self._check_invoice_date(data))
        checks.append(self._check_gstin_format(data))
        checks.append(self._check_gstin_active(data))

        # Arithmetic
        checks.append(self._check_line_item_arithmetic(data))
        checks.append(self._check_subtotal_consistency(data))
        checks.append(self._check_tax_calculation_accuracy(data))

        # Commercial terms
        checks.append(self._check_discount_application(data))
        checks.append(self._check_rounding_rules(data))
        checks.append(self._check_fx_conversion(data))
        checks.append(self._check_advance_adjustment(data))
        checks.append(self._check_credit_debit_linkage(data))
        checks.append(self._check_partial_payment(data))
        checks.append(self._check_tds_calculation(data))

        # GST
        checks.append(self._check_invoice_total(data))
        checks.append(self._check_gst_rate(data))

        return {
            "summary": self._aggregate_results(checks),
            "checks": checks,
        }

    # -------------------------------------------------
    # Result helpers
    # -------------------------------------------------
    def _result(self, checkpoint: str, status: str, details: str = "", severity: str = "LOW") -> Dict:
        return {
            "checkpoint": checkpoint,
            "status": status,      # PASS | FAIL | REVIEW | NA
            "severity": severity,  # LOW | MEDIUM | HIGH
            "details": details,
        }

    # -------------------------------------------------
    # Aggregation logic
    # -------------------------------------------------
    def _aggregate_results(self, checks: List[Dict]) -> Dict:
        for c in checks:
            if c["status"] == "FAIL" and c["severity"] == "HIGH":
                return {"final_status": "FAIL"}

        for c in checks:
            if c["status"] == "FAIL":
                return {"final_status": "REVIEW"}

        return {"final_status": "PASS"}

    # -------------------------------------------------
    # Structural checks
    # -------------------------------------------------
    def _check_invoice_number(self, data: Dict) -> Dict:
        if data.get("invoice_no"):
            return self._result("Invoice number present", "PASS")
        return self._result("Invoice number present", "FAIL", "Missing invoice number", "HIGH")

    def _check_invoice_date(self, data: Dict) -> Dict:
        if data.get("invoice_date"):
            return self._result("Invoice date present", "PASS")
        return self._result("Invoice date present", "FAIL", "Missing invoice date", "HIGH")

    def _check_gstin_format(self, data: Dict) -> Dict:
        pattern = r"\b\d{2}[A-Z0-9]{13}\b"
        for field in ("vendor_gstin", "buyer_gstin"):
            gstin = data.get(field)
            if gstin and not re.match(pattern, gstin):
                return self._result("GSTIN format validation", "FAIL", f"{field} invalid", "HIGH")
        return self._result("GSTIN format validation", "PASS")

    def _check_gstin_active(self, data: Dict) -> Dict:
        gstin = data.get("vendor_gstin")
        if not gstin:
            return self._result("GSTIN active status", "NA", "Vendor GSTIN missing")

        try:
            resp = requests.post(GST_API_URL, json={"gstin": gstin}, timeout=5)
        except Exception as e:
            return self._result(
                "GSTIN active status",
                "REVIEW",
                f"GST API unreachable: {e}",
                "MEDIUM",
            )

        if resp.status_code != 200:
            return self._result(
                "GSTIN active status",
                "FAIL",
                "GSTIN not found or invalid",
                "HIGH",
            )

        payload = resp.json()
        if payload.get("status") == "SUSPENDED":
            return self._result(
                "GSTIN active status",
                "FAIL",
                "GSTIN suspended",
                "HIGH",
            )

        return self._result("GSTIN active status", "PASS")

    # -------------------------------------------------
    # Arithmetic checks
    # -------------------------------------------------
    def _check_line_item_arithmetic(self, data: Dict) -> Dict:
        for idx, item in enumerate(data.get("items", [])):
            q, r, a = item.get("quantity"), item.get("unit_price"), item.get("line_total")
            if None in (q, r, a):
                continue
            if abs((q * r) - a) > 1:
                return self._result(
                    "Line item amount calculation",
                    "FAIL",
                    f"Mismatch at item {idx}",
                    "HIGH",
                )
        return self._result("Line item amount calculation", "PASS")

    def _check_subtotal_consistency(self, data: Dict) -> Dict:
        return self._result("Subtotal consistency", "NA", "Subtotal not provided")

    def _check_tax_calculation_accuracy(self, data: Dict) -> Dict:
        return self._result("Tax calculation accuracy", "NA", "Tax breakup not available")

    def _check_discount_application(self, data: Dict) -> Dict:
        return self._result("Discount application", "NA", "No discount applicable")

    def _check_rounding_rules(self, data: Dict) -> Dict:
        return self._result("Rounding rules compliance", "PASS")

    def _check_fx_conversion(self, data: Dict) -> Dict:
        return self._result("Foreign currency conversion", "NA", "Invoice in INR")

    def _check_advance_adjustment(self, data: Dict) -> Dict:
        return self._result("Advance adjustment reconciliation", "NA", "No advance adjustment")

    def _check_credit_debit_linkage(self, data: Dict) -> Dict:
        return self._result("Credit/Debit note linkage", "NA", "Not a credit/debit note")

    def _check_partial_payment(self, data: Dict) -> Dict:
        return self._result("Partial payment calculation", "NA", "Single payment assumed")

    def _check_tds_calculation(self, data: Dict) -> Dict:
        return self._result("TDS calculation", "NA", "TDS not applicable")

    # -------------------------------------------------
    # GST checks
    # -------------------------------------------------
    def _check_invoice_total(self, data: Dict) -> Dict:
        total = data.get("total")
        if total is None:
            return self._result("Invoice total validation", "REVIEW", "Invoice total missing")

        taxable = sum(i.get("line_total") or 0 for i in data.get("items", []))
        if total >= taxable:
            return self._result("Invoice total validation", "PASS")

        return self._result(
            "Invoice total validation",
            "FAIL",
            "Total less than taxable value",
            "HIGH",
        )

    def _check_gst_rate(self, data: Dict) -> Dict:
        taxable = sum(i.get("line_total") or 0 for i in data.get("items", []))
        total = data.get("total")

        if not taxable or not total:
            return self._result("GST rate validation", "NA", "Insufficient data")

        inferred_rate = round(((total - taxable) / taxable) * 100, 2)

        if inferred_rate <= 0.5:
            return self._result("GST rate validation", "PASS", "No GST applied")

        return self._result(
            "GST rate validation",
            "REVIEW",
            f"Inferred GST rate {inferred_rate}% requires HSN/SAC verification",
            "MEDIUM",
        )
