# Workbook release identities

The recommended frozen download is [v1.0.2](https://github.com/faizsaifulnizam/card-book-quality/releases/tag/v1.0.2). This ledger records saved anonymous-download evidence from 10 October 2026, not a new download or a claim about current server bytes. Current source output has the corrected formulas and newly qualified notes; it therefore differs in bytes from the frozen release.

| Saved artifact | SHA-256 | Status |
|---|---|---|
| v1.0 downloaded asset | `153ccf4abff49d5147b6868e099ea3d5a2131af4817c31582c70a3bc07d2d91d` | Superseded; differs from its tag, cause and timing unknown |
| v1.0 tagged workbook | `c88f7f9d905a098c9cfea85f9129164ed753fc7b081088d67c0cfe9dcf97b8cc` | Historical; tag ref `af5c25661d5486f7ec71376de5f6fe5d1b1c09b0` |
| v1.0.1 downloaded/tagged asset | `153ccf4abff49d5147b6868e099ea3d5a2131af4817c31582c70a3bc07d2d91d` | Superseded; tag ref `754128210615c4291e345c4df0be7e374b5a0917` |
| v1.0.2 saved downloaded asset / pre-repair current workbook | `6dc5fdfdaa4836f7e882b82f67ada7d8f7388d41201808db2d6d9bf303ebfa91` | Corrected frozen formula surface; local v1.0.2 tag absent, tag equality not newly verified |

The saved v1.0/v1.0.1 downloads omit current-minus-prior subtraction in `Quarterly!J2:J48` and omit the 2015 baseline needed for the first annual comparison. This is historical formula evidence, not an observed legacy-engine display. Current formulas already subtract current and prior rates and include the baseline; no formula rewrite is justified for these old defects. Original assets/tags are retained, not silently replaced.

## Publication-dependent follow-up

**Public release-description updates remain pending** separate authorization and exact-target read-back. Proposed notice for both old releases:

> Superseded by v1.0.2. This workbook's Quarterly rate-change column omits current-minus-prior subtraction, and its Annual bridge omits the 2015 baseline. Use the corrected [v1.0.2 workbook](https://github.com/faizsaifulnizam/card-book-quality/releases/tag/v1.0.2) for quick checks. The original asset is retained for historical traceability.

For v1.0 add:

> The saved downloaded asset SHA-256 is `153ccf4abff49d5147b6868e099ea3d5a2131af4817c31582c70a3bc07d2d91d`, unlike the tagged workbook `c88f7f9d905a098c9cfea85f9129164ed753fc7b081088d67c0cfe9dcf97b8cc`; cause and timing unknown.

Before publishing, anonymously re-download each exact asset and compare its bytes to this ledger, resolve current tag commits, and verify the notices and recommended link. A local draft is not a release edit. LibreOffice-converted test copies are not release replacements.
