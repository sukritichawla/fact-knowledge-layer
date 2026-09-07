import os
from typing import Optional
from pydantic import BaseModel, Field

class ExtractedFact(BaseModel):
    subject: str
    predicate: str
    value: str
    normalized_value: Optional[str] = None
    unit: Optional[str] = None
    date: Optional[str] = None
    scope: Optional[str] = None
    page: int = Field(ge=1)
    quote: str
    confidence: float = Field(ge=0, le=1)
    extraction_note: Optional[str] = None

class ExtractionResult(BaseModel):
    facts: list[ExtractedFact]

class ComparedRelationship(BaseModel):
    source_fact_id: str
    target_fact_id: str
    relation: str
    rationale: str
    confidence: float = Field(ge=0, le=1)

class ComparisonResult(BaseModel):
    relationships: list[ComparedRelationship]

def client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_facts(text: str, filename: str, model: str) -> ExtractionResult:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    prompt = f'''Extract meaningful numerical or semantic facts from this PDF excerpt. Every fact must be directly supported by the supplied text. Return the page number and an exact source quote from that page. Do not infer facts that are not stated. Capture date/period and scope when present. Do not merge values from different periods. Return only facts useful for cross-document knowledge resolution.\n\nFILE: {filename}\nTEXT:\n{text}'''
    r = client().responses.parse(
        model=model,
        input=[
            {"role":"system","content":"You are a conservative information extraction system. Evidence must be traceable to the supplied document text."},
            {"role":"user","content":prompt},
        ],
        text_format=ExtractionResult,
    )
    return r.output_parsed

def compare_facts(facts: list, publication_dates: dict[str, str | None], model: str) -> ComparisonResult:
    if not os.getenv("OPENAI_API_KEY") or len(facts) < 2:
        return ComparisonResult(relationships=[])
    compact = [{
        "id": f.id, "subject": f.subject, "predicate": f.predicate,
        "value": f.value, "normalized_value": f.normalized_value,
        "unit": f.unit, "date": f.date, "scope": f.scope,
        "document": f.evidence.filename,
        "publication_date": publication_dates.get(f.evidence.document_id),
        "quote": f.evidence.quote,
    } for f in facts]
    prompt = '''Compare only meaningfully related facts. Use explicit evidence, date/period, scope and units before reasoning.\n\nClassification rules:\n- Corroborated: independent documents support the same claim; minor rounding or wording differences are acceptable.\n- Contradicted: the same claim has incompatible values under materially matching time, scope and units.\n- Context-Resolved: values differ, but the difference is explained by explicit time, scope, population, unit, or measurement-definition context.\n- Related: same topic but insufficient evidence for one of the above.\nNever use outside knowledge. Explain the decisive evidence briefly.''' + "\n\nFACTS:\n" + str(compact)
    r = client().responses.parse(
        model=model,
        input=[
            {"role":"system","content":"You are a conservative cross-document fact resolver. Never turn uncertainty into a contradiction."},
            {"role":"user","content":prompt},
        ],
        text_format=ComparisonResult,
    )
    return r.output_parsed
