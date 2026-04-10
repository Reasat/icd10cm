# Release notes

Ontology statistics and Phase 9 verification results. Update the **Latest verification** section when you cut a new GitHub release (after `just build` and before or after `just release`).

---

## Phase 9 checklist (Mondo source-ingest)

| Check | How |
|-------|-----|
| Title and version present | `scripts/verify.py` |
| No duplicate term IDs | `verify.py` |
| Non-empty `label` for all terms | `verify.py` |
| All `parents` resolve in-file | `verify.py` |
| Version vs upstream (optional) | `EXPECTED_VERSION=<id> just verify` |
| LinkML schema validation | `just validate` (`linkml.validator.cli`) |
| OWL loads in ROBOT / Protégé | Manual (see below) |
| `robot diff` vs mondo-ingest reference | Optional when migrating |

**OWL source:** released OWL is **`icd10cm.owl`** (ROBOT component). No `linkml-owl` derived OWL is required for Phase 9.

---

## Latest verification

**When:** 2026-04-10 (local full build + verify; artefacts present in repo workspace, not committed).

**Upstream:** BioPortal ICD10CM submission **`SUBMISSION_ID=28`** (from `.bioportal.env` after `just acquire`). YAML **`version`** field: **`2026`** (ICD10CM release id from ontology metadata).

| Metric | Value |
|--------|------:|
| Terms | 98,506 |
| Unique IDs | 98,506 |
| Broken parent refs | 0 |
| Terms with `definition` | 0 |
| Exact synonym items (non-empty) | 114,557 |
| Related / narrow / broad synonym items | 0 |
| Root terms (`is_root`) | 23 |
| Deprecated terms | 0 |

| Step | Result |
|------|--------|
| `just validate` | **PASS** — no issues found |
| `just verify` | **PASS** |
| `EXPECTED_VERSION=2026 just verify` | Not run for this entry; optional when version must match a pinned upstream id |

**Manual — OWL:** `robot merge -i icd10cm.owl -o /tmp/icd10cm_phase9_check.owl` completed successfully (ROBOT accepts the released file).

**Protégé:** not run in this session; spot-check before a major release if desired.

---

## Template for the next release

- **Git tag:**
- **Date:**
- **BioPortal `SUBMISSION_ID`:** (from `.bioportal.env`)
- **YAML `version`:** (must reflect upstream ICD10CM release id)
- Paste output of: `just check` and `just verify` (and `EXPECTED_VERSION=... just verify` if used)
- **Manual OWL:** ROBOT / Protégé result
- **Notes:**
