import hashlib
import re
from itertools import combinations
from .models import Relation
from .llm import ComparedRelationship, ComparisonResult

STOP={"metric","the","a","an","of","for","and","in","on","to","from","by","with","as","at","is","was","were","are","be","been","this","that","our","their","its","than","during","period","year","quarter","ended","end","more","less","approximately","number","total","count","amount"}

def _tokens(s):
    return {x for x in re.findall(r"[a-z][a-z0-9/-]*", s.casefold()) if x not in STOP and len(x)>2}

def _sim(a,b):
    x,y=_tokens(a),_tokens(b)
    return len(x&y)/max(1,len(x|y))

def _same_period(a,b):
    da=(a.date or "").casefold(); db=(b.date or "").casefold()
    return bool(da and db and da==db)

def _numeric_close(a,b):
    try:
        x,y=float(a),float(b)
    except (TypeError,ValueError):
        return False
    scale=max(abs(x),abs(y),1.0)
    return abs(x-y)/scale <= 0.002

def compare_local(facts, publication_dates):
    # Inverted-token blocking avoids an O(n^2) scan on large offline corpora.
    index = {}
    for f in facts:
        for token in _tokens(f.predicate):
            index.setdefault(token, []).append(f)

    pairs = set()
    for bucket in index.values():
        if len(bucket) > 40:
            bucket = sorted(bucket, key=lambda f: len(f.predicate))[:40]
        for a,b in combinations(bucket,2):
            if a.evidence.document_id != b.evidence.document_id:
                pairs.add((min(a.id,b.id), max(a.id,b.id)))

    by_id={f.id:f for f in facts}
    out=[]
    for aid,bid in pairs:
        a,b=by_id[aid],by_id[bid]
        sim=_sim(a.predicate,b.predicate)
        shared=_tokens(a.predicate) & _tokens(b.predicate)
        if sim < .15 or len(shared) < 1: continue
        av,bv=a.normalized_value,b.normalized_value
        if av is None or bv is None: continue
        if av==bv or _numeric_close(av,bv):
            rel=Relation.CORROBORATED.value
            rationale="Offline deterministic comparison: matching metric context and normalized numeric value across independent documents."
            conf=min(.95,.65+sim*.3)
        elif sim >= .55 and _same_period(a,b) and (a.scope or "").casefold()==(b.scope or "").casefold():
            rel=Relation.CONTRADICTED.value
            rationale="Offline deterministic comparison: closely matching metric context, period and scope, but incompatible normalized values."
            conf=min(.9,.58+sim*.3)
        else:
            rel=Relation.CONTEXT_RESOLVED.value
            details=[]
            if a.date!=b.date: details.append("different stated periods")
            if a.scope!=b.scope: details.append("different stated scopes")
            if a.unit!=b.unit: details.append("different units/representations")
            rationale="Offline deterministic comparison: values differ, but the available evidence does not establish a like-for-like conflict; " + ", ".join(details or ["context differs or is incomplete"]) + "."
            conf=min(.82,.5+sim*.25)
        out.append(ComparedRelationship(source_fact_id=a.id,target_fact_id=b.id,relation=rel,rationale=rationale,confidence=conf))
    return ComparisonResult(relationships=out)
