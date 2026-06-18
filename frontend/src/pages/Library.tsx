import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { uploadContract, analyzeContract, listContracts } from "../api/client";

export function Library() {
  const [rows, setRows] = useState<any[]>([]);
  const refresh = () => listContracts().then(setRows);
  useEffect(() => { refresh(); const t = setInterval(refresh, 2000); return () => clearInterval(t); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return;
    const { id } = await uploadContract(file);
    await analyzeContract(id); refresh();
  }
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Contract Library</h1>
      <input type="file" accept=".pdf,.docx" onChange={onUpload} />
      <ul className="divide-y border rounded-xl">
        {rows.map(r => (
          <li key={r.id} className="flex justify-between p-3">
            <Link className="text-blue-600" to={`/contracts/${r.id}`}>{r.filename}</Link>
            <span className="text-sm text-gray-500">{r.status}
              {r.overall_risk_score != null && ` · risk ${r.overall_risk_score}`}</span>
          </li>
        ))}
      </ul>
      <Link to="/compare" className="inline-block text-blue-600">→ Batch compare</Link>
    </div>
  );
}
