
# 🧾 Agentic Compliance Validator (LLM + LangGraph + FastAPI + Gradio)

An end-to-end **Agentic AI system** for automated invoice compliance validation with **human-in-the-loop review**, powered by **LangGraph**, **LLMs (Ollama)**, **FastAPI APIs**, and a **Gradio UI**.

This project simulates a real-world enterprise workflow:
- Extract invoice data  
- Validate GST / TDS / financial rules  
- Apply historical (stateful) compliance checks  
- Use LLMs for reasoning and remediation suggestions  
- Route to human review when needed  
- Expose results via API  
- Visualize and manage via UI  

---

## ✨ Features

- 🧠 **Agentic Workflow (LangGraph)**
  - Extractor Agent  
  - Validator Agent  
  - Stateful Compliance Agent  
  - Resolver Agent (LLM-powered reasoning)  
  - Human Review Agent  
  - Reporter Agent  

- 🔍 **Deterministic + LLM Hybrid Validation**
  - Rules decide pass/fail  
  - LLM explains failures & suggests actions  

- 🧑‍⚖️ **Human-in-the-Loop**
  - Fails / reviews are routed for manual decision  
  - Decisions are persisted for audit  

- 🌐 **FastAPI Backend**
  - Search invoices  
  - Fetch invoice details  
  - List human review queue  
  - Submit human decisions  

- 🖥️ **Gradio UI**
  - Search invoices  
  - View LLM reasoning  
  - View missing fields & actions  
  - Human review queue  

- 🛡️ **Production Safety**
  - Robust JSON parsing from LLM  
  - Fallback resolution if LLM fails  
  - Confidence normalization  
  - Audit-safe storage  

---

## 🏗️ Architecture Overview

Invoices (JSON)
│
▼
Extractor Agent
│
▼
Validator Agent (Rules)
│
▼
Stateful Compliance Agent
│
▼
Resolver Agent (LLM reasoning)
│
├── ACCEPT ──────► Reporter Agent ───► Result Store
│
└── HUMAN_REVIEW ─► Human Review Store ─► API/UI

Mock APIs

GSTIN Validation-POST http://127.0.0.1:5000/api/gst/validate-gstin
HSN / SAC Validation-POST http://127.0.0.1:5000/api/gst/validate-hsn
GST Rate Lookup-POST http://127.0.0.1:5000/api/gst/rate-schedule
Company Policy Check-POST http://127.0.0.1:5000/api/policy/check

Step 1: Run Agentic Pipeline
uv run python main.py

Step 2: Start FastAPI Backend
uv run uvicorn api.api:app --reload --port 8000

Step 3: Start Gradio UI
uv run python ui/gradio_app.py

## 🧪 Why This Project Is Valuable

This is not a toy chatbot.  
This simulates **real enterprise AI architecture**:

- Rule-based validation  
- LLM reasoning  
- Agent orchestration  
- HITL workflows  
- APIs  
- UI  
- Persistent state  
- Robust error handling  


