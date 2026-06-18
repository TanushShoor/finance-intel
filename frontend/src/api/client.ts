const BASE = "http://localhost:8000";

export async function uploadContract(file: File) {
  const fd = new FormData(); fd.append("file", file);
  const r = await fetch(`${BASE}/contracts`, { method: "POST", body: fd });
  return r.json() as Promise<{ id: number; filename: string; status: string }>;
}
export async function analyzeContract(id: number) {
  await fetch(`${BASE}/contracts/${id}/analyze`, { method: "POST" });
}
export async function getContract(id: number) {
  const r = await fetch(`${BASE}/contracts/${id}`);
  return r.json();
}
export async function listContracts() {
  const r = await fetch(`${BASE}/contracts`);
  return r.json();
}
export async function compareClause(contract_ids: number[], clause_type: string) {
  const r = await fetch(`${BASE}/compare`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_ids, clause_type }) });
  return r.json();
}
export async function getBaseline() { return (await fetch(`${BASE}/baseline`)).json(); }
