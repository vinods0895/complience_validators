from typing import Any
from graph.state import ComplianceState


  
# EXTRACT NODE
  

def extract_node(state: ComplianceState, extractor: Any) -> ComplianceState:
    if state.invoice is None:
        invoices = extractor.run(state.file_path)
        state.invoice = invoices[0]
    return state


  
# VALIDATE NODE (DETERMINISTIC)
  

def validate_node(state: ComplianceState, validator: Any) -> ComplianceState:
    state.validation = validator.validate_invoice(state.invoice)
    return state


  
# STATEFUL COMPLIANCE NODE
  

def stateful_node(state: ComplianceState, stateful_engine: Any) -> ComplianceState:
    try:
        state.stateful = stateful_engine.run(
            invoice=state.invoice,
            financial_year=state.financial_year,
        )
    except Exception:
        state.stateful = None
    return state


  
# RESOLVER NODE (LLM = REASONING ONLY)
  
def resolver_node(state: ComplianceState, resolver: Any) -> ComplianceState:
    final_status = state.validation.get("summary", {}).get("final_status")

    if final_status in ("FAIL", "REVIEW"):
        result = resolver.resolve(
            invoice_id=state.invoice.get("invoice_id"),
            invoice_number=state.invoice.get("invoice_number"),
            validation_result=state.validation,
        )

        # ✅ Extract only inner resolution payload
        state.resolution = result.get("resolution", {})
        state.confidence = result.get("confidence", 0.3)

    else:
        state.resolution = {
            "violation_type": "NONE",
            "recommended_action": "ACCEPT",
            "confidence": 1.0,
            "missing_fields": [],
            "reasoning": "No compliance issues detected.",
            "actions_required": [],
        }
        state.confidence = 1.0

    # 🚦 ROUTING (you control this — not LLM)
    if final_status == "FAIL":
        state.route = "REJECT"
    elif final_status == "REVIEW":
        state.route = "REQUEST_CLARIFICATION"
    else:
        state.route = "ACCEPT"

    return state
# ROUTING DECISION FOR LANGGRAPH
  

def route_decision(state: ComplianceState) -> str:
    if state.route == "REJECT":
        return "human_review"

    if state.route == "REQUEST_CLARIFICATION":
        return "clarification"

    return "auto_approve"


  
# HUMAN REVIEW NODE
  

def human_review_node(state: ComplianceState, store: Any) -> ComplianceState:
    review_id = store.create_review(
        invoice_id=state.invoice.get("invoice_id"),
        invoice_number=state.invoice.get("invoice_number"),
        confidence=state.confidence,
        validation=state.validation,
        resolution=state.resolution,
        stateful=state.stateful,
    )
    state.human_review_id = review_id
    return state


  
# REPORT NODE (PURE FORMAT + EXPLAIN)
  

def report_node(state: ComplianceState, reporter: Any) -> ComplianceState:
    state.report = reporter.run(
        data=state.invoice,
        validation=state.validation,
        resolution_wrapper=state.resolution,  # ✅ correct
        stateful=state.stateful,
        human_review_id=state.human_review_id,
    )
    return state
