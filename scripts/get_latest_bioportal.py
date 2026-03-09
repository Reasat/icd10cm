#!/usr/bin/env python3
"""
Resolve the latest ICD10CM submission from BioPortal and print download URL and submission ID.

Usage:
  python get_latest_bioportal.py [--apikey KEY]
  Or set API_KEY in .env (via python-dotenv) or in the environment.

Output (to stdout):
  DOWNLOAD_URL=<url>
  SUBMISSION_ID=<id>
  VERSION_IRI=<version IRI for this submission>
"""

import argparse
import json
import os
import re
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()


BIOPORTAL_BASE = "https://data.bioontology.org"
ONTOLOGY_ACRONYM = "ICD10CM"


def _submission_id(submission: dict) -> int | None:
    """Extract numeric submission ID from a submission object."""
    sid = submission.get("submissionId")
    if sid is not None:
        return int(sid)
    id_url = submission.get("id") or submission.get("@id")
    if isinstance(id_url, str):
        match = re.search(r"/submissions/(\d+)/?", id_url)
        if match:
            return int(match.group(1))
    return None


def _released_ts(submission: dict) -> str:
    """Return released date string for ordering (empty string if missing)."""
    return submission.get("released") or ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Get latest ICD10CM download URL from BioPortal")
    parser.add_argument(
        "--apikey",
        default=os.environ.get("API_KEY", ""),
        help="BioPortal API key (or set API_KEY in .env or environment)",
    )
    args = parser.parse_args()
    if not args.apikey:
        print("API_KEY must be set in .env, in the environment, or passed as --apikey", file=sys.stderr)
        sys.exit(1)

    url = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions?apikey={args.apikey}&display_links=false"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)

    if not data:
        print("No submissions returned from BioPortal", file=sys.stderr)
        sys.exit(1)

    # Pick latest by max `released` date; if missing, by max submissionId (safer than assuming API order).
    submission = max(
        (s for s in data if _submission_id(s) is not None),
        key=lambda s: (_released_ts(s), _submission_id(s)),
    )
    submission_id = _submission_id(submission)
    if submission_id is None:
        print("Could not determine submission ID from response", file=sys.stderr)
        sys.exit(1)

    submission_id = str(submission_id)
    download_url = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions/{submission_id}/download?apikey={args.apikey}"
    version_iri = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions/{submission_id}/icd10cm.owl"

    print(f"DOWNLOAD_URL={download_url}")
    print(f"SUBMISSION_ID={submission_id}")
    print(f"VERSION_IRI={version_iri}")


if __name__ == "__main__":
    main()
