import json
import re
from typing import Dict, List, Optional
from llm_clients import llm_clients


class ReporterAgent:
    def __init__(self, llm_backend: str = "openrouter_free"):
        self.llm = llm_clients[llm_backend]

    # -------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------
    def generate_report(
        self,
        invoice_id: str,
        validation_result: Dict,
        resolver_result: Optional[Dict] = None,
    ) -> Dict:
        llm_input = self._build_prompt(
            invoice_id, validation_result, resolver_result
        )

        llm_output = self._safe_call_llm(llm_input)

        # Always enforce schema + safety
        report = self._normalize_report(
            llm_output,
            invoice_id,
            validation_result,
            resolver_result,
        )

        return report

    # -------------------------------------------------
    # LLM PROMPT
    # -------------------------------------------------
    def _build_prompt(
        self,
        invoice_id: str,
        validation_result: Dict,
        resolver_result: Optional[Dict],
    ) -> str:
        return f"""
You are a compliance reporting system.

Return ONLY valid JSON.
No markdown. No explanation. No comments.

Schema:
{{
  "summary": string,
  "key_findings": [string],
  "recommended_action": string,
  "audit_notes": [string],
  "confidence_score": number between 0 and 1
}}

Invoice ID: {invoice_id}

Validation result:
{json.dumps(validation_result, indent=2)}

Resolver reasoning:
{resolver_result.get("llm_reasoning") if resolver_result else "N/A"}
""".strip()

    # -------------------------------------------------
    # SAFE LLM CALL (NEVER FAILS)
    # -------------------------------------------------
    def _safe_call_llm(self, prompt: str) -> Dict:
        try:
            raw = self.llm(prompt)
            return self._parse_json_safely(raw)
        except Exception as e:
            # Absolute fallback
            return {
                "summary": "Report generated without LLM due to parsing issues.",
                "key_findings": [],
                "recommended_action": "Manual review recommended.",
                "audit_notes": [str(e)],
                "confidence_score": 0.5,
            }

    # -------------------------------------------------
    # JSON PARSER (VERY IMPORTANT)
    # -------------------------------------------------
    def _parse_json_safely(self, text: str) -> Dict:
        # 1. Try strict JSON
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Extract JSON block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass

        # 3. Give up safely
        raise ValueError("LLM returned unparseable JSON")

    # -------------------------------------------------
    # NORMALIZATION & GUARDS
    # -------------------------------------------------
    def _normalize_report(
        self,
        data: Dict,
        invoice_id: str,
        validation_result: Dict,
        resolver_result: Optional[Dict],
    ) -> Dict:
        final_status = validation_result["summary"]["final_status"]

        # Summary
        summary = str(data.get("summary") or "Compliance report generated.")

        # Key findings
        key_findings = data.get("key_findings")
        if not isinstance(key_findings, list):
            key_findings = []

        key_findings = [str(x) for x in key_findings]

        # Audit notes
        audit_notes = data.get("audit_notes")
        if isinstance(audit_notes, str):
            audit_notes = [audit_notes]
        elif not isinstance(audit_notes, list):
            audit_notes = []

        # Confidence score
        try:
            confidence = float(data.get("confidence_score", 0.5))
        except Exception:
            confidence = 0.5

        # Clamp between 0 and 1
        confidence = max(0.0, min(confidence, 1.0))

        # Recommended action
        recommended_action = str(
            data.get("recommended_action")
            or self._default_action(final_status)
        )

        report = {
            "invoice_id": invoice_id,
            "final_decision": final_status,
            "risk_level": self._risk_level(final_status),
            "summary": summary,
            "key_findings": key_findings,
            "recommended_action": recommended_action,
            "audit_notes": audit_notes,
            "confidence_score": confidence,
        }

        if resolver_result:
            report["llm_reasoning"] = resolver_result.get("llm_reasoning")

        return report

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------
    def _risk_level(self, status: str) -> str:
        return {
            "PASS": "LOW",
            "REVIEW": "MEDIUM",
            "FAIL": "HIGH",
        }.get(status, "MEDIUM")

    def _default_action(self, status: str) -> str:
        if status == "PASS":
            return "Invoice can be processed."
        if status == "REVIEW":
            return "Manual review required."
        return "Invoice must be corrected by vendor."
