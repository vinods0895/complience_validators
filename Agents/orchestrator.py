# agents/orchestrator.py

from tools.state_manager import StateManager
from Agents.extractor import ExtractorAgent
from Agents.validator import ValidatorAgent
from Agents.reporter import ReporterAgent


class Orchestrator:
    def __init__(self):
        self.extractor = ExtractorAgent()

        # ✅ FIX: pass required paths to ValidatorAgent
        self.validator = ValidatorAgent(
            vendor_registry_path="data/vendor_registry.csv",
            gst_rates_path="data/gst_rates.csv",
            hsn_codes_path="data/hsn_codes.json",
            tds_sections_path="data/tds_sections.json",
            company_policy_path="data/company_policy.json",
            historical_decisions_path="data/historical_decisions.json"
        )

        self.reporter = ReporterAgent()
        self.state = StateManager()   # ✅ STATE LIVES HERE

    def process_invoice(self, file_path: str):
        data = self.extractor.run(file_path)

        invoice_no = data.get("invoice_number")
        vendor = data.get("vendor_name")
        amount = float(data.get("total_amount", 0))

        # 🔁 Duplicate check
        if self.state.check_duplicate(invoice_no):
            return {
                "status": "SKIPPED",
                "reason": "Duplicate     invoice",
                "invoice_number": invoice_no
            }

        # 📊 Vendor total tracking
        vendor_total = self.state.track_vendor_total(vendor, amount)

        # ✅ Validate
        validation_result = self.validator.run(data)

        # 🧾 Report
        return self.reporter.run(
            data=data,
            validation=validation_result,
            vendor_total=vendor_total
        )
