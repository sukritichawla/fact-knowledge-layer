from app.ingestion import IngestionResult

def test_ingestion_result_reports_processed_documents():
    result = IngestionResult(status="processed", filename="report.pdf", document_id="abc123", fact_count=7, relationship_count=3, message="ok")
    assert result.status == "processed"
    assert result.fact_count == 7
    assert result.relationship_count == 3

def test_ingestion_result_supports_duplicate_skip():
    result = IngestionResult(status="skipped", filename="duplicate.pdf", document_id="same-hash", message="Document already exists; extraction was not repeated.")
    assert result.status == "skipped"
    assert result.fact_count == 0
