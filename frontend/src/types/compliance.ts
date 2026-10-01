export type MappingType = "direct" | "related";
export type MappingConfidence = "low" | "medium" | "high";

export interface ComplianceMapping {
  id: number;
  finding_id: number;
  finding_title: string;
  finding_severity: string;
  finding_status: string;
  mapping_type: MappingType;
  mapping_confidence: MappingConfidence;
  rationale: string | null;
  source: string;
}

export interface ComplianceControl {
  id: number;
  control_id: string;
  title: string;
  description: string | null;
  mappings: ComplianceMapping[];
}

export interface ComplianceFramework {
  id: number;
  name: string;
  version: string | null;
  description: string | null;
  controls: ComplianceControl[];
}

export interface ComplianceAssessment {
  assessment_id: number;
  frameworks: ComplianceFramework[];
}
