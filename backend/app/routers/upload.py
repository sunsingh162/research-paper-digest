from fastapi import APIRouter, HTTPException, UploadFile

from app.config import get_settings
from app.services import ingestion
from app.services import vectorstore as vs
from app.state import PaperMeta, app_state

router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload_paper(file: UploadFile) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    settings = get_settings()
    settings.papers_dir.mkdir(parents=True, exist_ok=True)

    paper_id = ingestion.make_paper_id(file.filename)
    if paper_id in app_state.papers:
        raise HTTPException(status_code=409, detail=f"A paper with id '{paper_id}' was already uploaded.")

    dest_path = settings.papers_dir / file.filename
    contents = await file.read()
    dest_path.write_bytes(contents)

    chunks = ingestion.chunk_paper(dest_path, paper_id=paper_id, filename=file.filename)
    if not chunks:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="No extractable text found in this PDF.")

    if app_state.vectorstore is None:
        app_state.vectorstore = vs.build_index(chunks)
    else:
        vs.add_documents(app_state.vectorstore, chunks)
    vs.save_index(app_state.vectorstore, settings.faiss_index_dir)

    num_pages = max(c.metadata["page"] for c in chunks)
    app_state.papers[paper_id] = PaperMeta(
        paper_id=paper_id, filename=file.filename, num_pages=num_pages, num_chunks=len(chunks)
    )

    return {
        "paper_id": paper_id,
        "filename": file.filename,
        "num_pages": num_pages,
        "num_chunks": len(chunks),
        "status": "indexed",
    }
