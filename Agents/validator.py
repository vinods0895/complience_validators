import re
import requests
from typing import Dict, List, Any

# -------------------------------------------------------------------
# API ENDPOINTS (Mock Server = Master Data Owner)
# -------------------------------------------------------------------
GST_API_URL = "http://127.0.0.1:5000/api/gst/validate-gstin"
HSN_API_URL = "http://127.0.0.1:5000/api/gst/validate-hsn"
GST_RATE_API_URL = "http://127.0.0.1:5000/api/gst/rate-schedule"
POLICY_API_URL = "http://127.0.0.1:5000/api/policy/check"


class ValidatorAgent:
    # -------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------
    def validate_invoice(self, invoice: Any) -> Dict:
        data = invoice.model_dump()
        checks: List[Dict] = []

        # ---------------- Structural ----------------
        checks.append(self._check_invoice_number(data))
        checks.append(self._check_invoice_date(data))
        checks.append(self._check_gstin_format(data))
        checks.append(self._check_gstin_active(data))

        # ---------------- Arithmetic ----------------
        checks.append(self._check_line_item_arithmetic(data))
        checks.append(self._check_subtotal_consistency(data))
        checks.append(self._check_tax_calculation_accuracy(data))

        # ---------------- GST + Compliance ----------------
        checks.append(self._check_invoice_total(data))
        checks.append(self._check_hsn_code(data))      # ✅ FIXED
        checks.append(self._check_gst_rate(data))
        checks.append(self._check_company_policy(data))

        return {
            "summary": self._aggregate_results(checks),
            "checks": checks,
        }

    # -------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------
    def _result(
        self,
        checkpoint: str,
        status: str,
        details: str = "",
        severity: str = "LOW",
    ) -> Dict:
        return {
            "checkpoint": checkpoint,
            "status": status,
            "severity": severity,
            "details": details,
        }

    def _aggregate_results(self, checks: List[Dict]) -> Dict:
        for c in checks:
            if c["status"] == "FAIL" and c["severity"] == "HIGH":
                return {"final_status": "FAIL"}
        for c in checks:
            if c["status"] == "FAIL":
                return {"final_status": "REVIEW"}
        return {"final_status": "PASS"}

    # -------------------------------------------------------------------
    # STRUCTURAL CHECKS
    # -------------------------------------------------------------------
    def _check_invoice_number(self, data: Dict) -> Dict:
        if data.get("invoice_number"):
            return self._result("Invoice number present", "PASS")
        return self._result(
            "Invoice number present", "FAIL", "Missing invoice number", "HIGH"
        )

    def _check_invoice_date(self, data: Dict) -> Dict:
        if data.get("invoice_date"):
            return self._result("Invoice date present", "PASS")
        return self._result(
            "Invoice date present", "FAIL", "Missing invoice date", "HIGH"
        )

    def _check_gstin_format(self, data: Dict) -> Dict:
        pattern = r"\b\d{2}[A-Z0-9]{13}\b"
        gstin = (data.get("vendor") or {}).get("gstin")
        if gstin and not re.match(pattern, gstin):
            return self._result(
                "GSTIN format validation",
                "FAIL",
                "Invalid GSTIN format",
                "HIGH",
            )
        return self._result("GSTIN format validation", "PASS")

    def _check_gstin_active(self, data: Dict) -> Dict:
        gstin = (data.get("vendor") or {}).get("gstin")
        if not gstin:
            return self._result(
                "GSTIN active status", "NA", "Vendor GSTIN missing"
            )

        try:
            resp = requests.post(
                GST_API_URL, json={"gstin": gstin}, timeout=5
            )
        except Exception as e:
            return self._result(
                "GSTIN active status",
                "REVIEW",
                f"GST service unreachable: {e}",
                "MEDIUM",
            )

        if resp.status_code != 200:
            return self._result(
                "GSTIN active status", "FAIL", "GSTIN not found", "HIGH"
            )

        payload = resp.json()
        if payload.get("status") == "SUSPENDED":
            return self._result(
                "GSTIN active status", "FAIL", "GSTIN suspended", "HIGH"
            )

        return self._result("GSTIN active status", "PASS")

    # -------------------------------------------------------------------
    # ARITHMETIC CHECKS
    # -------------------------------------------------------------------
    def _check_line_item_arithmetic(self, data: Dict) -> Dict:
        for idx, item in enumerate(data.get("line_items", [])):
            q, r, a = (
                item.get("quantity"),
                item.get("rate"),
                item.get("amount"),
            )
            if None in (q, r, a):
                continue
            if abs((q * r) - a) > 1:
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
        calc = sum(
            i.get("amount") or 0 for i in data.get("line_items", [])
        )
        if abs(calc - subtotal) > 1:
            return self._result(
                "Subtotal consistency",
                "FAIL",
                "Subtotal mismatch",
                "HIGH",
            )
        return self._result("Subtotal consistency", "PASS")

    def _check_tax_calculation_accuracy(self, data: Dict) -> Dict:
        cgst, sgst, igst = (
            data.get("cgst_amount"),
            data.get("sgst_amount"),
            data.get("igst_amount"),
        )
        total_tax = data.get("total_tax")
        if total_tax is None:
            return self._result(
                "Tax calculation accuracy", "NA", "Tax breakup missing"
            )
        calc_tax = sum(x or 0 for x in [cgst, sgst, igst])
        if abs(calc_tax - total_tax) > 1:
            return self._result(
                "Tax calculation accuracy",
                "FAIL",
                "Tax mismatch",
                "HIGH",
            )
        return self._result("Tax calculation accuracy", "PASS")

    # -------------------------------------------------------------------
    # GST & COMPLIANCE (MASTER DATA VIA API)
    # -------------------------------------------------------------------
    def _check_invoice_total(self, data: Dict) -> Dict:
        total = data.get("total_amount")
        taxable = sum(
            i.get("amount") or 0 for i in data.get("line_items", [])
        )
        if total is None:
            return self._result(
                "Invoice total validation", "REVIEW", "Total missing"
            )
        if total >= taxable:
            return self._result("Invoice total validation", "PASS")
        return self._result(
            "Invoice total validation",
            "FAIL",
            "Total < taxable",
            "HIGH",
        )

    # -------------------------------------------------------------------
    # ✅ FIXED HSN/SAC VALIDATION (MASTER DATA + KEYWORDS)
    # -------------------------------------------------------------------
    def _check_hsn_code(self, data: Dict) -> Dict:
        for idx, item in enumerate(data.get("line_items", [])):
            hsn = item.get("hsn_sac")
            desc = (item.get("description") or "").lower()
            qty = item.get("quantity") or 0

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
                        f"Invalid HSN/SAC {hsn}",
                        "HIGH",
                    )

                master = resp.json()

                keywords = master.get("keywords", [])
                category = master.get("category")

                # GOODS sanity check
                if category == "GOODS" and qty <= 0:
                    return self._result(
                        "HSN/SAC validation",
                        "FAIL",
                        f"Invalid quantity for GOODS HSN {hsn}",
                        "HIGH",
                    )

                matched = [
                    kw for kw in keywords if kw.lower() in desc
                ]

                if not matched:
                    return self._result(
                        "HSN/SAC validation",
                        "REVIEW",
                        (
                            f"HSN {hsn} exists but description does not clearly "
                            "match master keywords. Manual review required."
                        ),
                        "MEDIUM",
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
    # GST RATE (UNCHANGED)
    # -------------------------------------------------------------------
    def _check_gst_rate(self, data: Dict) -> Dict:
        taxable = sum(
            i.get("amount") or 0 for i in data.get("line_items", [])
        )
        total = data.get("total_amount")

        if not taxable or not total:
            return self._result(
                "GST rate validation", "NA", "Insufficient data"
            )

        inferred_rate = round(((total - taxable) / taxable) * 100, 2)

        for item in data.get("line_items", []):
            hsn = item.get("hsn_sac")
            if not hsn:
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

                payload = resp.json()
                expected_rate = payload.get("total_rate")

                if expected_rate is None:
                    return self._result(
                        "GST rate validation",
                        "REVIEW",
                        "GST rate missing in response",
                        "MEDIUM",
                    )

                if abs(expected_rate - inferred_rate) > 1:
                    return self._result(
                        "GST rate validation",
                        "FAIL",
                        f"Expected {expected_rate}% but found {inferred_rate}%",
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
    # COMPANY POLICY (UNCHANGED)
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
            result = resp.json()
            if not result.get("compliant"):
                return self._result(
                    "Company policy check",
                    "FAIL",
                    result.get("rule", "Policy violation"),
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
