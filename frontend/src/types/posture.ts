export type PostureLevel = 'strong' | 'good' | 'moderate' | 'weak' | 'critical' | 'no_data';
export type CoverageStatus = 'sufficient' | 'limited' | 'unknown';

export interface PostureContributor {
  category: string;
  reason: string;
  impact: number;
  count: number;
  related_finding_ids: number[];
}

export interface PostureDimensions {
  finding_risk: number;
  finding_health: number;
  attack_surface: number;
  remediation: number;
  compliance: number;
}

export interface PostureResult {
  assessment_id: number;
  score: number | null;
  level: PostureLevel;
  coverage_status: CoverageStatus;
  methodology_version: string;
  dimensions: PostureDimensions;
  contributors: PostureContributor[];
  generated_at: string;
}
