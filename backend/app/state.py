"""In-memory application state: the live FAISS store + ingested-paper registry.

A single-process, single-instance app is the right scope for this capstone (see
README for the deployment model) so a simple in-memory singleton is appropriate
here rather than an external store.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_community.vectorstores import FAISS


@dataclass
class PaperMeta:
    paper_id: str
    filename: str
    num_pages: int = 0
    num_chunks: int = 0


@dataclass
class AppState:
    vectorstore: FAISS | None = None
    papers: dict[str, PaperMeta] = field(default_factory=dict)

    @property
    def index_loaded(self) -> bool:
        return self.vectorstore is not None

    @property
    def num_chunks(self) -> int:
        return sum(p.num_chunks for p in self.papers.values())


app_state = AppState()
