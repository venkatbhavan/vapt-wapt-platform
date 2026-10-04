export type RetestStatus = 'requested' | 'running' | 'completed' | 'failed';
export type RetestResultStatus = 'fixed' | 'still_present' | 'changed' | 'inconclusive';
export type RetestConfidence = 'low' | 'medium' | 'high';

export interface Evidence {
    id: number;
    finding_id?: number | null;
    retest_result_id?: number | null;
    evidence_type: string;
    title: string | null;
    content: string | null;
    source: string | null;
    created_at: string;
}

export interface RetestResult {
    id: number;
    retest_request_id: number;
    result: RetestResultStatus;
    confidence: RetestConfidence;
    rationale: string;
    previous_finding_id: number;
    current_finding_id: number | null;
    created_at: string;
    updated_at: string;
    evidence: Evidence[];
}

export interface RetestRequest {
    id: number;
    finding_id: number;
    status: RetestStatus;
    requested_at: string;
    started_at: string | null;
    completed_at: string | null;
    created_at: string;
    updated_at: string;
    result: RetestResult | null;
}
