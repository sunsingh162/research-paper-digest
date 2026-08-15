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
