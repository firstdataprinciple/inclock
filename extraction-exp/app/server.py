"""FastAPI backend: upload a PDF, poll the job, fetch rendered pages + results."""
from __future__ import annotations

import tempfile
import threading
import uuid
from pathlib import Path

import pymupdf as fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .pipeline import ROOT, extract

app = FastAPI(title="extraction-exp")
TMP = Path(tempfile.mkdtemp(prefix="extraction-exp-"))
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()  # OCR engines are not thread-safe: one extraction at a time


def _run(job: dict):
    def progress(p, m):
        job.update(progress=p, message=m)

    with LOCK:
        try:
            job["result"] = extract(job["path"], progress)
            job["status"] = "done"
        except Exception as e:  # surfaced to the UI
            job.update(status="error", message=f"{type(e).__name__}: {e}")


@app.post("/api/extract")
async def api_extract(pdf: UploadFile = File(...)):
    jid = uuid.uuid4().hex
    path = TMP / f"{jid}.pdf"
    path.write_bytes(await pdf.read())
    job = {"id": jid, "path": str(path), "name": pdf.filename, "status": "running", "progress": 0.0, "message": "Queued"}
    JOBS[jid] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": jid}


def _job(jid: str) -> dict:
    if jid not in JOBS:
        raise HTTPException(404, "unknown job")
    return JOBS[jid]


@app.get("/api/job/{jid}")
def api_job(jid: str):
    j = _job(jid)
    return {k: v for k, v in j.items() if k != "path"}


@app.get("/api/pdf/{jid}")
def api_pdf(jid: str):
    return FileResponse(_job(jid)["path"], media_type="application/pdf")


@app.get("/api/page/{jid}/{n}.png")
def api_page(jid: str, n: int, scale: float = 2.0):
    """Render page n at `scale` pixels per PDF point (the viewer overlays boxes on this)."""
    with fitz.open(_job(jid)["path"]) as doc:
        if not 1 <= n <= len(doc):
            raise HTTPException(404, "no such page")
        pix = doc[n - 1].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return Response(pix.tobytes("png"), media_type="image/png", headers={"Cache-Control": "max-age=3600"})


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
