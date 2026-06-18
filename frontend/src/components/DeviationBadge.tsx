const STYLES: Record<string, string> = {
  favourable: "bg-green-100 text-green-800",
  standard: "bg-gray-100 text-gray-700",
  unusual: "bg-amber-100 text-amber-800",
  unfavourable: "bg-red-100 text-red-800",
};
export function DeviationBadge({ classification }: { classification?: string }) {
  if (!classification) return null;
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${STYLES[classification] ?? ""}`}>
    {classification}</span>;
}
