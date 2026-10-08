# Security Posture Methodology

## 1. What is Security Posture?
Security Posture is an explainable aggregation of the security evidence available for a specific assessment. It provides a high-level view of an environment's security state based on findings, attack surface exposure, remediation progress, and retesting health.

## 2. Difference Between Finding Risk and Assessment Posture
- **Finding Risk:** The risk represented by a single vulnerability (calculated deterministically based on severity and confidence).
- **Assessment Posture:** The aggregated security state of the entire environment, accounting for all findings, how they are managed (remediation/retesting), and the attack surface exposure. Posture consumes finding risk rather than redefining it.

## 3. Dimensions
The posture score is calculated across five dimensions:
1. **Finding Risk:** Active (open) findings present in the environment.
2. **Finding Health (Retesting):** Penalty for findings that remain present after being formally retested.
3. **Attack Surface:** Penalty for exposing risky network services (e.g., Telnet, FTP).
4. **Remediation Health:** Penalty for high/critical findings lacking actionable remediation guidance.
5. **Compliance Signal:** Penalty for open findings that violate mapped regulatory compliance controls.

## 4. Scoring Methodology
- **Base Score:** 100
- **Deductions:** Deterministic penalties are subtracted based on the evidence in the dimensions above.
- **Boundaries:** The score is strictly bounded between `0` and `100`.
- **Formula:** `Score = max(0, min(100, 100 - Total_Penalties))`

## 5. Weighting Principles
- **Critical findings** penalize the score significantly more than High findings.
- **Confidence** acts as a multiplier (High=1.0, Med=0.75, Low=0.5) embedded in the underlying `risk_score`.
- Penalty scales exponentially to prevent score flooding by low-severity findings.
  - Calculation: `penalty = round(finding.risk_score ^ 2.5, 2)`
  - Example: A single Critical (score 4.0) results in a 32-point penalty. A single Low (score 1.0) results in a 1-point penalty.

## 6. Posture Bands
- **STRONG (90 - 100):** Excellent security posture. (Allows ~1 High or a few Medium findings).
- **GOOD (70 - 89):** Solid security posture. (Allows ~1 Critical or 2 High findings).
- **MODERATE (50 - 69):** Average security posture. (Allows ~1 Critical and 1 High finding).
- **WEAK (25 - 49):** Poor security posture requiring immediate attention.
- **CRITICAL (0 - 24):** Severely compromised posture.

## 7. Handling of Confidence
Confidence is handled at the finding risk layer. A low-confidence critical finding will result in a lower `risk_score` (e.g., 2.0 instead of 4.0), translating to a significantly smaller posture penalty (5.66 instead of 32).

## 8. Handling of Retesting
- **Fixed:** Findings marked as fixed/resolved are naturally excluded from active finding risk.
- **Still Present:** If a finding is retested and confirmed "still present", an additional -5 point penalty is applied for failing to remediate.
- **Inconclusive:** Treated as still open, retaining its standard risk penalty.

## 9. Handling of Remediation
High or Critical findings that lack any remediation guidance or text receive an additional -3 point penalty, reflecting poor remediation health.

## 10. Handling of Attack Surface
The platform evaluates the network services. Only services explicitly identified as risky and in an "open" state (e.g., Telnet, FTP, SMB) penalize the score (-2 points each). A large attack surface does not inherently reduce the score unless risky exposure is proven.

## 11. Compliance's Role
Compliance is a supporting signal. An open finding mapped to a compliance control applies a minor additional penalty (-1 point) to reflect the added regulatory risk. Compliance alone does not guarantee security.

## 12. No-Data / Coverage Limitations
If an assessment has no findings, it is not automatically granted a perfect score of 100.
- If no findings exist, the engine returns `level="NO_DATA"` and `score=None`.
- The `coverage_status` indicates whether assets were present (`limited` coverage) or not (`unknown` coverage).

## 13. Methodology Versioning
Current version: `1.0`. All persisted posture results (if implemented) will tag this version to ensure historical scores remain explainable if the algorithm changes in the future.

## 14. Examples
- **Scenario A:** 1 Critical Finding (High Conf)
  - Finding Risk: -32
  - Score: 68 (MODERATE)
- **Scenario B:** 10 Low Findings
  - Finding Risk: -10 (10 * 1.0)
  - Score: 90 (STRONG)
- **Scenario C:** 1 Medium Finding, but still present after retest
  - Finding Risk: -5.66
  - Finding Health: -5.0
  - Score: 89 (GOOD)
