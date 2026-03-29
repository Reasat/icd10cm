#!/usr/bin/env python3
"""
Resolve an ICD10CM submission from BioPortal and print download URL and submission ID.

Usage:
  Set BIOPORTAL_API_KEY in .env (via python-dotenv) or in the environment, then:
  python get_latest_bioportal.py

  To pin a specific submission (skip "latest" discovery):
  BIOPORTAL_SUBMISSION_ID=27 python get_latest_bioportal.py

Output (to stdout):
  DOWNLOAD_URL=<url>
  SUBMISSION_ID=<id>
  VERSION_IRI=<version IRI for this submission>
"""

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


def _emit_for_submission_id(apikey: str, submission_id: str) -> None:
    download_url = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions/{submission_id}/download?apikey={apikey}"
    version_iri = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions/{submission_id}/icd10cm.owl"
    print(f"DOWNLOAD_URL={download_url}")
    print(f"SUBMISSION_ID={submission_id}")
    print(f"VERSION_IRI={version_iri}")


def main() -> None:
    apikey = os.environ.get("BIOPORTAL_API_KEY", "")
    if not apikey:
        print("BIOPORTAL_API_KEY must be set in .env or in the environment", file=sys.stderr)
        sys.exit(1)

    pinned = os.environ.get("BIOPORTAL_SUBMISSION_ID", "").strip()
    if pinned:
        if not pinned.isdigit():
            print("BIOPORTAL_SUBMISSION_ID must be a positive integer", file=sys.stderr)
            sys.exit(1)
        _emit_for_submission_id(apikey, pinned)
        return

    url = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions?apikey={apikey}&display_links=false"
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
    _emit_for_submission_id(apikey, submission_id)


if __name__ == "__main__":
    main()
