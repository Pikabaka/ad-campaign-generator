"""FastAPI server for the Ad Campaign Studio.

Architecture: poll-based.
  - POST /api/generate kicks off a background asyncio task and returns {job_id}
  - Server keeps job state in JOB_STATES (in-memory dict)
  - Client polls GET /api/job-state/{job_id}?since=N every 2s for new events
  - Bulletproof against connection drops, sleeping browsers, etc.

Endpoints:
  GET  /                         → index.html
  GET  /static/*                 → frontend assets
  GET  /outputs/{c}/{f}          → generated campaign assets
  GET  /presets_demo/{c}/{f}     → pre-rendered demo case assets
  GET  /api/health               → config sanity check
  GET  /api/presets              → 8 style presets (summary)
  GET  /api/preset/{id}          → full preset detail
  GET  /api/product-info         → default product_info.json
  POST /api/extract-product      → freeform text → structured product fields
  POST /api/generate             → start pipeline, returns {job_id}
  GET  /api/job-state/{id}?since=N → poll endpoint, returns events since index N
  GET  /api/gallery              → list past campaigns
  GET  /api/demo-cases           → list pre-rendered demo cases
  POST /api/export-pdf/{c}       → build & return PDF for campaign c
  GET  /api/campaign/{id}        → get campaign summary
"""

import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import (
    FileResponse, JSONResponse, HTMLResponse
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline import run_pipeline, extract_product_info
from pdf_export import export_pitch_deck
from presets import list_presets, get_preset

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
OUTPUTS = ROOT / "outputs"
PRESETS_DEMO = ROOT / "presets_demo"
OUTPUTS.mkdir(exist_ok=True)
PRESETS_DEMO.mkdir(exist_ok=True)

app = FastAPI(title="AI Ad Campaign Studio")

# In-memory job store: job_id -> state dict
#   state = { "status": "running"|"done"|"error", "events": [...],
#             "started_at": float, "updated_at": float, "error": str|None }
JOB_STATES: dict[str, dict] = {}
JOB_TTL_SEC = 3600  # keep job state for 1h after last update


def _gc_jobs():
    now = time.time()
    stale = [k for k, v in JOB_STATES.items() if now - v.get("updated_at", 0) > JOB_TTL_SEC]
    for k in stale:
        JOB_STATES.pop(k, None)


# --- Static / asset routes -------------------------------------------------

if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")
app.mount("/presets_demo", StaticFiles(directory=PRESETS_DEMO), name="presets_demo")


@app.get("/", response_class=HTMLResponse)
async def index():
    idx = STATIC / "index.html"
    if not idx.exists():
        return HTMLResponse("<h1>UI not built yet</h1><p>Missing static/index.html</p>", status_code=500)
    return FileResponse(idx)


# --- Health & config --------------------------------------------------------

@app.get("/api/health")
async def health():
    cfg_path = ROOT / "api_config.json"
    has_config = cfg_path.exists()
    has_keys = False
    if has_config:
        try:
            cfg = json.loads(cfg_path.read_text())
            has_keys = bool(cfg.get("openai_api_key")) and bool(cfg.get("fal_api_key"))
        except Exception:
            pass
    import shutil as _shutil
    return {
        "config_present": has_config,
        "keys_present": has_keys,
        "ffmpeg": bool(_shutil.which("ffmpeg")),
    }


# --- Presets / product info -------------------------------------------------

@app.get("/api/presets")
async def api_presets():
    return [
        {k: p[k] for k in ("id", "name", "emoji", "gradient", "tone")}
        for p in list_presets()
    ]


@app.get("/api/preset/{preset_id}")
async def api_preset_detail(preset_id: str):
    p = get_preset(preset_id)
    if not p:
        raise HTTPException(404, "preset not found")
    return p


@app.get("/api/product-info")
async def api_product_info():
    p = ROOT / "product_info.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


class ExtractReq(BaseModel):
    text: str


@app.post("/api/extract-product")
async def api_extract(req: ExtractReq):
    try:
        return await extract_product_info(req.text)
    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {e}")


# --- Generation pipeline ----------------------------------------------------

class GenerateReq(BaseModel):
    product_info: dict
    preset_id: str | None = None


@app.post("/api/generate")
async def api_generate(req: GenerateReq):
    _gc_jobs()
    job_id = uuid.uuid4().hex[:12]
    state: dict = {
        "status": "running",
        "events": [],
        "started_at": time.time(),
        "updated_at": time.time(),
        "error": None,
    }
    JOB_STATES[job_id] = state

    async def _runner():
        try:
            await run_pipeline(req.product_info, req.preset_id, state, OUTPUTS)
            state["status"] = "done"
        except Exception as e:
            state["status"] = "error"
            state["error"] = f"{type(e).__name__}: {e}"
            state["events"].append({"event": "error", "data": {"message": state["error"]}})
        finally:
            state["updated_at"] = time.time()

    asyncio.create_task(_runner())
    return {"job_id": job_id}


@app.get("/api/job-state/{job_id}")
async def api_job_state(job_id: str, since: int = 0):
    s = JOB_STATES.get(job_id)
    if not s:
        return JSONResponse({"status": "unknown", "events": [], "total_events": 0})
    events = s["events"][since:] if since < len(s["events"]) else []
    return {
        "status": s["status"],
        "events": events,
        "total_events": len(s["events"]),
        "error": s.get("error"),
    }


# --- Gallery ----------------------------------------------------------------

def _scan_campaigns(root: Path):
    items = []
    if not root.exists():
        return items
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        summary_p = d / "campaign_summary.json"
        if not summary_p.exists():
            continue
        try:
            summary = json.loads(summary_p.read_text())
        except Exception:
            continue
        items.append({
            "id": d.name,
            "product_name": summary.get("product_info", {}).get("product_name", "Untitled"),
            "company_name": summary.get("product_info", {}).get("company_name", ""),
            "slogan": summary.get("campaign_theme", {}).get("slogan", ""),
            "preset_id": summary.get("preset_id"),
            "total_cost": summary.get("total_cost", 0),
            "poster": f"{root.name}/{d.name}/poster.png",
            "video": f"{root.name}/{d.name}/ad_video.mp4",
            "ig_square": f"{root.name}/{d.name}/poster_ig_square.jpg",
            "ig_story": f"{root.name}/{d.name}/poster_ig_story.jpg",
            "wide": f"{root.name}/{d.name}/poster_wide.jpg",
            "summary": summary,
        })
    return items


@app.get("/api/gallery")
async def api_gallery():
    return _scan_campaigns(OUTPUTS)


@app.get("/api/demo-cases")
async def api_demo_cases():
    return _scan_campaigns(PRESETS_DEMO)


# --- PDF export -------------------------------------------------------------

@app.post("/api/export-pdf/{campaign_id}")
async def api_export_pdf(campaign_id: str):
    for root in (OUTPUTS, PRESETS_DEMO):
        cdir = root / campaign_id
        if cdir.exists():
            out_path = cdir / "pitch_deck.pdf"
            try:
                await asyncio.to_thread(export_pitch_deck, cdir, out_path)
            except Exception as e:
                raise HTTPException(500, f"PDF export failed: {e}")
            return FileResponse(out_path, media_type="application/pdf",
                                filename=f"{campaign_id}_pitch_deck.pdf")
    raise HTTPException(404, "campaign not found")


@app.get("/api/campaign/{campaign_id}")
async def api_campaign(campaign_id: str):
    for root in (OUTPUTS, PRESETS_DEMO):
        cdir = root / campaign_id
        summary_p = cdir / "campaign_summary.json"
        if summary_p.exists():
            return json.loads(summary_p.read_text())
    raise HTTPException(404, "campaign not found")


# --- Run convenience --------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
