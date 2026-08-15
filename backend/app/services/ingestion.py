"""PDF ingestion: extract per-page text (preserving page numbers for citations),
guess section headings, and chunk into token-sized pieces with metadata attached."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# ~500-800 tokens per chunk with ~15% overlap, per the step-by-step guide.
CHUNK_SIZE_TOKENS = 650
CHUNK_OVERLAP_TOKENS = 100

_SECTION_HEADING_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?([A-Za-z][A-Za-z ,\-]{2,60})\s*$")
_KNOWN_SECTION_WORDS = {
    "abstract",
    "introduction",
    "related work",
    "background",
    "method",
    "methods",
    "methodology",
    "approach",
    "model",
    "model architecture",
    "experiments",
    "experimental setup",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "references",
    "acknowledgments",
    "acknowledgements",
    "appendix",
}


def _guess_section(line: str) -> str | None:
    line = line.strip()
    if not line or len(line) > 70:
        return None
    match = _SECTION_HEADING_RE.match(line)
    if not match:
        return None
    candidate = match.group(1).strip()
    if candidate.lower() in _KNOWN_SECTION_WORDS:
        return candidate.title()
    return None


@dataclass
class PageText:
    page: int  # 1-indexed
    text: str
    section: str | None


def extract_pages(pdf_path: Path) -> list[PageText]:
    reader = PdfReader(str(pdf_path))
    pages: list[PageText] = []
    current_section: str | None = None
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        # Section headings tend to appear near the top of the page they start on.
        for line in text.splitlines()[:15]:
            guessed = _guess_section(line)
            if guessed:
                current_section = guessed
                break
        pages.append(PageText(page=i, text=text, section=current_section))
    return pages


def make_paper_id(filename: str) -> str:
    stem = Path(filename).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def chunk_paper(pdf_path: Path, paper_id: str, filename: str) -> list[Document]:
    """Extract + chunk a single PDF into Documents with citation metadata.

    Chunking is done per-page (not across page boundaries) so every chunk's
    page number is exact -- required for the citation/source-attribution feature.
    """
    pages = extract_pages(pdf_path)
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=CHUNK_SIZE_TOKENS,
        chunk_overlap=CHUNK_OVERLAP_TOKENS,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Document] = []
    for page_obj in pages:
        if not page_obj.text.strip():
            continue
        for idx, chunk_text in enumerate(splitter.split_text(page_obj.text)):
            chunk_id = f"{paper_id}_p{page_obj.page}_c{idx}"
            chunks.append(
                Document(
                    page_content=chunk_text,
                    metadata={
                        "chunk_id": chunk_id,
                        "paper_id": paper_id,
                        "filename": filename,
                        "page": page_obj.page,
                        "section": page_obj.section,
                        "chunk_index": idx,
                    },
                )
            )
    return chunks


def chunk_papers_in_dir(papers_dir: Path) -> list[Document]:
    """Chunk every PDF in a directory. Used to build the seeded base corpus at startup."""
    all_chunks: list[Document] = []
    for pdf_path in sorted(papers_dir.glob("*.pdf")):
        paper_id = make_paper_id(pdf_path.name)
        all_chunks.extend(chunk_paper(pdf_path, paper_id=paper_id, filename=pdf_path.name))
    return all_chunks
