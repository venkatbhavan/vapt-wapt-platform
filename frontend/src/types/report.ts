export interface ReportMetadata {
  id: number;
  assessment_id: number;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  generated_at: string | null;
}

export interface ReportAssessmentScope {
  id: number;
  name: string;
  target: string;
  scope: string;
  status: string;
}

export interface ExecutiveSummary {
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  informational_findings: number;
  total_assets: number;
  total_network_services: number;
  total_web_applications: number;
  total_endpoints: number;
  total_retests: number;
  fixed_findings: number;
  still_present_findings: number;
  changed_findings: number;
  inconclusive_retests: number;
}

export interface RiskSummary {
  severity_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  risk_level_distribution: Record<string, number>;
}

export interface AttackSurfaceSummary {
  asset_types: Record<string, number>;
  service_protocols: Record<string, number>;
  service_states: Record<string, number>;
  web_application_schemes: Record<string, number>;
}

export interface FindingsSummary {
  status_distribution: Record<string, number>;
  normalized_category_distribution: Record<string, number>;
  normalized_type_distribution: Record<string, number>;
  scanner_source_distribution: Record<string, number>;
}

export interface ComplianceSummary {
  frameworks_represented: number;
  controls_represented: number;
  mapped_finding_count: number;
  mappings_by_framework: Record<string, number>;
}

export interface RemediationSummary {
  findings_with_remediation: number;
  remediation_guidance_count: number;
  priority_distribution: Record<string, number>;
  remediation_type_distribution: Record<string, number>;
}

export interface RetestingSummary {
  total_requests: number;
  completed: number;
  failed: number;
  requested_running: number;
}

export interface TechnicalFinding {
  id: number;
  title: string;
  severity: string;
  confidence: string;
  risk_score: number;
  risk_level: string;
  status: string;
  normalized_category: string;
  normalized_type: string;
  root_cause: string;
  exploitability_context: string;
  evidence_quality: string;
  location: string | null;
  scanner_sources: string[];
  compliance_controls: string[];
  remediation_guidances: string[];
  retest_history: string[];
}

export interface ReportDataset {
  scope: ReportAssessmentScope;
  executive_summary: ExecutiveSummary;
  risk_summary: RiskSummary;
  attack_surface_summary: AttackSurfaceSummary;
  findings_summary: FindingsSummary;
  compliance_summary: ComplianceSummary;
  remediation_summary: RemediationSummary;
  retesting_summary: RetestingSummary;
  technical_findings: TechnicalFinding[];
}