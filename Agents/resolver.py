import json
from typing import Dict, Any, List
from llm_clients import llm_clients


class ResolverAgent:
    """
    Advisory LLM resolver.
    NEVER overrides deterministic validation.
    """

    def __init__(self, llm_backend: str = "ollama_llama3"):
        if llm_backend not in llm_clients:
            raise ValueError(
                f"Unknown LLM backend: {llm_backend}. "
                f"Available backends: {list(llm_clients.keys())}"
            )
        self.llm = llm_clients[llm_backend]

    def should_resolve(self, validation_result: Dict) -> bool:
        return validation_result.get("summary", {}).get(
            "final_status"
        ) in ("FAIL", "REVIEW")

    def resolve(
        self,
        invoice_id: str,
        invoice_number: str,
        validation_result: Dict,
    ) -> Dict[str, Any]:

        failed_checks: List[Dict] = [
            {
                "checkpoint": c.get("checkpoint"),
                "status": c.get("status"),
                "severity": c.get("severity"),
                "details": c.get("details"),
            }
            for c in validation_result.get("checks", [])
            if c.get("status") in ("FAIL", "REVIEW")
        ]

        payload = {
            "task": "invoice_compliance_classification",
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "failed_checks": failed_checks,
            "instructions": (
                "Return ONLY valid JSON with keys: "
                "violation_type, recommended_action, confidence. "
                "No explanations outside JSON."
            ),
        }

        try:
            raw = self.llm(json.dumps(payload, indent=2))

            # Ollama often adds text → extract JSON safely
            start = raw.find("{")
            end = raw.rfind("}")
            parsed = json.loads(raw[start:end + 1])

            return {
                "resolution": parsed
            }

        except Exception as e:
            return {
                "resolution": {
                    "violation_type": "UNKNOWN",
                    "recommended_action": "ESCALATE",
                    "confidence": 0.0,
                },
                "error": str(e),
            }
