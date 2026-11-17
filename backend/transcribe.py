import os
import json
import time
from pathlib import Path
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY

def transcribe_audio_gemini(audio_path: str, api_key: str = None) -> dict:
    """
    Transcribes audio using Gemini 2.5 Flash with word-level and phrase-level timestamps.
    Returns:
        {
            "full_text": str,
            "segments": [
                {
                    "start": float,
                    "end": float,
                    "text": str,
                    "words": [{"word": str, "start": float, "end": float}]
                }
            ]
        }
    """
    key = api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is required for AI transcription and viral analysis.")

    client = genai.Client(
        api_key=key,
        http_options=types.HttpOptions(timeout=180000)
    )

    # Ensure audio filename is 100% ASCII to prevent httpx header UnicodeEncodeError in google-genai SDK
    audio_file = Path(audio_path)
    clean_audio_path = audio_path
    temp_copy = None

    if any(ord(c) > 127 for c in audio_file.name):
        import shutil, uuid
        temp_name = f"safe_audio_{uuid.uuid4().hex[:8]}{audio_file.suffix}"
        temp_copy = audio_file.parent / temp_name
        shutil.copy2(audio_file, temp_copy)
        clean_audio_path = str(temp_copy)

    audio_upload = None
    try:
        # Upload audio file to Gemini File API with retry resilience
        for attempt in range(3):
            try:
                audio_upload = client.files.upload(file=clean_audio_path)
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(2 * (attempt + 1))
    finally:
        if temp_copy and temp_copy.exists():
            try:
                temp_copy.unlink()
            except Exception:
                pass
    
    # Wait for processing if needed
    while audio_upload.state.name == "PROCESSING":
        time.sleep(1)
        audio_upload = client.files.get(name=audio_upload.name)

    prompt = """
    Transcribe the spoken audio with high-precision timestamps.
    Break the speech into natural spoken sentences/segments (each around 2-8 seconds long).
    Provide up to 40 key prominent spoken segments across the audio.
    For each segment, provide:
    1. start timestamp in seconds (float)
    2. end timestamp in seconds (float)
    3. text of the segment
    4. word-level timestamps: for each word in the segment, provide its exact 'word', 'start' (float seconds), and 'end' (float seconds).

    Output STRICT JSON matching this structure:
    {
      "full_text": "...",
      "segments": [
        {
          "start": 0.0,
          "end": 3.4,
          "text": "Have you ever wondered why some videos go viral?",
          "words": [
            {"word": "Have", "start": 0.0, "end": 0.25},
            {"word": "you", "start": 0.26, "end": 0.45},
            {"word": "ever", "start": 0.46, "end": 0.70},
            {"word": "wondered", "start": 0.72, "end": 1.15},
            {"word": "why", "start": 1.18, "end": 1.40},
            {"word": "some", "start": 1.42, "end": 1.65},
            {"word": "videos", "start": 1.68, "end": 2.10},
            {"word": "go", "start": 2.12, "end": 2.35},
            {"word": "viral?", "start": 2.38, "end": 3.40}
          ]
        }
      ]
    }
    """

    try:
        response = None
        last_err = None
        candidate_models = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-3.8-flash"]
        for attempt in range(3):
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[audio_upload, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                        )
                    )
                    if response and response.text:
                        break
                except Exception as e:
                    last_err = e
                    time.sleep(1.5)
            if response:
                break

        if not response:
            raise last_err or RuntimeError("Failed to transcribe audio with Gemini models")
        
        result = json.loads(response.text)
        return result
    finally:
        try:
            client.files.delete(name=audio_upload.name)
        except Exception:
            pass

def transcribe_audio_slice(source_video_path: str, start_time: float, end_time: float, api_key: str = None) -> list:
    """Extracts and transcribes a short clip slice with word-level precision."""
    import subprocess
    from backend.config import FFMPEG_PATH, TEMP_DIR
    duration = max(1.0, end_time - start_time)
    slice_audio_path = str(TEMP_DIR / f"slice_{int(start_time)}_{int(end_time)}.m4a")
    
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", str(start_time),
        "-i", source_video_path,
        "-t", str(duration),
        "-vn",
        "-c:a", "aac",
        "-b:a", "32k",
        "-ar", "16000",
        "-ac", "1",
        slice_audio_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res = transcribe_audio_gemini(slice_audio_path, api_key=api_key)
        # Shift timestamps by start_time
        segments = res.get("segments", [])
        for s in segments:
            s["start"] = round(s.get("start", 0.0) + start_time, 2)
            s["end"] = round(s.get("end", 0.0) + start_time, 2)
            for w in s.get("words", []):
                w["start"] = round(w.get("start", 0.0) + start_time, 2)
                w["end"] = round(w.get("end", 0.0) + start_time, 2)
        return segments
    except Exception as e:
        print(f"[TranscribeSlice] Failed to transcribe slice {start_time}-{end_time}: {e}")
        return []
    finally:
        if os.path.exists(slice_audio_path):
            try:
                os.remove(slice_audio_path)
            except Exception:
                pass

def transcribe_video_smart_windows(video_path: str, duration: float, api_key: str = None) -> dict:
    """
    Intelligently transcribes a video by either:
    1. Transcribing full compressed audio if duration <= 300s (<= 5 min).
    2. Multi-window smart sampling (intro hook, mid highlight, climax) if duration > 300s.
       This prevents 503 UNAVAILABLE errors caused by exceeding multimodal audio token limits,
       while capturing the most viral moments across the entire video timeline.
    """
    dur = float(duration or 0.0)
    if dur <= 0.0:
        from backend.ingest import get_video_metadata
        try:
            meta = get_video_metadata(video_path)
            dur = float(meta.get("duration", 0.0))
        except Exception:
            dur = 60.0

    # Case 1: Short video (<= 5 minutes) -> full audio transcription
    if dur <= 300.0:
        try:
            from backend.ingest import extract_audio
            audio_path = extract_audio(video_path)
            return transcribe_audio_gemini(audio_path, api_key=api_key)
        except Exception as e:
            print(f"[Transcribe] Full audio transcription failed ({e}), attempting slice fallback.")

    # Case 2: Long video (> 5 minutes) -> sample 3 strategic viral timeline windows
    # Window 1: Early Hook (6% - 8% into video)
    # Window 2: Mid-game highlight (45% into video)
    # Window 3: Climax / Clutch finish (80% into video)
    target_offsets = [0.08, 0.45, 0.80]
    window_length = 60.0 # 60 seconds per window
    
    all_segments = []
    for off in target_offsets:
        s_time = max(0.0, off * dur)
        if s_time + window_length > dur:
            s_time = max(0.0, dur - window_length)
        e_time = min(dur, s_time + window_length)
        
        try:
            segs = transcribe_audio_slice(
                source_video_path=video_path,
                start_time=s_time,
                end_time=e_time,
                api_key=api_key
            )
            if segs:
                all_segments.extend(segs)
        except Exception as slice_err:
            print(f"[Transcribe] Slice {s_time:.1f}s-{e_time:.1f}s failed: {slice_err}")

    # Sort all segments chronologically by start time
    all_segments.sort(key=lambda s: s.get("start", 0.0))
    full_text = " ".join([s.get("text", "") for s in all_segments])
    
    return {
        "full_text": full_text,
        "segments": all_segments
    }
