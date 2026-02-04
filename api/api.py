from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List

from tools.results_store import ResultStore
from tools.human_review_store import HumanReviewStore

app = FastAPI(title="Compliance Agent API")

result_store = ResultStore()
human_review_store = HumanReviewStore()


@app.get("/results/search")
def search_results(
    invoice_number: Optional[str] = None,
    vendor_gstin: Optional[str] = None,
    route: Optional[str] = Query(None, pattern="^(ACCEPT|HUMAN_REVIEW|REJECT)$"),
    max_confidence: Optional[float] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Search invoices with filters for UI.
    """
    results = result_store.filter_results(
        vendor_gstin=vendor_gstin,
        route=route,
        max_confidence=max_confidence,
        limit=limit,
        offset=offset,
    )

    # Optional: exact match by invoice_number on top of filters
    if invoice_number:
        results = [r for r in results if r.get("invoice_number") == invoice_number]

    return {
        "total": len(results),
        "items": results,
    }


@app.get("/results/by-invoice-number/{invoice_number}")
def get_by_invoice_number(invoice_number: str):
    result = result_store.get_by_invoice_number(invoice_number)
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result


@app.get("/human-reviews")
def list_human_reviews(
    status: Optional[str] = Query(None, pattern="^(PENDING|COMPLETED)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items = human_review_store.list_reviews(status=status, limit=limit, offset=offset)
    return {
        "total": len(items),
        "items": items,
    }


@app.get("/human-reviews/{review_id}")
def get_human_review(review_id: str):
    review = human_review_store.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/human-reviews/{review_id}/decision")
def submit_human_decision(review_id: str, payload: dict):
    decision = payload.get("decision")
    comments = payload.get("comments")

    if decision not in ("ACCEPT", "REJECT", "REQUEST_MORE_INFO"):
        raise HTTPException(status_code=400, detail="Invalid decision")

    ok = human_review_store.submit_decision(review_id, decision, comments)
    if not ok:
        raise HTTPException(status_code=404, detail="Review not found")

    return {"success": True}

@app.get("/results/by-invoice-number")
def get_by_invoice_number_query(invoice_number: str):
    result = result_store.get_by_invoice_number(invoice_number)
    if not result:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result