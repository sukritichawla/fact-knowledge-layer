import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from .db import init_db, load_layer
from .evaluation import summarize_layer
from .export import excel_bytes, json_bytes, push_webhook
from .ingestion import ingest_pdf
from .pdf import highlighted_page_png
from .ui_helpers import RELATION_META, relation_icon

load_dotenv()
init_db()
st.set_page_config(page_title="FactLayer", page_icon="🔎", layout="wide")

# Keep the Streamlit layer intentionally lightweight. Heavy extraction/comparison is
# performed only from the explicit Process documents button; large persisted layers
# are displayed as bounded tables rather than hundreds of individual widgets.

st.title("🔎 FactLayer")
st.caption("Grounded extraction → normalized facts → cross-document resolution → inspectable evidence")

with st.sidebar:
    st.header("Workspace")
    
    api_enabled = bool(os.getenv("OPENAI_API_KEY"))`r`n    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    if api_enabled:
        st.success("LLM mode enabled")
        st.caption("Structured extraction and comparison use the configured OpenAI model.")
    else:
        st.info("Offline mode")
        st.caption("No API key detected. Local deterministic extraction and comparison are used; no API calls are made.")

    st.markdown("**Relationship legend**")
    for name, (icon, description) in RELATION_META.items():
        st.write(f"{icon} **{name}**")
        st.caption(description)

    st.markdown("**Evidence contract**")
    st.caption("Every persisted fact keeps its source document, page, quote, offsets, and verification status.")

st.markdown("### 1. Add source documents")
uploads = st.file_uploader(
    "Drop one or more PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    help="Select documents first, then explicitly click Process documents.",
)

if uploads:
    st.caption(f"{len(uploads)} PDF(s) selected. Existing documents are skipped by content hash.")
    selected_rows = [{"filename": u.name, "size_mb": round(len(u.getvalue()) / 1024 / 1024, 2)} for u in uploads]
    st.dataframe(selected_rows, use_container_width=True, hide_index=True)

    if st.button("⚙️ Process documents", type="primary", use_container_width=True):
        results = []
        progress = st.progress(0, text="Starting document processing…")
        for index, upload in enumerate(uploads, start=1):
            try:
                raw = upload.getvalue()
                result = ingest_pdf(raw, upload.name, model)
                results.append(result)
                if result.status == "skipped":
                    st.info(f"Skipped existing document: {upload.name}")
                else:
                    st.success(f"Processed {upload.name}: {result.fact_count} facts; {result.relationship_count} relationships refreshed.")
            except Exception as exc:
                # Never allow an ingestion failure to take down the Streamlit page.
                st.error(f"Failed to process {upload.name}: {type(exc).__name__}: {exc}")
            progress.progress(index / len(uploads), text=f"Processed {index}/{len(uploads)} document(s)")
        st.session_state["last_processing_count"] = len(results)
        st.session_state["layer_refresh"] = st.session_state.get("layer_refresh", 0) + 1
        progress.empty()
        st.success("Processing run finished. The knowledge layer below has been refreshed.")

layer = load_layer()
summary = summarize_layer(layer)

st.markdown("### 2. Knowledge layer")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Documents", summary["documents"])
c2.metric("Facts", summary["facts"])
c3.metric("Relationships", summary["relationships"])
c4.metric("Evidence verified", f"{summary['evidence_verification_rate']:.0%}")

if layer.documents:
    with st.expander("Document inventory", expanded=False):
        st.dataframe(
            [
                {
                    "document": d.filename,
                    "pages": d.pages,
                    "publication date": d.publication_date or "Not detected",
                    "document id": d.id,
                }
                for d in layer.documents
            ],
            use_container_width=True,
            hide_index=True,
        )

if layer.relationships:
    relation_counts = summary["relationships_by_type"]
    st.caption(" · ".join(f"{relation_icon(name)} {name}: {relation_counts.get(name, 0)}" for name in RELATION_META))

if layer.facts:
    # Radio navigation is deliberate: unlike st.tabs, only the selected section is
    # rendered, which keeps large knowledge layers responsive after ingestion.
    view = st.radio(
        "Knowledge layer view",
        ["Facts", "Relationships", "Evidence", "Evaluation", "Export"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view == "Facts":
        st.markdown("#### Grounded facts")
        st.caption("Showing up to 100 facts in the UI. The complete layer remains available through export.")
        rows = []
        for fact in layer.facts[:100]:
            rows.append({
                "subject": fact.subject,
                "predicate": fact.predicate,
                "value": fact.value,
                "normalized": fact.normalized_value or "",
                "unit": fact.unit or "",
                "date": fact.date or "",
                "document": fact.evidence.filename,
                "page": fact.evidence.page,
                "confidence": f"{fact.confidence:.0%}",
                "verified": "Yes" if fact.evidence.verified else "No",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    elif view == "Relationships":
        st.markdown("#### Cross-document reasoning")
        st.caption("Showing up to 100 relationships in the UI. Full relationship data is included in export.")
        lookup = {fact.id: fact for fact in layer.facts}
        rows = []
        for relationship in layer.relationships[:100]:
            a = lookup.get(relationship.source_fact_id)
            b = lookup.get(relationship.target_fact_id)
            rows.append({
                "relationship": relationship.relation.value,
                "source": a.value if a else relationship.source_fact_id,
                "target": b.value if b else relationship.target_fact_id,
                "source document": a.evidence.filename if a else "",
                "target document": b.evidence.filename if b else "",
                "rationale": relationship.rationale,
                "confidence": f"{relationship.confidence:.0%}",
            })
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No cross-document relationships have been identified yet.")

    elif view == "Evidence":
        st.markdown("#### Inspect source evidence")
        # Avoid creating a widget containing hundreds of long labels. The index is
        # stable and lightweight, while the selected fact supplies the evidence.
        index = st.number_input("Fact number", min_value=1, max_value=len(layer.facts), value=1, step=1)
        fact = layer.facts[index - 1]

        left, right = st.columns([1, 1.5])
        with left:
            st.markdown("#### Extracted fact")
            st.write(f"**{fact.subject} — {fact.predicate}**")
            st.write(fact.value)
            if fact.normalized_value:
                st.caption(f"Normalized value: {fact.normalized_value} {fact.unit or ''}".strip())
            st.markdown("#### Source evidence")
            st.info(fact.evidence.quote)
            status = "Verified exact/normalized match" if fact.evidence.verified else "Fallback source span — model quote was not directly verified"
            (st.success if fact.evidence.verified else st.warning)(status)
            st.caption(f"Document: {fact.evidence.filename} · page {fact.evidence.page}\n\nOffsets: {fact.evidence.char_start}–{fact.evidence.char_end}")
            if fact.evidence.verification_note:
                st.caption(fact.evidence.verification_note)

        with right:
            pdf_path = Path("data/uploads") / f"{fact.evidence.document_id}.pdf"
            if pdf_path.exists():
                try:
                    page_png = highlighted_page_png(pdf_path.read_bytes(), fact.evidence.page, fact.evidence.quote)
                    st.image(page_png, caption=f"Source page {fact.evidence.page} · highlighted evidence", use_container_width=True)
                except Exception as exc:
                    st.warning(f"Evidence preview could not be rendered: {type(exc).__name__}: {exc}")
            else:
                st.warning("Source PDF is not available locally. Re-upload the document to restore the evidence viewer.")

        related = [r for r in layer.relationships if r.source_fact_id == fact.id or r.target_fact_id == fact.id]
        if related:
            st.markdown("#### Related cross-document reasoning")
            for relationship in related[:20]:
                other_id = relationship.target_fact_id if relationship.source_fact_id == fact.id else relationship.source_fact_id
                other = next((item for item in layer.facts if item.id == other_id), None)
                if other:
                    st.write(f"{relation_icon(relationship.relation.value)} **{relationship.relation.value}** with {other.evidence.filename} p.{other.evidence.page}")
                    st.caption(relationship.rationale)

    elif view == "Evaluation":
        st.markdown("#### Evaluation audit")
        e1, e2, e3 = st.columns(3)
        e1.metric("Verified evidence", summary["verified_evidence"])
        e2.metric("Unverified evidence", summary["unverified_evidence"])
        e3.metric("Verification rate", f"{summary['evidence_verification_rate']:.0%}")

        distribution = [
            {"relationship": name, "count": summary["relationships_by_type"].get(name, 0)}
            for name in RELATION_META
        ]
        st.dataframe(distribution, use_container_width=True, hide_index=True)

        report_path = Path("data/evaluation-report.json")
        if report_path.exists():
            st.download_button("Download latest dataset audit", report_path.read_bytes(), "evaluation-report.json", "application/json")

    elif view == "Export":
        st.markdown("#### Export resolved layer")
        # Export bytes are generated only when this view is selected.
        st.download_button("Download JSON", json_bytes(layer), "fact-knowledge-layer.json", "application/json")
        st.download_button("Download Excel", excel_bytes(layer), "fact-knowledge-layer.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if os.getenv("GOOGLE_SHEETS_WEBHOOK_URL"):
            if st.button("Push to Google Sheets"):
                try:
                    st.success(push_webhook(layer))
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.caption("Google Sheets push is disabled until GOOGLE_SHEETS_WEBHOOK_URL is configured.")
else:
    st.info("Upload PDFs to populate the knowledge layer. You can use Offline mode without an API key.")

st.divider()
st.caption(
    "LLMs are optional: when enabled they propose structured facts and relationships; "
    "Pydantic validates the schema, source spans are verified before persistence, "
    "and deterministic IDs support incremental reprocessing."
)
