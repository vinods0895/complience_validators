from Agents.extractor import ExtractorAgent
from Agents.validator import ValidatorAgent
from Agents.stateful_compliance import StatefulComplianceEngine
from Agents.resolver import ResolverAgent
from Agents.reporter import ReporterAgent
from tools.state_manager import StateManager
from tools.human_review_store import HumanReviewStore


class Orchestrator:
    def __init__(self):
        self.extractor = ExtractorAgent()
        self.validator = ValidatorAgent()
        self.state_manager = StateManager()
        self.stateful_engine = StatefulComplianceEngine(self.state_manager)
        self.resolver = ResolverAgent()
        self.reporter = ReporterAgent()
        self.human_review_store = HumanReviewStore()

    def process_invoice(self, file_path: str, financial_year: str):
        invoices = self.extractor.run(file_path)
        results = []

        for invoice in invoices:
            invoice_id = invoice.get("invoice_id")
            invoice_number = invoice.get("invoice_number")

            # 1. Stateless validation
            validation_result = self.validator.validate_invoice(invoice)

            # 2. Stateful compliance
            try:
                stateful_result = self.stateful_engine.run(
                    invoice=invoice,
                    financial_year=financial_year,
                )
            except Exception:
                stateful_result = None

            # 3. Resolver  ✅ FIXED
            if self.resolver.should_resolve(validation_result):
                resolution = self.resolver.resolve(
                    invoice_id=invoice_id,
                    invoice_number=invoice_number,
                    validation_result=validation_result,
                    stateful_result=stateful_result,
                )
            else:
                resolution = {
                    "resolution": {
                        "violation_type": "NONE",
                        "recommended_action": "ACCEPT",
                        "confidence": 1.0,
                    }
                }

            # 4. Routing
            resolution_data = resolution["resolution"]
            confidence = resolution_data.get("confidence", 0.0)
            action = resolution_data.get("recommended_action")

            if action == "REJECT" or confidence < 0.70:
                route = "HUMAN_REVIEW"
            elif confidence < 0.85:
                route = "REQUEST_CLARIFICATION"
            else:
                route = "AUTO_APPROVE"

            # 5. Human review persistence ✅ FIXED
            human_review_id = None
            if route == "HUMAN_REVIEW":
                human_review_id = self.human_review_store.create_review(
                    invoice_id=invoice_id,
                    invoice_number=invoice_number,
                    confidence=confidence,
                    validation=validation_result,
                    resolution=resolution,
                    stateful=stateful_result,
                )

            # 6. Report
            report = self.reporter.run(
                data=invoice,
                validation=validation_result,
                resolution=resolution,
                stateful=stateful_result,
                route=route,
                confidence=confidence,
                human_review_id=human_review_id,
            )

            results.append(report)

        return results
