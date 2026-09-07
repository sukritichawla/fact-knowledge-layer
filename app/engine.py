import hashlib
import re
from .models import DocumentRecord, Fact, Evidence, Relationship, Relation
from .pdf import extract_pages, document_id, publication_date, locate_quote
from .llm import extract_facts, compare_facts

def normalize_value(value: str, unit: str | None) -> str | None:
    raw = value.strip().replace(",", "")
    m = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s*(%|thousand|million|billion|mn|bn|k|cr)?", raw, re.I)
    if not m:
        return None
    n = float(m.group(1)); suffix = (m.group(2) or "").lower()
    if suffix == "%": n /= 100
    elif suffix in {"thousand", "k"}: n *= 1e3
    elif suffix in {"million", "mn"}: n *= 1e6
    elif suffix in {"billion", "bn"}: n *= 1e9
    elif suffix == "cr": n *= 1e7
    elif unit:
        u = unit.lower()
        if "billion" in u or u in {"bn", "b"}: n *= 1e9
        elif "million" in u or u in {"mn", "m"}: n *= 1e6
        elif "crore" in u or u == "cr": n *= 1e7
    return f"{n:g}"

def _chunks(pages, max_chars=18000):
    chunks=[]; current=[]; size=0
    for p in pages:
        block=f"[PAGE {p.page}]\n{p.text}\n"
        if current and size + len(block) > max_chars:
            chunks.append("\n".join(current)); current=[]; size=0
        current.append(block); size += len(block)
    if current: chunks.append("\n".join(current))
    return chunks

def process_pdf(pdf_bytes: bytes, filename: str, model: str) -> tuple[DocumentRecord, list[Fact]]:
    doc_id = document_id(pdf_bytes)
    pages = extract_pages(pdf_bytes)
    page_map = {p.page: p.text for p in pages}
    extracted=[]
    for chunk in _chunks(pages):
        result = extract_facts(chunk, filename, model)
        extracted.extend(result.facts)
    facts=[]; seen=set()
    for ef in extracted:
        page_text=page_map.get(ef.page, "")
        quote,start,verified,note=locate_quote(page_text, ef.quote)
        key=(ef.subject.lower(),ef.predicate.lower(),(ef.normalized_value or normalize_value(ef.value,ef.unit) or ef.value).lower(),ef.page)
        if key in seen: continue
        seen.add(key)
        evidence=Evidence(document_id=doc_id,filename=filename,page=ef.page,quote=quote,char_start=max(start,0),char_end=max(start,0)+len(quote),verified=verified,verification_note=note)
        facts.append(Fact(id=hashlib.sha256(f"{doc_id}|{key}".encode()).hexdigest()[:20],subject=ef.subject,predicate=ef.predicate,value=ef.value,normalized_value=normalize_value(ef.value,ef.unit) or ef.normalized_value,unit=ef.unit,date=ef.date,scope=ef.scope,evidence=evidence,confidence=ef.confidence,extraction_note=ef.extraction_note))
    meta=DocumentRecord(id=doc_id,filename=filename,publication_date=publication_date("\n".join(p.text for p in pages)),pages=len(pages))
    return meta,facts

def compare_layer(facts: list[Fact], model: str, documents: list[DocumentRecord] | None = None) -> list[Relationship]:
    publication_dates={d.id:d.publication_date for d in (documents or [])}
    result=compare_facts(facts,publication_dates,model)
    allowed={r.value for r in Relation}; out=[]
    for x in result.relationships:
        if x.source_fact_id == x.target_fact_id: continue
        rel=x.relation if x.relation in allowed else Relation.RELATED.value
        rid=hashlib.sha256(f"{min(x.source_fact_id,x.target_fact_id)}|{max(x.source_fact_id,x.target_fact_id)}|{rel}".encode()).hexdigest()[:20]
        out.append(Relationship(id=rid,source_fact_id=x.source_fact_id,target_fact_id=x.target_fact_id,relation=rel,rationale=x.rationale,confidence=x.confidence))
    return out
