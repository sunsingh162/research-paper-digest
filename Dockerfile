# Root-level Dockerfile (backend deployment). Lives at the repo root because
# Render's direct API-created services only look for a literal `Dockerfile`
# here regardless of any custom dockerfilePath/dockerContext config -- see
# PROGRESS.md for the investigation. Build context is the whole repo; only
# backend/ is actually used.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake in the local HF models at build time -- avoids a slow/flaky download on
# every cold start (Render's free tier spins the service down after 15 min idle).
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

COPY backend/app ./app
COPY backend/scripts ./scripts

# Seed corpus PDFs aren't committed (third-party arXiv content) -- fetched at
# build time instead. The FAISS index itself is rebuilt from these at container
# startup (app/main.py lifespan) -- fast with only 3 papers, no volume required.
RUN python scripts/fetch_papers.py

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
