export interface RemediationMappingFinding {
  id: number;
  title: string;
  severity: string;
  status: string;
  normalized_type: string | null;
}

export interface RemediationMappingDetail {
  id: number;
  finding: RemediationMappingFinding;
  mapping_confidence: string;
  rationale: string;
}

export interface RemediationGuidanceWithMappings {
  id: number;
  title: string;
  summary: string;
  detailed_guidance: string;
  remediation_type: string;
  priority: string;
  verification_guidance: string;
  mappings: RemediationMappingDetail[];
}

export interface AssessmentRemediationResponse {
  assessment_id: number;
  remediations: RemediationGuidanceWithMappings[];
}
