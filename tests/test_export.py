from app.export import json_bytes
from app.models import Evidence, Fact, KnowledgeLayer


def test_json_export_contains_validated_layer():
    fact = Fact(
        id="f1",
        subject="Company",
        predicate="revenue",
        value="₹10 Mn",
        normalized_value="10000000",
        unit="million INR",
        evidence=Evidence(
            document_id="d1",
            filename="report.pdf",
            page=2,
            quote="Revenue was ₹10 Mn.",
            char_start=0,
            char_end=20,
        ),
        confidence=0.95,
    )
    payload = json_bytes(KnowledgeLayer(facts=[fact])).decode("utf-8")
    assert '"facts"' in payload
    assert '"evidence_verified":' not in payload
    assert '"filename": "report.pdf"' in payload
    assert '"page": 2' in payload
