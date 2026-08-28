from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from qa_system.services.transcription import OfflineTranscriptionService

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="金融销售电话质检系统")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
executor = ThreadPoolExecutor(max_workers=2)
service = OfflineTranscriptionService()
jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/jobs")
async def create_job(
    files: list[UploadFile] = File(...),
    diarization: str = Form("campp"),
    merge_threshold_chars: int = Form(12),
    hotwords: str = Form(""),
):
    job_id = uuid4().hex
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    source_paths: list[str] = []
    for file in files:
        save_path = job_dir / file.filename
        content = await file.read()
        save_path.write_bytes(content)
        source_paths.append(str(save_path))

    jobs[job_id] = {"status": "running", "created_at": datetime.now().isoformat()}

    def _run() -> None:
        try:
            service.diarizer.strategy = diarization
            transcripts = service.transcribe_batch(
                source_paths=source_paths,
                merge_threshold_chars=merge_threshold_chars,
                hotwords=hotwords,
            )
            result_file = RESULT_DIR / f"{job_id}.txt"
            dialogue_logs = [service.render_dialogue_log(t) for t in transcripts]
            result_file.write_text("\n\n".join(dialogue_logs), encoding="utf-8")
            jobs[job_id] = {
                "status": "done",
                "result": result_file.read_text(encoding="utf-8"),
                "files": [t.source_file for t in transcripts],
            }
        except Exception as exc:
            jobs[job_id] = {"status": "failed", "error": str(exc)}

    executor.submit(_run)
    return JSONResponse({"job_id": job_id, "status": jobs[job_id]["status"]})


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        return JSONResponse({"error": "job not found"}, status_code=404)
    return JSONResponse(jobs[job_id])
