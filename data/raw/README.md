# data/raw — raw files, never edited

**Source:** Credit and charge cards — Monetary Authority of Singapore, via data.gov.sg
**Files (fetched by [`src/download.py`](../../src/download.py), which validates structure before replacing):**

| file | dataset | role |
|------|---------|------|
| `credit-charge-cards-quarterly.csv` | [`d_5c8e5801c2a64e2e6b16608296ef3e02`](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view) | primary — 47 quarters, 2014 Q4 → 2026 Q2 |
| `credit-charge-cards-annual.csv` | [`d_b40deadbdc470e97b9e16de99c5e6ee2`](https://data.gov.sg/datasets/d_b40deadbdc470e97b9e16de99c5e6ee2/view) | cross-check — annual, 2014 → 2025 |

**Licence:** Singapore Open Data Licence (© Monetary Authority of Singapore / SingStat). Redistribution is allowed with attribution — which is why these two small CSVs (plus the metadata JSONs and the pull manifest) are **committed to the repo as vendored copies**: a clone reproduces the pipeline offline and CI runs it with no network.

**Pull:** scripted, `initiate → poll → signed URL` (data.gov.sg v1 public API); `pull_manifest.json` records file-byte SHA-256, coverage and retrieval time — figures read the pull date from it. The downloader's freshness floor rejects a pull whose latest quarter is more than two quarters old. This note describes the manifest, not a newly performed hash comparison.

**Last pull: 2026-10-03** — quarterly `df7f3a1a…` (2,300 bytes) · annual `ca2dd74f…` (666 bytes).
**Fixed historical analysis:** the written report refers to the 2026-10-03 snapshot, not an automatically updating feed. `dataset-metadata-quarterly.json` and `dataset-metadata-annual.json` are **historical reference captures**; CSV refresh does not guarantee that these JSONs refresh alongside it.

Re-pull: `python src/download.py --force`. Before publication, review both datasets and their annual overlap, manifest, generated artifacts, fixed-snapshot text and tests together. Do not assume cross-stage rollback on a failed run. The manifest contains file-byte hashes; this note does not claim a newly performed integrity check.

Publisher-definition retrieval limits and the source trail are recorded in [`docs/data_audit.md`](../../docs/data_audit.md).
