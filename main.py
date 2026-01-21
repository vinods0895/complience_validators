from Agents.extractor import ExtractorAgent
from Agents.validator import ValidatorAgent
from Agents.resolver import ResolverAgent
from Agents.reporter import ReporterAgent
from tools.state_manager import StateManager


def main():
    extractor = ExtractorAgent()
    validator = ValidatorAgent()
    resolver = ResolverAgent(llm_backend="ollama_llama3")
    reporter = ReporterAgent()
    state_manager = StateManager()

    file_path = "data/invoices/test_invoices.json"
    invoices = extractor.run(file_path)

    print(f"\n🔄 Processing {len(invoices)} invoices...\n")

    for idx, invoice in enumerate(invoices, start=1):
        invoice_number = invoice.get("invoice_number")
        invoice_id = invoice.get("invoice_id")

        print(f"➡️  Invoice {idx}/{len(invoices)}: {invoice_number}")

        # 1. Validation
        validation_result = validator.validate_invoice(invoice)

        failed = [
            c for c in validation_result["checks"]
            if c["status"] in ("FAIL", "REVIEW")
        ]

        if failed:
            print("   ❌ Validation issues:")
            for c in failed:
                print(f"     - [{c['status']}] {c['checkpoint']}: {c['details']}")

        # 2. Resolver
        if validation_result["summary"]["final_status"] in ("FAIL", "REVIEW"):
            resolution = resolver.resolve(
                invoice_id=invoice_id,
                invoice_number=invoice_number,
                validation_result=validation_result,
            )
        else:
            resolution = {
                "resolution": {
                    "recommended_action": "ACCEPT",
                    "confidence": 1.0,
                }
            }

        resolution_data = resolution.get("resolution", {})
        confidence = float(resolution_data.get("confidence", 0.0))
        action = resolution_data.get("recommended_action", "ESCALATE")

        # 3. Routing
        if action == "REJECT" or confidence < 0.70:
            route = "HUMAN_REVIEW"
            human_review_id = f"HR-{invoice_number}"
        elif confidence < 0.85:
            route = "REQUEST_CLARIFICATION"
            human_review_id = None
        else:
            route = "ACCEPT"
            human_review_id = None

        print(f"   🚦 Route: {route} | Confidence: {confidence}")

        # 4. Reporter (FULL ARGUMENTS — FIXED)
        report = reporter.run(
            data=invoice,
            validation=validation_result,
            resolution=resolution,
            stateful=None,
            route=route,
            confidence=confidence,
            human_review_id=human_review_id,
        )

    print("\n✅ Processing complete.\n")


if __name__ == "__main__":
    main()
