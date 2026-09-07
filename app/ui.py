import os
import streamlit as st
from dotenv import load_dotenv
from .db import init_db,load_layer,upsert_document,upsert_facts,upsert_relationships,document_exists
from .engine import process_pdf,compare_layer
from .export import excel_bytes,push_webhook
from .pdf import document_id,highlighted_page_png

load_dotenv(); init_db()
st.set_page_config(page_title="FactLayer",page_icon="🔎",layout="wide")
st.title("🔎 FactLayer")
st.caption("Grounded extraction → normalized facts → cross-document resolution → inspectable evidence")
with st.sidebar:
    model=st.text_input("LLM model",os.getenv("OPENAI_MODEL","gpt-4o-mini"))
    st.write("LLM:","✅ configured" if os.getenv("OPENAI_API_KEY") else "⚠️ configure OPENAI_API_KEY")
    st.markdown("**Relationships**")
    st.write("🟢 Corroborated · 🔴 Contradicted · 🟡 Context-Resolved · 🔵 Related")
uploads=st.file_uploader("Drop one or more PDFs",type=["pdf"],accept_multiple_files=True)
if uploads:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is required for extraction.")
    else:
        for upload in uploads:
            raw=upload.getvalue(); doc_id=document_id(raw)
            if document_exists(doc_id): st.info(f"Skipped existing document: {upload.name}"); continue
            with st.status(f"Processing {upload.name}…") as status:
                try:
                    doc,facts=process_pdf(raw,upload.name,model)
                    os.makedirs("data/uploads",exist_ok=True); open(f"data/uploads/{doc.id}.pdf","wb").write(raw)
                    upsert_document(doc); upsert_facts(facts)
                    layer=load_layer(); upsert_relationships(compare_layer(layer.facts,model,layer.documents))
                    status.update(label=f"Processed {upload.name}: {len(facts)} grounded facts",state="complete")
                except Exception as e:
                    status.update(label=f"Failed: {upload.name}",state="error"); st.exception(e)
layer=load_layer()
c1,c2,c3,c4=st.columns(4); c1.metric("Documents",len(layer.documents)); c2.metric("Facts",len(layer.facts)); c3.metric("Relationships",len(layer.relationships)); c4.metric("Contradictions",sum(r.relation.value=="Contradicted" for r in layer.relationships))
if layer.facts:
    tabs=st.tabs(["Facts","Relationships","Evidence","Export"])
    with tabs[0]:
        for f in layer.facts:
            with st.container(border=True):
                st.markdown(f"**{f.subject} — {f.predicate}**")
                st.write(f.value + (f" · normalized={f.normalized_value}" if f.normalized_value else ""))
                st.caption(f"{f.evidence.filename} · page {f.evidence.page} · {f.date or 'date not stated'} · confidence {f.confidence:.0%}")
                st.code(f.evidence.quote)
    with tabs[1]:
        lookup={f.id:f for f in layer.facts}
        for r in layer.relationships:
            a,b=lookup.get(r.source_fact_id),lookup.get(r.target_fact_id)
            icon={"Corroborated":"🟢","Contradicted":"🔴","Context-Resolved":"🟡","Related":"🔵"}.get(r.relation.value,"⚪")
            st.markdown(f"### {icon} {r.relation.value}")
            if a and b: st.write(f"**{a.subject}: {a.value}** ↔ **{b.subject}: {b.value}**")
            st.write(r.rationale); st.caption(f"Confidence {r.confidence:.0%}")
    with tabs[2]:
        choices={f"{f.evidence.filename} · p.{f.evidence.page} · {f.subject} — {f.predicate}":f.id for f in layer.facts}
        selected=st.selectbox("Select a fact to inspect its source",list(choices))
        f=next(x for x in layer.facts if x.id==choices[selected])
        st.info(f.evidence.quote)
        pdf_path=f"data/uploads/{f.evidence.document_id}.pdf"
        if os.path.exists(pdf_path): st.image(highlighted_page_png(open(pdf_path,"rb").read(),f.evidence.page,f.evidence.quote),caption=f"Page {f.evidence.page} · evidence {'verified' if f.evidence.verified else 'fallback'}")
        st.caption(f"Character offsets: {f.evidence.char_start}–{f.evidence.char_end}. {f.evidence.verification_note or ''}")
    with tabs[3]:
        st.download_button("Download Excel",excel_bytes(layer),"fact-knowledge-layer.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") and st.button("Push to Google Sheets"):
            try: st.success(push_webhook(layer))
            except Exception as e: st.error(str(e))
else: st.info("Upload PDFs to populate the knowledge layer.")
st.divider(); st.caption("LLMs propose structured facts; Pydantic validates them; source spans are verified before persistence; relationship IDs are deterministic for incremental reprocessing.")
