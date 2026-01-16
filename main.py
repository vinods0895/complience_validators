import json
from pathlib import Path

from models.invoice_model import InvoiceModel
from Agents.validator import ValidatorAgent
from Agents.resolver import ResolverAgent
from Agents.reporter import ReporterAgent


# -------------------------------------------------
# Normalize raw invoice JSON into InvoiceModel shape
# -------------------------------------------------
def normalize_invoice(raw: dict) -> dict:
    return {
        "invoice_id": raw.get("invoice_id"),
        "invoice_no": raw.get("invoice_number"),
        "invoice_date": raw.get("invoice_date"),
        "vendor_gstin": (raw.get("vendor") or {}).get("gstin"),
        "buyer_gstin": (raw.get("buyer") or {}).get("gstin"),
        "items": [
            {
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("rate"),
                "line_total": item.get("amount"),
            }
            for item in raw.get("line_items", [])
        ],
        "total": raw.get("total_amount"),
    }


# -------------------------------------------------
# Load invoices
# -------------------------------------------------
def load_invoices(invoices_path: Path):
    invoices = []

    for file in invoices_path.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for idx, raw_inv in enumerate(data):
                invoice = InvoiceModel(**normalize_invoice(raw_inv))
                invoices.append((f"{file.name}#{idx}", invoice))
        else:
            invoice = InvoiceModel(**normalize_invoice(data))
            invoices.append((file.name, invoice))

    return invoices


# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    PROJECT_ROOT = Path(__file__).resolve().parent
    DATA_PATH = PROJECT_ROOT / "data"
    MASTER_DATA = DATA_PATH / "master_data"

    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"📁 Data path: {DATA_PATH}")
    print(f"📁 Master data path: {MASTER_DATA}")
    print(f"📁 Historical decisions path: {DATA_PATH / 'historical_decisions.jsonl'}")

    # -------------------------------
    # Initialize agents
    # -------------------------------
    validator = ValidatorAgent(
        vendor_registry_path=str(MASTER_DATA / "vendor_registry.json"),
        gst_rates_path=str(MASTER_DATA / "gst_rates_schedule.csv"),
        hsn_codes_path=str(MASTER_DATA / "hsn_sac_codes.json"),
        tds_sections_path=str(MASTER_DATA / "tds_sections.json"),
        company_policy_path=str(MASTER_DATA / "company_policy.yaml"),
        historical_decisions_path=str(DATA_PATH / "historical_decisions.jsonl"),
    )

    resolver = ResolverAgent(llm_backend="openrouter_free")
    reporter = ReporterAgent()

    # -------------------------------
    # Load invoices
    # -------------------------------
    invoices = load_invoices(DATA_PATH / "invoices")
    print(f"\n📂 Extracted {len(invoices)} invoice(s)")

    # -------------------------------
    # Run pipeline
    # -------------------------------
    for filename, invoice in invoices:
        print(f"\n🔍 Validating {filename}...")

        validation_result = validator.validate_invoice(invoice)

        for check in validation_result["checks"]:
            icon = (
                "✅" if check["status"] == "PASS"
                else "➖" if check["status"] in ("NA", "REVIEW")
                else "❌"
            )
            print(f"{icon} {check['checkpoint']}: {check['details'] or 'OK'}")

        final_status = validation_result["summary"]["final_status"]
        print(f"\n📌 FINAL DECISION: {final_status}")

        # -------------------------------
        # Resolver (LLM reasoning)
        # -------------------------------
        resolver_result = None
        if final_status in ("FAIL", "REVIEW"):
            print("\n🧠 LLM Reasoning:")
            resolver_result = resolver.resolve(
            invoice_id=filename,
            validation_result=validation_result
        )
            print(resolver_result.get("llm_reasoning", "No reasoning returned"))

        # -------------------------------
        # Reporter
        # -------------------------------
        report = reporter.generate_report(
            invoice_id=filename,
            validation_result=validation_result,
            resolver_result=resolver_result,
        )

        print("\n📄 REPORT SUMMARY")
        print(f"Decision           : {report['final_decision']}")
        print(f"Risk Level         : {report['risk_level']}")
        print(f"Summary            : {report['summary']}")
        print(f"Recommended Action : {report['recommended_action']}")
        print(f"Confidence Score   : {report['confidence_score']}")

    print("\n✅ Compliance validation completed.")


if __name__ == "__main__":
    main()
