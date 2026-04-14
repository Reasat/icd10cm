# Justfile for icd10cm — full source pipeline (Mondo source-ingest scaffold)
# Prerequisites: uv (https://docs.astral.sh/uv/), robot
# Canonical icd10cm.owl = ROBOT component (tmp/icd10cm-component.owl), not linkml-data2owl.
# Usage: just <recipe>

SCHEMA        := "linkml/mondo_source_schema.yaml"
MIRROR        := "tmp/mirror-icd10cm.owl"
COMPONENT_OWL := "tmp/icd10cm-component.owl"
TMP_OWL       := "tmp/.icd10cm.tmp.owl"
SIG_TXT       := "tmp/icd10cm_relevant_signature.txt"
BP_ENV        := ".bioportal.env"
YAML_OUT      := "icd10cm.linkml.yml"
OWL_OUT       := "icd10cm.owl"
ONTOLOGY_IRI  := "https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl"
URIBASE       := "http://purl.obolibrary.org/obo"
ROBOT                  := "robot"
# Optional: set when using ROBOT plugins (e.g. odk). Empty is fine for stock robot.
ROBOT_PLUGINS_DIRECTORY := env_var_or_default("ROBOT_PLUGINS_DIRECTORY", "")
PYTHON                 := "uv run python"

# ── Setup ─────────────────────────────────────────────────────────────────────

# Install all Python dependencies declared in pyproject.toml
install:
    uv sync

# Pin linkml-owl + main-branch linkml/linkml-runtime (mondo-source-ingest comma-in-synonym workaround).
# Run after `uv sync` in CI before `just build` or `just test`.
dependencies:
    uv pip install linkml-owl==0.5.0 \
        "linkml @ git+https://github.com/linkml/linkml.git@main#subdirectory=packages/linkml" \
        "linkml-runtime @ git+https://github.com/linkml/linkml.git@main#subdirectory=packages/linkml_runtime"

# ── Resolve BioPortal submission ──────────────────────────────────────────────

# Resolve ICD10CM submission from BioPortal → .bioportal.env (no download)
# Credentials: env/.env (see env/.env.example). Optional: BIOPORTAL_SUBMISSION_ID.
resolve:
    {{ PYTHON }} scripts/resolve_version.py > {{ BP_ENV }}
    @echo "Resolved latest BioPortal submission; see {{ BP_ENV }}"

# Print the resolved BioPortal env (download URL, submission ID, version IRI)
env: resolve
    @cat {{ BP_ENV }}

# Download raw OWL from BioPortal → .bioportal.env + tmp/.icd10cm.tmp.owl (Mondo skill: acquire)
acquire:
    {{ PYTHON }} scripts/acquire.py

# ── Part A: Mirror build ──────────────────────────────────────────────────────

# Fetch raw OWL from BioPortal (scripts/acquire.py), then remove imports + unwanted properties,
# annotate with stable IRI and version IRI, normalize → tmp/mirror-icd10cm.owl
mirror: acquire
    #!/usr/bin/env bash
    set -euo pipefail
    source {{ BP_ENV }}
    mkdir -p tmp
    echo "Running: robot remove + annotate + odk:normalize → {{ MIRROR }}"
    ROBOT_PLUGINS_DIRECTORY={{ ROBOT_PLUGINS_DIRECTORY }} \
    {{ ROBOT }} remove -i {{ TMP_OWL }} --select imports \
        remove -T config/remove_properties.txt \
        annotate \
            --ontology-iri {{ ONTOLOGY_IRI }} \
            --version-iri "$VERSION_IRI" \
        odk:normalize --add-source true -o {{ MIRROR }}
    rm -f {{ TMP_OWL }}
    echo "Built {{ MIRROR }}"

# ── Part B: Component build ───────────────────────────────────────────────────

# Query mirror for all ICD10CM term IRIs (relevant signature).
signature: mirror
    mkdir -p tmp
    {{ ROBOT }} query -i {{ MIRROR }} -q sparql/icd10cm-relevant-signature.sparql {{ SIG_TXT }}
    @echo "Built {{ SIG_TXT }}"

# Filter to relevant terms, rename properties, apply SPARQL fixes, strip to Mondo properties.
component: signature
    #!/usr/bin/env bash
    set -euo pipefail
    TODAY="$(date +%Y-%m-%d)"
    echo "Running: robot merge + rename + remove + query --update + annotate → {{ COMPONENT_OWL }}"
    ROBOT_PLUGINS_DIRECTORY={{ ROBOT_PLUGINS_DIRECTORY }} \
    {{ ROBOT }} merge -i {{ MIRROR }} \
        rename --mappings config/property-map.sssom.tsv \
            --allow-missing-entities true --allow-duplicates true \
        remove -T {{ SIG_TXT }} --select complement --select "classes individuals" --trim false \
        remove -T {{ SIG_TXT }} --select individuals \
        query \
            --update sparql/fix_xref_prefixes.ru \
            --update sparql/fix_omimps.ru \
            --update sparql/fix-labels-with-brackets.ru \
            --update sparql/exact_syn_from_label.ru \
        remove -T config/properties.txt --select complement --select properties --trim true \
        annotate \
            --ontology-iri {{ URIBASE }}/mondo/sources/icd10cm.owl \
            --version-iri {{ URIBASE }}/mondo/sources/$TODAY/icd10cm.owl \
        -o {{ COMPONENT_OWL }}
    echo "Built {{ COMPONENT_OWL }}"

# ── Transform (LinkML pipeline) ───────────────────────────────────────────────

# Serialize component OWL → schema-conformant YAML (no data fixes; ROBOT did them).
transform: component
    {{ PYTHON }} scripts/transform.py \
        --input {{ COMPONENT_OWL }} \
        --schema {{ SCHEMA }} \
        --output {{ YAML_OUT }}

# ── Validate ──────────────────────────────────────────────────────────────────

# Validate YAML against the LinkML schema
validate:
    uv run python -m linkml.validator.cli -s {{ SCHEMA }} -C OntologyDocument {{ YAML_OUT }}

# Structural checks on YAML (Phase 9 — scripts/verify.py).
# Optional: EXPECTED_VERSION=2026 just verify  — YAML version must match upstream ICD10CM release id.
verify:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "${EXPECTED_VERSION:-}" ]; then
      uv run python scripts/verify.py --yaml "{{ YAML_OUT }}" --expected-version "$EXPECTED_VERSION"
    else
      uv run python scripts/verify.py --yaml "{{ YAML_OUT }}"
    fi

check: validate verify

# ── OWL publish (canonical) ───────────────────────────────────────────────────

# Full-fidelity OWL = ROBOT component (no YAML round-trip). Copies tmp → repo root.
publish-owl:
    cp {{ COMPONENT_OWL }} {{ OWL_OUT }}
    @echo "Published {{ OWL_OUT }} (identical to {{ COMPONENT_OWL }})"

# Optional: regenerate OWL from YAML via linkml-owl (lossy vs component; for experiments only).
data2owl:
    uv run python -m linkml_owl.dumpers.owl_dumper \
        --schema {{ SCHEMA }} \
        -o icd10cm_from_linkml.owl \
        {{ YAML_OUT }}

# ── Composite targets ─────────────────────────────────────────────────────────

# Full build: mirror → component → YAML → validate → verify → copy component OWL to {{ OWL_OUT }}
build: component transform validate verify publish-owl
    @echo "Build complete: {{ YAML_OUT }} (LinkML) and {{ OWL_OUT }} (ROBOT component copy)"

# Re-run transform → validate → verify → publish-owl (assumes component already built)
iterate: transform validate verify publish-owl
    @echo "Iteration complete: {{ YAML_OUT }} valid; {{ OWL_OUT }} = component copy"

# ── Tests ─────────────────────────────────────────────────────────────────────

# Run all tests
test:
    uv run python -m unittest discover -s tests -p "test_*.py" -v

# ── Cleanup ───────────────────────────────────────────────────────────────────

# Remove all generated files
clean:
    rm -f {{ OWL_OUT }} {{ YAML_OUT }} icd10cm_from_linkml.owl {{ TMP_OWL }} {{ BP_ENV }}
    rm -rf tmp/

# ── Docs ──────────────────────────────────────────────────────────────────────

# Run mondo-ingest Make help and save output to docs/mondo-ingest-help.txt
mondo-ingest-help:
    mkdir -p docs
    make -C ../mondo-ingest/src/ontology help > docs/mondo-ingest-help.txt
    @echo "Saved to docs/mondo-ingest-help.txt"

# ── Release ───────────────────────────────────────────────────────────────────

# Create a GitHub release with both YAML and OWL attached.
# Usage: just release v20250310-1
release tag:
    gh release create {{ tag }} \
        --title "Release {{ tag }}" \
        --generate-notes \
        {{ YAML_OUT }} \
        {{ OWL_OUT }}
