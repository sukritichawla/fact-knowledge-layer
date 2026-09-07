"""Validate the source-backed evaluation targets against a PDF directory.

Usage:
    python scripts/validate_case_study.py data/starter-datasets

This validator is deliberately separate from runtime extraction: it checks that
our documented demo cases still point to real source evidence. The application
itself remains filename-agnostic.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pdf import extract_pages, locate_quote


def _normalized_text(value: str) -> str:
    """Normalize PDF line wrapping/whitespace for source-evidence checks."""
    return " ".join(value.split()).casefold()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--manifest", type=Path, default=ROOT / "examples" / "evaluation-cases.json")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pdfs = {p.name: p for p in args.directory.rglob("*.pdf")}
    failures = []

    for case in manifest["cases"]:
        for item in case["documents"]:
            path = pdfs.get(item["filename"])
            if not path:
                failures.append(f"{case['id']}: missing {item['filename']}")
                continue
            pages = {p.page: p.text for p in extract_pages(path.read_bytes())}
            text = pages.get(item["page"], "")
            if _normalized_text(item["quote_contains"]) not in _normalized_text(text):
                failures.append(f"{case['id']}: expected text not found on page {item['page']}")

        if case.get("failure_test"):
            path = pdfs[case["documents"][0]["filename"]]
            page = case["documents"][0]["page"]
            text = {p.page: p.text for p in extract_pages(path.read_bytes())}[page]
            _, _, verified, _ = locate_quote(text, "THIS QUOTE DOES NOT EXIST IN THE SOURCE")
            if verified:
                failures.append(f"{case['id']}: mismatched quote was incorrectly marked verified")

    if failures:
        print("CASE STUDY VALIDATION FAILED")
        print("\n".join(f"- {x}" for x in failures))
        return 1

    print(f"Validated {len(manifest['cases'])} evaluation cases against {len(pdfs)} PDFs.")
    print("All source references and the deliberate evidence failure behave as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
