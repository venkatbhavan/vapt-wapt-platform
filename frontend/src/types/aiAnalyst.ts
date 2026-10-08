export interface EvidenceReference {
  entity_type: string;
  entity_id: number;
}

export interface AIAnalystResponse {
  assessment_id: number;
  analyst_version: string;
  summary: string;
  key_observations: string[];
  risk_priorities: string[];
  correlations: string[];
  recommendations: string[];
  uncertainties: string[];
  evidence_references: EvidenceReference[];
}

export interface APIAnalystRequest {
  question: string;
  analysis_type?: string;
}
