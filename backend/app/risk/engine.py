from typing import Optional
from .models import RiskLevel, RiskResult

# Platform-defined deterministic scoring model
SEVERITY_WEIGHTS = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}

CONFIDENCE_MULTIPLIERS = {
    "low": 0.5,
    "medium": 0.75,
    "high": 1.0
}

def calculate_risk(severity: str, confidence: Optional[str]) -> RiskResult:
    """
    Calculate risk deterministically using a platform-defined scoring model:
    risk_score = severity_weight * confidence_multiplier
    """
    severity_lower = severity.lower() if severity else "info"
    weight = SEVERITY_WEIGHTS.get(severity_lower, 0)
    
    missing_confidence = False
    if not confidence:
        missing_confidence = True
        confidence_str = "medium"
    else:
        confidence_str = confidence.lower()
        if confidence_str not in CONFIDENCE_MULTIPLIERS:
            missing_confidence = True
            confidence_str = "medium"
            
    multiplier = CONFIDENCE_MULTIPLIERS[confidence_str]
    score = weight * multiplier
    
    # Map score to RiskLevel
    if score == 0:
        level = RiskLevel.info
    elif 0 < score <= 1:
        level = RiskLevel.low
    elif 1 < score <= 2:
        level = RiskLevel.medium
    elif 2 < score <= 3:
        level = RiskLevel.high
    else:
        level = RiskLevel.critical
        
    rationale = f"Severity={severity_lower}, confidence={confidence_str}, weighted score={score:.2f}."
    if missing_confidence:
        rationale += " Confidence was not provided; medium confidence was used."
        
    return RiskResult(score=score, level=level, rationale=rationale)
