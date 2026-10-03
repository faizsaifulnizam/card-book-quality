# data/raw — raw files are never edited or committed

**Source:** Credit and charge cards — Monetary Authority of Singapore, via data.gov.sg
**Files (fetched by [`src/download.py`](../../src/download.py), which validates structure before replacing):**

| file | dataset | role |
|------|---------|------|
| `credit-charge-cards-quarterly.csv` | [`d_5c8e5801c2a64e2e6b16608296ef3e02`](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view) | primary — 47 quarters, 2014 Q4 → 2026 Q2 |
| `credit-charge-cards-annual.csv` | [`d_b40deadbdc470e97b9e16de99c5e6ee2`](https://data.gov.sg/datasets/d_b40deadbdc470e97b9e16de99c5e6ee2/view) | cross-check — annual, 2014 → 2025 |

**Licence:** Singapore Open Data Licence (© Monetary Authority of Singapore / SingStat).
**Pull:** scripted, `initiate → poll → signed URL` (data.gov.sg v1 public API); manifest (`pull_manifest.json`) carries SHA-256, coverage and the retrieval time — figures read the pull date from it.

**Last pull: 2026-10-03** — quarterly `df7f3a1a…` (2,300 bytes) · annual `ca2dd74f…` (666 bytes).
The raw CSVs themselves are gitignored (this note is the committed record).
