# ICD10CM preprocessed build
# Part A: Mirror build      → tmp/mirror-icd10cm.owl
# Part B: Component build   → icd10cm.owl
# Requires: ROBOT, Python 3, wget. Set BIOPORTAL_API_KEY (or pass apikey= to make).

ROBOT       ?= robot
PYTHON      ?= python3
WGET        ?= wget
CONFIG_DIR  := config
SCRIPTS_DIR := scripts
SPARQL_DIR  := sparql
TMP_DIR     := tmp
OUTPUT_OWL  := icd10cm.owl
TMP_OWL     := .icd10cm.tmp.owl
MIRROR_OWL  := $(TMP_DIR)/mirror-icd10cm.owl
SIG_TXT     := $(TMP_DIR)/icd10cm_relevant_signature.txt
BP_ENV      := .bioportal.env
ONTOLOGY_IRI := https://github.com/monarch-initiative/icd10cm/releases/latest/download/icd10cm.owl
URIBASE     := http://purl.obolibrary.org/obo
TODAY       := $(shell date +%Y-%m-%d)

.PHONY: all build clean env test
all: build

# ── Directory ─────────────────────────────────────────────────────────────────
$(TMP_DIR):
	mkdir -p $(TMP_DIR)

# ── Resolve BioPortal submission ──────────────────────────────────────────────
# API key: set BIOPORTAL_API_KEY or make apikey=KEY, or put API_KEY in .env.
$(BP_ENV): $(SCRIPTS_DIR)/get_latest_bioportal.py
	@if [ -n "$$BIOPORTAL_API_KEY" ] || [ -n "$(apikey)" ]; then \
		$(PYTHON) $(SCRIPTS_DIR)/get_latest_bioportal.py --apikey "$${BIOPORTAL_API_KEY:-$(apikey)}" > $@; \
	else \
		$(PYTHON) $(SCRIPTS_DIR)/get_latest_bioportal.py > $@; \
	fi
	@echo "Resolved latest BioPortal submission; see $@"

# ── Part A: Mirror build ──────────────────────────────────────────────────────
# Downloads raw OWL from BioPortal, removes imports and unwanted properties,
# annotates with stable IRI and version IRI, normalizes.
$(MIRROR_OWL): $(BP_ENV) $(CONFIG_DIR)/remove_properties.txt | $(TMP_DIR)
	@. ./$(BP_ENV) && \
	echo "Downloading ICD10CM from BioPortal..." && \
	$(WGET) "$$DOWNLOAD_URL" -O $(TMP_OWL) && \
	echo "Running: robot remove + annotate + odk:normalize -> $@" && \
	$(ROBOT) remove -i $(TMP_OWL) --select imports \
		remove -T $(CONFIG_DIR)/remove_properties.txt \
		annotate \
			--ontology-iri $(ONTOLOGY_IRI) \
			--version-iri "$$VERSION_IRI" \
		odk:normalize --add-source true -o $@ && \
	rm -f $(TMP_OWL)
	@echo "Built $@"

# ── Part B: Relevant signature ────────────────────────────────────────────────
# Query the mirror for all ICD10CM IRIs to use as the relevant signature.
$(SIG_TXT): $(MIRROR_OWL) $(SPARQL_DIR)/icd10cm-relevant-signature.sparql | $(TMP_DIR)
	$(ROBOT) query -i $< -q $(SPARQL_DIR)/icd10cm-relevant-signature.sparql $@
	@echo "Built $@"

# ── Part B: Component build ───────────────────────────────────────────────────
# Filters to relevant terms, remaps properties, applies SPARQL fixes,
# then strips everything except Mondo-approved properties.
$(OUTPUT_OWL): $(SIG_TXT) $(MIRROR_OWL) \
		$(CONFIG_DIR)/property-map.sssom.tsv $(CONFIG_DIR)/properties.txt \
		$(SPARQL_DIR)/fix_omimps.ru $(SPARQL_DIR)/fix-labels-with-brackets.ru \
		$(SPARQL_DIR)/exact_syn_from_label.ru
	$(ROBOT) merge -i $(MIRROR_OWL) \
		rename --mappings $(CONFIG_DIR)/property-map.sssom.tsv \
			--allow-missing-entities true --allow-duplicates true \
		remove -T $(SIG_TXT) --select complement --select "classes individuals" --trim false \
		remove -T $(SIG_TXT) --select individuals \
		query \
			--update $(SPARQL_DIR)/fix_omimps.ru \
			--update $(SPARQL_DIR)/fix-labels-with-brackets.ru \
			--update $(SPARQL_DIR)/exact_syn_from_label.ru \
		remove -T $(CONFIG_DIR)/properties.txt --select complement --select properties --trim true \
		annotate \
			--ontology-iri $(URIBASE)/mondo/sources/icd10cm.owl \
			--version-iri $(URIBASE)/mondo/sources/$(TODAY)/icd10cm.owl \
		-o $@
	@echo "Built $@"

build: $(OUTPUT_OWL)
	@echo "Build complete: $(OUTPUT_OWL)"

# ── Utilities ─────────────────────────────────────────────────────────────────
env: $(BP_ENV)
	@cat $(BP_ENV)

clean:
	rm -f $(OUTPUT_OWL) $(TMP_OWL) $(BP_ENV)
	rm -rf $(TMP_DIR)

# ── Tests (require ROBOT and rdflib: pip install -r requirements.txt) ─────────
test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
