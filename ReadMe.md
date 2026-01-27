

## Overview

This  **validation workflow** that combines **deterministic rule-based checks** with **LLM-powered reasoning and explainability**, while explicitly keeping a **Human-in-the-Loop (HITL)** for risky or uncertain cases.

**Core principle:**

> **Rules decide facts. Humans decide outcomes. LLMs explain and assist.**

---

## What This System Does

1. Reads invoice data (JSON)
2. Runs deterministic GST / TDS / arithmetic / policy validations
3. Applies historical (stateful) compliance checks
4. Uses an LLM to reason about validation failures
5. Assigns an explainable confidence score
6. Routes invoices automatically or to human review
7. Generates a human-readable audit explanation

---

## High-Level Workflow

```
Invoice
  ↓
ExtractorAgent
  ↓
ValidatorAgent (deterministic rules)
  ↓
StatefulComplianceEngine
  ↓
ResolverAgent (LLM reasoning + confidence)
  ↓
Routing Decision
  ├─ ACCEPT → Auto-approve
  ├─ REVIEW → Human clarification
  └─ FAIL   → Human review / rejection
  ↓
ReporterAgent (LLM audit explanation)
```

---

## Human-in-the-Loop (HITL)

This workflow **explicitly keeps humans in the decision loop**.

* **PASS** invoices are auto-approved
* **REVIEW** invoices are routed for human clarification
* **FAIL** invoices are routed for human review or rejection

Key characteristics:

* Routing is controlled by **deterministic validation**, not by LLM output
* A dedicated **human review node** persists invoice data, validation results, and LLM reasoning
* LLMs never approve, reject, or override compliance decisions

This ensures audit safety, accountability, and regulatory compliance.

---

## Core Components

### Agents

* **ExtractorAgent** – Loads and normalizes invoice data
* **ValidatorAgent** – Deterministic GST/TDS/policy checks (no LLM)
* **StatefulComplianceEngine** – Cross-invoice and historical compliance rules
* **ResolverAgent** – LLM-based reasoning and confidence scoring
* **ReporterAgent** – LLM-based human-readable audit report

### Workflow & Routing

* **LangGraph** orchestrates the workflow
* Routing decisions are based on validation status (PASS / REVIEW / FAIL)
* LLMs are used only after facts are established

### LLM Strategy

* Runs locally via **Ollama**
* Default model: **DeepSeek-R1**
* LLMs are optional, guarded, and safely fail without breaking the pipeline




### 1. (Optional) Check LLM Health

```bash
python models_health_check.py
```

### 2. Run the Pipeline

```bash
python main.py
```

---

## Sample Output

```
Invoice: TS/MH/2024/001234
Route: REQUEST_CLARIFICATION
Confidence: 0.42
Reason: GSTIN missing and subtotal mismatch
LLM Summary: Invoice requires vendor clarification due to GST issues.
```

---

## Why This Design Works

* Deterministic and auditable compliance checks
* Explicit Human-in-the-Loop for risk control
* LLMs constrained to reasoning and explanation
* Clear separation of responsibilities
* Enterprise-safe and easy to extend

---



> **A compliance engine that combines strict rule validation, explicit human oversight, and LLM-powered explainability for audit-safe decision making.**



Mock APIs

GSTIN Validation-POST http://127.0.0.1:5000/api/gst/validate-gstin
HSN / SAC Validation-POST http://127.0.0.1:5000/api/gst/validate-hsn
GST Rate Lookup-POST http://127.0.0.1:5000/api/gst/rate-schedule
Company Policy Check-POST http://127.0.0.1:5000/api/policy/check
