"""Structural integrity tests: Part B pipeline must not drop or add ICD10CM classes."""
import subprocess
import unittest
from pathlib import Path

# Project root (parent of tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
SPARQL_DIR = PROJECT_ROOT / "sparql"
MIRROR_OWL = PROJECT_ROOT / "tests" / "input" / "icd10cm_mini.owl"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
SIG_TXT = OUTPUT_DIR / "icd10cm_test_sig.txt"
SIG_TXT_TERMS = OUTPUT_DIR / "icd10cm_test_sig_terms.txt"
OUTPUT_OWL = OUTPUT_DIR / "icd10cm_test.owl"

ICD10CM_PREFIX = "http://purl.bioontology.org/ontology/ICD10CM/"
EXPECTED_TERM_COUNT = 10
KNOWN_CODES = ["A00", "A01", "B20", "Z00", "Z04"]


def count_icd10cm_classes(owl_path: Path) -> set:
    """Return set of class IRIs in the ontology that match ICD10CM prefix."""
    try:
        from rdflib import Graph, URIRef
        from rdflib.namespace import OWL
    except ImportError:
        raise unittest.SkipTest("rdflib not installed")
    g = Graph()
    g.parse(str(owl_path))
    return {
        str(s)
        for s in g.subjects(URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), OWL.Class)
        if str(s).startswith(ICD10CM_PREFIX)
    }


class TestStructuralIntegrity(unittest.TestCase):
    """Part B must preserve all ICD10CM classes: no drops, no spurious adds."""

    @classmethod
    def setUpClass(cls):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        # 1. Generate relevant signature from mini mirror
        subprocess.run(
            [
                "robot",
                "query",
                "-i",
                str(MIRROR_OWL),
                "-q",
                str(SPARQL_DIR / "icd10cm-relevant-signature.sparql"),
                str(SIG_TXT),
            ],
            check=True,
            cwd=str(PROJECT_ROOT),
        )
        # ROBOT query outputs CSV with header; remove -T expects one term per line.
        # Write a terms-only file (one IRI per line).
        with open(SIG_TXT) as f:
            lines = f.readlines()
        with open(SIG_TXT_TERMS, "w") as f:
            for line in lines[1:]:
                line = line.strip()
                if line:
                    f.write(line + "\n")
        # 2. Run Part B pipeline (same as Makefile, minus annotate for simplicity)
        subprocess.run(
            [
                "robot",
                "merge",
                "-i",
                str(MIRROR_OWL),
                "rename",
                "--mappings",
                str(CONFIG_DIR / "property-map.sssom.tsv"),
                "--allow-missing-entities",
                "true",
                "--allow-duplicates",
                "true",
                "remove",
                "-T",
                str(SIG_TXT_TERMS),
                "--select",
                "complement",
                "--select",
                "classes individuals",
                "--trim",
                "false",
                "remove",
                "-T",
                str(SIG_TXT_TERMS),
                "--select",
                "individuals",
                "query",
                "--update",
                str(SPARQL_DIR / "fix_omimps.ru"),
                "--update",
                str(SPARQL_DIR / "fix-labels-with-brackets.ru"),
                "--update",
                str(SPARQL_DIR / "exact_syn_from_label.ru"),
                "remove",
                "-T",
                str(CONFIG_DIR / "properties.txt"),
                "--select",
                "complement",
                "--select",
                "properties",
                "--trim",
                "true",
                "-o",
                str(OUTPUT_OWL),
            ],
            check=True,
            cwd=str(PROJECT_ROOT),
        )
        cls.input_terms = count_icd10cm_classes(MIRROR_OWL)
        cls.output_terms = count_icd10cm_classes(OUTPUT_OWL)

    def test_no_terms_dropped(self):
        """Every ICD10CM class in the mirror must appear in the output."""
        dropped = self.input_terms - self.output_terms
        self.assertEqual(set(), dropped, f"Terms dropped: {dropped}")

    def test_no_terms_added(self):
        """No ICD10CM class in the output that was not in the mirror."""
        added = self.output_terms - self.input_terms
        self.assertEqual(set(), added, f"Unexpected terms added: {added}")

    def test_expected_term_count(self):
        """Regression: output class count matches known count from mini OWL."""
        self.assertEqual(EXPECTED_TERM_COUNT, len(self.output_terms))

    def test_known_terms_present(self):
        """Spot-check that specific codes survive the pipeline."""
        for code in KNOWN_CODES:
            iri = ICD10CM_PREFIX + code
            self.assertIn(iri, self.output_terms, f"Expected term missing: {iri}")


if __name__ == "__main__":
    unittest.main()
