"""Syntactic tests: each SPARQL update is applied to a minimal OWL and we assert the expected change occurred."""
import subprocess
import unittest
from pathlib import Path
from typing import Optional

# Project root (parent of tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPARQL_DIR = PROJECT_ROOT / "sparql"
INPUT_OWL = PROJECT_ROOT / "tests" / "input" / "icd10cm_sparql_test.owl"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
OUTPUT_OWL = OUTPUT_DIR / "sparql_test_out.owl"

OBOINOWL_NS = "http://www.geneontology.org/formats/oboInOwl#"


def run_robot_update(
    sparql_file: Path,
    input_owl: Path = INPUT_OWL,
    output_owl: Optional[Path] = None,
) -> Path:
    """Run robot query --update with the given SPARQL update file. Returns path to output."""
    out = output_owl if output_owl is not None else OUTPUT_DIR / f"sparql_test_out_{sparql_file.stem}.owl"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "robot",
            "query",
            "-i",
            str(input_owl),
            "--update",
            str(sparql_file),
            "-o",
            str(out),
        ],
        check=True,
        cwd=str(PROJECT_ROOT),
    )
    return out


def get_all_literal_values(owl_path: Path, predicate_uri: str) -> set:
    """Return all literal values for the predicate (including from annotated axioms)."""
    try:
        from rdflib import Graph, Literal, URIRef
    except ImportError:
        raise unittest.SkipTest("rdflib not installed")
    g = Graph()
    g.parse(str(owl_path))
    pred = URIRef(predicate_uri)
    out = set()
    for s, p, o in g.triples((None, pred, None)):
        if isinstance(o, Literal):
            out.add(str(o))
    return out


class TestFixOmimps(unittest.TestCase):
    """fix_omimps.ru: MIM:PS* xrefs become OMIMPS:*."""

    def test_mim_ps_rewritten_to_omimps(self):
        out = run_robot_update(SPARQL_DIR / "fix_omimps.ru")
        xref_values = get_all_literal_values(out, OBOINOWL_NS + "hasDbXref")
        self.assertIn("OMIMPS:123", xref_values)
        self.assertNotIn("MIM:PS123", xref_values)


class TestFixLabelsWithBrackets(unittest.TestCase):
    """fix-labels-with-brackets.ru: label ending in (...) or [...] gets stripped as exact synonym."""

    def test_bracketed_label_gets_synonym(self):
        out = run_robot_update(SPARQL_DIR / "fix-labels-with-brackets.ru")
        syn_values = get_all_literal_values(out, OBOINOWL_NS + "hasExactSynonym")
        self.assertIn("cholera", syn_values)


class TestExactSynFromLabel(unittest.TestCase):
    """exact_syn_from_label.ru: non-deprecated terms get exact synonym from label."""

    def test_label_becomes_exact_synonym(self):
        out = run_robot_update(SPARQL_DIR / "exact_syn_from_label.ru")
        syn_values = get_all_literal_values(out, OBOINOWL_NS + "hasExactSynonym")
        self.assertIn("Typhoid fever", syn_values)

    def test_deprecated_term_label_not_added(self):
        out = run_robot_update(SPARQL_DIR / "exact_syn_from_label.ru")
        syn_values = get_all_literal_values(out, OBOINOWL_NS + "hasExactSynonym")
        self.assertIn("Typhoid fever", syn_values, "Update must add synonyms for non-deprecated terms")
        self.assertNotIn("Deprecated disease", syn_values)


if __name__ == "__main__":
    unittest.main()
