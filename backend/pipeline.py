import os
import json
import uuid
from pathlib import Path
from backend.config import UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR
from backend.ingest import download_youtube_video, extract_audio, get_video_metadata
from backend.transcribe import transcribe_audio_gemini
from backend.viral_detector import detect_viral_clips
from backend.editor import render_viral_clip

JOBS_DB = {}
JOBS_CACHE_FILE = TEMP_DIR / "jobs_cache.json"

def _save_jobs():
    try:
        with open(JOBS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(JOBS_DB, f, indent=2)
    except Exception:
        pass

def _load_jobs():
    global JOBS_DB
    if JOBS_CACHE_FILE.exists():
        try:
            with open(JOBS_CACHE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    JOBS_DB.update(loaded)
        except Exception:
            pass

_load_jobs()

def get_job(job_id: str) -> dict:
    if job_id not in JOBS_DB:
        _load_jobs()
    return JOBS_DB.get(job_id)

def create_job(video_path: str, title: str, duration: float, thumbnail: str = "") -> str:
    job_id = str(uuid.uuid4())[:8]
    JOBS_DB[job_id] = {
        "job_id": job_id,
        "title": title,
        "video_path": video_path,
        "duration": duration,
        "thumbnail": thumbnail,
        "status": "initialized",
        "progress": 5,
        "message": "Job initialized",
        "transcript": None,
        "clips": [],
        "rendered_clips": {}
    }
    _save_jobs()
    return job_id

def create_job_from_url(url: str, cookies: str = None) -> str:
    job_id = str(uuid.uuid4())[:8]
    JOBS_DB[job_id] = {
        "job_id": job_id,
        "title": "YouTube Video",
        "video_path": None,
        "url": url,
        "cookies": cookies,
        "duration": 0,
        "thumbnail": "",
        "status": "processing",
        "progress": 10,
        "message": "Connecting to YouTube & downloading video stream...",
        "transcript": None,
        "clips": [],
        "rendered_clips": {}
    }
    _save_jobs()
    return job_id

def run_analysis_pipeline(job_id: str, api_key: str = None) -> dict:
    """
    Executes Ingestion -> Audio Extraction -> Transcription -> Viral Detection.
    """
    job = JOBS_DB.get(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    try:
        # Step 1: Download from YouTube if needed
        if job.get("url") and not job.get("video_path"):
            job["status"] = "processing"
            job["progress"] = 15
            job["message"] = "Downloading YouTube video stream (anti-throttled)..."
            dl_res = download_youtube_video(job["url"], job_id, cookies=job.get("cookies"))
            job["video_path"] = dl_res["video_path"]
            job["title"] = dl_res["title"]
            job["duration"] = dl_res["duration"]
            job["thumbnail"] = dl_res.get("thumbnail", "")

        # Step 2: Use native YouTube transcript if available, or run Smart Window AI transcription
        transcript_data = None
        if 'dl_res' in locals() and dl_res.get("transcript"):
            transcript_data = dl_res["transcript"]
            job["progress"] = 70
            job["message"] = "Retrieved millisecond-accurate native speech timestamps..."
        else:
            job["status"] = "processing"
            job["progress"] = 35
            job["message"] = "Analyzing speech across high-retention timeline windows..."
            from backend.transcribe import transcribe_video_smart_windows
            transcript_data = transcribe_video_smart_windows(
                video_path=job["video_path"],
                duration=job["duration"],
                api_key=api_key
            )
            job["progress"] = 70
            num_segs = len(transcript_data.get("segments", []))
            job["message"] = f"Transcribed speech segments ({num_segs} key moments mapped)..."

        job["transcript"] = transcript_data
        job["progress"] = 80
        job["message"] = "Detecting viral hooks & retention curves with Gemini..."

        # Step 3: Viral moment detection
        clips = detect_viral_clips(transcript_data, job["duration"], api_key=api_key)
        
        for idx, c in enumerate(clips):
            c["id"] = f"clip_{idx + 1}"
            c["selected"] = True

        job["clips"] = clips
        job["status"] = "ready_for_render"
        job["progress"] = 100
        job["message"] = f"Found {len(clips)} viral moments ready for Premiere Pro editing!"
        _save_jobs()
        return job

    except Exception as e:
        job["status"] = "failed"
        job["message"] = f"Processing Error: {str(e)}"
        _save_jobs()
        raise e

def render_single_clip(job_id: str, clip_id: str, options: dict = None) -> dict:
    """
    Renders a specific candidate clip into a finished 9:16 vertical video.
    """
    job = JOBS_DB.get(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    clip_info = next((c for c in job["clips"] if c["id"] == clip_id), None)
    if not clip_info:
        raise ValueError(f"Clip {clip_id} not found in job {job_id}")

    start_s = clip_info["start_time"]
    end_s = clip_info["end_time"]
    
    clip_segments = []
    if job.get("transcript") and "segments" in job["transcript"]:
        for seg in job["transcript"]["segments"]:
            if seg.get("end", 0) >= start_s and seg.get("start", 0) <= end_s:
                clip_segments.append(seg)

    # If word-level segments for this specific clip window are missing, transcribe the exact clip slice
    if not clip_segments and job.get("video_path") and os.path.exists(job["video_path"]):
        from backend.transcribe import transcribe_audio_slice
        clip_segments = transcribe_audio_slice(
            source_video_path=job["video_path"],
            start_time=start_s,
            end_time=end_s
        )

    # If still empty (e.g. gameplay audio/music without clear speech), synthesize punchy hook words
    if not clip_segments:
        hook_text = clip_info.get("title", "UNBELIEVABLE MOMENT 🔥")
        words = hook_text.split()
        dur = max(1.0, end_s - start_s)
        word_dur = dur / max(1, len(words))
        word_list = []
        for i, w in enumerate(words):
            word_list.append({
                "word": w,
                "start": round(start_s + i * word_dur, 2),
                "end": round(start_s + (i + 1) * word_dur, 2)
            })
        clip_segments = [{
            "start": round(start_s, 2),
            "end": round(end_s, 2),
            "text": hook_text,
            "words": word_list
        }]

    result = render_viral_clip(
        source_video_path=job["video_path"],
        clip_info=clip_info,
        transcript_segments=clip_segments,
        options=options
    )

    job["rendered_clips"][clip_id] = result
    _save_jobs()
    return result
