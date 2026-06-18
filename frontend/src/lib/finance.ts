export const METRIC_LABELS: Record<string, string> = {
  revenue: "Revenue",
  gross_margin: "Gross margin",
  operating_income: "Operating income",
  operating_margin: "Operating margin",
  net_income: "Net income",
  eps: "EPS",
  ebitda: "EBITDA",
  free_cash_flow: "Free cash flow",
  capex: "Capex",
  total_debt: "Total debt",
  cash_and_equivalents: "Cash & equivalents",
  guidance_revenue: "Revenue guidance",
};

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function metricLabel(name: string): string {
  return METRIC_LABELS[name] ?? titleCase(name);
}

export const SENTIMENT: Record<string, { color: string; label: string }> = {
  confident: { color: "#1E7A66", label: "Confident" },
  cautious: { color: "#B23322", label: "Cautious" },
  neutral: { color: "#59636E", label: "Neutral" },
  mixed: { color: "#B5791A", label: "Mixed" },
};

export const RISK_STATUS: Record<string, { color: string; label: string }> = {
  new: { color: "#B23322", label: "New" },
  escalated: { color: "#B5791A", label: "Escalated" },
  unchanged: { color: "#59636E", label: "Unchanged" },
  removed: { color: "#9AA3AB", label: "Removed" },
};

/** Severity (0–100) → token colour. */
export function severityColor(s: number): string {
  if (s >= 67) return "#B23322";
  if (s >= 34) return "#B5791A";
  return "#1E7A66";
}

/** Coarse pipeline stage → human label for the progress view. */
export const STAGE_LABELS: Record<string, string> = {
  structuring: "Reconstructing document",
  identifying: "Identifying company & period",
  metrics: "Extracting financial metrics",
  tone: "Analysing management tone",
  risk_factors: "Extracting risk factors",
  memo: "Writing investment memo",
};
