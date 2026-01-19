import json
from pathlib import Path

from models.invoice_model import InvoiceModel
from Agents.validator import ValidatorAgent
from Agents.resolver import ResolverAgent
from Agents.reporter import ReporterAgent

# load invoices 
def load_invoices(invoices_path: Path):
    invoices = []

    for file in invoices_path.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for idx, raw_inv in enumerate(data):
                invoice = InvoiceModel(**raw_inv)
                invoices.append((f"{file.name}#{idx}", invoice))
        else:
            invoice = InvoiceModel(**data)
            invoices.append((file.name, invoice))

    return invoices



# print invoice context

def print_invoice_context(invoice: InvoiceModel):
    vendor = invoice.vendor
    buyer = invoice.buyer

    print("\n📄 INVOICE DETAILS")
    print("-" * 50)
    print(f"Invoice Number : {invoice.invoice_number}")
    print(f"Invoice Date   : {invoice.invoice_date}")
    print(f"Currency       : {invoice.currency}")
    print(f"Subtotal       : {invoice.subtotal}")
    print(f"Total Tax      : {invoice.total_tax}")
    print(f"Total Amount   : {invoice.total_amount}")

    print("\n🏢 VENDOR DETAILS")
    if vendor:
        v = vendor.model_dump()
        print(f"Vendor Name    : {v.get('name')}")
        print(f"Vendor GSTIN   : {v.get('gstin')}")

        if "state" in v:
            print(f"Vendor State   : {v.get('state')}")
        elif "state_code" in v:
            print(f"Vendor State Code : {v.get('state_code')}")
        elif v.get("gstin"):
            print(f"Vendor State (from GSTIN) : {v['gstin'][:2]}")
        else:
            print("Vendor State   : Not available")
    else:
        print("Vendor details missing")

    print("\n🏬 BUYER DETAILS")
    if buyer:
        b = buyer.model_dump()
        print(f"Buyer Name     : {b.get('name')}")
        print(f"Buyer GSTIN    : {b.get('gstin')}")

        if "state" in b:
            print(f"Buyer State    : {b.get('state')}")
        elif "state_code" in b:
            print(f"Buyer State Code : {b.get('state_code')}")
        elif b.get("gstin"):
            print(f"Buyer State (from GSTIN) : {b['gstin'][:2]}")
        else:
            print("Buyer State    : Not available")
    else:
        print("Buyer details missing")

    print("-" * 50)



# Save report as JSON

def save_result_as_json(invoice_id: str, report: dict):
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"{invoice_id.replace('#', '_')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"📄 JSON report saved to: {output_file}")



# Main pipeline

def main():
    PROJECT_ROOT = Path(__file__).resolve().parent
    DATA_PATH = PROJECT_ROOT / "data"

    print(f"📁 Project root : {PROJECT_ROOT}")
    print(f"📁 Data path    : {DATA_PATH}")

    
    # Initialize agents
    
    validator = ValidatorAgent()
    resolver = ResolverAgent(llm_backend="openrouter_free")
    reporter = ReporterAgent(llm_backend="openrouter_free")

    
    # Load invoices
    
    invoices = load_invoices(DATA_PATH / "invoices")
    print(f"\n📂 Extracted {len(invoices)} invoice(s)")

   
    # Run pipeline
   
    for filename, invoice in invoices:
        print(f"\n🔍 VALIDATING: {filename}")

        # Print invoice context
        print_invoice_context(invoice)

        
        # Validation
        
        validation_result = validator.validate_invoice(invoice)

        print("\n🧪 VALIDATION RESULTS")
        for check in validation_result["checks"]:
            icon = (
                "✅" if check["status"] == "PASS"
                else "➖" if check["status"] in ("NA", "REVIEW")
                else "❌"
            )

            details = check["details"] or "OK"
            severity = check.get("severity", "LOW")

            print(
                f"{icon} [{severity}] {check['checkpoint']} "
                f"→ {check['status']} | {details}"
            )

        final_status = validation_result["summary"]["final_status"]
        print(f"\n📌 FINAL VALIDATION STATUS: {final_status}")

        # Resolver (LLM reasoning)
        
        resolver_result = None
        if final_status in ("FAIL", "REVIEW"):
            print("\n🧠 LLM REASONING")
            resolver_result = resolver.resolve(
                invoice_id=filename,
                validation_result=validation_result,
            )
            print(resolver_result.get("llm_reasoning", "No reasoning returned"))

        
        # Reporter (LLM narrative)
        
        report = reporter.generate_report(
            invoice_id=filename,
            validation_result=validation_result,
            resolver_result=resolver_result,
        )

        save_result_as_json(filename, report)

        
        # Print final report
        
        print("\n📊 FINAL REPORT")
        print("-" * 50)
        print(f"Decision           : {report['final_decision']}")
        print(f"Risk Level         : {report['risk_level']}")
        print(f"Summary            : {report['summary']}")
        print(f"Recommended Action : {report['recommended_action']}")
        print(f"Confidence Score   : {report['confidence_score']}")
        print("-" * 50)

    print("\n✅ COMPLIANCE VALIDATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
