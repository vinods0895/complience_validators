import json
from typing import Dict, Any, List
from llm_clients import llm_clients


class ResolverAgent:
    """
    LLM-based resolver.

    Responsibilities:
    - Explain WHY an invoice needs action
    - Assign explainable confidence scores
    - Never hardcode rejection reasons
    - Never return confidence = 0.0
    - Fall back to fact-based reasoning if LLM fails
    """

    MIN_CONFIDENCE = 0.30
    MAX_CONFIDENCE = 0.95

    def __init__(self, llm_backend: str = "ollama_deepseek_r1"):
        if llm_backend not in llm_clients:
            raise ValueError(
                f"Unknown LLM backend: {llm_backend}. "
                f"Available backends: {list(llm_clients.keys())}"
            )
        self.llm = llm_clients[llm_backend]

     
    # GATING LOGIC
     

    def should_resolve(self, validation_result: Dict) -> bool:
        return validation_result.get("summary", {}).get(
            "final_status"
        ) in ("REVIEW", "FAIL")

     
    # CORE RESOLUTION LOGIC
     

    def resolve(
        self,
        invoice_id: str,
        invoice_number: str,
        validation_result: Dict,
        stateful_result: Dict | None = None,
    ) -> Dict[str, Any]:

        failed_checks = self._collect_failed_checks(validation_result)

        if not failed_checks:
            return self._auto_accept(invoice_id, invoice_number)

        prompt = self._build_prompt(
            invoice_id, invoice_number, failed_checks
        )

        try:
            response = self.llm(json.dumps(prompt, indent=2))
            parsed = self._safe_json(response)

            confidence = self._clamp_confidence(parsed.get("confidence"))

            return {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "resolution": {
                    "violation_type": parsed.get(
                        "violation_type", "DOCUMENTATION_GAP"
                    ),
                    "recommended_action": parsed.get(
                        "recommended_action", "REQUEST_CLARIFICATION"
                    ),
                    "confidence": confidence,
                    "missing_fields": parsed.get("missing_fields", []),
                    "reasoning": parsed.get(
                        "reasoning",
                        "Compliance gaps detected based on validation checks.",
                    ),
                    "actions_required": parsed.get(
                        "actions_required", []
                    ),
                },
            }

        except Exception as e:
            return self._fallback_resolution(
                invoice_id, invoice_number, validation_result, error=str(e)
            )

     
    # PROMPT CONSTRUCTION
     

    def _build_prompt(
        self,
        invoice_id: str,
        invoice_number: str,
        failed_checks: List[Dict],
    ) -> Dict[str, Any]:

        return {
            "role": "You are a senior GST & TDS compliance officer.",
            "task": "Review invoice validation failures and explain required actions.",
            "invoice": {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
            },
            "failed_checks": failed_checks,
            "instructions": [
                "Identify missing or weak compliance fields",
                "Explain how each issue affects confidence",
                "Classify the violation type",
                "Recommend next action",
                "Assign confidence strictly based on issues",
                "Suggest concrete remediation steps",
                "Return STRICT JSON only",
            ],
            "output_schema": {
                "violation_type": [
                    "HARD_COMPLIANCE",
                    "SOFT_COMPLIANCE",
                    "DOCUMENTATION_GAP",
                ],
                "recommended_action": [
                    "ACCEPT",
                    "REQUEST_CLARIFICATION",
                    "ESCALATE",
                    "REJECT",
                ],
                "confidence": "float (0-1)",
                "missing_fields": "list of strings",
                "reasoning": "string",
                "actions_required": "list of strings",
            },
        }

     
    # FALLBACK LOGIC (NO LLM)
     

    def _fallback_resolution(
        self,
        invoice_id: str,
        invoice_number: str,
        validation_result: Dict,
        error: str,
    ) -> Dict[str, Any]:

        failed_checks = self._collect_failed_checks(validation_result)
        confidence = self._fallback_confidence(failed_checks)

        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "resolution": {
                "violation_type": "DOCUMENTATION_GAP",
                "recommended_action": "REQUEST_CLARIFICATION",
                "confidence": confidence,
                "missing_fields": [
                    c["checkpoint"] for c in failed_checks
                ],
                "reasoning": self._fallback_reasoning(failed_checks),
                "actions_required": self._fallback_actions(failed_checks),
            },
            "error": error,
        }

     
    # HELPERS
     

    def _collect_failed_checks(
        self, validation_result: Dict
    ) -> List[Dict]:

        return [
            {
                "checkpoint": c["checkpoint"],
                "status": c["status"],
                "severity": c["severity"],
                "details": c["details"],
            }
            for c in validation_result.get("checks", [])
            if c["status"] in ("FAIL", "REVIEW")
        ]

    def _fallback_confidence(self, failed_checks: List[Dict]) -> float:
        reduction = 0.2 * len(failed_checks)
        return max(self.MIN_CONFIDENCE, 1.0 - reduction)

    def _fallback_reasoning(self, failed_checks: List[Dict]) -> str:
        reasons = [
            f"{c['checkpoint']} ({c['severity']}): {c['details']}"
            for c in failed_checks
        ]
        return "Issues detected: " + "; ".join(reasons)

    def _fallback_actions(self, failed_checks: List[Dict]) -> List[str]:
        actions = set()

        for c in failed_checks:
            if "GST" in c["checkpoint"]:
                actions.add("Verify supplier GSTIN details")
            if "AMOUNT" in c["checkpoint"]:
                actions.add("Confirm invoice amount and tax breakup")
            if "DATE" in c["checkpoint"]:
                actions.add("Validate invoice date")
            if "DOC" in c["checkpoint"]:
                actions.add("Upload clearer invoice document")

        return list(actions) or ["Request manual review"]

    def _auto_accept(self, invoice_id: str, invoice_number: str) -> Dict[str, Any]:
        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "resolution": {
                "violation_type": "NONE",
                "recommended_action": "ACCEPT",
                "confidence": 1.0,
                "missing_fields": [],
                "reasoning": "No compliance issues detected.",
                "actions_required": [],
            },
        }

    def _safe_json(self, text: str) -> Dict[str, Any]:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a valid JSON object")
        return parsed

    def _clamp_confidence(self, value: Any) -> float:
        try:
            return max(
                self.MIN_CONFIDENCE,
                min(self.MAX_CONFIDENCE, float(value)),
            )
        except Exception:
            return self.MIN_CONFIDENCE
