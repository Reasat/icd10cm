# Justfile for icd10cm — full source pipeline (replaces Makefile)
# Prerequisites: uv (https://docs.astral.sh/uv/), robot, wget
# Usage: just <recipe>

SCHEMA        := "linkml/mondo_source_schema.yaml"
MIRROR        := "tmp/mirror-icd10cm.owl"
COMPONENT_OWL := "tmp/icd10cm-component.owl"
TMP_OWL       := "tmp/.icd10cm.tmp.owl"
SIG_TXT       := "tmp/icd10cm_relevant_signature.txt"
BP_ENV        := ".bioportal.env"
YAML_OUT      := "icd10cm.yaml"
OWL_OUT       := "icd10cm.owl"
ONTOLOGY_IRI  := "https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl"
URIBASE       := "http://purl.obolibrary.org/obo"
ROBOT                  := "robot"
ROBOT_PLUGINS_DIRECTORY := env("ROBOT_PLUGINS_DIRECTORY")
PYTHON                 := "uv run python"

# ── Setup ─────────────────────────────────────────────────────────────────────

# Install all Python dependencies declared in pyproject.toml
install:
    uv sync

# ── Resolve BioPortal submission ──────────────────────────────────────────────

# Resolve latest ICD10CM submission from BioPortal → .bioportal.env
# Reads BIOPORTAL_API_KEY from environment or .env file.
resolve:
    #!/usr/bin/env bash
    set -euo pipefail
    # Load .env if it exists so BIOPORTAL_API_KEY is available.
    [ -f .env ] && export $(grep -v '^#' .env | xargs)
    KEY="${BIOPORTAL_API_KEY:-}"
    if [ -z "$KEY" ]; then
      echo "Error: set BIOPORTAL_API_KEY in .env or environment" >&2
      exit 1
    fi
    {{ PYTHON }} scripts/get_latest_bioportal.py > {{ BP_ENV }}
    echo "Resolved latest BioPortal submission; see {{ BP_ENV }}"

# Print the resolved BioPortal env (download URL, submission ID, version IRI)
env: resolve
    @cat {{ BP_ENV }}

# ── Part A: Mirror build ──────────────────────────────────────────────────────

# Download raw OWL from BioPortal, remove imports + unwanted properties,
# annotate with stable IRI and version IRI, normalize → tmp/mirror-icd10cm.owl
mirror: resolve
    #!/usr/bin/env bash
    set -euo pipefail
    source {{ BP_ENV }}
    mkdir -p tmp
    echo "Downloading ICD10CM from BioPortal..."
    wget "$DOWNLOAD_URL" -O {{ TMP_OWL }}
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

# Validate YAML against the LinkML schema (drift detection)
validate:
    uv run linkml-validate \
        --schema {{ SCHEMA }} \
        --target-class OntologyDocument \
        {{ YAML_OUT }}

# ── OWL export ────────────────────────────────────────────────────────────────

# Convert schema-conformant YAML → OWL using linkml-data2owl
data2owl:
    uv run linkml-data2owl \
        --schema {{ SCHEMA }} \
        -o {{ OWL_OUT }} \
        {{ YAML_OUT }}

# ── Composite targets ─────────────────────────────────────────────────────────

# Full build: mirror → component → transform → validate → OWL export
build: component transform validate data2owl
    @echo "Build complete: {{ YAML_OUT }} and {{ OWL_OUT }}"

# Re-run from component onward (transform → validate; component runs if needed)
iterate: transform validate
    @echo "Iteration complete: {{ YAML_OUT }} is schema-valid"

# ── Tests ─────────────────────────────────────────────────────────────────────

# Run all tests
test:
    uv run python -m unittest discover -s tests -p "test_*.py" -v

# ── Cleanup ───────────────────────────────────────────────────────────────────

# Remove all generated files
clean:
    rm -f {{ OWL_OUT }} {{ YAML_OUT }} {{ TMP_OWL }} {{ BP_ENV }}
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
