import json
from typing import Dict, Any, List
from llm_clients import llm_clients


class ResolverAgent:
    """
    LLM-based resolver.
    - Explains WHY an invoice needs clarification / escalation
    - Does NOT override validator facts
    - Produces confidence score for routing
    """

    def __init__(self, llm_backend: str = "ollama_llama3"):
        if llm_backend not in llm_clients:
            raise ValueError(
                f"Unknown LLM backend: {llm_backend}. "
                f"Available backends: {list(llm_clients.keys())}"
            )
        self.llm = llm_clients[llm_backend]

    # CORE HELPERS

    def should_resolve(self, validation_result: Dict) -> bool:
        return validation_result.get("summary", {}).get(
            "final_status"
        ) in ("REVIEW", "FAIL")

    # CORE LOGIC

    def resolve(
        self,
        invoice_id: str,
        invoice_number: str,
        validation_result: Dict,
        stateful_result: Dict | None = None,
    ) -> Dict[str, Any]:

        failed_checks: List[Dict] = [
            {
                "checkpoint": c["checkpoint"],
                "status": c["status"],
                "severity": c["severity"],
                "details": c["details"],
            }
            for c in validation_result.get("checks", [])
            if c["status"] in ("FAIL", "REVIEW")
        ]

        if not failed_checks:
            return self._auto_accept(invoice_id, invoice_number)

        prompt = {
            "role": "You are a senior GST & TDS compliance officer.",
            "task": "Review invoice compliance findings and recommend next action.",
            "invoice": {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
            },
            "failed_checks": failed_checks,
            "instructions": [
                "Classify violation type",
                "Explain why the invoice needs action",
                "Decide if clarification is sufficient or escalation is required",
                "Assign confidence between 0 and 1",
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
                "reasoning": "string",
            },
        }

        try:
            response = self.llm(json.dumps(prompt, indent=2))
            parsed = self._safe_json(response)

            return {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "resolution": {
                    "violation_type": parsed.get("violation_type", "UNKNOWN"),
                    "recommended_action": parsed.get(
                        "recommended_action", "ESCALATE"
                    ),
                    "confidence": float(parsed.get("confidence", 0.0)),
                    "reasoning": parsed.get(
                        "reasoning",
                        "Unable to determine reason automatically.",
                    ),
                },
            }

        except Exception as e:
            return {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "resolution": {
                    "violation_type": "UNKNOWN",
                    "recommended_action": "ESCALATE",
                    "confidence": 0.0,
                    "reasoning": "LLM unavailable. Manual review required.",
                },
                "error": str(e),
            }

    # HELPERS

    def _auto_accept(self, invoice_id: str, invoice_number: str) -> Dict[str, Any]:
        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "resolution": {
                "violation_type": "NONE",
                "recommended_action": "ACCEPT",
                "confidence": 1.0,
                "reasoning": "No compliance issues detected.",
            },
        }

    def _safe_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            return {}
