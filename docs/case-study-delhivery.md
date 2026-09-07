# Starter dataset case study — Delhivery

This case study is grounded in the supplied Delhivery starter PDFs. It is a demonstration target for the UI and regression tests; the runtime still extracts facts dynamically from uploaded PDFs.

## Case 1 — Corroborated

**Claim:** FY24 revenue from services was approximately ₹8,142 crore.

- Annual Report 2023-24, page 4: `₹81,415Mn Revenue from services`.
- Q4 FY24 Earnings Presentation, page 6: `₹8,142 Cr FY24 revenue from services`.

The values differ only because one source uses ₹ million and the other uses ₹ crore with rounding. After unit normalization they are approximately the same.

## Case 2 — Likely contradiction

**Claim:** Female workers increased year-on-year during FY24.

The Annual Report, page 8, contains two nearby figures for the same topic: the narrative says the combined on-roll/off-roll female workforce `increased 60% year-on-year`, while the following highlight says `Number of female workers increased by 59% year-on-year`.

The system should surface this as a **likely contradiction / source inconsistency**, not silently choose one number. Because both statements are in the same source and no denominator definition is supplied in the excerpt, the rationale should remain conservative.

## Case 3 — Context-resolved

**Claim:** Delhivery's active-customer count differs between the 2022 prospectus and FY24 reporting.

- Prospectus, page 42: `23,113 Active Customers (excluding those serviced by Spoton)` for the nine months ended December 31, 2021; Spoton is separately stated at `5,533 Active Customers`.
- Q4 FY24 Earnings Presentation, page 8: `No. of Active Customers ... 33,278` for Q4 FY24.

The values should **not** be treated as a direct contradiction: the periods differ and the prospectus explicitly excludes Spoton from its 23,113 figure, while the Q4 table defines the quarterly active-customer metric at the company reporting level.

## Case 4 — Extraction failure

A realistic failure occurs when a model returns a quote whose whitespace/punctuation differs from the PDF text layer. The ingestion pipeline therefore verifies every returned quote against the declared page. If exact matching fails, it records a same-page fallback sentence and marks `evidence.verified=false` instead of pretending the model quote was exact.

This failure is intentionally handled as an audit event. A future version should assign sentence IDs during preprocessing and require the model to reference those IDs.
