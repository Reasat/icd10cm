# icd10cm

Preprocessed ICD-10-CM (US Clinical Modification) from BioPortal for Mondo source ingest — LinkML YAML plus ROBOT-built OWL.

## Setup

1. Get an API key from [BioPortal](https://bioportal.bioontology.org/account).
2. Copy `env/.env.example` → `env/.env` and set `BIOPORTAL_API_KEY`.
3. Install dependencies: `uv sync`

## Run

Requires [ROBOT](https://github.com/ontodev/robot) and the ODK normalize plugin (e.g. via `obolibrary/odkfull` Docker, as in CI).

```bash
just acquire       # resolve + download raw OWL from BioPortal
just build         # mirror → component → YAML → validate → verify → publish OWL
just iterate       # transform → validate → verify → publish-owl (skips acquire/mirror)
```

## Outputs

| File | Description |
|------|-------------|
| `icd10cm.linkml.yml` | Primary artefact for Mondo ingest (LinkML) |
| `icd10cm.owl` | Canonical OWL — ROBOT component output (not YAML round-trip) |

Optional: `just data2owl` emits linkml-OWL from YAML for experiments only; see `docs/report.md`.

## Docs

| Doc | Contents |
|-----|----------|
| [`docs/plan.md`](docs/plan.md) | Pipeline architecture, field mappings, ID scheme |
| [`docs/release_notes.md`](docs/release_notes.md) | Ontology stats and verification results per release |
| [`docs/report.md`](docs/report.md) | Deviations and tool limitations |

## CI

GitHub Actions expects the repository secret `BIOPORTAL_API_KEY` (same variable as in `env/.env`).
