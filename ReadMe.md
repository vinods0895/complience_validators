Overview

This project validates vendor invoices against compliance, GST, and internal company policies using a rule-first, AI-assisted architecture.

1.Architecture (High Level)

Invoice JSON
    ↓
ValidatorAgent (Rules)
    ↓
PASS ─────────► Final Report
    ↓
REVIEW / FAIL
    ↓
ResolverAgent (LLM reasoning)
    ↓
ReporterAgent (LLM narrative + safety)


2.Key Components

2.1-ValidatorAgent

-Deterministic rule engine
-Performs structural, arithmetic, GST, HSN/SAC, and policy checks
-Never uses LLMs
-Missing data → REVIEW, not FAIL

2.2-ResolverAgent
-Runs only for REVIEW or FAIL
-Uses LLM to explain validation outcomes
-Does not change decisions

2.3-ReporterAgent
-Generates final audit-friendly report
-Safely handles invalid LLM output
-Always returns valid structured JSON

Mock APIs

GSTIN Validation-POST http://127.0.0.1:5000/api/gst/validate-gstin
HSN / SAC Validation-POST http://127.0.0.1:5000/api/gst/validate-hsn
GST Rate Lookup-POST http://127.0.0.1:5000/api/gst/rate-schedule
Company Policy Check-POST http://127.0.0.1:5000/api/policy/check
