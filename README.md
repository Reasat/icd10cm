# icd10cm

Preprocessed **ICD-10-CM** (US Clinical Modification) ontology for downstream consumers (e.g. [Mondo](https://github.com/monarch-initiative/mondo)).

## What this repo does

1. Resolves the **latest** ICD10CM submission from [BioPortal](https://bioportal.bioontology.org/ontologies/ICD10CM) via API (no hardcoded submission ID).
2. Downloads the ontology and runs preprocessing (mirror + component build) as in [mondo-ingest](https://github.com/monarch-initiative/mondo-ingest):
   - **Mirror:** remove imports, remove unwanted properties (`config/remove_properties.txt`), set ontology/version IRI, normalize.
   - **Component:** filter to relevant ICD10CM terms, remap properties to Mondo conventions, apply SPARQL fixes, keep only allowed properties; output `icd10cm.owl`.
3. Publishes the result as **GitHub Release** assets so pipelines can pull a stable URL instead of depending on BioPortal at build time.

## Download

- **Latest release:**  
  https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl

## Build locally

- **Requirements:** [ROBOT](https://github.com/ontodev/robot), Python 3, `wget`. Run `pip install -r requirements.txt` for the resolve script and tests.

- **API key:** Get a key from [BioPortal](https://bioportal.bioontology.org/account) and set `BIOPORTAL_API_KEY` (or pass `apikey=YOUR_KEY` to make).

```bash
export BIOPORTAL_API_KEY=your_key
make build
```

Output: `icd10cm.owl`. Run `make test` to run the test suite (requires ROBOT).

## CI

GitHub Actions (see [.github/workflows/release.yml](.github/workflows/release.yml)) can build and create a new release on schedule, on push to `main`, or via **workflow_dispatch**. Configure the repository secret **BIOPORTAL_API_KEY** for the workflow to access BioPortal.

## License

ICD-10-CM content is from the National Center for Health Statistics / CMS; see [BioPortal ICD10CM](https://bioportal.bioontology.org/ontologies/ICD10CM) and UMLS license terms. This repository’s build scripts and config are provided under an open license as in the Monarch Initiative repos.
