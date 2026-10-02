export type RetestStatus = 'requested' | 'running' | 'completed' | 'failed';
export type RetestResultStatus = 'fixed' | 'still_present' | 'changed' | 'inconclusive';
export type RetestConfidence = 'low' | 'medium' | 'high';

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
