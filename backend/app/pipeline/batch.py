from app.schemas.models import BatchComparison, BatchCell
from app.clause_types import ClauseType
from app.llm.prompts import BATCH_PROMPT


def build_batch_comparison(stored: list[dict], clause_type: ClauseType, llm) -> BatchComparison:
    cells: list[BatchCell] = []
    for item in stored:
        analysis = item.get("analysis") or {}
        clause = next((c for c in analysis.get("clauses", [])
                       if c["type"] == clause_type.value), None)
        dev = next((d for d in analysis.get("deviations", [])
                    if d["clause_type"] == clause_type.value), None)
        risk = next((r for r in analysis.get("risks", [])
                     if r["clause_type"] == clause_type.value), None)
        cells.append(BatchCell(
            contract_id=item["id"], contract_name=item["name"],
            present=bool(clause and clause.get("present")),
            text=(clause or {}).get("text", ""),
            classification=(dev or {}).get("classification"),
            risk_score=(risk or {}).get("score")))

    cell_text = "\n\n".join(f"{c.contract_name}: {c.text or '(not present)'}" for c in cells)
    prompt = BATCH_PROMPT.format(clause_type=clause_type.value, cells=cell_text)
    diff: BatchComparison = llm.generate_structured(BatchComparison, prompt)
    return BatchComparison(clause_type=clause_type, cells=cells,
                           differences=diff.differences)
