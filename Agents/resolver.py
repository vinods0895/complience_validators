import json
from typing import Dict, Any, List, Optional
from llm_clients import llm_clients


class ResolverAgent:
    """
    LLM-based resolver (Decision Authority).

    Guarantees:
    - Confidence is ALWAYS normalized (0.30 ≤ confidence ≤ 0.95)
    - Route is ALWAYS derived from confidence + recommendation
    - No downstream component mutates confidence or route
    - Safe fallback if LLM fails
    """

    MIN_CONFIDENCE = 0.30
    MAX_CONFIDENCE = 0.95

    HUMAN_REVIEW_THRESHOLD = 0.60

    def __init__(self, llm_backend: str = "ollama_deepseek_r1"):
        if llm_backend not in llm_clients:
            raise ValueError(
                f"Unknown LLM backend: {llm_backend}. "
                f"Available backends: {list(llm_clients.keys())}"
            )
        self.llm = llm_clients[llm_backend]

    
    # GATING
    

    def should_resolve(self, validation_result: Dict) -> bool:
        return validation_result.get("summary", {}).get(
            "final_status"
        ) in ("REVIEW", "FAIL")

    
    # CORE RESOLUTION
    

    def resolve(
        self,
        invoice_id: str,
        invoice_number: str,
        validation_result: Dict,
        stateful_result: Optional[Dict] = None,
    ) -> Dict[str, Any]:

        failed_checks = self._collect_failed_checks(validation_result)

        # ✅ Fast path: clean invoice
        if not failed_checks:
            return self._auto_accept(invoice_id, invoice_number)

        prompt = self._build_prompt(
            invoice_id, invoice_number, failed_checks
        )

        try:
            response = self.llm(json.dumps(prompt, indent=2))
            parsed = self._safe_json(response)

            confidence = self._normalize_confidence(
                parsed.get("confidence")
            )

            resolution = {
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
            }

            route = self._decide_route(resolution, confidence)

            return {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "route": route,
                "confidence": confidence,
                "resolution": resolution,
            }

        except Exception as e:
            return self._fallback_resolution(
                invoice_id, invoice_number, validation_result, error=str(e)
            )

    
    # PROMPT
    

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
                "missing_fields": "list[str]",
                "reasoning": "string",
                "actions_required": "list[str]",
            },
        }

    
    # FALLBACK (NO LLM)
    

    def _fallback_resolution(
        self,
        invoice_id: str,
        invoice_number: str,
        validation_result: Dict,
        error: str,
    ) -> Dict[str, Any]:

        failed_checks = self._collect_failed_checks(validation_result)
        confidence = self._fallback_confidence(failed_checks)

        resolution = {
            "violation_type": "DOCUMENTATION_GAP",
            "recommended_action": "REQUEST_CLARIFICATION",
            "confidence": confidence,
            "missing_fields": [
                c["checkpoint"] for c in failed_checks
            ],
            "reasoning": self._fallback_reasoning(failed_checks),
            "actions_required": self._fallback_actions(failed_checks),
        }

        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "route": "HUMAN_REVIEW",
            "confidence": confidence,
            "resolution": resolution,
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

    def _normalize_confidence(self, value: Any) -> float:
        try:
            value = float(value)
        except Exception:
            return self.MIN_CONFIDENCE

        value = max(self.MIN_CONFIDENCE, min(self.MAX_CONFIDENCE, value))
        return round(value, 2)

    def _decide_route(self, resolution: Dict, confidence: float) -> str:
        """
        Final routing authority.
        """
        if confidence < self.HUMAN_REVIEW_THRESHOLD:
            return "HUMAN_REVIEW"

        action = resolution.get("recommended_action")

        if action in ("ESCALATE", "REJECT"):
            return "HUMAN_REVIEW"

        return "ACCEPT"

    def _fallback_confidence(self, failed_checks: List[Dict]) -> float:
        reduction = 0.2 * len(failed_checks)
        return self._normalize_confidence(1.0 - reduction)

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

    def _auto_accept(
        self, invoice_id: str, invoice_number: str
    ) -> Dict[str, Any]:

        confidence = self.MAX_CONFIDENCE

        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "route": "ACCEPT",
            "confidence": confidence,
            "resolution": {
                "violation_type": "NONE",
                "recommended_action": "ACCEPT",
                "confidence": confidence,
                "missing_fields": [],
                "reasoning": "No compliance issues detected.",
                "actions_required": [],
            },
        }

    def _safe_json(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("Empty response from LLM")

        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block if LLM wrapped it in text or markdown
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass

        # If still failing, raise clean error
        raise ValueError(f"LLM returned non-JSON output: {text[:200]}...")

