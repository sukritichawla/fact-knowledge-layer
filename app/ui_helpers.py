RELATION_META = {
    "Corroborated": ("🟢", "Independent sources support the same claim after normalization."),
    "Contradicted": ("🔴", "Claims conflict under materially matching context."),
    "Context-Resolved": ("🟡", "The difference is explained by time, scope, units, or definition."),
    "Related": ("🔵", "The claims are related, but the evidence is insufficient for a stronger label."),
}


def relation_icon(name: str) -> str:
    return RELATION_META.get(name, ("⚪", ""))[0]
