#!/usr/bin/env python3
"""
Fetch the raw ICD10CM OWL from BioPortal after resolving the latest submission.

Writes `.bioportal.env` (DOWNLOAD_URL, SUBMISSION_ID, VERSION_IRI) and downloads
the ontology to `tmp/.icd10cm.tmp.owl` for the ROBOT mirror step.

Requires BIOPORTAL_API_KEY in env/.env or the environment (see env/.env.example).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import urllib.request

from dotenv import load_dotenv

load_dotenv("env/.env")
load_dotenv()

from resolve_version import get_download_info


def main() -> None:
    p = argparse.ArgumentParser(description="Download ICD10CM OWL from BioPortal")
    p.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/.icd10cm.tmp.owl"),
        help="Path for the downloaded raw OWL file",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(".bioportal.env"),
        help="Where to write DOWNLOAD_URL / SUBMISSION_ID / VERSION_IRI",
    )
    args = p.parse_args()

    try:
        info = get_download_info()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.env_file.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"DOWNLOAD_URL={info['download_url']}",
        f"SUBMISSION_ID={info['submission_id']}",
        f"VERSION_IRI={info['version_iri']}",
    ]
    args.env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Downloading ICD10CM from BioPortal → {args.output}", file=sys.stderr)
    urllib.request.urlretrieve(info["download_url"], args.output)
    print(f"Wrote {args.env_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
