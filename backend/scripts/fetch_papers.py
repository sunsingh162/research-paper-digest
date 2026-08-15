"""Download the seed corpus (3 classic arXiv papers) for the Research Paper Digest demo.

The PDFs themselves aren't committed to the repo (they're third-party copyrighted
content redistributed by arXiv under its own terms) -- this script fetches them
directly from arXiv into app/data/papers/ so the demo corpus is reproducible.

Run from backend/: python scripts/fetch_papers.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

PAPERS_DIR = Path(__file__).resolve().parent.parent / "app" / "data" / "papers"

PAPERS = {
    "attention_is_all_you_need.pdf": "https://arxiv.org/pdf/1706.03762",
    "bert_pretraining.pdf": "https://arxiv.org/pdf/1810.04805",
    "retrieval_augmented_generation.pdf": "https://arxiv.org/pdf/2005.11401",
}

USER_AGENT = "Mozilla/5.0 (research-paper-digest capstone project; educational, non-commercial use)"


def fetch(filename: str, url: str) -> None:
    dest = PAPERS_DIR / filename
    if dest.exists():
        print(f"skip (already present): {filename}")
        return
    print(f"downloading {filename} <- {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response, open(dest, "wb") as out_file:
        out_file.write(response.read())


def main() -> None:
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in PAPERS.items():
        try:
            fetch(filename, url)
        except Exception as exc:  # noqa: BLE001 - report and continue, don't abort the whole batch
            print(f"FAILED: {filename}: {exc}", file=sys.stderr)
    print("done.")


if __name__ == "__main__":
    main()
