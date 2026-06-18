from app.ingestion.structure import structure_document
from app.schemas.models import StructuredDocument, ClauseNode


def test_structure_document_calls_llm_and_returns_tree(mock_llm):
    mock_llm.queue_response(StructuredDocument(
        title="MSA",
        nodes=[ClauseNode(number="1", heading="Indemnity", text="...")]))
    out = structure_document("raw contract text", llm=mock_llm)
    assert out.title == "MSA"
    assert out.nodes[0].heading == "Indemnity"
    assert "raw contract text" in mock_llm.calls[0]["prompt"]
