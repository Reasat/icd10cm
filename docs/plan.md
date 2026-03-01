# ICD10CM from BioPortal to Mondo component

This document describes the two preprocessing steps previously at [line 67](https://github.com/monarch-initiative/mondo-ingest/blob/65b4a4e0c78ed102c8222a69b3091fab178c6e98/src/ontology/mondo-ingest.Makefile#L67) and [line 198](https://github.com/monarch-initiative/mondo-ingest/blob/65b4a4e0c78ed102c8222a69b3091fab178c6e98/src/ontology/mondo-ingest.Makefile#L198) of mondo-ingest, now implemented in this repo.

The plan is to implement these two preprocessing steps in this repo (icd10cm) and reduce mondo-ingest responsibility. This repo publishes a preprocessed file (`icd10cm.owl`) that is directly ingested by **mondo-ingest** (no further preprocessing required); mondo-ingest no longer calls BioPortal or runs any build step for ICD10CM.

---

## Part A: Mirror Build

Reproduces what used to run in mondo-ingest at [line 67](https://github.com/monarch-initiative/mondo-ingest/blob/65b4a4e0c78ed102c8222a69b3091fab178c6e98/src/ontology/mondo-ingest.Makefile#L67). **Runs in the icd10cm repo.** Produces an intermediate mirror (`tmp/mirror-icd10cm.owl`) that feeds Part B.

**Why this repo takes over the mirror build:** `ICD10_BP_CODE=27` and the BioPortal download URL (including an API key in plain text) are hardcoded in mondo-ingest. Every new ICD10CM release requires a manual version bump there.

### Mirror: build `tmp/mirror-icd10cm.owl`

**Goal:** Resolve the latest BioPortal submission, download, and preprocess into a clean intermediate mirror.

The first two steps are separate invocations. The remaining ROBOT steps (Remove imports → Remove properties → Annotate → Normalize) are chained into a single `robot` invocation; each is a subcommand.

| Step | Command / action |
|------|------------------|
| **Resolve version** | `python3 scripts/get_latest_bioportal.py [--apikey KEY]` — queries BioPortal submissions API, picks the one with the latest `released` date, writes `DOWNLOAD_URL`, `SUBMISSION_ID`, and `VERSION_IRI` to `.bioportal.env`. See `docs/get_latest_version.md` for latest download url logic. |
| **Download** | `wget "$DOWNLOAD_URL" -O .icd10cm.tmp.owl` — fetches raw OWL from BioPortal using the resolved URL. |
| **Remove imports** | `robot remove -i .icd10cm.tmp.owl --select imports` — inlines the imported ontology (e.g. SKOS) then drops the import statement, making the file self-contained. |
| **Remove properties** | `robot remove -T config/remove_properties.txt` — drops coding-instruction and external metadata properties not needed for Mondo (e.g. `EXCLUDES1`, `NOTE`, `hasSTY`). |
| **Annotate** | `robot annotate --ontology-iri https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl --version-iri "$VERSION_IRI"` — sets a stable ontology IRI and a version-specific IRI from the BioPortal submission. |
| **Normalize** | `robot odk:normalize --add-source true -o tmp/mirror-icd10cm.owl` — adds `dc:source` (provenance) from the version IRI. Output is an intermediate file consumed by Part B. |

---

## Part B: Component Build

Reproduces what used to run in mondo-ingest at [line 198](https://github.com/monarch-initiative/mondo-ingest/blob/65b4a4e0c78ed102c8222a69b3091fab178c6e98/src/ontology/mondo-ingest.Makefile#L198). **Runs in the icd10cm repo.** The output of Part A (`tmp/mirror-icd10cm.owl`) is the input here. The final output (`icd10cm.owl`) is published via GitHub Releases and directly consumed by mondo-ingest.

### Component: build `icd10cm.owl`

**Goal:** Turn the mirror into the final Mondo-ready component: only relevant terms, Mondo-style properties and annotations.

### Relevant signature: build `tmp/icd10cm_relevant_signature.txt`

Runs as a separate Make target (prerequisite of the component target). Queries `tmp/mirror-icd10cm.owl` with `sparql/icd10cm-relevant-signature.sparql` and writes one IRI per line (e.g. `http://purl.bioontology.org/ontology/ICD10CM/A00`) to `tmp/icd10cm_relevant_signature.txt`.

### Component: build `icd10cm.owl`

All steps below are chained into a single `robot` invocation; each row is a subcommand.

| Step | Command / action |
|------|------------------|
| **Merge** | `robot merge -i tmp/mirror-icd10cm.owl` — with a single input, `merge` does not combine ontologies; it just loads the file as the entry point for the chained steps that follow. |
| **Rename (properties)** | `robot rename --mappings config/property-map.sssom.tsv --allow-missing-entities true --allow-duplicates true` — map to Mondo's preferred property IRIs. `--allow-missing-entities` and `--allow-duplicates` are required because not every property in the mapping file is present in every ICD10CM release. |
| **Remove by signature (complement)** | `robot remove -T tmp/icd10cm_relevant_signature.txt --select complement --select "classes individuals" --trim false` — drop every class/individual **not** in the relevant signature. Two selectors are needed because a single `remove` cannot simultaneously select "complement of signature" and restrict to classes only. |
| **Remove individuals** | `robot remove -T tmp/icd10cm_relevant_signature.txt --select individuals` — drop the individuals that remain after the previous step, leaving only **classes** from the relevant set. |
| **SPARQL updates** | `robot query --update sparql/fix_omimps.ru --update sparql/fix-labels-with-brackets.ru --update sparql/exact_syn_from_label.ru` — exactly these three updates, in this order: normalize OMIM xrefs, fix labels with brackets, add exact synonyms from labels. |
| **Remove extra properties** | `robot remove -T config/properties.txt --select complement --select properties --trim true` — keep only Mondo-approved properties; `--trim true` removes dangling references left after property removal. |
| **Annotate** | `robot annotate --ontology-iri $(URIBASE)/mondo/sources/icd10cm.owl --version-iri $(URIBASE)/mondo/sources/$(TODAY)/icd10cm.owl` |
| **Output** | `-o icd10cm.owl` |

### Publish

Release `icd10cm.owl` via GitHub Releases:
`https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl`

**Outcome:** `icd10cm.owl` — Mondo's ICD10CM source, used directly by mondo-ingest with no further preprocessing.

---

## Changes in mondo-ingest

Once this repo publishes, mondo-ingest makes the following changes:

- Remove `ICD10_BP_CODE` and the old `ICD10CM` BioPortal download URL.
- Set `ICD10CM` to the GitHub release URL:
  ```
  ICD10CM = https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl
  ```
- Replace the existing mirror target (line 67) with the standard normalized download, consistent with other GitHub-release-based mirrors (ICD10WHO, ICD11, OMIM):
  ```bash
  robot merge -I $(ICD10CM) odk:normalize -o tmp/mirror-icd10cm.owl
  ```
  `--add-source true` is omitted because `dc:source` is already set in the published file.
- Remove the component build target (line 198–208) entirely; `components/icd10cm.owl` is no longer built in mondo-ingest.

### Config and SPARQL files moving to this repo

The following files currently in mondo-ingest `src/ontology/` need to be copied into this repo:

| File in mondo-ingest | Destination in icd10cm |
|----------------------|------------------------|
| `config/property-map.sssom.tsv` | `config/property-map.sssom.tsv` |
| `config/properties.txt` | `config/properties.txt` |
| `sparql/fix_omimps.ru` | `sparql/fix_omimps.ru` |
| `sparql/fix-labels-with-brackets.ru` | `sparql/fix-labels-with-brackets.ru` |
| `sparql/exact_syn_from_label.ru` | `sparql/exact_syn_from_label.ru` |
| `sparql/icd10cm-relevant-signature.sparql` | `sparql/icd10cm-relevant-signature.sparql` |

## Note
Claude claims that, in the linked mondo-ingest makefile (part A), the `--ontology-iri` is set to `https://bioportal.bioontology.org/ontologies/ICD10CM/$@`, where `$@` expands to the Make target path (`tmp/mirror-icd10cm.owl`), producing a broken IRI
