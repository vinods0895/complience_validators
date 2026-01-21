from typing import Any
from graph.state import ComplianceState


# -------------------------------------------------
# EXTRACT NODE
# -------------------------------------------------

def extract_node(state: ComplianceState, extractor: Any) -> ComplianceState:
    """
    Extract invoice data only if not already present.
    This prevents re-extraction during batch / API runs.
    """
    if state.invoice is not None:
        return state

    invoices = extractor.run(state.file_path)
    state.invoice = invoices[0]
    return state


# -------------------------------------------------
# VALIDATE NODE
# -------------------------------------------------

def validate_node(state: ComplianceState, validator: Any) -> ComplianceState:
    state.validation = validator.validate_invoice(state.invoice)
    return state


# -------------------------------------------------
# STATEFUL COMPLIANCE NODE
# -------------------------------------------------

def stateful_node(
    state: ComplianceState,
    stateful_engine: Any,
) -> ComplianceState:
    try:
        state.stateful = stateful_engine.run(
            invoice=state.invoice,
            financial_year=state.financial_year,
        )
    except Exception:
        state.stateful = None
    return state


# -------------------------------------------------
# RESOLVER NODE (LLM)
# -------------------------------------------------

def resolver_node(state: ComplianceState, resolver: Any) -> ComplianceState:
    if resolver.should_resolve(state.validation):
        state.resolution = resolver.resolve(
            invoice_id=state.invoice.get("invoice_id"),
            invoice_number=state.invoice.get("invoice_number"),
            validation_result=state.validation,
            stateful_result=state.stateful,
        )
    else:
        state.resolution = {
            "resolution": {
                "violation_type": "NONE",
                "recommended_action": "ACCEPT",
                "confidence": 1.0,
            }
        }

    resolution_data = state.resolution.get("resolution", {})
    state.confidence = resolution_data.get("confidence", 0.0)
    state.route = resolution_data.get("recommended_action")

    return state


# -------------------------------------------------
# ROUTING DECISION
# -------------------------------------------------

def route_decision(state: ComplianceState) -> str:
    if state.route == "REJECT" or state.confidence < 0.70:
        return "human_review"

    if state.confidence < 0.85:
        return "clarification"

    return "auto_approve"


# -------------------------------------------------
# HUMAN REVIEW NODE
# -------------------------------------------------

def human_review_node(
    state: ComplianceState,
    store: Any,
) -> ComplianceState:
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


# -------------------------------------------------
# REPORT NODE
# -------------------------------------------------

def report_node(
    state: ComplianceState,
    reporter: Any,
) -> ComplianceState:
    state.report = reporter.run(
        data=state.invoice,
        validation=state.validation,
        resolution=state.resolution,
        stateful=state.stateful,
        route=state.route,
        confidence=state.confidence,
        human_review_id=state.human_review_id,
    )
    return state
