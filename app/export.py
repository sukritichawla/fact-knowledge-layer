import io
import os
import re

import pandas as pd
import requests

from .models import KnowledgeLayer


_EXCEL_ILLEGAL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _clean_excel_value(value):
    if isinstance(value, str):
        return _EXCEL_ILLEGAL_CHARS.sub("", value)
    return value


def facts_dataframe(layer: KnowledgeLayer) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fact_id": f.id,
                "subject": f.subject,
                "predicate": f.predicate,
                "value": f.value,
                "normalized_value": f.normalized_value,
                "unit": f.unit,
                "date": f.date,
                "scope": f.scope,
                "document": f.evidence.filename,
                "page": f.evidence.page,
                "quote": f.evidence.quote,
                "evidence_verified": f.evidence.verified,
                "verification_note": f.evidence.verification_note,
                "confidence": f.confidence,
            }
            for f in layer.facts
        ]
    )


def relationships_dataframe(layer: KnowledgeLayer) -> pd.DataFrame:
    lookup = {f.id: f for f in layer.facts}
    rows = []

    for r in layer.relationships:
        a = lookup.get(r.source_fact_id)
        b = lookup.get(r.target_fact_id)

        rows.append(
            {
                "relationship_id": r.id,
                "relationship": r.relation.value,
                "source_fact_id": r.source_fact_id,
                "target_fact_id": r.target_fact_id,
                "source": a.value if a else "",
                "target": b.value if b else "",
                "source_document": a.evidence.filename if a else "",
                "target_document": b.evidence.filename if b else "",
                "source_page": a.evidence.page if a else "",
                "target_page": b.evidence.page if b else "",
                "rationale": r.rationale,
                "confidence": r.confidence,
            }
        )

    return pd.DataFrame(rows)


def json_bytes(layer: KnowledgeLayer) -> bytes:
    """Export the complete validated knowledge layer as deterministic JSON."""
    return layer.model_dump_json(indent=2).encode("utf-8")


def excel_bytes(layer: KnowledgeLayer) -> bytes:
    """Export facts and relationships as a valid Excel workbook."""
    facts = facts_dataframe(layer).map(_clean_excel_value)
    relationships = relationships_dataframe(layer).map(_clean_excel_value)

    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Always create the Facts worksheet.
        facts.to_excel(
            writer,
            index=False,
            sheet_name="Facts",
        )

        # Always create the Relationships worksheet.
        relationships.to_excel(
            writer,
            index=False,
            sheet_name="Relationships",
        )

    return buf.getvalue()


def push_webhook(layer: KnowledgeLayer) -> str:
    url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
    if not url:
        raise RuntimeError("GOOGLE_SHEETS_WEBHOOK_URL is not configured")

    payload = {
        "facts": facts_dataframe(layer).fillna("").to_dict("records"),
        "relationships": relationships_dataframe(layer).fillna("").to_dict("records"),
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

    return response.text or "Google Sheets webhook accepted the payload"
