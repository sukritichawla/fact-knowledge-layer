# FactLayer — Superjoin Engineering Assignment

A small, inspectable fact knowledge layer for extracting grounded facts from PDFs and resolving cross-document relationships.

## What it demonstrates

- Structured, Pydantic-validated fact extraction
- Two-stage extraction workflow: optional structured LLM extraction first, comparison second
- Zero-cost offline deterministic fallback for local evaluation when no API key is configured
- Exact page/quote evidence with verification status
- Unit normalization and explicit date/scope fields
- Corroborated / Contradicted / Context-Resolved / Related relationships
- Publication-date metadata for temporal reasoning
- Incremental PDF ingestion with content-addressed document IDs
- Deterministic fact and relationship IDs for safe reprocessing
- Streamlit inspection UI with highlighted source pages
- Deterministic JSON export, Excel export, and optional Google Sheets webhook export
- Explicit failure handling rather than silently accepting unsupported evidence

The assignment asks for grounded facts, cross-document relationships, a simple upload UI/API, four demonstration cases, meaningful Git usage, and README documentation of setup, approach, limitations and demo. This prototype is designed around those requirements.

## Incremental ingestion

Uploaded PDFs are identified by a SHA-256 content hash. A document already present in SQLite is skipped rather than extracted again. New documents are persisted with their source PDF, grounded facts are added to the existing layer, and cross-document relationships are refreshed. The extraction and comparison pipeline does not depend on starter-dataset filenames or hardcoded facts.

## Architecture

```text
PDF upload
   │
   ▼
PyMuPDF page extraction ──► stable document SHA-256 ID
   │
   ▼
chunked extraction LLM ──► Pydantic ExtractionResult
   │
   ▼
quote verification + normalization
   │
   ▼
SQLite knowledge layer
   │
   ▼
comparison LLM + publication-date metadata
   │
   ▼
Pydantic relationships
   │
   ├── Streamlit evidence viewer
   └── Excel / Google Sheets export
```

### Why two LLM calls?

Extraction and comparison have different failure modes. Keeping them separate makes the system easier to test: extraction is responsible for producing grounded atomic facts; comparison is responsible for deciding how already-grounded facts relate. This also avoids asking one prompt to simultaneously discover, normalize and reconcile claims.

### Why SQLite?

The assignment does not require a graph database. SQLite keeps the prototype understandable, persistent, portable and easy to deploy. Facts and relationships are stored as validated JSON payloads, while stable IDs make incremental ingestion straightforward.

### Why Pydantic?

The LLM output is parsed into strict schemas with bounded confidence values and required evidence fields. The application never treats free-form model text as the database contract.

## Evidence grounding

Every persisted fact contains:

- source document ID and filename
- page number
- source quote
- character offsets
- evidence verification status
- optional verification note

If the model's quote cannot be verified, the pipeline does **not** silently mark it exact. It stores a conservative same-page fallback and exposes the failure in the UI.

## Relationship semantics

| Relationship | Meaning |
|---|---|
| Corroborated | Same claim supported independently, allowing harmless wording/rounding differences |
| Contradicted | Incompatible claims under materially matching time/scope/units |
| Context-Resolved | Difference explained by explicit time, scope, units, or measurement definition |
| Related | Same topic, but insufficient evidence for stronger classification |

## Starter dataset examples

See [`docs/case-study-delhivery.md`](docs/case-study-delhivery.md) for grounded examples from the supplied Delhivery PDFs.

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env` only if you want the optional structured-LLM path. **It is not required for local tests or offline dataset evaluation.** Without a key, FactLayer uses deterministic numeric/metric-context extraction and deterministic relationship blocking/comparison.

Run:

```bash
streamlit run main.py
```

Tests:

```bash
pytest
```

## Incremental processing

Each PDF receives a SHA-256-derived ID. If the same file is uploaded again, the UI skips it. New documents are added to the SQLite layer without rebuilding prior documents. Relationship IDs are deterministic so rerunning comparison replaces the same relationship instead of creating duplicates.

## Demo UI

The Streamlit UI is organized as a short evaluator workflow: add PDFs, inspect the knowledge-layer counts, review grounded facts and cross-document relationships, inspect a fact's highlighted source page, view the evaluation audit, and export the resolved layer. The sidebar always states whether the workspace is using optional LLM mode or zero-cost offline mode.

Offline mode requires no API key and makes no API calls. LLM mode is opt-in through `OPENAI_API_KEY`.

## Google Sheets

The prototype supports a `GOOGLE_SHEETS_WEBHOOK_URL` environment variable. The endpoint receives JSON containing the resolved facts and relationships and can be implemented with Google Apps Script or another lightweight integration. See [`docs/google-sheets.md`](docs/google-sheets.md) for a minimal receiver. The same validated layer is also downloadable as deterministic JSON, while Excel remains available as a no-setup tabular fallback.

## Engineering trade-offs

**Chunking vs. global context:** large PDFs are processed in bounded chunks to avoid oversized prompts. This can miss relationships that depend on distant pages; the second-stage comparison partly compensates once facts are in the shared layer.

**LLM vs. deterministic logic:** the LLM discovers semantic facts and proposes relationships, while Pydantic validation, evidence verification, hashing, normalization and persistence are deterministic. A production system would likely add deterministic candidate generation before LLM comparison to reduce cost.

**Quote fallback vs. rejection:** the current fallback preserves an auditable source sentence but marks it unverified. A stricter production mode could reject such facts entirely.

## Limitations

- LLM extraction quality depends on the selected model when API mode is enabled. The offline fallback is intentionally conservative and less semantically rich.
- Scanned/image-only PDFs require OCR, which is not included in this prototype.
- Offline extraction intentionally caps candidates per document to keep local evaluation bounded; richer semantic extraction is available through the optional LLM path.
- Google Sheets is exposed through a webhook rather than requiring service-account credentials in the repository.
- Publication-date extraction is heuristic when a document contains multiple dates.

## Next steps

1. Sentence-ID evidence indexing and deterministic evidence references.
2. Embedding/entity-based candidate blocking before comparison.
3. OCR with confidence metadata for scanned PDFs.
4. Background processing for very large documents.
5. Direct Google Sheets API integration behind a secure deployment secret.
6. Human review queue for low-confidence or unverified evidence.

## AI tools used

OpenAI structured-output parsing is used for fact extraction and relationship comparison. Pydantic defines the machine-readable contract. PyMuPDF handles PDF text/evidence rendering, SQLite provides local persistence, and Streamlit provides the inspection interface.

## Video demo

Add the final demo URL here after recording. Keep the demonstration under three minutes and show: PDF upload → grounded facts → one corroboration → one contradiction → one context resolution → the failure handling path.

### Dataset-scale validation

For reproducible evaluation outside the UI, `scripts/run_dataset.py` recursively discovers PDFs under a directory and sends every file through the same incremental ingestion path used by the Streamlit uploader. It is intentionally filename-agnostic and writes a JSON audit report with per-file status plus document/fact/relationship and evidence-verification counts. If `OPENAI_API_KEY` is absent, the runner automatically uses the zero-cost offline path.

Example:

```bash
python scripts/run_dataset.py path/to/starter-datasets
```

Starter PDFs are kept outside the repository; the repository contains the runner and validation logic rather than hardcoding their filenames or facts.
