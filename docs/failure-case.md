# Failure Case Log

## Observed failure mode

LLM extraction can return a quote that is semantically correct but not byte-for-byte identical to the PDF text layer because of whitespace normalization, line wrapping, punctuation, or merged lines.

## Detection

`app/pdf.py::locate_quote` first searches for an exact substring, then tries whitespace-normalized matching. If neither succeeds, it selects a conservative same-page sentence based on shared distinctive tokens.

## Handling

The actual page text is persisted as evidence. `Evidence.verified` and `verification_note` make the fallback visible in the UI and export rather than silently accepting an unverified quote.

## Why this is a useful failure case

A fact knowledge layer should optimize for **auditability over apparent recall**. An unsupported quote can make a correct-looking fact impossible to verify.

## Improvement

Preprocess each page into stable sentence/bullet IDs and require the extraction model to return one or more source IDs. The application can then verify IDs deterministically. OCR confidence should become another evidence field for scanned PDFs.
