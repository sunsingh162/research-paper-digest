# Build Progress Log

Running log of what's been built, key decisions, and verification results — kept in sync as the project progresses. See `README.md` for the polished final docs, and the approved plan for the full architecture.

Domain: **Research Paper Digest** — RAG assistant over arXiv-style research papers, with page/section citations.

---

## 2026-08-15 — Environment setup

- Target machine (macOS 15.7, Apple Silicon) had no Homebrew, no Node.js, and only system Python 3.9.6 (project needs Python 3.11+, Node 18+).
- Homebrew install failed non-interactively (needs an interactive sudo password this session can't supply).
- Installed **nvm** (`~/.nvm`) → Node v24.19.0 LTS, npm v11.17.0. No admin rights required.
- Installed **pyenv** (`~/.pyenv`) → Python 3.11.9, set as `pyenv global`. No admin rights required. (Note: the `_lzma` module didn't compile — no `xz` headers available without Homebrew. Not expected to affect this project's dependencies; flagged here in case a future package needs it.)
- Both tool loaders added to `~/.zshrc`.

## 2026-08-15 — Step 1: Scaffold

- `git init` at repo root.
- Created `backend/app/{routers,models,services,data/papers}` and `backend/storage/{faiss_index,logs}`.
- Root `.gitignore` (Python venv, `.env`, Next.js build artifacts, runtime-generated FAISS index / JSONL logs), `LICENSE` (MIT).
- **Backend**: FastAPI skeleton (`app/main.py`, `app/config.py` via `pydantic-settings`, `app/routers/health.py`). `GET /health` returns `{"status": "ok"}`. `CORS_ORIGINS` config accepts a plain comma-separated string (friendlier for PaaS env var dashboards than requiring JSON array syntax). Model defaults set to `claude-haiku-4-5-20251001` for generation/routing/RAGAS-judge.
- **Frontend**: scaffolded with `create-next-app@latest` (Next.js 16.3.1, React 19.2, TypeScript, Tailwind v4, App Router, Turbopack). Replaced the default template page with a minimal client component that calls the backend via `lib/api.ts` (reads `NEXT_PUBLIC_API_BASE_URL`) and shows online/offline status.
- **Next.js 16 note**: this version ships its own `AGENTS.md` warning that APIs may differ from training data (breaking changes: async `params`/`searchParams`, `middleware` → `proxy` rename, Turbopack now default, etc. — see `frontend/node_modules/next/dist/docs/01-app/02-guides/upgrading/version-16.md`). Checked before writing frontend code; none of the breaking changes affect this simple client-fetch page.
- **Verified end-to-end**: started both servers, drove the frontend with Playwright (headless Chromium — installed to a scratch dir since `chromium-cli` wasn't available in this environment), confirmed the page renders "Research Paper Digest" with a status badge reading **"online"** and zero browser console errors — i.e. the frontend successfully reached the FastAPI backend. Screenshot captured as evidence.
- ✅ Step 1 checkpoint met. Servers stopped after verification.

**Environment note for future steps:** this shell's default `PATH` doesn't have `node`/`npm`/`python` on it automatically — each new terminal needs `nvm`/`pyenv` loaded (see `~/.zshrc`, added during environment setup) and the backend venv activated (`source backend/.venv/bin/activate`).

## 2026-08-15 — GitHub setup

- Installed GitHub CLI (`gh`, to `~/bin`, no admin rights needed) and authenticated as `sunsingh162`.
- Created public repo **https://github.com/sunsingh162/research-paper-digest**, pushed Step 1.
- Note: local git commit identity is currently auto-detected (`simranvaishnav@Simrans-MacBook-Air.local`) rather than explicitly configured — flagged to the user; can be corrected with `git commit --amend --reset-author` if they want a different name/email on commits. Did not touch global git config.

## 2026-08-15 — Step 2: Ingestion & chunking

- Sourced the 3-paper seed corpus (real arXiv papers, not filler): *Attention Is All You Need* (1706.03762, 15pp), *BERT* (1810.04805, 16pp), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2005.11401, 19pp) — thematically fitting since it's literally the RAG paper.
- **Decision**: PDFs are *not* committed to the repo (third-party copyrighted arXiv content) — instead `backend/scripts/fetch_papers.py` downloads them from arXiv on demand. `.gitignore` excludes `backend/app/data/papers/*.pdf`.
- `backend/app/services/ingestion.py`: `pypdf` per-page text extraction (preserves page numbers for citations) + best-effort section-heading detection (regex + known-heading-word list) + token-aware chunking via `RecursiveCharacterTextSplitter.from_tiktoken_encoder` (650 tokens/chunk, 100 token overlap ≈ 15%, per the guide's 500–800 token / 10–15% overlap spec). Chunking is done per-page (not across page boundaries) so every chunk's page number is exact. Each chunk gets `{chunk_id, paper_id, filename, page, section, chunk_index}` metadata.
- **Known limitation** (to note in the final README): section-heading detection is best-effort — multi-column academic PDF text extraction via `pypdf` doesn't preserve reading order perfectly, so some sections are missed. Page-number citations are exact; section labels are a bonus, not guaranteed.
- **Verified**: ran ingestion against all 3 seeded PDFs — 102 total chunks, page ranges exactly matching each paper's real length (1–15, 1–16, 1–19), sample chunk inspected with correct metadata and readable content.
- ✅ Step 2 checkpoint met.

## 2026-08-15 — Git identity & authorship fix

- Set local (repo-scoped, not global) git identity to `Sunny Kumar Singh <sunsingh162@gmail.com>` at the user's request.
- Rewrote both existing commits (`git filter-branch`) to fix author/committer and strip the `Co-Authored-By: Claude` trailer, then force-pushed — safe since the repo was brand-new with no other collaborators. Future commits from this session drop the co-author trailer entirely.
- Confirmed via `git fetch` + `git cat-file` that the pushed history is clean (both commits solely authored by Sunny Kumar Singh, no co-author trailer). GitHub's own "Contributors" sidebar still briefly showed a cached `claude` entry from before the rewrite — that's a GitHub-side stats cache that lags behind a force-pushed rewrite; nothing left in the actual git history for it to be reading.
- Confirmed with the user: per the program's own Submission Guidelines doc, AI-assisted coding is explicitly permitted ("expected, not penalized") — this was a personal preference about commit display, not an academic-integrity requirement.

## 2026-08-15 — Step 3: Embeddings & FAISS index

- `backend/app/services/embeddings.py`: `langchain_huggingface.HuggingFaceEmbeddings` wrapping `sentence-transformers/all-MiniLM-L6-v2`, `normalize_embeddings=True`.
- `backend/app/services/vectorstore.py`: `langchain_community.vectorstores.FAISS` with `DistanceStrategy.MAX_INNER_PRODUCT` (correct pairing with normalized embeddings = cosine similarity). `build_index`, `save_index`/`load_index` (disk persistence, `allow_dangerous_deserialization=True` — safe, only ever loads an index this app wrote), `add_documents` (for future user uploads), `query_index` (top-k with scores).
- **Dependency note**: `langchain-community` is in a long-term deprecation/sunset process. Checked for the standalone replacement (`langchain-faiss` on PyPI) — it's still an empty placeholder package (exports nothing usable as of this check), so stayed on `langchain_community.vectorstores.FAISS`, which is fully functional today. Worth re-checking `langchain-faiss` maturity before the final submission if time allows.
- **Wired into the app itself** (not just a standalone script): `app/state.py` holds an in-memory `AppState` (FAISS store + per-paper metadata registry — appropriate for this single-process capstone deployment). `app/main.py` now uses a FastAPI `lifespan` handler that loads a cached index from disk if present, otherwise builds one from the seeded PDFs (fast — only 3 papers) and persists it. `GET /health` now reports `index_loaded`, `num_chunks`, `num_papers` for real.
- **Verified**: fresh build (deleted `storage/faiss_index/`) → app startup rebuilds from the 3 seeded PDFs → `/health` returns `{"index_loaded": true, "num_chunks": 102, "num_papers": 3}`. Separately verified in a script: same question run twice returns byte-identical top-k results and scores (repeatable); two different questions about different papers (Transformer self-attention vs. BERT masked-LM pretraining) return entirely disjoint top-3 chunks, each correctly pulled from the matching paper (query-sensitive, not hardcoded).
- ✅ Step 3 checkpoint met.

## 2026-08-15 — Anthropic API key & billing

- User created an Anthropic API key and added $5 in credits (Claude Console billing). Key saved to `backend/.env` (git-ignored, confirmed via `git check-ignore`, never printed to logs/output).
- Verified the key works with a live `ChatAnthropic` call before proceeding.

## 2026-08-15 — Step 4: LCEL generation chain

- `backend/app/models/schemas.py`: `SourceChunk` (chunk_id, paper_id, page, section, snippet) and `GenerationOutput` (answer, cited_chunk_ids).
- **Key design decision**: the LLM only ever outputs `cited_chunk_ids` (which chunk_ids it used) — never page numbers, sections, or snippets directly. The service layer (`generation.py`) resolves those `chunk_id`s back to the *actual* Document metadata afterwards. This avoids a real citation-hallucination risk: an LLM asked to reproduce a page number in its own output can get it wrong even when the underlying answer is correctly grounded; sourcing it from ground-truth chunk metadata instead makes every citation mechanically correct by construction.
- `backend/app/services/generation.py`: LCEL chain = `ChatPromptTemplate | ChatAnthropic.with_structured_output(GenerationOutput, method="json_schema")`. System prompt forces context-only answers and an explicit "not covered in the provided document(s)" response when the context doesn't contain the answer, instead of guessing. `format_context()` renders each chunk with a `[chunk_id=... | paper=... | page=... | section=...]` header so the model can cite by chunk_id.
- **Verified** against the real FAISS index from Step 3 (no routing/re-ranking wired in yet — that's Steps 5–6, this only tests the generation stage in isolation):
  - Answerable question ("What is the self-attention mechanism in the Transformer architecture?") → correct, grounded answer citing 3 real chunks from the Attention paper, pages 2/3/5 — all citations verified to point to chunks that actually discuss self-attention.
  - Out-of-scope question ("What is the capital of France?", deliberately run against retrieved-but-irrelevant Transformer-paper context) → model correctly refused: *"This isn't covered in the provided document(s)... They do not contain information about the capital of France."* — empty `cited_chunk_ids`, no hallucination.
- ✅ Step 4 checkpoint met.

## 2026-08-15 — Step 5: Query routing & decomposition

- `backend/app/services/routing.py`: one structured-output Claude call (`RouteDecision {query_type, sub_queries}`) classifying `single_fact` / `multi_part` / `summarization`. For multi-part questions, decomposition into 2+ atomic sub-questions happens in the *same* call (no extra round trip).
- `backend/app/services/retrieval.py`: `retrieve_merged()` runs FAISS similarity search per sub-query, merges results across sub-queries, dedupes by `chunk_id` keeping each chunk's best score, returns sorted descending.
- **Verified** against the real index:
  - Single-fact question ("What dataset was used to pretrain BERT?") → correctly classified `single_fact`, sub_queries = `[original question]` unchanged.
  - Genuine multi-part question ("What is the self-attention mechanism in the Transformer, and how does BERT use masked language modeling for pretraining?") → correctly classified `multi_part`, decomposed into 2 clean atomic sub-questions (one per paper). Merged retrieval then pulled chunks from **both** `attention-is-all-you-need` and `bert-pretraining` — i.e. both parts of the question demonstrably retrieved for, not just whichever paper scored higher on the combined query.
- ✅ Step 5 checkpoint met.

## 2026-08-15 — Step 6: Re-ranking

- `backend/app/services/reranking.py`: `sentence_transformers.CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` rescoring merged FAISS candidates. Every call logs pre-rerank (FAISS) and post-rerank (cross-encoder) ordering, plus a computed `rank_changes` diff, to `backend/storage/logs/rerank_log.jsonl`.
- **Verified**: ran 4 test queries through the full routing → retrieval → rerank pipeline. All 4 showed substantial reordering (6–8 rank changes out of 8–9 candidates each) — re-ranking is doing real work, not a no-op.
- **README evidence captured** (query: *"What optimizer and learning rate schedule was used to train the Transformer?"*): FAISS's #1 result (`attention-is-all-you-need_p8_c0`) dropped to #3 after re-ranking; the actual best chunk (`attention-is-all-you-need_p7_c1`, FAISS rank #3) moved to #1. A `bert-pretraining` chunk that FAISS ranked #2 — plausible only by surface similarity, not actually about the Transformer's optimizer — correctly dropped to #5 post-rerank. Full JSON saved for the README's before/after section.
- ✅ Step 6 checkpoint met.

## 2026-08-15 — Environment fix: `_lzma` module

- Hit a real blocker installing `ragas`: its dependency chain (via HuggingFace `datasets`) imports Python's stdlib `lzma` unconditionally, which never compiled during the original pyenv Python 3.11.9 build (no `xz`/liblzma available without Homebrew — this was flagged as a non-fatal warning back at initial environment setup, and it came due).
- Fix: built `xz` 5.6.3 from source into a user-local prefix (`~/local-libs`, no admin rights needed), then reinstalled Python 3.11.9 via pyenv with `CPPFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH` pointed at it. Confirmed `import lzma` now works.
- Recreated the backend `.venv` from scratch against the fixed Python build (old venv was linked against the pre-fix interpreter) and reinstalled all requirements — verified clean.

## 2026-08-15 — Step 7: RAGAS evaluation

This was flagged in the plan as the highest API-churn risk in the stack, so every claim below was verified against the actually-installed `ragas==0.4.3` package rather than assumed from docs/training data. Three real incompatibilities were found and fixed; full detail is in the module docstring of `backend/app/services/evaluation.py`:

1. **Import-breaking dependency conflict**: `ragas.llms.base` unconditionally imports `langchain_community.chat_models.vertexai.ChatVertexAI` (dead code path for the deprecated `LangchainLLMWrapper` we don't use), which was removed from `langchain-community` 0.4.x. Fixed by pinning `langchain-community==0.3.31` (last version with that module) — our own FAISS usage is unaffected.
2. **Sync-vs-async client**: `ragas.llms.llm_factory(provider="anthropic", ...)` needs `anthropic.AsyncAnthropic`, not the sync `Anthropic` client — `ascore()` raises `TypeError` at call time on a sync client with no earlier warning.
3. **Sampling-params incompatibility with current Claude models**: ragas's `InstructorLLM` always sends both `temperature` and `top_p` to the provider by default, with no public way to omit one. Current Claude models reject that combination outright (`claude-haiku-4-5-20251001`), and `claude-sonnet-5` deprecates `temperature` entirely — confirmed both errors directly against the live API before concluding this wasn't a config mistake on our side. Worked around by overwriting the constructed LLM's `model_args` attribute post-construction to just `{"max_tokens": 4096}` (also bumped from ragas's 1024 default — the faithfulness metric's NLI-verdict step can truncate at that ceiling).
4. Confirmed real export/method names by inspecting the installed package directly (`ragas.metrics.collections.{Faithfulness, AnswerRelevancy, ContextPrecisionWithReference}`, `.ascore(...)`, `MetricResult.value`) rather than trusting any single doc source — `AnswerRelevancy` is the real name (not `ResponseRelevancy`, which appeared in some outside references during planning).

Architecture built:
- `backend/app/services/pipeline.py`: `answer_question(store, question)` — the actual end-to-end composition (route → multi-query retrieve → rerank → generate) that Steps 4–6 built as separate, independently-tested stages. This is what both the golden-set eval and the future `/api/query` endpoint call.
- `backend/app/data/golden_eval_set.json`: 8 hand-written question/reference pairs covering all 3 papers (including cross-paper questions), used for `context_precision` (needs a reference answer a live query doesn't have).
- `backend/app/services/evaluation.py`: `score_live_query()` (faithfulness + answer_relevancy, reference-free, safe on real traffic), `score_context_precision()` (golden-set only), `run_golden_eval()` (runs the full pipeline + all 3 metrics against the golden set, logs each to `eval_log.jsonl`).

**Verified**: ran `run_golden_eval()` against the real index/pipeline. Aggregate: faithfulness 0.95, answer_relevancy 0.68, context_precision 0.56 — scores present, varied, and plausible (not all 1.0, not missing), satisfying the grading rubric directly. Two `answer_relevancy=0.0` results were sanity-checked individually rather than assumed to be a bug: both were cases where the model honestly said the retrieved context didn't fully cover the question (e.g. BERT's MLM/NSP task *names* weren't present in the top-4 reranked chunks for that query) — correct, honest low scores that also surface a real, documentable retrieval-coverage limitation, not hallucination. Good material for the README rather than something to hide.
- ✅ Step 7 checkpoint met.

## 2026-08-15 — Step 8a: API endpoints wired end-to-end

Before building the UI, assembled the actual FastAPI routers tying every prior step's service module together, and smoke-tested each one live:

- `GET /api/papers` — lists ingested papers from `app_state.papers`.
- `POST /api/upload` — accepts a PDF, chunks it (`ingestion.chunk_paper`), adds to the live FAISS index (`vectorstore.add_documents`) or builds a fresh one if empty, persists to disk, registers in `app_state.papers`. Verified live: uploaded a test PDF, confirmed it appeared in `/api/papers` immediately, then cleaned up the test artifact (uploads land in the same `papers_dir` as the seed corpus, so anything dropped there persists across local dev restarts by design — consistent with the documented deploy-time behavior where `papers_dir` only ever has the seed PDFs unless a volume is attached).
- `POST /api/query` — runs `pipeline.answer_question` (the full route → retrieve → rerank → generate composition from Step 7).
  - **Design change made after live-testing latency**: originally scored RAGAS (faithfulness + answer_relevancy) inline before responding, per the original plan. Measured **~44s total** (12-14s pipeline + ~30s RAGAS scoring, since scoring itself makes several more Claude calls) — that's uncomfortably close to, and could exceed, the assignment's "cited answer within 60 seconds" checkpoint on a slower connection. **Changed to**: return the answer/sources/citations immediately after the pipeline (~12s), score RAGAS in a FastAPI `BackgroundTask` afterward, log it to `eval_log.jsonl` the same as before -- just not blocking the response. RAGAS is still "logged per query" as the assignment requires; it's just not synchronously inline. Response includes `ragas: null, ragas_pending: true` so the frontend knows to fetch the score shortly after rather than expect it inline.
- `POST /api/eval/run`, `GET /api/eval/logs`, `GET /api/eval/rerank-log` — golden-set batch eval trigger and JSONL log tailing.
- **Verified live end-to-end**: `/api/query` for "What are the two unsupervised tasks used to pretrain BERT?" → correct answer (Masked LM + Next Sentence Prediction, both named explicitly) with accurate citations, returned in ~12s; background task logged `faithfulness=0.8, answer_relevancy≈1.0` about 22s later, retrievable via `/api/eval/logs`.
- ✅ API layer complete and verified; proceeding to the frontend UI (rest of Step 8).
