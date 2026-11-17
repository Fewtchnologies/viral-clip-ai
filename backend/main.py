import os
import re
import shutil
import uuid
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, GEMINI_API_KEY
from backend.ingest import download_youtube_video, get_video_metadata
from backend.pipeline import JOBS_DB, create_job, create_job_from_url, run_analysis_pipeline, render_single_clip
from backend.voiceover import VOICE_PROFILES

app = FastAPI(
    title="AI Viral Clip Studio API",
    description="Automated AI-powered YouTube video clipping, 9:16 smart framing, dynamic captions, and Premiere Pro-style editing.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeURLRequest(BaseModel):
    url: str
    api_key: Optional[str] = None

class RenderOptions(BaseModel):
    caption_style: Optional[dict] = {
        "font_name": "Arial Black",
        "font_size": 42,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FFFF",
        "outline_width": 3.5,
        "max_words_per_line": 3,
        "uppercase": True,
        "bounce_animation": True,
    }
    enable_punch_zoom: Optional[bool] = True
    enable_hook_banner: Optional[bool] = True
    enable_color_grade: Optional[bool] = True
    enable_impact_flash: Optional[bool] = True
    enable_progress_bar: Optional[bool] = True
    progress_bar_color: Optional[str] = "yellow"
    hook_style: Optional[str] = "gold"
    custom_hook_title: Optional[str] = None
    enable_voiceover: Optional[bool] = False
    voice_key: Optional[str] = "deep_narrator"
    voiceover_text: Optional[str] = None

@app.get("/api/voices")
def get_available_voices():
    """Returns list of neural AI voice profiles."""
    return VOICE_PROFILES

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "gemini_api_key_configured": bool(GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    }

@app.post("/api/analyze/url")
def analyze_youtube_url(payload: AnalyzeURLRequest, background_tasks: BackgroundTasks):
    """Initiates asynchronous YouTube video download and background viral analysis."""
    try:
        job_id = create_job_from_url(payload.url)
        
        # Run entire download + analysis pipeline in background
        background_tasks.add_task(
            run_analysis_pipeline,
            job_id=job_id,
            api_key=payload.api_key
        )

        return {
            "status": "started",
            "job_id": job_id,
            "title": "YouTube Video",
            "duration": 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analyze/upload")
async def analyze_video_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    """Uploads local video and initiates background viral analysis."""
    try:
        file_id = str(uuid.uuid4())[:8]
        raw_stem = Path(file.filename).stem
        safe_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_stem)
        ext = Path(file.filename).suffix or ".mp4"
        dest_filename = f"{file_id}_{safe_stem}{ext}"
        dest_path = UPLOAD_DIR / dest_filename

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        meta = get_video_metadata(str(dest_path))
        job_id = create_job(
            video_path=str(dest_path),
            title=Path(file.filename).stem,
            duration=meta["duration"]
        )

        background_tasks.add_task(
            run_analysis_pipeline,
            job_id=job_id,
            api_key=api_key
        )

        return {
            "status": "started",
            "job_id": job_id,
            "title": Path(file.filename).stem,
            "duration": meta["duration"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/job/{job_id}")
def get_job_status(job_id: str):
    """Returns real-time progress and identified viral clips."""
    from backend.pipeline import get_job
    job = get_job(job_id)
    if not job:
        if job_id == "demo":
            return get_demo_preview()
        return {
            "job_id": job_id,
            "status": "failed",
            "progress": 0,
            "message": "Session expired or job not found. Please click 'Load Demo' or start a new analysis.",
            "clips": []
        }
    return job

@app.post("/api/job/{job_id}/render/{clip_id}")
def render_clip(job_id: str, clip_id: str, options: RenderOptions):
    """Renders candidate viral clip into 9:16 vertical video with Premiere Pro-style edits."""
    try:
        result = render_single_clip(
            job_id=job_id,
            clip_id=clip_id,
            options=options.model_dump()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/video/{filename}")
def stream_video(filename: str):
    """Streams or downloads rendered MP4 video."""
    video_path = OUTPUT_DIR / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(video_path), media_type="video/mp4", filename=filename)

@app.get("/api/thumbnail/{filename}")
def get_thumbnail(filename: str):
    """Serves video thumbnail image."""
    thumb_path = OUTPUT_DIR / filename
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(path=str(thumb_path), media_type="image/jpeg")

@app.get("/api/demo")
def get_demo_preview():
    """Returns pre-rendered demo job with viral clips and 9:16 vertical video player preview."""
    demo_job = {
        "job_id": "demo",
        "title": "Mastering Short-Form Video (Premiere Pro FX Demo)",
        "duration": 5.5,
        "video_path": str(TEMP_DIR / "sample_input_16x9.mp4"),
        "status": "ready_for_render",
        "progress": 100,
        "message": "Demo clips ready for preview!",
        "transcript": {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.5,
                    "text": "Stop scrolling right now! This is the ten million dollar lesson!",
                    "words": [
                        {"word": "Stop", "start": 0.0, "end": 0.5},
                        {"word": "scrolling", "start": 0.5, "end": 1.1},
                        {"word": "right", "start": 1.1, "end": 1.4},
                        {"word": "now!", "start": 1.4, "end": 1.8},
                        {"word": "This", "start": 1.8, "end": 2.2},
                        {"word": "is", "start": 2.2, "end": 2.4},
                        {"word": "the", "start": 2.4, "end": 2.6},
                        {"word": "ten", "start": 2.6, "end": 2.9},
                        {"word": "million", "start": 2.9, "end": 3.4},
                        {"word": "dollar", "start": 3.4, "end": 3.9},
                        {"word": "lesson!", "start": 3.9, "end": 4.5}
                    ]
                }
            ]
        },
        "clips": [
            {
                "id": "clip_1",
                "title": "THE $10,000,000 LESSON 💰",
                "start_time": 0.0,
                "end_time": 5.5,
                "viral_score": 99,
                "hook_summary": "High tension hook revealing a multimillion dollar lesson in the first 3 seconds.",
                "punch_keywords": ["BORING", "PREMIERE", "VOICEOVER"],
                "hooks": {
                    "curiosity": "YOU WON'T BELIEVE THIS 🤯",
                    "warning": "STOP DOING THIS RIGHT NOW 🚨",
                    "secret": "THE VIRAL SECRET NOBODY TELLS YOU 🤫",
                    "value": "THE $10,000,000 LESSON 💰"
                }
            },
            {
                "id": "clip_2",
                "title": "STOP DOING THIS RIGHT NOW 🚨",
                "start_time": 0.0,
                "end_time": 5.5,
                "viral_score": 96,
                "hook_summary": "Loss-aversion warning hook provoking immediate curiosity to stop scrolling.",
                "punch_keywords": ["STOP", "MISTAKE", "VIRAL"],
                "hooks": {
                    "curiosity": "WAIT TILL THE END 😱",
                    "warning": "STOP DOING THIS RIGHT NOW 🚨",
                    "secret": "THEY LIED ABOUT THIS 🤫",
                    "value": "THE 10X RETENTION FORMULA 💰"
                }
            }
        ],
        "rendered_clips": {
            "clip_1": {
                "status": "completed",
                "clip_id": "clip_1",
                "filename": "voiceover_ducking_9x16.mp4",
                "thumbnail_name": "voiceover_ducking_9x16_thumb.jpg",
                "start_time": 0.0,
                "end_time": 5.5,
                "duration": 5.5,
                "tracking_mode": "Single Speaker Centered",
                "hook_title": "THE $10,000,000 LESSON 💰",
                "voiceover": {
                    "voice_name": "Deep Dramatic Narrator",
                    "clean_text": "Stop scrolling right now! This is the ten million dollar lesson!"
                },
                "effects_applied": {
                    "lumetri_color_grade": True,
                    "punch_in_zoom": True,
                    "hook_banner": True,
                    "bottom_progress_bar": True,
                    "impact_flash": True,
                    "ai_voiceover": True
                }
            },
            "clip_2": {
                "status": "completed",
                "clip_id": "clip_2",
                "filename": "premiere_pro_viral_fx_9x16.mp4",
                "thumbnail_name": "premiere_pro_viral_fx_9x16_thumb.jpg",
                "start_time": 0.0,
                "end_time": 5.5,
                "duration": 5.5,
                "tracking_mode": "Single Speaker Centered",
                "hook_title": "STOP DOING THIS RIGHT NOW 🚨",
                "effects_applied": {
                    "lumetri_color_grade": True,
                    "punch_in_zoom": True,
                    "hook_banner": True,
                    "bottom_progress_bar": True,
                    "impact_flash": True,
                    "ai_voiceover": False
                }
            }
        }
    }
    JOBS_DB["demo"] = demo_job
    return demo_job

# Pre-populate demo in database
get_demo_preview()

# Mount Built React Frontend if present
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

@app.exception_handler(404)
async def custom_404_handler(request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": f"API endpoint '{request.url.path}' not found."})
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(status_code=404, content={"detail": "Not found"})

if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

