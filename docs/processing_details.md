# ICD10CM preprocessing: step-by-step detail

This document explains each step of the build pipeline that produces `icd10cm.owl` from the raw BioPortal download.

The pipeline has two parts:

- **Part A (mirror build):** Downloads and cleans the raw BioPortal OWL → `tmp/mirror-icd10cm.owl`
- **Part B (component build):** Filters to relevant terms, remaps and strips properties → `tmp/icd10cm-component.owl`, then copied to `icd10cm.owl` for release

---

## Part A: Mirror build → `tmp/mirror-icd10cm.owl`

### A1. Resolve and download (Mondo skill: acquire)

**Commands:**

- **`uv run python scripts/resolve_version.py > .bioportal.env`** — resolve only (no download). Optional: `just resolve`.
- **`uv run python scripts/acquire.py`** or **`just acquire`** — resolves the latest submission (unless `BIOPORTAL_SUBMISSION_ID` is set), writes `.bioportal.env`, and downloads the raw OWL to **`tmp/.icd10cm.tmp.owl`**.

Set `BIOPORTAL_API_KEY` via **`env/.env`** (copy from `env/.env.example`) or the environment (CI uses the repository secret of the same name).

The `.bioportal.env` file contains:

- `DOWNLOAD_URL` — the BioPortal download URL for that submission
- `SUBMISSION_ID` — the numeric submission ID
- `VERSION_IRI` — a versioned IRI for the submission (used in the annotate step)

---

### A2. Remove imports

**Command:** `robot remove -i tmp/.icd10cm.tmp.owl --select imports`

ROBOT does not simply delete the `owl:imports` line. It makes the ontology **self-contained** by:

1. Resolving the imported ontology (SKOS Core: `http://www.w3.org/2004/02/skos/core`).
2. Copying all axioms and declarations from that ontology into the current file.
3. Dropping the `owl:imports` statement.

The output is larger than the input because it now contains the full SKOS ontology inlined alongside ICD10CM.

---

### A4. Remove properties

**Command:** `robot remove -T config/remove_properties.txt`

Removes every axiom that uses one of the properties listed in `config/remove_properties.txt`:

| Property | Purpose / why removed |
|----------|------------------------|
| `ICD10CM:CODE_ALSO`, `CODE_FIRST`, `USE_ADDITIONAL` | Coding instructions for billing. Not needed for a disease hierarchy. |
| `ICD10CM:EXCLUDES1`, `EXCLUDES2` | "Excludes" notes from the official ICD-10-CM. |
| `ICD10CM:NOTE` | Free-text notes. |
| `ICD10CM:ORDER_NO` | Presentation ordering for the official book. |
| `skos:notation` | Code string (e.g. `"A00.0"`); redundant with other annotations. |
| `hasSTY` (UMLS) | "Has Semantic Type" from BioPortal/UMLS — not part of Mondo's model. |

---

### A5. Annotate

**Command:** `robot annotate --ontology-iri <ONTOLOGY_IRI> --version-iri <VERSION_IRI>`

Sets the `owl:Ontology` header identifiers only (no class or axiom annotations are changed):

- `--ontology-iri` — canonical URL of the published artifact:
  `https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl`
- `--version-iri` — BioPortal submission URL from `.bioportal.env` (e.g. `https://data.bioontology.org/ontologies/ICD10CM/submissions/27/icd10cm.owl`)

---

### A6. Normalize

**Command:** `robot odk:normalize --add-source true -o tmp/mirror-icd10cm.owl`

With `--add-source true` only. Adds a single ontology-level annotation:

- **Property:** `dc:source` (`http://purl.org/dc/elements/1.1/source`)
- **Value:** the version IRI set in the annotate step

This records provenance — where this version of the file came from. The output is `tmp/mirror-icd10cm.owl`, consumed by Part B.

---

## Part B: Component build → `icd10cm.owl`

### B1. Relevant signature

**Command:** `robot query -i tmp/mirror-icd10cm.owl -q sparql/icd10cm-relevant-signature.sparql tmp/icd10cm_relevant_signature.txt`

Queries the mirror for all IRIs matching `http://purl.bioontology.org/ontology/ICD10CM/` and writes one IRI per line to `tmp/icd10cm_relevant_signature.txt`. This is the set of classes to keep.

---

### B2. Merge (entry point)

**Command:** `robot merge -i tmp/mirror-icd10cm.owl`

With a single input, `merge` does not combine ontologies; it just loads the file as the entry point for the chained subcommands that follow.

---

### B3. Rename properties

**Command:** `robot rename --mappings config/property-map.sssom.tsv --allow-missing-entities true --allow-duplicates true`

Maps BioPortal/SKOS/EFO property IRIs to Mondo's preferred IRIs. For example:

- `skos:prefLabel` → `rdfs:label`
- `skos:altLabel` → `oboInOwl:hasExactSynonym`
- `dc:source` → `oboInOwl:source`

`--allow-missing-entities` and `--allow-duplicates` are required because not every property in the mapping file is present in every ICD10CM release.

---

### B4. Remove by signature (complement)

**Command:** `robot remove -T tmp/icd10cm_relevant_signature.txt --select complement --select "classes individuals" --trim false`

Drops every class and individual **not** in the relevant signature. `--trim false` preserves axioms that reference removed terms (they are cleaned up by the next step and the final property removal).

---

### B5. Remove individuals

**Command:** `robot remove -T tmp/icd10cm_relevant_signature.txt --select individuals`

Drops any individuals that were in the relevant signature but should not be in the final output. After this step only **classes** from the relevant set remain.

---

### B6. SPARQL updates

**Command:** `robot query --update sparql/fix_omimps.ru --update sparql/fix-labels-with-brackets.ru --update sparql/exact_syn_from_label.ru`

Three updates applied in order:

1. **`fix_omimps.ru`** — rewrites `MIM:PS*` xrefs to `OMIMPS:*` format.
2. **`fix-labels-with-brackets.ru`** — for labels ending in `(...)` or `[...]`, adds the stripped version as an exact synonym.
3. **`exact_syn_from_label.ru`** — adds an exact synonym copy of every `rdfs:label`.

---

### B7. Remove extra properties

**Command:** `robot remove -T config/properties.txt --select complement --select properties --trim true`

Keeps only the properties in `config/properties.txt` (the Mondo-approved allowlist) and drops everything else. `--trim true` removes dangling references left after property removal.

---

### B8. Annotate

**Command:** `robot annotate --ontology-iri http://purl.obolibrary.org/obo/mondo/sources/icd10cm.owl --version-iri http://purl.obolibrary.org/obo/mondo/sources/<TODAY>/icd10cm.owl`

Sets the final Mondo-style ontology IRI and a date-stamped version IRI.

---

### B9. Output

**Command:** `-o icd10cm.owl`

Final output: `icd10cm.owl` — Mondo's ICD10CM source, published via GitHub Releases and consumed directly by mondo-ingest.

---

## Summary

| Step | Input | Output | Main effect |
|------|-------|--------|-------------|
| A1. Acquire | BioPortal API | `.bioportal.env`, `tmp/.icd10cm.tmp.owl` | Resolve URL + fetch raw OWL (`scripts/acquire.py`). |
| A2–A6. ROBOT chain | `tmp/.icd10cm.tmp.owl` | `tmp/mirror-icd10cm.owl` | Remove imports, drop properties, annotate, add dc:source. |
| B1. Signature | `tmp/mirror-icd10cm.owl` | `tmp/icd10cm_relevant_signature.txt` | List all ICD10CM IRIs. |
| B2–B9. ROBOT chain | `tmp/mirror-icd10cm.owl` | `tmp/icd10cm-component.owl` → copy to `icd10cm.owl` | Filter terms, remap properties, SPARQL fixes, strip to allowlist, annotate. |
| LinkML | `tmp/icd10cm-component.owl` | `icd10cm.linkml.yml` | `transform.py` + `just validate` + `just verify`. |

Published release assets: **`icd10cm.linkml.yml`** and **`icd10cm.owl`** (ROBOT component copy).
