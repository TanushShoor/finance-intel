// Configurable at build time via VITE_API_BASE; falls back to local dev.
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function uploadDocument(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${BASE}/contracts`, { method: "POST", body: fd });
  return r.json() as Promise<{ id: number; filename: string; status: string }>;
}
export async function analyzeDocument(id: number) {
  await fetch(`${BASE}/contracts/${id}/analyze`, { method: "POST" });
}
export async function getDocument(id: number) {
  const r = await fetch(`${BASE}/contracts/${id}`);
  return r.json();
}
export async function listDocuments() {
  const r = await fetch(`${BASE}/contracts`);
  return r.json();
}
export async function deleteDocument(id: number) {
  await fetch(`${BASE}/contracts/${id}`, { method: "DELETE" });
}
export async function benchmark(contract_ids: number[], metric_names?: string[]) {
  const r = await fetch(`${BASE}/benchmark`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_ids, metric_names }),
  });
  return r.json();
}
export async function compareRisk(prior_id: number, current_id: number) {
  const r = await fetch(`${BASE}/compare/risk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prior_id, current_id }),
  });
  return r.json();
}
