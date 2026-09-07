from dataclasses import dataclass
from pathlib import Path

from .db import document_exists, load_layer, upsert_document, upsert_facts, upsert_relationships
from .engine import compare_layer, process_pdf
from .pdf import document_id

UPLOAD_DIR = Path("data/uploads")

@dataclass(frozen=True)
class IngestionResult:
    status: str
    filename: str
    document_id: str
    fact_count: int = 0
    relationship_count: int = 0
    message: str = ""

def _persist_source(pdf_bytes: bytes, doc_id: str) -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / f"{doc_id}.pdf"
    if not destination.exists():
        destination.write_bytes(pdf_bytes)

def ingest_pdf(pdf_bytes: bytes, filename: str, model: str) -> IngestionResult:
    """Process one new PDF incrementally, skipping an already-known document hash."""
    doc_id = document_id(pdf_bytes)
    if document_exists(doc_id):
        _persist_source(pdf_bytes, doc_id)
        return IngestionResult(status="skipped", filename=filename, document_id=doc_id, message="Document already exists; extraction was not repeated.")

    doc, facts = process_pdf(pdf_bytes, filename, model)
    upsert_document(doc)
    upsert_facts(facts)
    _persist_source(pdf_bytes, doc.id)
    layer = load_layer()
    relationships = compare_layer(layer.facts, model, layer.documents)
    upsert_relationships(relationships)
    return IngestionResult(status="processed", filename=filename, document_id=doc.id, fact_count=len(facts), relationship_count=len(relationships), message=f"Processed {len(facts)} grounded facts and refreshed cross-document relationships.")
