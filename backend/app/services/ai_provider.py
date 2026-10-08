from abc import ABC, abstractmethod
from typing import Dict, Any
from app.schemas.ai_analyst import AIAnalystResponse, EvidenceReference

class AIProvider(ABC):
    @abstractmethod
    def analyze(self, context: Dict[str, Any], instructions: str) -> AIAnalystResponse:
        pass

class MockAIProvider(AIProvider):
    """
    A mock provider for testing and environments without configured LLMs.
    It returns a deterministic response based on the context.
    """
    def analyze(self, context: Dict[str, Any], instructions: str) -> AIAnalystResponse:
        finding_count = len(context.get("findings", []))
        posture = context.get("posture")
        posture_level = posture.get("level", "unknown") if posture else "unknown"
        
        return AIAnalystResponse(
            assessment_id=context["assessment_id"],
            analyst_version="mock-1.0",
            summary=f"[DEMO MODE] This is a deterministic mock AI analysis. A real LLM was not invoked to save costs/API keys in the public demo. Assessment {context['assessment_id']} has {finding_count} findings and posture level {posture_level}.",
            key_observations=[f"Observed {finding_count} active findings."],
            risk_priorities=["Fix critical vulnerabilities first."] if finding_count > 0 else ["No immediate risk priorities."],
            correlations=["Findings correlate with exposed attack surface." if context.get("attack_surface", {}).get("services") else "No direct attack surface correlations observed."],
            recommendations=["Review open findings and apply remediation."],
            uncertainties=["Mock provider cannot fully infer vulnerability depth."],
            evidence_references=[
                EvidenceReference(entity_type="finding", entity_id=f["id"]) for f in context.get("findings", [])[:1]
            ]
        )
