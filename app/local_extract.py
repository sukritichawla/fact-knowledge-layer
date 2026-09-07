import re
from .llm import ExtractedFact, ExtractionResult

NUM_RE = re.compile(r"(?<![A-Za-z0-9])(?:₹\s*)?[-+]?\d[\d,]*(?:\.\d+)?\s*(?:%|million|billion|trillion|mn|bn|tn|cr|crore|lakh|thousand|k|m)?", re.I)
STOP = {"the","a","an","of","for","and","in","on","to","from","by","with","as","at","is","was","were","are","be","been","this","that","our","their","its","than","during","period","year","quarter","ended","end","per","about","more","less","approximately","as","out","of"}
DATE_RE = re.compile(r"(?i)\b(?:FY\s*\d{2,4}|Q[1-4]\s*FY\s*\d{2,4}|\d{4}-\d{2,4}|March\s+\d{1,2},\s*\d{4}|(?:year|period|quarter)\s+ended\s+[^,.;\n]+)")

def _metric(context: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z'/-]*", context)
    words = [w.lower() for w in words if w.lower() not in STOP and not re.fullmatch(r"fy\d+", w.lower())]
    return " ".join(words[-10:])

def _quote(page_text: str, start: int, end: int) -> str:
    left=max(page_text.rfind("\n",0,start), page_text.rfind(".",0,start), page_text.rfind(";",0,start))
    right_candidates=[x for x in (page_text.find("\n",end), page_text.find(".",end), page_text.find(";",end)) if x>=0]
    right=min(right_candidates) if right_candidates else len(page_text)
    q=re.sub(r"\s+"," ",page_text[left+1:right]).strip()
    return q[:1200]

def _period(context: str) -> str | None:
    matches=list(DATE_RE.finditer(context))
    return matches[-1].group(0) if matches else None

def extract_local(text: str, filename: str) -> ExtractionResult:
    facts=[]
    page=None
    current=[]
    for line in text.splitlines(True):
        pm=re.fullmatch(r"\[PAGE\s+(\d+)\]\s*", line.strip(), re.I)
        if pm:
            if page is not None:
                facts.extend(_extract_page(page, "".join(current)))
            page=int(pm.group(1)); current=[]
        else:
            current.append(line)
    if page is not None:
        facts.extend(_extract_page(page, "".join(current)))
    seen=set(); unique=[]
    for f in facts:
        key=(f.predicate.casefold(),f.value.casefold(),f.page)
        if key not in seen:
            seen.add(key); unique.append(f)
    # Keep offline evaluation bounded and deterministic while retaining the most useful metric spans.
    unique.sort(key=lambda f: (bool(f.unit), len(_metric(f.quote)), len(f.quote)), reverse=True)
    return ExtractionResult(facts=unique[:250])

def _extract_page(page: int, page_text: str):
    out=[]
    compact=re.sub(r"[ \t]+"," ",page_text)
    for m in NUM_RE.finditer(compact):
        raw=m.group(0).strip()
        before=compact[max(0,m.start()-140):m.start()]
        after=compact[m.end():m.end()+100]
        metric=_metric(before)
        if not metric:
            continue
        # Avoid isolated page numbers, years, and footnote markers.
        numeric_only=re.sub(r"[^0-9]", "", raw)
        if numeric_only in {"2019","2020","2021","2022","2023","2024","2025","2026"} and len(metric.split()) < 2:
            continue
        unit=None
        um=re.search(r"(?i)(%|million|billion|trillion|mn|bn|tn|cr|crore|lakh|thousand|k|m)\s*$", raw)
        if um: unit=um.group(1)
        quote=_quote(compact,m.start(),m.end())
        context=before+" "+after
        out.append(ExtractedFact(
            subject="metric",
            predicate=metric,
            value=raw,
            normalized_value=None,
            unit=unit,
            date=_period(context),
            scope=None,
            page=page,
            quote=quote or raw,
            confidence=0.72,
            extraction_note="Deterministic offline extraction: numeric expression linked to nearby metric context; LLM not used.",
        ))
    return out
