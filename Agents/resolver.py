from typing import Dict, Any, List
from langchain_core.prompts import PromptTemplate
from llm_clients import llm_clients


class ResolverAgent:
    """
    Uses LLM ONLY to explain REVIEW / FAIL decisions.
    Never changes deterministic validator output.
    """

    def __init__(self, llm_backend: str = "openrouter_free"):
        if llm_backend not in llm_clients:
            raise ValueError(f"Unknown LLM backend: {llm_backend}")

        # Pick the backend from llm_clients registry
        self.llm = llm_clients[llm_backend]

        # Define reusable prompt template
        self.prompt = PromptTemplate.from_template("""
You are a GST compliance expert assisting an Accounts Payable team.

Invoice ID: {invoice_id}

Compliance issues detected:
{issues_text}

Answer clearly:
1. Is this a hard compliance violation or a documentation gap?
2. Can the invoice be accepted with clarification?
3. What is the recommended next action?

Do NOT restate the issues verbatim.
Do NOT mention system or technical errors.
Respond in plain business English.
""")

    # -------------------------------------------------
    # Decision gate
    # -------------------------------------------------
    def should_resolve(self, validation_result: Dict) -> bool:
        """
        Decide if LLM reasoning is needed.
        """
        return validation_result["summary"]["final_status"] in ("FAIL", "REVIEW")

    # -------------------------------------------------
    # LLM reasoning
    # -------------------------------------------------
    def resolve(
        self,
        invoice_id: str,
        validation_result: Dict
    ) -> Dict[str, Any]:
        """
        Generate human-readable reasoning using LLM.
        """

        failed_checks: List[Dict] = [
            c for c in validation_result["checks"]
            if c["status"] in ("FAIL", "REVIEW")
        ]

        if not failed_checks:
            return {
                "llm_reasoning": "No compliance issues detected.",
                "resolution_type": "NO_ACTION",
            }

        # Build compact issues text for LLM
        issues_text = "\n".join(
            f"- {c['checkpoint']} ({c['status']}): {c['details']}"
            for c in failed_checks
        )

        # Format prompt with template
        prompt = self.prompt.format(
            invoice_id=invoice_id,
            issues_text=issues_text
        )

        try:
            # Call the selected LLM backend
            response = self.llm(prompt)

            return {
                "llm_reasoning": response.strip(),
                "resolution_type": "LLM_REASONED_REVIEW",
            }

        except Exception as e:
            # Enterprise-safe fallback
            return {
                "llm_reasoning": (
                    "LLM reasoning unavailable. "
                    "Invoice requires manual compliance review."
                ),
                "resolution_type": "LLM_FALLBACK",
                "error": str(e),
            }
