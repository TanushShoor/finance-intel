STRUCTURE_PROMPT = """You are a legal document parser. Given the raw text of a contract,
reconstruct its clause hierarchy. Identify section numbers (e.g. 1, 1.1, (a)), headings,
the text of each clause, and any cross-references (e.g. "subject to Section 9.2").
Return the nested structure. Raw contract text:

{text}
"""

EXTRACTION_PROMPT = """You are a contract analyst. From the contract below, locate each of these
clause types: {clause_types}. For each, return whether it is present, its verbatim text, its
section location, and your confidence (0-1). If a type is absent, set present=false, text="",
confidence=0. Contract:

{text}
"""

COMPARISON_PROMPT = """You are a senior commercial lawyer. Compare this {clause_type} clause to the
market-standard baseline and classify it as favourable, unfavourable, unusual, or standard
(from the reviewing party's perspective), with a one-sentence rationale.

Market-standard baseline for {clause_type}:
{baseline}

Clause under review:
{clause_text}
"""

RISK_PROMPT = """You are a risk analyst. For this {clause_type} clause (classified as
'{classification}' vs market standard), assign a risk category (financial, operational, legal, or
reputational), a severity 0-100, and a one-sentence rationale.

Clause:
{clause_text}
Deviation rationale: {deviation_rationale}
"""

SUMMARY_PROMPT = """You are explaining a contract to a non-lawyer business owner. In plain English,
write: (1) coverage — what the contract is about; (2) who_carries_risk — which party bears more
risk and why; (3) key_commercial_terms — bullet list of the main commercial terms; (4) top_issues —
the top 3 issues to negotiate. Be concrete and avoid legalese.

Clauses and their risk findings:
{findings}
"""

BATCH_PROMPT = """Compare the following {clause_type} clauses drawn from different contracts.
Summarize the substantive differences a due-diligence reviewer would care about as a bullet list.

{cells}
"""
