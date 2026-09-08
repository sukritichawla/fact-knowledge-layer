# FactLayer

A small document intelligence system that extracts facts from PDFs, connects them to the source evidence, and compares facts across documents.

Built for the Superjoin VIT 2026 Engineering Intern assignment.

## Demo

Live app: https://fact-knowledge-layer.streamlit.app/

Demo video: https://drive.google.com/file/d/1y7BuxbW7l27guge8TLGo97gcDRmEhR2P/view?usp=sharing

Github repository: https://github.com/sukritichawla/fact-knowledge-layer

## What it does

FactLayer takes PDF documents and builds a simple knowledge layer from them.

For each extracted fact, the system keeps:

- the fact itself
- its value and normalized value
- the source document
- the source page
- the original evidence text
- confidence and verification status

Facts from different documents can then be compared. The system tries to determine whether they are:

- **Corroborated** — both documents support the same fact
- **Contradicted** — the claims conflict
- **Context-Resolved** — the numbers look different but have different time periods, scopes, units, etc.
- **Related** — the facts are connected but cannot be directly compared

The goal is not to assume that two similar numbers mean the same thing. The surrounding context is important.

## Example

One example from the Delhivery documents is FY24 revenue.

The annual report gives:

`₹81,415 Mn`

The Q4 FY24 earnings presentation gives:

`₹8,142 Cr`

After converting the units, these refer to the same FY24 revenue figure, so FactLayer treats them as corroborating evidence rather than contradictory numbers.

Another example is active customers:

- `23,113` active customers in the prospectus
- `33,278` active customers in the FY24 earnings presentation

These are not treated as a direct contradiction because they refer to different periods and scopes. The prospectus figure also explicitly excludes customers serviced by Spoton.

The system also preserves cases where the source itself appears inconsistent. For example, the annual report contains both `60%` and `59%` figures for year-on-year female workforce growth.

## How it works

The basic pipeline is:

```text
PDF
 ↓
Text + page extraction
 ↓
Fact extraction
 ↓
Evidence verification
 ↓
Value normalization
 ↓
Cross-document comparison
 ↓
Relationship + explanation
 ↓
UI / JSON / Excel
```

### 1. PDF ingestion

PDFs can be uploaded directly through the Streamlit UI.

Documents are identified using a content hash. This means uploading the exact same document again does not require processing it again.

New documents can be added without changing the code or adding document-specific rules.

### 2. Fact extraction

The extraction layer looks for meaningful statements containing numerical or measurable information and keeps the surrounding text as evidence.

Each fact is associated with its source page and evidence quote.

There are two extraction modes:

- **OpenAI mode** — uses an LLM for richer fact extraction and comparison
- **Offline mode** — uses deterministic local extraction and comparison without requiring an API key

The offline implementation is mainly useful for running and evaluating the project without API costs.

### 3. Normalization

Values are normalized before comparison.

For example:

```text
81,415 Mn
8,142 Cr
```

are converted into comparable numeric values.

The normalization layer handles units such as:

- thousand / k
- million / mn
- billion / bn
- crore / cr
- percentages
- common currency symbols

This helps avoid treating differences in presentation as contradictions.

### 4. Comparing facts

Potentially related facts are compared using their text, metric context, values and surrounding information.

The comparison considers things such as:

- metric
- value
- unit
- reporting period
- scope
- qualifiers
- source document

The result is stored as a relationship with an explanation rather than just a similarity score.

## Evidence

Evidence is treated as part of the fact rather than something added later.

The UI lets you select a fact and inspect:

- source document
- page number
- original quote
- character offsets
- verification status
- relevant section of the PDF

The system also verifies that the stored evidence can actually be found in the source text.

This makes it possible to detect an extraction/evidence failure instead of silently presenting an unsupported fact.

## Required evaluation cases

The repository contains four evaluation cases in:

`examples/evaluation-cases.json`

They cover the four cases from the assignment.

| Case | Documents | Evidence | Result |
|---|---|---|---|
| Corroboration | Annual Report + Q4 Presentation | p4 / p6 | 81,415 Mn = 8,142 Cr |
| Contradiction | Annual Report | p8 | 60% vs 59% |
| Context | Prospectus + Q4 Presentation | p42 / p8 | Different periods/scopes |
| Failure | Annual Report | p4 | Incorrect quote rejected |

### 1. Corroborated fact

Delhivery FY24 revenue:

- Annual Report: `₹81,415 Mn`
- Q4 FY24 presentation: `₹8,142 Cr`

The values match after normalization.

### 2. Likely contradiction

The Delhivery annual report contains two different statements for female workforce growth:

- `60% year-on-year`
- `59% year-on-year`

Both are preserved as source claims rather than choosing one arbitrarily.

### 3. Context-resolved difference

Active customers:

- Prospectus: `23,113`, excluding customers serviced by Spoton
- FY24 earnings presentation: `33,278`

The figures have different periods/scopes, so they should not be treated as a direct contradiction.

### 4. Extraction / evidence failure

The evaluation also includes a deliberately incorrect evidence quote.

The verifier detects that the quote does not exist in the referenced source and marks the evidence as unverified.

This is intentional. A document extraction system should be able to say that its evidence is wrong instead of assuming every extracted result is correct.

## Project structure

```text
fact-knowledge-layer/
│
├── app/
│   ├── db.py
│   ├── engine.py
│   ├── export.py
│   ├── ingestion.py
│   ├── llm.py
│   ├── local_compare.py
│   ├── local_extract.py
│   ├── models.py
│   ├── pdf.py
│   ├── ui.py
│   └── ui_helpers.py
│
├── docs/
│   ├── case-study-delhivery.md
│   ├── failure-case.md
│   └── google-sheets.md
│
├── examples/
│   └── evaluation-cases.json
│
├── scripts/
│   ├── run_dataset.py
│   └── validate_case_study.py
│
├── tests/
│   └── ...
│
├── main.py
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```

## Running locally

### 1. Clone the repository

```bash
git clone https://github.com/sukritichawla/fact-knowledge-layer.git
cd fact-knowledge-layer
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the application

```bash
streamlit run main.py
```

Open the Streamlit URL shown in the terminal.

You can then upload PDFs from the UI and inspect the extracted facts and relationships.

## Optional LLM mode

The project can use the OpenAI API for LLM-based extraction and comparison.

Create a `.env` file based on `.env.example`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
```

If an API key is not available, the application falls back to the local deterministic implementation.

No API keys are included in the repository.

## Running the tests

```bash
pytest -q
```

The test suite covers the core extraction, normalization, comparison, evidence verification, ingestion and UI helper behaviour.

## Evaluating the starter dataset

The dataset evaluation script automatically selects OpenAI mode when an API key is available and otherwise uses offline mode.

```bash
python scripts/run_dataset.py
```

The evaluation output is written to:

```text
data/evaluation-report.json
```

The four source-backed evaluation cases can also be checked directly:

```bash
python scripts/validate_case_study.py
```

## Storage

SQLite is used for local persistence.

The database stores documents, extracted facts and relationships so that newly uploaded documents can be added without rebuilding the whole knowledge layer.

## Design decisions

### Why not just use embeddings?

Semantic similarity is useful for finding potentially related facts, but similarity alone does not tell us whether two claims agree.

For example:

```text
23,113 active customers
33,278 active customers
```

could look contradictory without considering the reporting period and scope.

FactLayer therefore separates:

1. finding potentially related facts
2. normalizing their values
3. checking their context
4. deciding the relationship

### Why keep the original evidence?

An extracted fact without its source is difficult to trust.

Keeping the original quote and page reference makes the output inspectable and also gives us a way to verify the extraction.

### Why have an offline mode?

The assignment should be runnable without requiring an evaluator to provide an API key or pay for API usage.

The offline mode is less capable than the LLM-based pipeline, but provides a deterministic fallback for basic extraction and comparison.

## Limitations

This is a prototype, so there are several things I would improve.

- PDF extraction can still be noisy, especially with complex layouts and tables.
- The local extraction mode is intentionally simple and can miss facts or produce irrelevant numerical candidates.
- Context resolution is not guaranteed to be correct for every type of document.
- A stronger production system would need better entity and metric resolution.
- Very large PDFs would benefit from more efficient chunking and parallel processing.
- Relationship detection could be improved with a dedicated retrieval layer before comparison.
- The current schema is flexible enough for the starter dataset, but a production version would need stronger support for evolving fact types.

## What I would build next

If I continued the project, I would focus on:

1. Better table extraction for financial reports.
2. Entity and metric linking across differently worded documents.
3. A retrieval layer to reduce the number of fact pairs that need comparison.
4. More explicit temporal and scope modelling.
5. Confidence calibration using a larger evaluation dataset.
6. Better handling of corrections and later versions of the same document.
7. More scalable storage for large document collections.

## AI tools used

I used AI assistance during development for debugging, code review, implementation ideas and iteration.

The final repository contains the implementation, tests and evaluation scripts used to run the project.

## Git history

The project was developed incrementally using Git.

The commits reflect additions such as:

- initial knowledge layer
- knowledge layer exports
- fact comparison reasoning
- evidence inspection
- incremental document ingestion
- dataset evaluation
- offline evaluation and case validation
- UI and deployment fixes

## Additional notes

The starter Delhivery and India macroeconomy PDFs were used for evaluation.

The implementation does not contain hard-coded starter filenames or individual fact values. New PDFs can be uploaded through the UI and processed using the same pipeline.

The main design goal was to keep the system understandable: every extracted fact should be traceable back to the document, and every cross-document relationship should have some explanation behind it.

---

## Repository

https://github.com/sukritichawla/fact-knowledge-layer
