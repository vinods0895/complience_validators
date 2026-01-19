import re
import requests
from typing import Dict, List, Any

# -------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------
GST_API_URL = "http://127.0.0.1:5000/api/gst/validate-gstin"
HSN_API_URL = "http://127.0.0.1:5000/api/gst/validate-hsn"
GST_RATE_API_URL = "http://127.0.0.1:5000/api/gst/rate-schedule"
POLICY_API_URL = "http://127.0.0.1:5000/api/policy/check"


class ValidatorAgent:
    """
    Deterministic GST Invoice Validator.
    LLMs are NOT used here.
    """

    # -------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------
    def validate_invoice(self, invoice: Any) -> Dict:
        data = invoice.model_dump()
        checks: List[Dict] = []

        # Structural
        checks.append(self._check_invoice_number(data))
        checks.append(self._check_invoice_date(data))
        checks.append(self._check_gstin_format(data))
        checks.append(self._check_gstin_active(data))

        # ❗ FAIL FAST — NEGATIVE VALUES
        checks.append(self._check_negative_values(data))

        # Arithmetic
        checks.append(self._check_line_item_arithmetic(data))
        checks.append(self._check_subtotal_consistency(data))
        checks.append(self._check_tax_calculation_accuracy(data))
        checks.append(self._check_invoice_total(data))

        # Compliance
        checks.append(self._check_hsn_code(data))
        checks.append(self._check_gst_rate(data))
        checks.append(self._check_company_policy(data))

        return {
            "summary": self._aggregate_results(checks),
            "checks": checks,
        }

    # -------------------------------------------------------------------
    # CORE HELPERS
    # -------------------------------------------------------------------
    def _result(
        self,
        checkpoint: str,
        status: str,
        details: str = "",
        severity: str = "LOW",
        extra: Dict | None = None,
    ) -> Dict:
        result = {
            "checkpoint": checkpoint,
            "status": status,
            "severity": severity,
            "details": details,
        }
        if extra:
            result.update(extra)
        return result

    def _aggregate_results(self, checks: List[Dict]) -> Dict:
        for c in checks:
            if c["status"] == "FAIL" and c["severity"] == "HIGH":
                return {"final_status": "FAIL"}
        for c in checks:
            if c["status"] == "FAIL":
                return {"final_status": "REVIEW"}
        return {"final_status": "PASS"}

    def _normalize_hsn(self, raw: Any) -> str:
        return re.sub(r"\D", "", str(raw or "")).strip()

    # -------------------------------------------------------------------
    # STRUCTURAL CHECKS
    # -------------------------------------------------------------------
    def _check_invoice_number(self, data: Dict) -> Dict:
        return (
            self._result("Invoice number present", "PASS")
            if data.get("invoice_number")
            else self._result(
                "Invoice number present",
                "FAIL",
                "Missing invoice number",
                "HIGH",
            )
        )

    def _check_invoice_date(self, data: Dict) -> Dict:
        return (
            self._result("Invoice date present", "PASS")
            if data.get("invoice_date")
            else self._result(
                "Invoice date present",
                "FAIL",
                "Missing invoice date",
                "HIGH",
            )
        )

    def _check_gstin_format(self, data: Dict) -> Dict:
        gstin = (data.get("vendor") or {}).get("gstin")
        if gstin and not re.fullmatch(r"\d{2}[A-Z0-9]{13}", gstin):
            return self._result(
                "GSTIN format validation",
                "FAIL",
                "Invalid GSTIN format",
                "HIGH",
            )
        return self._result("GSTIN format validation", "PASS")

    # -------------------------------------------------------------------
    # GSTIN ACTIVE STATUS (WITH METADATA)
    # -------------------------------------------------------------------
    def _check_gstin_active(self, data: Dict) -> Dict:
        gstin = (data.get("vendor") or {}).get("gstin")
        if not gstin:
            return self._result(
                "GSTIN active status",
                "NA",
                "Vendor GSTIN missing",
                extra={
                    "gstin_status": "UNKNOWN",
                    "suspended_from": None,
                    "gstin_reason": None,
                },
            )

        try:
            resp = requests.post(
                GST_API_URL, json={"gstin": gstin}, timeout=5
            )
            payload = resp.json()

            status = payload.get("status", "UNKNOWN")
            suspended_from = payload.get("suspended_from")
            reason = payload.get("reason")

            if status == "SUSPENDED":
                return self._result(
                    "GSTIN active status",
                    "FAIL",
                    f"SUSPENDED since {suspended_from or 'unknown'}",
                    "HIGH",
                    extra={
                        "gstin_status": status,
                        "suspended_from": suspended_from,
                        "gstin_reason": reason,
                    },
                )

            return self._result(
                "GSTIN active status",
                "PASS",
                "GSTIN active",
                extra={
                    "gstin_status": status,
                    "suspended_from": None,
                    "gstin_reason": None,
                },
            )

        except Exception as e:
            return self._result(
                "GSTIN active status",
                "REVIEW",
                f"GST service unreachable: {e}",
                "MEDIUM",
                extra={
                    "gstin_status": "UNKNOWN",
                    "suspended_from": None,
                    "gstin_reason": None,
                },
            )

    # -------------------------------------------------------------------
    # ❗ NEGATIVE VALUE VALIDATION
    # -------------------------------------------------------------------
    def _check_negative_values(self, data: Dict) -> Dict:
        fields = [
            "subtotal",
            "total_tax",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
        ]

        for field in fields:
            val = data.get(field)
            if val is not None and val < 0:
                return self._result(
                    "Negative value validation",
                    "FAIL",
                    f"{field} cannot be negative",
                    "HIGH",
                )

        for idx, item in enumerate(data.get("line_items", [])):
            for k in ("quantity", "rate", "amount"):
                v = item.get(k)
                if v is not None and v < 0:
                    return self._result(
                        "Negative value validation",
                        "FAIL",
                        f"Negative {k} at line {idx}",
                        "HIGH",
                    )

        return self._result("Negative value validation", "PASS")

    # -------------------------------------------------------------------
    # ARITHMETIC
    # -------------------------------------------------------------------
    def _check_line_item_arithmetic(self, data: Dict) -> Dict:
        for idx, item in enumerate(data.get("line_items", [])):
            q, r, a = item.get("quantity"), item.get("rate"), item.get("amount")
            if None not in (q, r, a) and abs((q * r) - a) > 1:
                return self._result(
                    "Line item calculation",
                    "FAIL",
                    f"Mismatch at item {idx}",
                    "HIGH",
                )
        return self._result("Line item calculation", "PASS")

    def _check_subtotal_consistency(self, data: Dict) -> Dict:
        subtotal = data.get("subtotal")
        if subtotal is None:
            return self._result(
                "Subtotal consistency", "NA", "Subtotal missing"
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

    def _check_tax_calculation_accuracy(self, data: Dict) -> Dict:
        total_tax = data.get("total_tax")
        if total_tax is None:
            return self._result(
                "Tax calculation accuracy", "NA", "Tax missing"
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
                "Tax calculation accuracy",
                "FAIL",
                "Tax mismatch",
                "HIGH",
            )

        return self._result("Tax calculation accuracy", "PASS")

    def _check_invoice_total(self, data: Dict) -> Dict:
        if data.get("total_amount") is None:
            return self._result(
                "Invoice total validation", "REVIEW", "Total missing"
            )
        return self._result("Invoice total validation", "PASS")

    # -------------------------------------------------------------------
    # HSN / SAC
    # -------------------------------------------------------------------
    def _check_hsn_code(self, data: Dict) -> Dict:
        for idx, item in enumerate(data.get("line_items", [])):
            hsn = self._normalize_hsn(item.get("hsn_sac"))
            if not hsn:
                return self._result(
                    "HSN/SAC validation",
                    "FAIL",
                    f"Missing HSN/SAC at item {idx}",
                    "HIGH",
                )

            try:
                resp = requests.post(
                    HSN_API_URL, json={"hsn_sac": hsn}, timeout=5
                )
                if resp.status_code != 200:
                    return self._result(
                        "HSN/SAC validation",
                        "FAIL",
                        f"HSN/SAC not found in master: {hsn}",
                        "HIGH",
                    )
            except Exception as e:
                return self._result(
                    "HSN/SAC validation",
                    "REVIEW",
                    f"HSN service unreachable: {e}",
                    "MEDIUM",
                )

        return self._result("HSN/SAC validation", "PASS")

    # -------------------------------------------------------------------
    # GST RATE
    # -------------------------------------------------------------------
    def _check_gst_rate(self, data: Dict) -> Dict:
        for item in data.get("line_items", []):
            hsn = self._normalize_hsn(item.get("hsn_sac"))
            amount = item.get("amount") or 0
            if not hsn or amount <= 0:
                continue

            try:
                resp = requests.post(
                    GST_RATE_API_URL, json={"hsn_sac": hsn}, timeout=5
                )
                if resp.status_code != 200:
                    return self._result(
                        "GST rate validation",
                        "FAIL",
                        f"GST rate not found for {hsn}",
                        "HIGH",
                    )
            except Exception as e:
                return self._result(
                    "GST rate validation",
                    "REVIEW",
                    f"GST rate service unreachable: {e}",
                    "MEDIUM",
                )

        return self._result("GST rate validation", "PASS")

    # -------------------------------------------------------------------
    # COMPANY POLICY
    # -------------------------------------------------------------------
    def _check_company_policy(self, data: Dict) -> Dict:
        total = data.get("total_amount")
        if total is None:
            return self._result(
                "Company policy check", "NA", "Total missing"
            )

        try:
            resp = requests.post(
                POLICY_API_URL,
                json={"field": "invoice_amount", "value": total},
                timeout=5,
            )
            if not resp.json().get("compliant"):
                return self._result(
                    "Company policy check",
                    "FAIL",
                    resp.json().get("rule", "Policy violation"),
                    "HIGH",
                )
        except Exception as e:
            return self._result(
                "Company policy check",
                "REVIEW",
                f"Policy service unreachable: {e}",
                "MEDIUM",
            )

        return self._result("Company policy check", "PASS")
