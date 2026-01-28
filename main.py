from datetime import datetime, timezone
from typing import Optional, Dict, Any

from Agents.extractor import ExtractorAgent
from Agents.validator import ValidatorAgent
from Agents.stateful_compliance import StatefulComplianceEngine
from Agents.resolver import ResolverAgent
from Agents.reporter import ReporterAgent

from tools.state_manager import StateManager
from tools.human_review_store import HumanReviewStore
from tools.results_store import ResultStore

from graph.workflow import build_compliance_graph
from graph.state import ComplianceState



# Helper: Print LLM reasons 

def _print_llm_reasons(
    resolution: Optional[Dict[str, Any]]
) -> None:
    if not resolution:
        return

    reasons = resolution.get("reasoning")
    if not reasons:
        return

    print("   🧠 LLM Reasons:")

    # Case 1: list[str]
    if isinstance(reasons, list):
        for idx, reason in enumerate(reasons, start=1):
            print(f"      {idx}. {reason}")

    # Case 2: string (split safely)
    elif isinstance(reasons, str):
        lines = [
            r.strip()
            for r in reasons.replace("\n", ".").split(".")
            if r.strip()
        ]
        for idx, line in enumerate(lines, start=1):
            print(f"      {idx}. {line}")


def main():
    print("🚀 Processing invoices...\n")

    
    # Initialize agents
    
    extractor = ExtractorAgent()
    validator = ValidatorAgent()

    state_manager = StateManager()
    stateful_engine = StatefulComplianceEngine(state_manager)

    resolver = ResolverAgent(llm_backend="ollama_deepseek_r1")
    reporter = ReporterAgent(llm_backend="ollama_deepseek_r1")

    
    # Persistence layers
    
    result_store = ResultStore()
    human_review_store = HumanReviewStore()

    
    # Build workflow graph
    
    graph = build_compliance_graph(
        extractor=extractor,
        validator=validator,
        stateful_engine=stateful_engine,
        resolver=resolver,
        reporter=reporter,
        human_review_store=human_review_store,
    )

    
    # Load invoices
    
    invoices = extractor.run("data/invoices/test_invoices.json")

    
    # Process invoices
    
    for idx, invoice in enumerate(invoices, start=1):

        # ---- Enforce invariants (fixes Pylance + runtime safety)
        invoice_id = invoice.get("invoice_id")
        invoice_number = invoice.get("invoice_number")

        if not invoice_id or not invoice_number:
            raise ValueError(
                "Invoice must contain 'invoice_id' and 'invoice_number'"
            )

        print(f"➡️ Invoice {idx}/{len(invoices)}: {invoice_number}")

        try:
            # Initial graph state
            state = ComplianceState(
                invoice=invoice,
                financial_year="2024-25",
            )

            # Execute agentic workflow
            final_state: Dict[str, Any] = graph.invoke(state)

            # Resolver is the single source of truth
            route: str = final_state["route"]
            confidence: float = final_state["confidence"]
            resolution: Optional[Dict[str, Any]] = final_state.get("resolution")

            
            # Build persisted result object
            
            result: Dict[str, Any] = {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "vendor_gstin": invoice.get("vendor_gstin"),
                "total_amount": invoice.get("total_amount"),

                "route": route,
                "confidence": confidence,
                "human_review_id": None,

                "resolution": resolution,
                "validation_summary": final_state.get("validation_summary"),
                "stateful": final_state.get("stateful"),
                "llm_report": final_state.get("llm_report"),

                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            
            # Create HUMAN_REVIEW snapshot
            
            if route == "HUMAN_REVIEW":
                review_id = human_review_store.create_review(
                    invoice_id=invoice_id,
                    invoice_number=invoice_number,
                    confidence=confidence,
                    validation=result["validation_summary"],
                    resolution=result["resolution"],
                    stateful=result.get("stateful"),
                )
                result["human_review_id"] = review_id

            
            # Persist final result
            
            result_store.save_result(result)

            print(
                f"   ✅ Saved | Route={route} | Confidence={confidence}"
            )

            
            # Print LLM reasoning (line-by-line)
            
            if route in ("HUMAN_REVIEW", "REJECT"):
                _print_llm_reasons(resolution)

        except Exception as e:
            print(f"   ❌ Failed invoice {invoice_id}: {str(e)}")
            result_store.save_failure(invoice_id, str(e))

        print("")

    print("🎉 Invoice processing complete.")


if __name__ == "__main__":
    main()
