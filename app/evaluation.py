from collections import Counter
from .models import KnowledgeLayer


def summarize_layer(layer: KnowledgeLayer) -> dict:
    """Return a compact, JSON-serializable audit summary of a knowledge layer."""
    relations = Counter(r.relation.value for r in layer.relationships)
    verified = sum(1 for f in layer.facts if f.evidence.verified)
    return {
        "documents": len(layer.documents),
        "facts": len(layer.facts),
        "relationships": len(layer.relationships),
        "relationships_by_type": dict(sorted(relations.items())),
        "verified_evidence": verified,
        "unverified_evidence": len(layer.facts) - verified,
        "evidence_verification_rate": (verified / len(layer.facts)) if layer.facts else 0.0,
    }
