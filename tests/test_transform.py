"""
Tests for scripts/transform.py.

Runs the transform against icd10cm_component_mini.owl (component-style fixture;
ROBOT has already applied renames and SPARQL fixes). Asserts that the output
YAML conforms to expected structure (pure serialization, no in-Python fixes).
"""
import sys
import unittest
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Component-style fixture (rdfs:label, oboInOwl:hasExactSynonym, etc.)
COMPONENT_MINI_OWL = PROJECT_ROOT / "tests" / "input" / "icd10cm_component_mini.owl"
SCHEMA_YAML = PROJECT_ROOT / "linkml" / "mondo_source_schema.yaml"
OUTPUT_YAML = PROJECT_ROOT / "tests" / "output" / "icd10cm_transform_test.yaml"

ICD10CM_PREFIX = "ICD10CM:"


# ── Integration test: run transform on component mini OWL ─────────────────────

class TestTransformOnComponentMiniOWL(unittest.TestCase):
    """Run the full transform on the component-style fixture and assert structure."""

    doc: dict

    @classmethod
    def setUpClass(cls):
        try:
            import rdflib  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("rdflib not installed")

        from transform import transform

        OUTPUT_YAML.parent.mkdir(parents=True, exist_ok=True)
        transform(COMPONENT_MINI_OWL, OUTPUT_YAML)

        with open(OUTPUT_YAML, encoding="utf-8") as fh:
            cls.doc = yaml.safe_load(fh)

    # ── Document-level ──────────────────────────────────────────────────────

    def test_document_has_title(self):
        self.assertIn("title", self.doc)
        self.assertIsInstance(self.doc["title"], str)

    def test_document_has_version(self):
        self.assertIn("version", self.doc)
        self.assertIsInstance(self.doc["version"], str)

    def test_document_has_terms(self):
        self.assertIn("terms", self.doc)
        self.assertIsInstance(self.doc["terms"], list)

    def test_term_count_matches_fixture(self):
        self.assertEqual(len(self.doc["terms"]), 10)

    # ── Per-term structure ───────────────────────────────────────────────────

    def test_every_term_has_id(self):
        for term in self.doc["terms"]:
            self.assertIn("id", term, f"Missing id in term: {term}")
            self.assertTrue(
                term["id"].startswith(ICD10CM_PREFIX),
                f"id should be ICD10CM CURIE: {term['id']}",
            )

    def test_every_term_has_label(self):
        for term in self.doc["terms"]:
            self.assertIn("label", term, f"Missing label in term: {term}")
            self.assertIsInstance(term["label"], str)
            self.assertTrue(len(term["label"]) > 0)

    def test_term_ids_are_unique(self):
        ids = [t["id"] for t in self.doc["terms"]]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate term IDs found")

    # ── Spot-check known codes ────────────────────────────────────────────────

    def _get_term(self, code: str) -> dict | None:
        curie = ICD10CM_PREFIX + code
        for term in self.doc["terms"]:
            if term["id"] == curie:
                return term
        return None

    def test_known_codes_present(self):
        for code in ["A00", "A01", "B20", "Z00", "Z04"]:
            self.assertIsNotNone(self._get_term(code), f"Missing expected term: {code}")

    # ── Component OWL has label as exact synonym for non-deprecated ────────────

    def test_label_in_exact_synonyms_when_present_in_owl(self):
        """Non-deprecated terms in the fixture have label in exact_synonyms."""
        for term in self.doc["terms"]:
            if term.get("deprecated"):
                continue
            syns = term.get("exact_synonyms", [])
            self.assertIn(
                term["label"],
                syns,
                f"Label '{term['label']}' not in exact_synonyms for {term['id']}",
            )

    # ── Bracket-stripped synonym is in fixture (Z00) ───────────────────────────

    def test_z00_has_stripped_synonym(self):
        """Fixture Z00 has 'encounter for general examination' as exact synonym."""
        z00 = self._get_term("Z00")
        self.assertIsNotNone(z00)
        syns = z00.get("exact_synonyms", [])
        self.assertIn("encounter for general examination", syns)

    # ── Deprecated term has no label-as-synonym ────────────────────────────────

    def test_deprecated_b20_has_no_exact_synonyms(self):
        """B20 is deprecated; fixture has no exact_syn_from_label for it."""
        b20 = self._get_term("B20")
        self.assertIsNotNone(b20)
        self.assertTrue(b20.get("deprecated"))
        # Component OWL does not add label as synonym for deprecated
        syns = b20.get("exact_synonyms", [])
        self.assertNotIn(b20["label"], syns)

    # ── Parents and root flags ────────────────────────────────────────────────

    def test_roots_have_is_root_true(self):
        """Terms with no named ICD10CM parents must be marked is_root."""
        for term in self.doc["terms"]:
            parents = term.get("parents", [])
            if len(parents) == 0:
                self.assertTrue(
                    term.get("is_root", False),
                    f"Term {term['id']} has no parents but is_root is not True",
                )

    def test_non_roots_have_icd10cm_parents(self):
        """Parent CURIEs must be ICD10CM: prefixed."""
        for term in self.doc["terms"]:
            for parent in term.get("parents", []):
                self.assertTrue(
                    parent.startswith(ICD10CM_PREFIX),
                    f"Parent '{parent}' in {term['id']} is not an ICD10CM CURIE",
                )


if __name__ == "__main__":
    unittest.main()
