import io, os, pandas as pd, requests
from .models import KnowledgeLayer

def facts_dataframe(layer):
    return pd.DataFrame([{"fact_id":f.id,"subject":f.subject,"predicate":f.predicate,"value":f.value,"normalized_value":f.normalized_value,"unit":f.unit,"date":f.date,"scope":f.scope,"document":f.evidence.filename,"page":f.evidence.page,"quote":f.evidence.quote,"evidence_verified":f.evidence.verified,"confidence":f.confidence} for f in layer.facts])

def relationships_dataframe(layer):
    lookup={f.id:f for f in layer.facts}; rows=[]
    for r in layer.relationships:
        a,b=lookup.get(r.source_fact_id),lookup.get(r.target_fact_id)
        rows.append({"relationship":r.relation.value,"source":a.value if a else "","target":b.value if b else "","source_document":a.evidence.filename if a else "","target_document":b.evidence.filename if b else "","source_page":a.evidence.page if a else "","target_page":b.evidence.page if b else "","rationale":r.rationale,"confidence":r.confidence})
    return pd.DataFrame(rows)

def excel_bytes(layer):
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        facts_dataframe(layer).to_excel(writer,index=False,sheet_name="Facts")
        relationships_dataframe(layer).to_excel(writer,index=False,sheet_name="Relationships")
    return buf.getvalue()

def push_webhook(layer):
    url=os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
    if not url: raise RuntimeError("GOOGLE_SHEETS_WEBHOOK_URL is not configured")
    payload={"facts":facts_dataframe(layer).fillna("").to_dict("records"),"relationships":relationships_dataframe(layer).fillna("").to_dict("records")}
    r=requests.post(url,json=payload,timeout=30); r.raise_for_status(); return r.text or "Google Sheets webhook accepted the payload"
