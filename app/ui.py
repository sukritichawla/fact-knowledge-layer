import os
import streamlit as st
from dotenv import load_dotenv
from .db import init_db, load_layer
from .ingestion import ingest_pdf
from .export import excel_bytes, json_bytes, push_webhook
from .pdf import highlighted_page_png

load_dotenv()
init_db()
st.set_page_config(page_title="FactLayer", page_icon="🔎", layout="wide")
st.title("🔎 FactLayer")
st.caption("Grounded extraction → normalized facts → cross-document resolution → inspectable evidence")

with st.sidebar:
    model = st.text_input("LLM model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    st.write("LLM:", "✅ configured" if os.getenv("OPENAI_API_KEY") else "⚠️ configure OPENAI_API_KEY")
    st.markdown("**Relationships**")
    st.write("🟢 Corroborated · 🔴 Contradicted · 🟡 Context-Resolved · 🔵 Related")
    st.markdown("**Evidence**")
    st.caption("Every persisted fact keeps its source document, page, quote, offsets, and verification status.")

uploads = st.file_uploader("Drop one or more PDFs", type=["pdf"], accept_multiple_files=True)
if uploads:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is required for extraction.")
    else:
        for upload in uploads:
            raw = upload.getvalue()
            with st.status(f"Processing {upload.name}…") as status:
                try:
                    result = ingest_pdf(raw, upload.name, model)
                    if result.status == "skipped":
                        status.update(label=f"Skipped existing document: {upload.name}", state="complete")
                    else:
                        status.update(label=f"Processed {upload.name}: {result.fact_count} grounded facts", state="complete")
                    st.caption(result.message)
                except Exception as e:
                    status.update(label=f"Failed: {upload.name}", state="error")
                    st.exception(e)

layer = load_layer()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Documents", len(layer.documents))
c2.metric("Facts", len(layer.facts))
c3.metric("Relationships", len(layer.relationships))
c4.metric("Contradictions", sum(r.relation.value == "Contradicted" for r in layer.relationships))

if layer.facts:
    tabs = st.tabs(["Facts", "Relationships", "Evidence", "Export"])

    with tabs[0]:
        st.caption("Facts are shown with their normalized value and the source span used to ground them.")
        for f in layer.facts:
            with st.container(border=True):
                st.markdown(f"**{f.subject} — {f.predicate}**")
                st.write(f.value + (f" · normalized={f.normalized_value}" if f.normalized_value else ""))
                verification = "verified" if f.evidence.verified else "fallback source span"
                st.caption(
                    f"{f.evidence.filename} · page {f.evidence.page} · "
                    f"{f.date or 'date not stated'} · confidence {f.confidence:.0%} · evidence {verification}"
                )
                st.code(f.evidence.quote)

    with tabs[1]:
        lookup = {f.id: f for f in layer.facts}
        if not layer.relationships:
            st.info("No cross-document relationships have been identified yet.")
        for r in layer.relationships:
            a, b = lookup.get(r.source_fact_id), lookup.get(r.target_fact_id)
            icon = {"Corroborated": "🟢", "Contradicted": "🔴", "Context-Resolved": "🟡", "Related": "🔵"}.get(r.relation.value, "⚪")
            st.markdown(f"### {icon} {r.relation.value}")
            if a and b:
                st.write(f"**{a.subject}: {a.value}** ↔ **{b.subject}: {b.value}**")
                st.caption(f"Sources: {a.evidence.filename} p.{a.evidence.page} ↔ {b.evidence.filename} p.{b.evidence.page}")
            st.write(r.rationale)
            st.caption(f"Confidence {r.confidence:.0%}")

    with tabs[2]:
        choices = {
            f"{f.evidence.filename} · p.{f.evidence.page} · {f.subject} — {f.predicate}": f.id
            for f in layer.facts
        }
        selected = st.selectbox("Select a fact to inspect its source", list(choices))
        f = next(x for x in layer.facts if x.id == choices[selected])

        left, right = st.columns([1, 1.5])
        with left:
            st.markdown("#### Extracted fact")
            st.write(f"**{f.subject} — {f.predicate}**")
            st.write(f.value)
            if f.normalized_value:
                st.caption(f"Normalized value: {f.normalized_value} {f.unit or ''}".strip())
            st.markdown("#### Source evidence")
            st.info(f.evidence.quote)
            status = "Verified exact/normalized match" if f.evidence.verified else "Fallback source span — model quote was not directly verified"
            (st.success if f.evidence.verified else st.warning)(status)
            st.caption(
                f"Document: {f.evidence.filename} · page {f.evidence.page}\n\n"
                f"Offsets: {f.evidence.char_start}–{f.evidence.char_end}"
            )
            if f.evidence.verification_note:
                st.caption(f.evidence.verification_note)

        with right:
            pdf_path = f"data/uploads/{f.evidence.document_id}.pdf"
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as handle:
                    page_png = highlighted_page_png(handle.read(), f.evidence.page, f.evidence.quote)
                st.image(page_png, caption=f"Source page {f.evidence.page} · highlighted evidence", use_container_width=True)
            else:
                st.warning("Source PDF is not available locally. Re-upload the document to restore the evidence viewer.")

        related = [
            r for r in layer.relationships
            if r.source_fact_id == f.id or r.target_fact_id == f.id
        ]
        if related:
            st.markdown("#### Related cross-document reasoning")
            for r in related:
                other_id = r.target_fact_id if r.source_fact_id == f.id else r.source_fact_id
                other = next((x for x in layer.facts if x.id == other_id), None)
                if other:
                    icon = {"Corroborated": "🟢", "Contradicted": "🔴", "Context-Resolved": "🟡", "Related": "🔵"}.get(r.relation.value, "⚪")
                    st.write(f"{icon} **{r.relation.value}** with {other.evidence.filename} p.{other.evidence.page}")
                    st.caption(r.rationale)

    with tabs[3]:
        st.download_button("Download JSON", json_bytes(layer), "fact-knowledge-layer.json", "application/json")
        st.download_button(
            "Download Excel",
            excel_bytes(layer),
            "fact-knowledge-layer.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") and st.button("Push to Google Sheets"):
            try:
                st.success(push_webhook(layer))
            except Exception as e:
                st.error(str(e))
else:
    st.info("Upload PDFs to populate the knowledge layer.")

st.divider()
st.caption("LLMs propose structured facts; Pydantic validates them; source spans are verified before persistence; relationship IDs are deterministic for incremental reprocessing.")
