from app.pdf import document_id, publication_date, locate_quote

def test_document_id_is_stable():
    assert document_id(b"hello") == document_id(b"hello")
    assert document_id(b"hello") != document_id(b"world")

def test_publication_date():
    assert publication_date("Published: 2025-04-07") == "2025-04-07"

def test_quote_verification_falls_back_conservatively():
    quote,start,verified,note=locate_quote("Revenue was Rs 10 million in FY24.","Revenue was Rs 10 million in FY24")
    assert verified is True
    quote,start,verified,note=locate_quote("Revenue was Rs 10 million in FY24.","Revenue was Rs 12 million")
    assert verified is False
    assert "Unable" in note or "fallback" in note
