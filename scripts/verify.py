#!/usr/bin/env python3
"""
Structural checks on the produced LinkML YAML.

Required checks:
  - Accept --yaml <path> and --expected-version <str> (optional)
  - Check title and version are present and non-empty
  - Check for duplicate term IDs
  - Check every term has a non-empty label
  - Check every parents entry resolves to a known term ID
  - Print summary (term count, unique IDs, broken parent refs); exit 0 on PASS, 1 on FAIL

Optional --raw-json: acquire output; cross-checks (API traversal sources — not used for ICD10CM OWL).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def main() -> None:
    p = argparse.ArgumentParser(
        description="Structural checks on produced LinkML YAML (labels, parents, ids, version)"
    )
    p.add_argument("--yaml", type=Path, required=True)
    p.add_argument(
        "--expected-version",
        default=None,
        help="If set, YAML version must equal this upstream release id",
    )
    p.add_argument(
        "--raw-json",
        type=Path,
        default=None,
        help="Optional acquire output: entity count cross-check",
    )
    args = p.parse_args()

    if not args.yaml.exists():
        print(f"ERROR: YAML not found: {args.yaml}", file=sys.stderr)
        sys.exit(1)

    with open(args.yaml, encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    version = doc.get("version")
    terms = doc.get("terms") or []
    title = doc.get("title")

    errors: list[str] = []

    if title is None or not str(title).strip():
        errors.append("OntologyDocument.title is missing or empty")
    if version is None or not str(version).strip():
        errors.append("OntologyDocument.version is missing or empty")

    expected_ver = args.expected_version
    if expected_ver is not None and version != expected_ver:
        errors.append(
            f"version mismatch: YAML has {version!r}, expected upstream {expected_ver!r}"
        )

    ids: set[str] = set()
    dup: list[str] = []
    missing_ids = 0
    for t in terms:
        tid = t.get("id")
        if tid is None or not str(tid).strip():
            missing_ids += 1
            continue
        tid = str(tid).strip()
        if tid in ids:
            dup.append(tid)
        ids.add(tid)
    if missing_ids:
        errors.append(f"terms with missing/empty id: {missing_ids}")
    if dup:
        errors.append(f"duplicate term ids (first 10): {dup[:10]}")

    empty_labels = 0
    for t in terms:
        lab = t.get("label")
        if lab is None or not str(lab).strip():
            empty_labels += 1
    if empty_labels:
        errors.append(f"terms with missing/empty label: {empty_labels}")

    broken_parents: list[tuple[str, str]] = []
    terms_with_definition = 0
    exact_synonym_items = 0
    related_synonym_items = 0
    narrow_synonym_items = 0
    broad_synonym_items = 0
    root_terms = 0
    deprecated_terms = 0

    def _strip_nonempty(val: object) -> bool:
        return val is not None and bool(str(val).strip())

    for t in terms:
        if _strip_nonempty(t.get("definition")):
            terms_with_definition += 1
        exact_synonym_items += sum(
            1 for x in (t.get("exact_synonyms") or []) if _strip_nonempty(x)
        )
        related_synonym_items += sum(
            1 for x in (t.get("related_synonyms") or []) if _strip_nonempty(x)
        )
        narrow_synonym_items += sum(
            1 for x in (t.get("narrow_synonyms") or []) if _strip_nonempty(x)
        )
        broad_synonym_items += sum(
            1 for x in (t.get("broad_synonyms") or []) if _strip_nonempty(x)
        )
        if t.get("is_root") is True:
            root_terms += 1
        if t.get("deprecated") is True:
            deprecated_terms += 1

    for t in terms:
        tid = t.get("id")
        for par in t.get("parents") or []:
            if par not in ids:
                broken_parents.append((str(tid), str(par)))
    if broken_parents:
        sample = broken_parents[:15]
        errors.append(
            "parent id not found in terms (sample up to 15): "
            + "; ".join(f"{c}->{p}" for c, p in sample)
        )
        if len(broken_parents) > 15:
            errors.append(f"... and {len(broken_parents) - 15} more broken parent refs")

    if args.raw_json is not None:
        if not args.raw_json.exists():
            errors.append(f"raw JSON not found: {args.raw_json}")
        else:
            with open(args.raw_json, encoding="utf-8") as f:
                raw = json.load(f)
            n_ent = len(raw.get("entities") or {})
            n_terms = len(terms)
            if n_ent != n_terms:
                errors.append(
                    f"term count mismatch: YAML has {n_terms} terms, "
                    f"raw JSON has {n_ent} entities"
                )

    print(f"title: {title!r}")
    print(f"version: {version!r}")
    print(f"terms: {len(terms)}")
    print(f"unique ids: {len(ids)}")
    print(f"broken parent refs: {len(broken_parents)}")
    print(f"terms_with_definition: {terms_with_definition}")
    print(f"exact_synonym_items: {exact_synonym_items}")
    print(f"related_synonym_items: {related_synonym_items}")
    print(f"narrow_synonym_items: {narrow_synonym_items}")
    print(f"broad_synonym_items: {broad_synonym_items}")
    print(f"root_terms (is_root): {root_terms}")
    print(f"deprecated_terms: {deprecated_terms}")

    if errors:
        print("\nFAIL", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print("\nVERIFY: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
