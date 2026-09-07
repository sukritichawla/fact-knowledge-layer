from app.local_extract import extract_local
from app.engine import _comparison_candidates
from app.models import Evidence, Fact


def test_local_extraction_is_available_without_llm():
    text = "[PAGE 4]\nRevenue from services was ₹81,415Mn in FY24.\n"
    result = extract_local(text, "example.pdf")
    assert result.facts
    fact = result.facts[0]
    assert fact.page == 4
    assert "81,415" in fact.value
    assert fact.quote


def test_candidate_blocking_allows_lexical_metric_matches():
    e1 = Evidence(document_id="a", filename="a.pdf", page=1, quote="revenue from services ₹81,415Mn", char_start=0, char_end=30)
    e2 = Evidence(document_id="b", filename="b.pdf", page=1, quote="revenue services ₹8,142 Cr", char_start=0, char_end=25)
    a = Fact(id="a1", subject="metric", predicate="revenue services", value="₹81,415Mn", normalized_value="81415000000", evidence=e1, confidence=.7)
    b = Fact(id="b1", subject="metric", predicate="revenue from services", value="₹8,142 Cr", normalized_value="81420000000", evidence=e2, confidence=.7)
    candidates = _comparison_candidates([a,b])
    assert {f.id for f in candidates} == {"a1", "b1"}
