#!/usr/bin/env python3
"""
Serialize ICD10CM component OWL → schema-conformant YAML.

Expects the output of the ROBOT component build (rename, filter, SPARQL fixes,
property strip). Reads rdfs:label, oboInOwl:hasExactSynonym, and other
schema slots directly — no data fixes; those are done by ROBOT.

Input:  tmp/icd10cm-component.owl   (after just component)
Output: icd10cm.linkml.yml          (conforms to linkml/mondo_source_schema.yaml)

Usage:
    python scripts/transform.py \\
        --input tmp/icd10cm-component.owl \\
        --schema linkml/mondo_source_schema.yaml \\
        --output icd10cm.linkml.yml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef
from rdflib.namespace import Namespace

# ── Namespaces ────────────────────────────────────────────────────────────────

OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
OBO = Namespace("http://purl.obolibrary.org/obo/")

ICD10CM_IRI_PREFIX = "http://purl.bioontology.org/ontology/ICD10CM/"
ICD10CM_CURIE_PREFIX = "ICD10CM:"

# Component OWL uses Mondo/obo property IRIs (after rename)
DEFINITION = OBO["IAO_0000115"]
OWL_THING = OWL.Thing
OWL_DEPRECATED_PROP = OWL.deprecated


# ── YAML: quote strings that break plain YAML scalars ─────────────────────────


class QuotingDumper(yaml.SafeDumper):
    pass


def _represent_str(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if any(c in data for c in ",:{}") or data.strip() != data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


QuotingDumper.add_representer(str, _represent_str)


# ── IRI helpers ────────────────────────────────────────────────────────────────

def is_icd10cm_iri(iri: str) -> bool:
    return iri.startswith(ICD10CM_IRI_PREFIX)


def iri_to_curie(iri: str) -> str:
    """Convert a full ICD10CM IRI to a CURIE, e.g. '…/A00' → 'ICD10CM:A00'."""
    if is_icd10cm_iri(iri):
        return ICD10CM_CURIE_PREFIX + iri[len(ICD10CM_IRI_PREFIX) :]
    return iri


# ── Graph traversal ───────────────────────────────────────────────────────────

def extract_ontology_metadata(g: Graph) -> dict:
    """Return document-level fields from the owl:Ontology node (for YAML / LinkML round-trip)."""
    meta: dict = {
        "title": "ICD10CM",
        "version": "unknown",
    }
    for ont in g.subjects(RDF.type, OWL.Ontology):
        lbl = g.value(ont, RDFS.label)
        if lbl:
            meta["title"] = str(lbl)
        ver = g.value(ont, OWL.versionInfo)
        if ver:
            meta["version"] = str(ver)
        src = g.value(ont, OBOINOWL.source)
        if src:
            meta["source"] = str(src)
        cmt = g.value(ont, RDFS.comment)
        if cmt:
            meta["ontology_comment"] = str(cmt)
        viri = g.value(ont, OWL.versionIRI)
        if viri:
            meta["version_iri"] = str(viri)
        break
    return meta


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

        # ── Exact synonyms (component OWL has SPARQL fixes applied) ───────────
        exact_syns: list[dict] = []
        for o in g.objects(subj, OBOINOWL.hasExactSynonym):
            if isinstance(o, Literal):
                t = str(o).strip()
                if t:
                    exact_syns.append(
                        {"synonym_text": t, "synonym_type": "generated_from_label"}
                    )

        # ── Parents ───────────────────────────────────────────────────────────
        parent_iris = [
            str(o)
            for o in g.objects(subj, RDFS.subClassOf)
            if isinstance(o, URIRef) and is_icd10cm_iri(str(o))
        ]
        parent_curies = [iri_to_curie(p) for p in sorted(parent_iris)]

        # ── Root detection (internal only — not written to YAML) ──────────────
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
        if not is_root:
            term["parents"] = parent_curies

        terms.append(term)

    return terms


# ── Main ──────────────────────────────────────────────────────────────────────

def transform(input_path: Path, output_path: Path) -> None:
    print(f"Parsing component OWL: {input_path}", file=sys.stderr)
    g = Graph()
    g.parse(str(input_path))

    doc = extract_ontology_metadata(g)
    terms = extract_terms(g)
    print(f"Extracted {len(terms)} ICD10CM terms", file=sys.stderr)

    doc["terms"] = terms

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        yaml.dump(
            doc,
            fh,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            Dumper=QuotingDumper,
        )

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
        help="Output YAML path (e.g. icd10cm.linkml.yml)",
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
