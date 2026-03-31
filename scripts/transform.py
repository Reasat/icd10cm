#!/usr/bin/env python3
"""
Serialize ICD10CM component OWL → schema-conformant YAML.

Expects the output of the ROBOT component build (rename, filter, SPARQL fixes,
property strip). Reads rdfs:label, oboInOwl:hasExactSynonym, and other
schema slots directly — no data fixes; those are done by ROBOT.

Input:  tmp/icd10cm-component.owl   (after just component)
Output: icd10cm.yaml                 (conforms to linkml/mondo_source_schema.yaml)

Usage:
    python scripts/transform.py \\
        --input tmp/icd10cm-component.owl \\
        --schema linkml/mondo_source_schema.yaml \\
        --output icd10cm.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, Namespace, SKOS

# ── Namespaces ────────────────────────────────────────────────────────────────

OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
MONDO = Namespace("http://purl.obolibrary.org/obo/mondo#")

ICD10CM_IRI_PREFIX = "http://purl.bioontology.org/ontology/ICD10CM/"
ICD10CM_CURIE_PREFIX = "ICD10CM:"

# Component OWL uses Mondo/obo property IRIs (after rename)
DEFINITION = OBO["IAO_0000115"]
OMO_0003012 = OBO["OMO_0003012"]
OWL_THING = OWL.Thing
OWL_DEPRECATED_PROP = OWL.deprecated

# RO / BFO object properties (allowed on component per config/properties.txt)
RO_0004001 = OBO["RO_0004001"]
RO_0004003 = OBO["RO_0004003"]
RO_0004004 = OBO["RO_0004004"]
BFO_0000050 = OBO["BFO_0000050"]
BFO_0000051 = OBO["BFO_0000051"]


# ── IRI helpers ───────────────────────────────────────────────────────────────

def is_icd10cm_iri(iri: str) -> bool:
    return iri.startswith(ICD10CM_IRI_PREFIX)


def iri_to_curie(iri: str) -> str:
    """Convert a full ICD10CM IRI to a CURIE, e.g. '…/A00' → 'ICD10CM:A00'."""
    if is_icd10cm_iri(iri):
        return ICD10CM_CURIE_PREFIX + iri[len(ICD10CM_IRI_PREFIX) :]
    return iri


def _literal_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out = [str(o) for o in g.objects(subj, pred) if isinstance(o, Literal)]
    return sorted(set(out)) if out else []


def _uri_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out = [str(o) for o in g.objects(subj, pred) if isinstance(o, URIRef)]
    return sorted(out) if out else []


def _uri_or_literal_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out: list[str] = []
    for o in g.objects(subj, pred):
        if isinstance(o, (Literal, URIRef)):
            out.append(str(o))
    return sorted(set(out)) if out else []


# ── Graph traversal ───────────────────────────────────────────────────────────

def extract_ontology_metadata(g: Graph) -> tuple[str, str]:
    """Return (title, version) from the owl:Ontology node."""
    title = "ICD10CM"
    version = "unknown"
    for ont in g.subjects(RDF.type, OWL.Ontology):
        lbl = g.value(ont, RDFS.label)
        if lbl:
            title = str(lbl)
        ver = g.value(ont, OWL.versionInfo)
        if ver:
            version = str(ver)
        break
    return title, version


def extract_terms(g: Graph) -> list[dict]:
    """
    Extract all ICD10CM classes from the component graph.
    Component OWL already has rdfs:label, oboInOwl:hasExactSynonym, etc.
    No normalizations — pure serialization.
    """
    icd10cm_iris: set[str] = {
        str(s)
        for s in g.subjects(RDF.type, OWL.Class)
        if isinstance(s, URIRef) and is_icd10cm_iri(str(s))
    }

    terms: list[dict] = []

    for iri in sorted(icd10cm_iris):
        subj = URIRef(iri)
        curie = iri_to_curie(iri)

        # ── Label (component OWL has rdfs:label after rename) ─────────────────
        label_node = g.value(subj, RDFS.label)
        if label_node is None:
            continue
        label = str(label_node)

        # ── Deprecated ─────────────────────────────────────────────────────────
        dep_node = g.value(subj, OWL_DEPRECATED_PROP)
        is_deprecated = dep_node is not None and str(dep_node).lower() == "true"

        # ── Definition ─────────────────────────────────────────────────────────
        defn_node = g.value(subj, DEFINITION)
        definition = str(defn_node) if defn_node else None

        # ── Exact synonyms (component OWL has SPARQL fixes applied) ─────────────
        exact_syns: list[str] = [
            str(o)
            for o in g.objects(subj, OBOINOWL.hasExactSynonym)
            if isinstance(o, Literal)
        ]

        # ── Parents ───────────────────────────────────────────────────────────
        parent_iris = [
            str(o)
            for o in g.objects(subj, RDFS.subClassOf)
            if isinstance(o, URIRef) and is_icd10cm_iri(str(o))
        ]
        parent_curies = [iri_to_curie(p) for p in sorted(parent_iris)]

        # ── Root detection ────────────────────────────────────────────────────
        has_thing_parent = OWL_THING in g.objects(subj, RDFS.subClassOf)
        is_root = has_thing_parent or len(parent_curies) == 0

        # ── Assemble term dict ─────────────────────────────────────────────────
        term: dict = {"id": curie, "label": label}
        if is_deprecated:
            term["deprecated"] = True
        if definition:
            term["definition"] = definition
        if exact_syns:
            term["exact_synonyms"] = exact_syns
        if is_root:
            term["is_root"] = True
        else:
            term["parents"] = parent_curies

        # ── Optional synonym / xref / annotation slots (align with config/properties.txt) ─
        for key, pred in (
            ("related_synonyms", OBOINOWL.hasRelatedSynonym),
            ("narrow_synonyms", OBOINOWL.hasNarrowSynonym),
            ("broad_synonyms", OBOINOWL.hasBroadSynonym),
        ):
            vals = _literal_values(g, subj, pred)
            if vals:
                term[key] = vals

        obo_close = _uri_or_literal_values(g, subj, OBOINOWL.hasCloseSynonym)
        if obo_close:
            term["obo_has_close_synonym"] = obo_close

        for key, pred in (
            ("database_cross_references", OBOINOWL.hasDbXref),
            ("comments", RDFS.comment),
            ("descriptions", DCTERMS.description),
            ("sources", OBOINOWL.source),
        ):
            vals = _uri_or_literal_values(g, subj, pred)
            if vals:
                term[key] = vals

        see_also = _uri_or_literal_values(g, subj, RDFS.seeAlso)
        if see_also:
            term["see_also"] = see_also

        for key, pred in (
            ("in_subsets", OBOINOWL.inSubset),
            ("synonym_types", OBOINOWL.hasSynonymType),
        ):
            vals = _uri_values(g, subj, pred)
            if vals:
                term[key] = vals

        for key, pred in (
            ("skos_exact_match", SKOS.exactMatch),
            ("skos_broad_match", SKOS.broadMatch),
            ("skos_narrow_match", SKOS.narrowMatch),
            ("skos_related_match", SKOS.relatedMatch),
            ("close_synonyms", SKOS.closeMatch),
        ):
            vals = _uri_or_literal_values(g, subj, pred)
            if vals:
                term[key] = vals

        for key, pred in (
            ("mondo_generated", MONDO.GENERATED),
            ("mondo_generated_from_label", MONDO.GENERATED_FROM_LABEL),
            ("mondo_omim_included", MONDO.omim_included),
            ("mondo_omim_formerly", MONDO.omim_formerly),
            ("mondo_abbreviation", MONDO.ABBREVIATION),
        ):
            vals = _uri_or_literal_values(g, subj, pred)
            if vals:
                term[key] = vals

        omo = _uri_or_literal_values(g, subj, OMO_0003012)
        if omo:
            term["omo_0003012"] = omo

        for key, pred in (
            ("ro_0004001", RO_0004001),
            ("ro_0004003", RO_0004003),
            ("ro_0004004", RO_0004004),
            ("bfo_0000050", BFO_0000050),
            ("bfo_0000051", BFO_0000051),
        ):
            vals = _uri_values(g, subj, pred)
            if vals:
                term[key] = vals

        terms.append(term)

    return terms


# ── Main ──────────────────────────────────────────────────────────────────────

def transform(input_path: Path, output_path: Path) -> None:
    print(f"Parsing component OWL: {input_path}", file=sys.stderr)
    g = Graph()
    g.parse(str(input_path))

    title, version = extract_ontology_metadata(g)
    terms = extract_terms(g)
    print(f"Extracted {len(terms)} ICD10CM terms", file=sys.stderr)

    doc = {
        "title": title,
        "version": version,
        "terms": terms,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        yaml.dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"Written: {output_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serialize ICD10CM component OWL → schema YAML"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to tmp/icd10cm-component.owl (output of just component)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        required=True,
        help="Path to LinkML schema (linkml/mondo_source_schema.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output YAML path (e.g. icd10cm.yaml)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not args.schema.exists():
        print(f"Error: schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)

    transform(args.input, args.output)


if __name__ == "__main__":
    main()
