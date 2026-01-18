

from typing import Dict, List, Optional


class ReporterAgent:
    def __init__(self):
        pass

    
    def generate_report(
        self,
        invoice_id: str,
        validation_result: Dict,
        resolver_result: Optional[Dict] = None,
    ) -> Dict:
        """
        Generates a structured compliance report for one invoice.
        """

        final_status = validation_result["summary"]["final_status"]
        checks = validation_result["checks"]

        # Extract findings
        failed = [c for c in checks if c["status"] == "FAIL"]
        warnings = [c for c in checks if c["status"] in ("REVIEW", "NA")]

        # Determine risk level
        risk_level = self._determine_risk(final_status, failed)

        # Build report sections
        report = {
            "invoice_id": invoice_id,
            "final_decision": final_status,
            "risk_level": risk_level,
            "summary": self._build_summary(final_status, failed, warnings),
            "key_findings": self._extract_key_findings(failed, warnings),
            "recommended_action": self._recommended_action(
                final_status, resolver_result
            ),
            "audit_notes": self._audit_notes(failed, warnings),
            "confidence_score": self._confidence_score(final_status, warnings),
        }

        # Attach LLM reasoning if present
        if resolver_result:
            report["llm_reasoning"] = resolver_result.get("llm_reasoning")

        return report

    
    def _determine_risk(self, final_status: str, failed: List[Dict]) -> str:
        if final_status == "FAIL":
            return "HIGH"
        if final_status == "REVIEW":
            return "MEDIUM"
        return "LOW"

    def _build_summary(
        self,
        final_status: str,
        failed: List[Dict],
        warnings: List[Dict],
    ) -> str:
        if final_status == "PASS":
            if warnings:
                return (
                    "Invoice is largely compliant with minor informational gaps "
                    "that do not block processing."
                )
            return "Invoice is fully compliant with all validation checks."

        if final_status == "REVIEW":
            return (
                "Invoice requires review due to ambiguous or missing information. "
                "No critical violations detected."
            )

        return (
            "Invoice has critical compliance issues and cannot be processed "
            "without correction."
        )

    def _extract_key_findings(
        self,
        failed: List[Dict],
        warnings: List[Dict],
    ) -> List[str]:
        findings = []

        for c in failed:
            findings.append(f"{c['checkpoint']}: {c['details']}")

        for c in warnings:
            if c["details"]:
                findings.append(f"{c['checkpoint']}: {c['details']}")

        return findings

    def _recommended_action(
        self,
        final_status: str,
        resolver_result: Optional[Dict],
    ) -> str:
        if final_status == "PASS":
            return "Invoice can be processed without restrictions."

        if final_status == "REVIEW":
            if resolver_result and resolver_result.get("llm_reasoning"):
                return (
                    "Process invoice with caution. "
                    "Follow recommendations provided in the reasoning section."
                )
            return "Seek clarification from vendor before processing."

        return "Reject invoice and request corrected version from vendor."

    def _audit_notes(
        self,
        failed: List[Dict],
        warnings: List[Dict],
    ) -> List[str]:
        notes = []

        for c in failed:
            notes.append(
                f"FAIL: {c['checkpoint']} ({c.get('severity', 'UNKNOWN')})"
            )

        for c in warnings:
            notes.append(
                f"{c['status']}: {c['checkpoint']}"
            )

        if not notes:
            notes.append("All compliance checks passed.")

        return notes

    def _confidence_score(self, final_status: str, warnings: List[Dict]) -> float:
        """
        Simple deterministic confidence scoring.
        """
        if final_status == "FAIL":
            return 0.30
        if final_status == "REVIEW":
            return round(0.70 - (len(warnings) * 0.05), 2)
        return 0.95 