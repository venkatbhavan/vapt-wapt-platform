# AI Security Analyst

## Purpose
The AI Security Analyst provides an explanation, correlation, prioritization, and recommendation layer over the existing platform evidence. It acts exclusively as an *analyst*, meaning it helps human operators understand the findings but does not replace the deterministic tools (like Nmap, ZAP) or existing risk scoring methodologies.

## Architecture
The foundation utilizes a strictly evidence-driven context pipeline:
1. **Evidence Gathering:** The `ai_context_engine.py` securely aggregates finding metadata, attack surface data, compliance mappings, and remediation guidance restricted exactly to a specific assessment.
2. **Deterministic Context Bounds:** Evidence is explicitly sorted and capped (e.g., top 50 active findings by risk score) to prevent context exhaustion and hallucination.
3. **Provider Abstraction:** Evaluated via an `AIProvider` base class interface, allowing the backend to plug in LLM models smoothly while using a `MockAIProvider` for test isolation.
4. **Structured JSON Responses:** Outputs strictly validate against `AIAnalystResponse` Pydantic models containing explicit observation blocks and tracing fields.

## Assessment Isolation and Read-Only Guarantees
- The context builder forces `assessment_id` filters on all queries, guaranteeing zero cross-assessment data leakage.
- Execution occurs across standard `.query()` SQLAlchemy lookups.
- The analyst cannot `.add()`, `.commit()`, or delete data. It is entirely read-only.
- It cannot invoke subprocesses or execute scanners.

## Sanitization
Before passing evidence into the AI context window, a basic regex-based deterministic `sanitize_dict` algorithm attempts to scrub common sensitive field leakage (such as `Authorization: Bearer` tokens and AWS access keys).
**Limitation Note:** This sanitizer is naive and based on regex pattern matching; it will not reliably detect all application-specific secrets or environment variables.

## Handling Inferences, Recommendations, and Uncertainty
The AI Analyst distinguishes strictly between facts it has `observed` via evidence and `correlations/recommendations` it is inferring. The response schema enforces an `uncertainties` block, demanding the model explicitly highlight areas where evidence is insufficient, preventing unsupported claims and uncontrolled hallucination.
