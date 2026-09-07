import hashlib
import re
from dataclasses import dataclass
import fitz

@dataclass
class PageText:
    page: int
    text: str

def document_id(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()[:16]

def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [PageText(i + 1, page.get_text("text")) for i, page in enumerate(doc)]

def publication_date(text: str) -> str | None:
    patterns = [
        r'\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b',
        r'\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            g = m.groups()
            if len(g[0]) == 4:
                return f"{g[0]}-{int(g[1]):02d}-{int(g[2]):02d}"
            return f"{g[2]}-{int(g[1]):02d}-{int(g[0]):02d}"
    year = re.search(r'\b(20\d{2})\b', text)
    return f"{year.group(1)}-12-31" if year else None

def sentence_candidates(text: str) -> list[str]:
    # Keep paragraph/bullet boundaries because PDF extraction frequently splits lines.
    normalized = re.sub(r'\s+', ' ', text).strip()
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|(?=• )', normalized) if s.strip()]

def locate_quote(page_text: str, quote: str) -> tuple[str, int, bool, str | None]:
    if not quote:
        return "", 0, False, "Model returned an empty quote"
    exact = page_text.find(quote)
    if exact >= 0:
        return quote, exact, True, None
    # Retry with whitespace-normalized matching, but store the real source text.
    compact_page = re.sub(r'\s+', ' ', page_text).strip()
    compact_quote = re.sub(r'\s+', ' ', quote).strip()
    pos = compact_page.lower().find(compact_quote.lower())
    if pos >= 0:
        return compact_quote, pos, True, "Verified after whitespace normalization"
    # Conservative fallback: choose a sentence sharing several distinctive tokens.
    tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9₹$%.-]+", quote) if len(t) > 2][:12]
    candidates = sentence_candidates(page_text)
    scored = sorted(((sum(t in c.lower() for t in tokens), c) for c in candidates), reverse=True)
    if scored and scored[0][0] >= max(2, min(5, len(tokens))):
        candidate = scored[0][1]
        start = page_text.find(candidate)
        return candidate, max(start, 0), False, "Model quote did not match exactly; stored best same-page fallback source sentence"
    return page_text[:500].strip(), 0, False, "Unable to verify model quote against page text"

def highlighted_page_png(pdf_bytes: bytes, page_number: int, quote: str) -> bytes:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_number - 1]
        rects = page.search_for(quote[:250]) if quote else []
        if not rects and quote:
            words = quote.split()[:10]
            rects = page.search_for(" ".join(words))
        for rect in rects[:8]:
            annot = page.add_highlight_annot(rect)
            annot.update()
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False, annots=True)
        return pix.tobytes("png")
