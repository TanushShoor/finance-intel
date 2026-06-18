export type ClauseType =
  | "indemnity" | "limitation_of_liability" | "governing_law" | "termination"
  | "ip_ownership" | "payment_terms" | "confidentiality";

export interface ExtractedClause {
  type: ClauseType; present: boolean; text: string;
  location: string | null; confidence: number;
}
export interface Deviation {
  clause_type: ClauseType; classification: string; rationale: string;
}
export interface ClauseRisk {
  clause_type: ClauseType; category: string; score: number; rationale: string;
}
export interface ExecutiveSummary {
  coverage: string; who_carries_risk: string;
  key_commercial_terms: string[]; top_issues: string[];
}
export interface Analysis {
  clauses: ExtractedClause[]; deviations: Deviation[]; risks: ClauseRisk[];
  overall_risk_score: number; category_breakdown: Record<string, number>;
  summary: ExecutiveSummary;
}
export interface ContractDetail {
  id: number; filename: string; status: string;
  error: string | null; analysis: Analysis | null;
}
