"""Run the FactLayer pipeline over every PDF in a directory tree.

Usage:
    python scripts/run_dataset.py path/to/pdfs

The script is deliberately filename-agnostic: any PDF found recursively is
processed through the same ingestion path used by the Streamlit UI.
"""
import argparse
import sys
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation import summarize_layer
from app.db import load_layer
from app.ingestion import ingest_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="Process a directory of PDFs incrementally.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--report", type=Path, default=Path("data/evaluation-report.json"))
    args = parser.parse_args()

    mode = "openai" if os.getenv("OPENAI_API_KEY") else "offline"
    print(f"Extraction mode: {mode}")
    if not args.directory.exists() or not args.directory.is_dir():
        parser.error(f"Not a directory: {args.directory}")

    pdfs = sorted(args.directory.rglob("*.pdf"))
    if not pdfs:
        parser.error(f"No PDF files found under {args.directory}")

    results = []
    for path in pdfs:
        raw = path.read_bytes()
        result = ingest_pdf(raw, path.name, args.model)
        results.append({
            "filename": result.filename,
            "document_id": result.document_id,
            "status": result.status,
            "facts": result.fact_count,
            "relationships": result.relationship_count,
            "message": result.message,
        })
        print(f"[{result.status}] {path.name}: {result.fact_count} facts, {result.relationship_count} relationships")

    layer = load_layer()
    report = {"files": results, "summary": summarize_layer(layer)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote report: {args.report}")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
