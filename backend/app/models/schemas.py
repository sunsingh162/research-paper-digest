from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: str
    paper_id: str
    page: int
    section: str | None = None
    snippet: str


class GenerationOutput(BaseModel):
    """Structured output from the generation LLM. Note: only `cited_chunk_ids` comes
    from the model -- full source metadata (page, section, snippet) is looked up
    from the actual retrieved Documents afterwards, never trusted from the LLM
    itself, to avoid hallucinated citation details."""

    answer: str = Field(
        description="The grounded answer, or an explicit statement that the "
        "provided context doesn't cover the question."
    )
    cited_chunk_ids: list[str] = Field(
        default_factory=list,
        description="chunk_id values (from the provided context) of chunks actually "
        "used to produce the answer. Empty if the answer wasn't found in the context.",
    )
