# Agents/reporter.py

import json
from typing import Dict, Any, Optional
from llm_clients import llm_clients


class ReporterAgent:
    """
    ReporterAgent responsibilities:
    - Format final output
    - Optionally generate LLM-based audit report
    - NEVER override resolver decisions
    - NEVER crash if LLM is unavailable
    """

    MIN_CONFIDENCE = 0.30
    MAX_CONFIDENCE = 1.00

    def __init__(self, llm_backend: Optional[str] = "ollama_llama3"):
        self.llm = None

        if (
            llm_backend
            and isinstance(llm_backend, str)
            and llm_backend in llm_clients
            and callable(llm_clients[llm_backend])
        ):
            self.llm = llm_clients[llm_backend]

      
    # CORE ENTRY
      

    def run(
        self,
        data: Dict[str, Any],
        validation: Dict[str, Any],
        resolution_wrapper: Dict[str, Any],
        stateful: Optional[Dict[str, Any]],
        human_review_id: Optional[str],
    ) -> Dict[str, Any]:

        resolution = resolution_wrapper.get("resolution", {})

        route = resolution.get("recommended_action", "REVIEW")
        confidence = self._clamp_confidence(
            resolution.get("confidence", self.MIN_CONFIDENCE)
        )

        llm_report = None
        llm_consistency_flag = "NOT_RUN"

        # 🔐 HARD GUARD — NEVER CALL None
        if callable(self.llm):
            try:
                llm_report = self._generate_llm_report(
                    data, validation, resolution
                )
                llm_consistency_flag = llm_report.get(
                    "consistency_check", "UNKNOWN"
                )
            except Exception as e:
                llm_report = {
                    "summary": "LLM report generation failed",
                    "error": str(e),
                }
                llm_consistency_flag = "FAILED"

        return {
            "invoice_id": data.get("invoice_id"),
            "invoice_number": data.get("invoice_number"),
            "route": route,
            "confidence": confidence,
            "human_review_id": human_review_id,
            "validation": validation,
            "resolution": resolution,
            "llm_report": llm_report,
            "llm_consistency_flag": llm_consistency_flag,
            "stateful": stateful,
        }

      
    # LLM REPORT GENERATION
      

    def _generate_llm_report(
        self,
        data: Dict[str, Any],
        validation: Dict[str, Any],
        resolution: Dict[str, Any],
    ) -> Dict[str, Any]:

        # 🔐 DOUBLE SAFETY
        if not callable(self.llm):
            raise RuntimeError("LLM client is not initialized")

        prompt = {
            "role": "You are an independent audit reviewer.",
            "task": "Generate a human-readable audit report for an invoice decision.",
            "invoice": {
                "invoice_id": data.get("invoice_id"),
                "invoice_number": data.get("invoice_number"),
            },
            "validation_summary": validation.get("summary"),
            "failed_checks": [
                c for c in validation.get("checks", [])
                if c.get("status") in ("FAIL", "REVIEW")
            ],
            "resolver_decision": resolution,
            "instructions": [
                "Do NOT change the resolver decision",
                "Check whether the decision logically follows from validation findings",
                "Explain confidence level in plain English",
                "Summarize key compliance risks",
                "Indicate whether decision is CONSISTENT or POTENTIALLY_INCONSISTENT",
                "Return STRICT JSON only",
            ],
            "output_schema": {
                "summary": "string",
                "confidence_explanation": "string",
                "key_risks": "list of strings",
                "consistency_check": [
                    "CONSISTENT",
                    "POTENTIALLY_INCONSISTENT",
                ],
            },
        }

        response = self.llm(json.dumps(prompt, indent=2))
        parsed = self._extract_json(response)

        return parsed

      
    # SAFE JSON EXTRACTION
      

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Safely extract JSON object from LLM output.
        Handles markdown, explanations, and extra text.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM output")

        return json.loads(text[start:end + 1])

      
    # HELPERS
      

    def _clamp_confidence(self, value: Any) -> float:
        try:
            return max(
                self.MIN_CONFIDENCE,
                min(self.MAX_CONFIDENCE, float(value)),
            )
        except Exception:
            return self.MIN_CONFIDENCE
