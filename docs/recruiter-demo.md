# Recruiter Demo Mode

## 1. Purpose
The Recruiter Demo mode is designed to safely showcase the VAPT/WAPT Security Platform capabilities to non-technical and technical audiences without exposing actual security scanners to the public internet, avoiding SSRF and network abuse risks.

## 2. Architecture
The demo leverages the existing React frontend and FastAPI backend by placing the application into a globally enforced `DEMO_MODE=true` state. This prevents all `POST`, `PUT`, and `DELETE` requests at the ASGI middleware level, converting the platform into a read-only viewer for seeded assessment data.

## 3. Demo Security Boundary
- **State Mutation Blocked:** A global HTTP middleware intercepts and denies all mutating actions.
- **Scanner Execution Disabled:** By blocking the `POST /scan-jobs` endpoint, the `subprocess` integration to Nmap and the API calls to OWASP ZAP are blocked from the public request path.
- **AI Analyst (Deterministic):** The AI analysis endpoint remains active but the backend Provider intercepts the call to utilize `MockAIProvider`, delivering deterministic responses and neutralizing API token leaks.

## 4. Data Model
The demo relies on standard platform data (`sql_app.db`) generated securely on a local developer machine using `seed_test_data.py`. No synthetic "demo-only" models are created. 

## 5. Disabled Operations
- **New Scans / Scopes:** Cannot launch active/deep/stealth scans.
- **Target Modification:** Cannot insert custom IP targets.
- **Finding Lifecycle:** Cannot close or alter vulnerability states.
- **Retesting:** Cannot trigger scanner-based revalidation.
- **Report Shares:** Cannot generate new temporary share links.

## 6. Scanner Isolation
The public deployment environment does not have Nmap or ZAP containers provisioned. Even if the HTTP boundary were bypassed, the actual network scanning workers are absent from the demo's cloud architecture.

## 7. AI Behavior
In demo mode, the AI component returns an explicit `[DEMO MODE]` summary and deterministic findings. This proves the integration logic without relying on expensive, open-ended LLM usage.

## 8. Deployment Model
- **Frontend:** Vercel (Static export).
- **Backend:** Read-only FastAPI service (Render/Railway).
- **Database:** Immutable SQLite database containing the seeded Juice Shop dataset.

## 9. Limitations
Demo mode cannot demonstrate real-time vulnerability discovery. It acts purely as a retrospective dashboard showing the state *after* an assessment has been finalized.

## 10. Future Production Architecture
Real production deployment requires a distributed queue (Celery/Redis), egress-firewalled dedicated workers, and PostgreSQL. The demo bypasses these requirements for portfolio simplicity.
