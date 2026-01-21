from Agents.extractor import ExtractorAgent
from Agents.validator import ValidatorAgent
from Agents.stateful_compliance import StatefulComplianceEngine
from Agents.resolver import ResolverAgent
from Agents.reporter import ReporterAgent

from tools.state_manager import StateManager
from tools.human_review_store import HumanReviewStore

from graph.workflow import build_compliance_graph
from graph.state import ComplianceState


def main():
    print("🔄 Processing invoices...\n")

    extractor = ExtractorAgent()
    validator = ValidatorAgent()

    state_manager = StateManager()
    stateful_engine = StatefulComplianceEngine(state_manager)

    resolver = ResolverAgent(llm_backend="ollama_llama3")
    reporter = ReporterAgent()
    human_review_store = HumanReviewStore()

    graph = build_compliance_graph(
        extractor=extractor,
        validator=validator,
        stateful_engine=stateful_engine,
        resolver=resolver,
        reporter=reporter,
        human_review_store=human_review_store,
    )

    invoices = extractor.run("data/invoices/test_invoices.json")

    for idx, invoice in enumerate(invoices, start=1):
        print(f"➡️  Invoice {idx}/{len(invoices)}: {invoice.get('invoice_number')}")

        state = ComplianceState(
            invoice=invoice,
            financial_year="2024-25",
        )

        # 🔑 LangGraph returns DICT
        final_state = graph.invoke(state)

        route = final_state.get("route")
        confidence = final_state.get("confidence", 0.0)

        print(f"   🚦 Route: {route} | Confidence: {confidence}")

        resolution = final_state.get("resolution", {})
        resolution_data = resolution.get("resolution", {})

        if resolution_data:
            print(f"   🧠 Reason: {resolution_data.get('reasoning')}")

        print("")


if __name__ == "__main__":
    main()
