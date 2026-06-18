export function RiskGauge({ score }: { score: number }) {
  const color = score >= 67 ? "text-red-600" : score >= 34 ? "text-amber-500" : "text-green-600";
  const label = score >= 67 ? "High" : score >= 34 ? "Medium" : "Low";
  return (
    <div className="flex flex-col items-center p-4 rounded-xl border">
      <div className={`text-5xl font-bold ${color}`}>{score}</div>
      <div className="text-sm text-gray-500">Overall risk · {label}</div>
    </div>
  );
}
