from app.ui_helpers import relation_icon


def test_relation_icon_has_known_and_fallback_values():
    assert relation_icon("Corroborated") == "🟢"
    assert relation_icon("Unknown") == "⚪"
