import os
import subprocess
import json
import uuid
import cv2
from pathlib import Path
import yt_dlp
from backend.config import FFMPEG_PATH, TEMP_DIR, UPLOAD_DIR

def get_video_metadata(video_path: str) -> dict:
    """Extract video metadata including width, height, duration, and FPS using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "aspect_ratio": f"{width}:{height}"
    }

def extract_transcript_from_info(info: dict) -> dict:
    """Extracts millisecond-precision transcripts directly from YouTube automatic captions/subtitles if available."""
    auto_subs = info.get('automatic_captions', {})
    subtitles = info.get('subtitles', {})
    
    chosen_lang = None
    for lang in ['en', 'en-orig', 'en-US', 'en-GB', 'hi']:
        if lang in subtitles and subtitles[lang]:
            chosen_lang = subtitles[lang]
            break
        if lang in auto_subs and auto_subs[lang]:
            chosen_lang = auto_subs[lang]
            break
            
    if not chosen_lang:
        for lang, formats in auto_subs.items():
            if formats:
                chosen_lang = formats
                break
                
    if not chosen_lang:
        return None
        
    try:
        json3_url = next((fmt['url'] for fmt in chosen_lang if fmt.get('ext') == 'json3'), None)
        if not json3_url:
            json3_url = chosen_lang[0]['url']
            
        import urllib.request
        req = urllib.request.Request(json3_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
        segments = []
        for event in data.get('events', []):
            if 'segs' not in event or 'tStartMs' not in event:
                continue
            start_s = event['tStartMs'] / 1000.0
            dur_s = event.get('dDurationMs', 1500) / 1000.0
            end_s = start_s + dur_s
            text = "".join(s.get('utf8', '') for s in event['segs']).strip()
            if not text:
                continue
            
            words = []
            for seg in event['segs']:
                w_text = seg.get('utf8', '').strip()
                if not w_text:
                    continue
                w_offset = seg.get('tOffsetMs', 0) / 1000.0
                w_start = start_s + w_offset
                words.append({'word': w_text, 'start': round(w_start, 2), 'end': round(w_start + 0.35, 2)})
                
            segments.append({
                'start': round(start_s, 2),
                'end': round(end_s, 2),
                'text': text,
                'words': words
            })
            
        if segments:
            return {
                'full_text': " ".join(s['text'] for s in segments),
                'segments': segments
            }
    except Exception:
        pass
    return None

def resolve_cookie_file(custom_cookies: str = None) -> str:
    """Returns path to cookiefile if available via parameter, environment variable, or existing file."""
    if custom_cookies and custom_cookies.strip():
        cookie_path = TEMP_DIR / "custom_cookies.txt"
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(custom_cookies.strip())
        return str(cookie_path)

    env_cookies = os.getenv("YOUTUBE_COOKIES")
    if env_cookies and env_cookies.strip():
        cookie_path = TEMP_DIR / "env_cookies.txt"
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(env_cookies.strip())
        return str(cookie_path)

    for p in [TEMP_DIR / "cookies.txt", Path("cookies.txt"), Path("backend/cookies.txt")]:
        if p.exists() and p.stat().st_size > 0:
            return str(p)

    return None

def download_youtube_video(youtube_url: str, job_id: str = None, cookies: str = None) -> dict:
    """Download YouTube video using yt-dlp to MP4 format with anti-throttling & anti-bot resilience."""
    import re
    job_id = job_id or str(uuid.uuid4())[:8]
    output_template = str(UPLOAD_DIR / f"{job_id}_input.%(ext)s")

    base_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/bv*+ba/b/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'js_runtimes': {'node': {}},
        'socket_timeout': 45,
        'retries': 15,
        'fragment_retries': 15,
        'http_chunk_size': 10485760,  # 10MB chunking prevents googlevideo CDN read timeout
        'nocheckcertificate': True,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
    }

    import shutil
    ffmpeg_bin = shutil.which("ffmpeg") or (FFMPEG_PATH if Path(FFMPEG_PATH).is_file() else None)
    if ffmpeg_bin and Path(ffmpeg_bin).is_file():
        base_opts['ffmpeg_location'] = str(Path(ffmpeg_bin).resolve().parent)

    cookie_file = resolve_cookie_file(cookies)
    if cookie_file:
        base_opts['cookiefile'] = cookie_file

    # Anti-bot bypass cascade:
    # 1. visionos & android_vr (bypasses YouTube datacenter bot challenges on Render without sign-in)
    # 2. android_vr standalone
    # 3. default (standard yt-dlp)
    strategies = [
        {"name": "visionos", "opts": {'extractor_args': {'youtube': {'player_client': ['visionos', 'android_vr']}}}},
        {"name": "android_vr", "opts": {'extractor_args': {'youtube': {'player_client': ['android_vr']}}}},
        {"name": "default", "opts": {}},
    ]

    # Only attempt browser auto-cookies on local desktop environments (never in headless Linux containers)
    import sys
    if sys.platform == "win32":
        strategies.extend([
            {"name": "edge_cookies", "opts": {'cookiesfrombrowser': ('edge', None, None, None)}},
            {"name": "chrome_cookies", "opts": {'cookiesfrombrowser': ('chrome', None, None, None)}},
        ])

    last_err = None
    info = None
    filename = None

    for strat in strategies:
        try:
            current_opts = {**base_opts, **strat["opts"]}
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                filename = ydl.prepare_filename(info)
                if filename and os.path.exists(filename):
                    break
                base = os.path.splitext(filename)[0]
                if os.path.exists(f"{base}.mp4"):
                    filename = f"{base}.mp4"
                    break
        except Exception as e:
            print(f"[ingest] Strategy {strat['name']} encountered: {e}")
            if "could not find chrome cookies" not in str(e).lower() and "could not find edge cookies" not in str(e).lower():
                last_err = e
            continue

    if not filename or not os.path.exists(filename):
        matches = list(UPLOAD_DIR.glob(f"{job_id}_input.*"))
        if matches:
            filename = str(matches[0])
        else:
            err_msg = str(last_err) if last_err else "Failed to download video stream from YouTube."
            if "Sign in to confirm you're not a bot" in err_msg or "bot" in err_msg.lower() or "requested format is not available" in err_msg.lower():
                raise RuntimeError(
                    "YouTube restricted cloud streaming for this video on Render. "
                    "Quick Fix: Paste your YouTube cookies into 'Cloud Anti-Bot & Cookies' below, "
                    "OR download the video on your computer and use the 'Upload MP4' button for 100% reliable instant analysis."
                ) from last_err
            raise last_err or RuntimeError("Failed to download video stream from YouTube.")

    # Ensure .mp4 extension
    if not filename.endswith('.mp4'):
        base = os.path.splitext(filename)[0]
        if os.path.exists(f"{base}.mp4"):
            filename = f"{base}.mp4"

    meta = get_video_metadata(filename)
    native_transcript = extract_transcript_from_info(info)
    return {
        "job_id": job_id,
        "title": info.get("title", "YouTube Video"),
        "video_path": filename,
        "duration": meta["duration"],
        "metadata": meta,
        "thumbnail": info.get("thumbnail", ""),
        "transcript": native_transcript,
    }

def extract_audio(video_path: str, output_audio_path: str = None) -> str:
    """Extract clean 16kHz mono compressed AAC audio for transcription and AI analysis."""
    import re
    if not output_audio_path:
        safe_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(video_path).stem)
        output_audio_path = str(TEMP_DIR / f"{safe_stem}_audio_16k.m4a")

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", video_path,
        "-vn",
        "-c:a", "aac",
        "-b:a", "32k",
        "-ar", "16000",
        "-ac", "1",
        output_audio_path
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_audio_path
