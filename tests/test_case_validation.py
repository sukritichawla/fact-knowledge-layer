import json
from pathlib import Path

from app.pdf import locate_quote


def test_evaluation_manifest_has_four_required_case_types():
    manifest = json.loads(Path("examples/evaluation-cases.json").read_text(encoding="utf-8"))
    types = {case["type"] for case in manifest["cases"]}
    assert {"Corroborated", "Contradicted", "Context-Resolved", "Extraction/Reasoning Failure"} <= types


def test_mismatched_evidence_is_never_marked_verified():
    quote, start, verified, note = locate_quote(
        "Revenue from services was ₹81,415Mn in FY24.",
        "Revenue from services was ₹999,999Mn in FY24.",
    )
    assert not verified
    assert note
    assert quote
    assert start >= 0


def test_manifest_matching_tolerates_pdf_line_wrapping():
    from scripts.validate_case_study import _normalized_text

    extracted = "The number of female workers increased\nby 59% year-on-year."
    expected = "increased by 59% year-on-year"
    assert _normalized_text(expected) in _normalized_text(extracted)
