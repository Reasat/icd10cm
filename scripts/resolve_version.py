#!/usr/bin/env python3
"""
Resolve an ICD10CM submission from BioPortal and print download URL and submission ID.

Usage:
  Set BIOPORTAL_API_KEY in env/.env (see env/.env.example) or in the environment, then:
  python scripts/resolve_version.py

  To pin a specific submission (skip "latest" discovery):
    BIOPORTAL_SUBMISSION_ID=27 python scripts/resolve_version.py

Output (to stdout):
  DOWNLOAD_URL=<url>
  SUBMISSION_ID=<id>
  VERSION_IRI=<version IRI for this submission>
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv("env/.env")
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


def get_download_info() -> dict[str, str]:
    """
    Query BioPortal and return download_url, submission_id, version_iri.
    Requires BIOPORTAL_API_KEY in the environment.
    """
    apikey = os.environ.get("BIOPORTAL_API_KEY", "")
    if not apikey:
        raise RuntimeError("BIOPORTAL_API_KEY must be set in env/.env or in the environment")

    pinned = os.environ.get("BIOPORTAL_SUBMISSION_ID", "").strip()
    if pinned:
        if not pinned.isdigit():
            raise RuntimeError("BIOPORTAL_SUBMISSION_ID must be a positive integer")
        submission_id = pinned
    else:
        url = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions?apikey={apikey}&display_links=false"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)

        if not data:
            raise RuntimeError("No submissions returned from BioPortal")

        submission = max(
            (s for s in data if _submission_id(s) is not None),
            key=lambda s: (_released_ts(s), _submission_id(s)),
        )
        sid = _submission_id(submission)
        if sid is None:
            raise RuntimeError("Could not determine submission ID from response")
        submission_id = str(sid)

    download_url = (
        f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions/"
        f"{submission_id}/download?apikey={apikey}"
    )
    version_iri = (
        f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions/"
        f"{submission_id}/icd10cm.owl"
    )
    return {
        "download_url": download_url,
        "submission_id": submission_id,
        "version_iri": version_iri,
    }


def emit_lines() -> None:
    info = get_download_info()
    print(f"DOWNLOAD_URL={info['download_url']}")
    print(f"SUBMISSION_ID={info['submission_id']}")
    print(f"VERSION_IRI={info['version_iri']}")


def main() -> None:
    try:
        emit_lines()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
