import re
import requests
from typing import Dict, List, Any, Optional

  
# API ENDPOINTS
  
GST_API_URL = "http://127.0.0.1:5000/api/gst/validate-gstin"
HSN_API_URL = "http://127.0.0.1:5000/api/gst/validate-hsn"
GST_RATE_API_URL = "http://127.0.0.1:5000/api/gst/rate-schedule"
POLICY_API_URL = "http://127.0.0.1:5000/api/policy/check"
VENDOR_API_URL = "http://127.0.0.1:5000/api/vendor/lookup"
TDS_API_URL = "http://127.0.0.1:5000/api/tds/sections"


class ValidatorAgent:
    """
    Deterministic GST + TDS Invoice Validator.
    - No LLMs
    - No auto-fixes
    - Fully auditable
    """

      
    # PUBLIC ENTRY
      

    def validate_invoice(self, invoice: Any) -> Dict[str, Any]:
        data: Dict[str, Any]

        if isinstance(invoice, dict):
            data = invoice
        else:
            data = invoice.model_dump()

        checks: List[Dict[str, Any]] = []

        # Structural
        checks.append(self._check_invoice_number(data))
        checks.append(self._check_invoice_date(data))

        # Vendor & GST
        checks.append(self._check_gstin_format(data))
        checks.append(self._check_gstin_active(data))
        checks.append(self._check_vendor_registry(data))

        # Arithmetic
        checks.append(self._check_negative_values(data))
        checks.append(self._check_line_item_arithmetic(data))
        checks.append(self._check_subtotal_consistency(data))
        checks.append(self._check_tax_calculation_accuracy(data))
        checks.append(self._check_invoice_total(data))

        # HSN / GST
        checks.append(self._check_hsn_code(data))
        checks.append(self._check_gst_rate(data))

        # TDS
        checks.append(self._check_tds_section(data))

        # Policy
        checks.append(self._check_company_policy(data))

        return {
            "summary": self._aggregate_results(checks),
            "checks": checks,
        }

      
    # CORE HELPERS
      

    def _result(
        self,
        checkpoint: str,
        status: str,
        details: str = "",
        severity: str = "LOW",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        result = {
            "checkpoint": checkpoint,
            "status": status,
            "severity": severity,
            "details": details,
        }

        if extra:
            result.update(extra)

        return result

    def _aggregate_results(self, checks: List[Dict[str, Any]]) -> Dict[str, str]:
        for check in checks:
            if check["status"] == "FAIL" and check["severity"] == "HIGH":
                return {"final_status": "FAIL"}

        for check in checks:
            if check["status"] == "FAIL":
                return {"final_status": "REVIEW"}

        return {"final_status": "PASS"}

      
    # STRUCTURAL
      

    def _check_invoice_number(self, data: Dict[str, Any]) -> Dict[str, Any]:
        exists = bool(data.get("invoice_number"))
        return self._result(
            "Invoice number present",
            "PASS" if exists else "FAIL",
            "Missing invoice number" if not exists else "",
            "HIGH" if not exists else "LOW",
        )

    def _check_invoice_date(self, data: Dict[str, Any]) -> Dict[str, Any]:
        exists = bool(data.get("invoice_date"))
        return self._result(
            "Invoice date present",
            "PASS" if exists else "FAIL",
            "Missing invoice date" if not exists else "",
            "HIGH" if not exists else "LOW",
        )

      
    # GSTIN & VENDOR
      

    def _check_gstin_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        gstin = (data.get("vendor") or {}).get("gstin")

        if gstin and not re.fullmatch(r"\d{2}[A-Z0-9]{13}", gstin):
            return self._result(
                "GSTIN format",
                "FAIL",
                "Invalid GSTIN format",
                "HIGH",
            )

        return self._result("GSTIN format", "PASS")

    def _check_gstin_active(self, data: Dict[str, Any]) -> Dict[str, Any]:
        gstin = (data.get("vendor") or {}).get("gstin")

        if not gstin:
            return self._result(
                "GSTIN active",
                "REVIEW",
                "GSTIN missing",
                "MEDIUM",
            )

        try:
            r = requests.post(GST_API_URL, json={"gstin": gstin}, timeout=5)
            payload = r.json()

            if payload.get("status") != "ACTIVE":
                return self._result(
                    "GSTIN active",
                    "FAIL",
                    payload.get("reason", "GSTIN inactive"),
                    "HIGH",
                )

            return self._result("GSTIN active", "PASS")

        except Exception as e:
            return self._result(
                "GSTIN active",
                "REVIEW",
                f"GST API error: {e}",
                "MEDIUM",
            )

    def _check_vendor_registry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        gstin = (data.get("vendor") or {}).get("gstin")

        if not gstin:
            return self._result(
                "Vendor registry",
                "REVIEW",
                "Vendor GSTIN missing",
                "MEDIUM",
            )

        try:
            r = requests.post(
                VENDOR_API_URL,
                json={"vendor_gstin": gstin},
                timeout=5,
            )

            if r.status_code != 200:
                return self._result(
                    "Vendor registry",
                    "FAIL",
                    "Vendor not found in registry",
                    "HIGH",
                )

            return self._result("Vendor registry", "PASS")

        except Exception as e:
            return self._result(
                "Vendor registry",
                "REVIEW",
                f"Vendor API error: {e}",
                "MEDIUM",
            )

      
    # TDS
      

    def _check_tds_section(self, data: Dict[str, Any]) -> Dict[str, Any]:
        tds_section = data.get("tds_section")

        if not tds_section:
            return self._result(
                "TDS section",
                "REVIEW",
                "TDS section not provided",
                "MEDIUM",
            )

        try:
            r = requests.post(
                TDS_API_URL,
                json={"tds_section": tds_section},
                timeout=5,
            )

            if r.status_code != 200:
                return self._result(
                    "TDS section",
                    "FAIL",
                    "Invalid TDS section",
                    "HIGH",
                )

            return self._result("TDS section", "PASS")

        except Exception as e:
            return self._result(
                "TDS section",
                "REVIEW",
                f"TDS API error: {e}",
                "MEDIUM",
            )

      
    # ARITHMETIC
      

    def _check_negative_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        fields = [
            "subtotal",
            "total_tax",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
        ]

        for field in fields:
            value = data.get(field)
            if value is not None and value < 0:
                return self._result(
                    "Negative values",
                    "FAIL",
                    f"{field} cannot be negative",
                    "HIGH",
                )

        return self._result("Negative values", "PASS")

    def _check_line_item_arithmetic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for idx, item in enumerate(data.get("line_items", [])):
            q = item.get("quantity")
            r = item.get("rate")
            a = item.get("amount")

            if None not in (q, r, a) and abs((q * r) - a) > 1:
                return self._result(
                    "Line item arithmetic",
                    "FAIL",
                    f"Mismatch at line {idx}",
                    "HIGH",
                )

        return self._result("Line item arithmetic", "PASS")

    def _check_subtotal_consistency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        subtotal = data.get("subtotal")

        if subtotal is None:
            return self._result(
                "Subtotal consistency",
                "REVIEW",
                "Subtotal missing",
                "MEDIUM",
            )

        calc = sum(i.get("amount") or 0 for i in data.get("line_items", []))

        if abs(calc - subtotal) > 1:
            return self._result(
                "Subtotal consistency",
                "FAIL",
                "Subtotal mismatch",
                "HIGH",
            )

        return self._result("Subtotal consistency", "PASS")

    def _check_tax_calculation_accuracy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        total_tax = data.get("total_tax")

        if total_tax is None:
            return self._result(
                "Tax calculation",
                "REVIEW",
                "Tax missing",
                "MEDIUM",
            )

        calc = sum(
            x or 0
            for x in (
                data.get("cgst_amount"),
                data.get("sgst_amount"),
                data.get("igst_amount"),
            )
        )

        if abs(calc - total_tax) > 1:
            return self._result(
                "Tax calculation",
                "FAIL",
                "Tax mismatch",
                "HIGH",
            )

        return self._result("Tax calculation", "PASS")

    def _check_invoice_total(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data.get("total_amount") is None:
            return self._result(
                "Invoice total",
                "REVIEW",
                "Total missing",
                "MEDIUM",
            )

        return self._result("Invoice total", "PASS")

      
    # HSN & GST RATE
      

    def _check_hsn_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for idx, item in enumerate(data.get("line_items", [])):
            hsn = re.sub(r"\D", "", str(item.get("hsn_sac") or ""))

            if not hsn:
                return self._result(
                    "HSN/SAC",
                    "FAIL",
                    f"Missing HSN at line {idx}",
                    "HIGH",
                )

            try:
                r = requests.post(
                    HSN_API_URL,
                    json={"hsn_sac": hsn},
                    timeout=5,
                )

                if r.status_code != 200:
                    return self._result(
                        "HSN/SAC",
                        "FAIL",
                        f"Invalid HSN {hsn}",
                        "HIGH",
                    )

            except Exception as e:
                return self._result(
                    "HSN/SAC",
                    "REVIEW",
                    f"HSN API error: {e}",
                    "MEDIUM",
                )

        return self._result("HSN/SAC", "PASS")

    def _check_gst_rate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for item in data.get("line_items", []):
            hsn = re.sub(r"\D", "", str(item.get("hsn_sac") or ""))

            if not hsn:
                continue

            try:
                r = requests.post(
                    GST_RATE_API_URL,
                    json={"hsn_sac": hsn},
                    timeout=5,
                )

                if r.status_code != 200:
                    return self._result(
                        "GST rate",
                        "FAIL",
                        f"GST rate not found for {hsn}",
                        "HIGH",
                    )

            except Exception as e:
                return self._result(
                    "GST rate",
                    "REVIEW",
                    f"GST rate API error: {e}",
                    "MEDIUM",
                )

        return self._result("GST rate", "PASS")

      
    # COMPANY POLICY
      

    def _check_company_policy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        total = data.get("total_amount")

        if total is None:
            return self._result(
                "Company policy",
                "REVIEW",
                "Total missing",
                "MEDIUM",
            )

        try:
            r = requests.post(
                POLICY_API_URL,
                json={"field": "invoice_amount", "value": total},
                timeout=5,
            )

            if not r.json().get("compliant"):
                return self._result(
                    "Company policy",
                    "FAIL",
                    "Policy violation",
                    "HIGH",
                )

        except Exception as e:
            return self._result(
                "Company policy",
                "REVIEW",
                f"Policy API error: {e}",
                "MEDIUM",
            )

        return self._result("Company policy", "PASS")
