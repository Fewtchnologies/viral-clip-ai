import asyncio
import os
import re
import subprocess
import uuid
from pathlib import Path
import edge_tts
from backend.config import TEMP_DIR, FFMPEG_PATH

VOICE_PROFILES = {
    "deep_narrator": {
        "id": "en-US-ChristopherNeural",
        "name": "Deep Dramatic Narrator",
        "gender": "Male",
        "style": "Cinematic & Authoritative",
        "pitch": "-2Hz",
        "rate": "+5%"
    },
    "energetic_host": {
        "id": "en-US-GuyNeural",
        "name": "Energetic Shorts Host",
        "gender": "Male",
        "style": "Fast & High Dopamine",
        "pitch": "+0Hz",
        "rate": "+12%"
    },
    "storyteller_female": {
        "id": "en-US-JennyNeural",
        "name": "Engaging Storyteller",
        "gender": "Female",
        "style": "Warm & Expressive",
        "pitch": "+0Hz",
        "rate": "+6%"
    },
    "british_accent": {
        "id": "en-GB-RyanNeural",
        "name": "British Sophisticate",
        "gender": "Male",
        "style": "Refined & Modern UK",
        "pitch": "+0Hz",
        "rate": "+4%"
    }
}

def clean_text_for_speech(text: str) -> str:
    """Removes emojis and symbols so TTS produces clean, natural articulation."""
    # Replace fullwidth symbols and vertical bars
    clean = str(text).replace('\uff5c', ', ').replace('|', ', ').replace('—', ' - ')
    # Remove emoji characters
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', clean)
    # Remove markdown/brackets
    clean = re.sub(r'[#*_~`\[\]()]', '', clean)
    # Normalize extra whitespaces
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def get_audio_duration(audio_path: str) -> float:
    """Calculates duration of an audio file using FFmpeg."""
    cmd = [FFMPEG_PATH, "-i", audio_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 3.0

async def _synthesize_speech(text: str, voice_id: str, rate: str, pitch: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice_id, rate=rate, pitch=pitch)
    await communicate.save(output_path)

def generate_voiceover_audio(
    text: str,
    voice_key: str = "deep_narrator",
    custom_voice_id: str = None,
    output_path: str = None
) -> dict:
    """
    Generates high-fidelity neural voiceover audio using edge-tts.
    Returns:
        {
            "audio_path": str,
            "duration": float,
            "voice_name": str,
            "clean_text": str
        }
    """
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        cleaned = "Wait till the end, you won't believe what happens next!"

    profile = VOICE_PROFILES.get(voice_key, VOICE_PROFILES["deep_narrator"])
    voice_id = custom_voice_id or profile["id"]
    rate = profile.get("rate", "+5%")
    pitch = profile.get("pitch", "+0Hz")

    if not output_path:
        out_id = str(uuid.uuid4())[:8]
        output_path = str(TEMP_DIR / f"voiceover_{out_id}.mp3")

    # Run async synthesis synchronously
    asyncio.run(_synthesize_speech(cleaned, voice_id, rate, pitch, output_path))

    duration = get_audio_duration(output_path)

    return {
        "audio_path": output_path,
        "duration": duration,
        "voice_name": profile["name"],
        "voice_id": voice_id,
        "clean_text": cleaned
    }
