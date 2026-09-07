from app.evaluation import summarize_layer
from app.models import KnowledgeLayer, DocumentRecord, Fact, Evidence, Relationship, Relation


def _fact(doc_id, fact_id, verified=True):
    return Fact(
        id=fact_id,
        subject="Revenue",
        predicate="amount",
        value="100 Cr",
        normalized_value="1000000000",
        unit="Cr",
        confidence=0.9,
        evidence=Evidence(
            document_id=doc_id,
            filename=f"{doc_id}.pdf",
            page=1,
            quote="Revenue was 100 Cr.",
            char_start=0,
            char_end=20,
            verified=verified,
        ),
    )


def test_summary_counts_relationships_and_evidence():
    layer = KnowledgeLayer(
        documents=[DocumentRecord(id="a", filename="a.pdf", pages=1)],
        facts=[_fact("a", "f1"), _fact("b", "f2", verified=False)],
        relationships=[Relationship(
            id="r1",
            source_fact_id="f1",
            target_fact_id="f2",
            relation=Relation.CORROBORATED,
            rationale="Same normalized claim.",
            confidence=0.9,
        )],
    )
    summary = summarize_layer(layer)
    assert summary["documents"] == 1
    assert summary["facts"] == 2
    assert summary["relationships_by_type"] == {"Corroborated": 1}
    assert summary["verified_evidence"] == 1
    assert summary["unverified_evidence"] == 1
    assert summary["evidence_verification_rate"] == 0.5
