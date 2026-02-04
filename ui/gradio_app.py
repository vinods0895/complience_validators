import gradio as gr
import requests
from typing import List, Dict, Any, Optional

API_BASE = "http://127.0.0.1:8000"


def search_invoices(
    invoice_number: Optional[str],
    vendor_gstin: Optional[str],
    route: Optional[str],
    max_confidence: float,
    limit: int,
):
    params = {
        "invoice_number": invoice_number or None,
        "vendor_gstin": vendor_gstin or None,
        "route": route or None,
        "max_confidence": max_confidence,
        "limit": limit,
        "offset": 0,
    }

    resp = requests.get(f"{API_BASE}/results/search", params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])

    rows = []
    for r in items:
        rows.append([
            r.get("invoice_number"),
            r.get("vendor_gstin"),
            r.get("route"),
            r.get("confidence"),
            r.get("generated_at"),
        ])

    return rows, items


def get_invoice_details(invoice_number: str) -> Dict[str, Any]:
    if not invoice_number:
        return {}

    resp = requests.get(
        f"{API_BASE}/results/by-invoice-number",
        params={"invoice_number": invoice_number},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def format_invoice_details(data: Dict[str, Any]) -> str:
    if not data:
        return "⬅️ Select an invoice row to see details."

    resolution = data.get("resolution", {})

    reasoning = resolution.get("reasoning", "No reasoning available.")
    missing_fields = resolution.get("missing_fields", [])
    actions = resolution.get("actions_required", [])

    text = f"""
## 🧾 Invoice Details

**Invoice Number:** {data.get("invoice_number")}  
**Route:** {data.get("route")}  
**Confidence:** {data.get("confidence")}  

---

## 🧠 LLM Reasoning
{reasoning}

---

## ❌ Missing Fields
"""

    if missing_fields:
        for f in missing_fields:
            text += f"- {f}\n"
    else:
        text += "None\n"

    text += "\n---\n## ✅ Actions Required\n"

    if actions:
        for a in actions:
            text += f"- {a}\n"
    else:
        text += "No actions required.\n"

    return text


def on_row_select(evt: gr.SelectData, items: List[Dict[str, Any]]) -> str:
    if evt is None or not items:
        return "⬅️ Select an invoice row to see details."

    row_index = evt.index[0]
    selected = items[row_index]

    invoice_number = selected.get("invoice_number")
    if not invoice_number:
        return "Invalid row selection."

    details = get_invoice_details(invoice_number)
    return format_invoice_details(details)


with gr.Blocks(title="Agentic Compliance Dashboard") as demo:
    gr.Markdown("# 🧾 Agentic Compliance Dashboard")

    with gr.Tab("🔎 Search Invoices"):
        with gr.Row():
            invoice_number = gr.Textbox(label="Invoice Number")
            vendor_gstin = gr.Textbox(label="Vendor GSTIN")
            route = gr.Dropdown(choices=["", "ACCEPT", "HUMAN_REVIEW", "REJECT"], value="", label="Route")
            max_confidence = gr.Slider(0.0, 1.0, value=1.0, label="Max Confidence")
            limit = gr.Slider(1, 50, value=20, step=1, label="Limit")

        search_btn = gr.Button("Search")

        results_table = gr.Dataframe(
            headers=["Invoice Number", "Vendor GSTIN", "Route", "Confidence", "Generated At"],
            interactive=True,
            wrap=True,
        )

        raw_items = gr.State([])

        invoice_details = gr.Markdown(
            value="⬅️ Select an invoice row to see details",
            label="Invoice Details",
        )

        search_btn.click(
            fn=search_invoices,
            inputs=[invoice_number, vendor_gstin, route, max_confidence, limit],
            outputs=[results_table, raw_items],
        )

        results_table.select(
            on_row_select,
            inputs=[raw_items],
            outputs=invoice_details,
        )

    gr.Markdown("— Powered by your Agentic Compliance System 🚀")

demo.launch(server_name="127.0.0.1", server_port=7860)
