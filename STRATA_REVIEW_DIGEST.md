# Strata result review digest

Reviewed 33 results pending at the start of this intervention. The five S001–S005 baseline outputs were previously source-reviewed and published. “Accepted” means useful as internal metadata, not proof beyond the cited source. Full verbose review-per-note files are rejected as standalone deliverables; their concrete corrections are captured here.

| Task | Disposition | Review outcome |
|---|---|---|
| `PS5-INV-06` | corrected | Fix numerical and hash-match claims; original note now corrected. |
| `PS5-INV-08` | accepted_internal | Useful test-name navigation, internal only; does not substitute for code/tests. |
| `NAGI-DEP-01` | rejected_low_value | Generic dependency summary adds no verifiable missing-input detail. |
| `NAGI-DEP-03` | rejected_incomplete | Manifest summary used truncated input and cannot support completeness claims. |
| `NAGI-DEP-04` | rejected_overclaim | Reference-closure conclusion exceeds the declared source evidence. |
| `PS5-AMD-01` | corrected_in_digest | Manifest note requires explicit limits: fetch templates, destination, sizes and hashes unverified. |
| `PS5-AMD-02` | corrected_in_digest | Loader review distinguishes a quarter-table upper bound from exact payload extent and records omitted validation gates. |
| `PS5-AMD-03` | corrected_in_digest | Historical M433–M441 design note is not current firmware or hardware evidence. |
| `PS5-AMD-04` | corrected_in_digest | Separate source-code observations from design notes; no firmware bytes or hardware initialization were tested. |
| `PS5-AMD-05` | corrected_in_digest | Portability conclusions remain source-derived; shared IP does not establish binary or boot compatibility. |
| `STRATA-OPS-02` | rejected_low_value | Repeats generic state coverage without a measured defect or test. |
| `STRATA-OPS-03` | actionable_followup | Watchdog exception handling merits a bounded regression test; note remains internal. |
| `PS5-INV-09` | accepted_internal | Useful provenance caveat; originals stay outside Git and provenance remains unverified. |
| `PS5-INV-10` | rejected_duplicate | Duplicates the existing cross-version limits without new evidence. |
| `NAGI-DEP-05` | rejected_inaccurate | Conflates build runs and contains unsupported release-state claims. |
| `PS5-INV-11` | rejected_low_value | Artifact-existence check has no lasting engineering value. |
| `REVIEW-PS5-INV-02` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-INV-03` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-INV-04` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-INV-05` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-INV-06` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-NAGI-DEP-01` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-NAGI-DEP-03` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-NAGI-DEP-04` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-AMD-01` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-AMD-02` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-AMD-03` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-AMD-04` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-AMD-05` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-STRATA-OPS-02` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-INV-09` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-PS5-INV-10` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |
| `REVIEW-NAGI-DEP-05` | rejected_redundant | One-review-per-note artifact is redundant; substantive corrections are consolidated in STRATA_REVIEW_DIGEST.md. |

## Verified operational work

- Five pinned Nagi Python build dependencies are installed under `D:\BC250-Development\scratch\py`; import and distribution-version checks passed: Meson 1.12.0, Mako 1.4.1, MarkupSafe 3.0.3, PyYAML 6.0.3 and packaging 25.0.
- Existing PS5 inventory metadata was summarized deterministically: 40 candidates, 40 parser bounds valid, 34 zero-function reports, six positive-function reports, no duplicate candidate SHA-256 values. This reads JSON only and does not identify firmware components.
- Review generation is disabled; backlog replenishment must use implementation/validation tasks. The scheduler rotates among available task areas and resumes a running task first.
- Automatic publication now requires an explicit unit-tested-code policy, a declared unittest command and paths limited to tools Python/JSON artifacts. The existing branch, empty-index and credential checks remain.

## Limits

The 40-candidate PS5 summary is metadata, not new disassembly. Ghidra function counts do not prove complete analysis. The supplied firmware provenance is still unverified; no firmware binary was added to Git.


## Additional validated result

- `NAGI-PYDEPS-VERIFY-01`: accepted after Codex corrected the generated verifier against `docs/build.md`. It checks Meson 1.12.0, Mako 1.4.1, MarkupSafe 3.0.3, PyYAML 6.0.3 and packaging 25.0 from the isolated target, without installing packages. Synthetic tests and a read-only check of the current target passed.
- `STRATA-PUBLISH-GATE-01`: accepted after mocked-Git regression checks. Large deletions to tracked files are rejected before staging.
