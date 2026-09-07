from app.engine import _comparison_candidates, normalize_value
from app.models import Evidence, Fact


def fact(fid, doc, subject, predicate, value, normalized):
    return Fact(
        id=fid, subject=subject, predicate=predicate, value=value, normalized_value=normalized,
        evidence=Evidence(document_id=doc, filename=f"{doc}.pdf", page=1, quote=value, char_start=0, char_end=len(value)),
        confidence=0.9,
    )


def test_normalize_common_financial_units():
    assert normalize_value("81,415", "million") == "81415000000"
    assert normalize_value("8,142", "crore") == "81420000000"
    assert normalize_value("59%", None) == "0.59"


def test_candidate_blocking_excludes_same_document_and_unrelated_claims():
    a = fact("a", "doc1", "Delhivery", "revenue from services", "81415", "81415000000")
    b = fact("b", "doc2", "Delhivery", "revenue from services", "8142", "81420000000")
    c = fact("c", "doc1", "Delhivery", "team size", "63713", "63713")
    d = fact("d", "doc3", "India", "population", "140", "1400000000")
    assert {f.id for f in _comparison_candidates([a, b, c, d])} == {"a", "b"}


def test_candidate_blocking_keeps_exact_normalized_value_across_documents():
    a = fact("a", "doc1", "Company", "customers", "10 million", "10000000")
    b = fact("b", "doc2", "Different wording", "active customers", "10000000", "10000000")
    assert {f.id for f in _comparison_candidates([a, b])} == {"a", "b"}
