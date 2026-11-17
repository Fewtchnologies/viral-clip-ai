import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
UPLOAD_DIR = BACKEND_DIR / "uploads"
OUTPUT_DIR = BACKEND_DIR / "output"
TEMP_DIR = BACKEND_DIR / "temp"
BIN_DIR = BASE_DIR / "bin"

for folder in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, BIN_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# FFmpeg Executable Detection
LOCAL_FFMPEG = BIN_DIR / "ffmpeg.exe"
if LOCAL_FFMPEG.exists():
    FFMPEG_PATH = str(LOCAL_FFMPEG)
else:
    try:
        import imageio_ffmpeg
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_PATH = "ffmpeg"

# Ensure FFmpeg directory is in system PATH for all subprocesses (including yt-dlp)
ffmpeg_dir = str(Path(FFMPEG_PATH).parent)
if ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


# API Keys
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


# Video & Subtitle Configuration
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
TARGET_FPS = 30

# Default Premiere-Style Captions
DEFAULT_CAPTION_STYLE = {
    "font_name": "Arial Black",
    "font_size": 42,
    "primary_color": "&H00FFFFFF",     # White
    "highlight_color": "&H0000FFFF",   # Neon Yellow
    "secondary_color": "&H0000FF55",   # Neon Green
    "outline_color": "&H00000000",     # Black
    "outline_width": 3.5,
    "shadow_width": 2.0,
    "max_words_per_line": 3,
    "uppercase": True,
    "bounce_animation": True,
}
