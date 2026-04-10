# Report

Unanticipated events, tool limitations, and deviations from the standard Mondo source-ingest pipeline during development and maintenance.

| Date | Event | Resolution |
|------|--------|------------|
| 2026-04-10 | Phase 9 `verify.py` reports `terms_with_definition: 0` | Confirmed: SPARQL on `icd10cm.owl` finds **no** classes with `obo:IAO_0000115`, `skos:definition`, `rdfs:comment`, or `dcterms:description`. The BioPortal ICD10CM submission, after this repo’s ROBOT pipeline, does not expose textual definitions on classes in those slots—so empty `definition` in LinkML is **correct**, not a transform bug. Labels and synonyms are populated. |

When `just data2owl` fails on very large outputs, document the error and release `icd10cm.linkml.yml` only; the canonical OWL for this OWL-based source remains the ROBOT-built `icd10cm.owl`.
