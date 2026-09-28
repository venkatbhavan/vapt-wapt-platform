from app.risk.engine import calculate_risk
from app.risk.models import RiskLevel

def test_risk_calculations():
    # 1. info + high confidence -> info
    res = calculate_risk("info", "high")
    assert res.level == RiskLevel.info
    assert res.score == 0.0

    # 2. low + high confidence -> low
    res = calculate_risk("low", "high")
    assert res.level == RiskLevel.low
    assert res.score == 1.0

    # 3. medium + high confidence -> medium
    res = calculate_risk("medium", "high")
    assert res.level == RiskLevel.medium
    assert res.score == 2.0

    # 4. high + high confidence -> high
    res = calculate_risk("high", "high")
    assert res.level == RiskLevel.high
    assert res.score == 3.0

    # 5. critical + high confidence -> critical
    res = calculate_risk("critical", "high")
    assert res.level == RiskLevel.critical
    assert res.score == 4.0

    # 6. high + medium confidence -> high
    res = calculate_risk("high", "medium")
    assert res.level == RiskLevel.high
    assert res.score == 2.25

    # 7. critical + low confidence -> medium
    res = calculate_risk("critical", "low")
    assert res.level == RiskLevel.medium
    assert res.score == 2.0

    # 8. missing confidence -> medium-confidence behavior
    res = calculate_risk("high", None)
    assert res.level == RiskLevel.high
    assert res.score == 2.25
    
    # 9. rationale is deterministic and contains the right text
    assert "Severity=high, confidence=medium, weighted score=2.25." in res.rationale
    assert "Confidence was not provided; medium confidence was used." in res.rationale

    print("Risk engine tests passed successfully!")

if __name__ == "__main__":
    test_risk_calculations()
