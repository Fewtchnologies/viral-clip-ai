import os
import subprocess
from pathlib import Path
from backend.config import FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR
from backend.editor import render_viral_clip
from backend.ingest import get_video_metadata

def create_synthetic_test_video(output_path: str):
    """
    Creates a 6-second 1920x1080 test video with synthesized speech tone and moving visual.
    """
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=size=1920x1080:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=6",
        "-t", "6",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path

def test_voiceover_and_effects_pipeline():
    print("=== STARTING AI VOICEOVER & PREMIERE PRO EFFECTS TEST ===")
    test_src = str(TEMP_DIR / "sample_input_16x9.mp4")
    create_synthetic_test_video(test_src)
    print(f"✓ Synthetic 16:9 test video created: {test_src}")

    meta = get_video_metadata(test_src)
    print(f"✓ Video probe: {meta['width']}x{meta['height']}, {meta['fps']} FPS, {meta['duration']}s")

    sample_segments = [
        {
            "start": 0.0,
            "end": 2.8,
            "text": "STOP MAKING BORING VIDEOS RIGHT NOW",
            "words": [
                {"word": "STOP", "start": 0.1, "end": 0.5},
                {"word": "MAKING", "start": 0.52, "end": 0.9},
                {"word": "BORING", "start": 0.92, "end": 1.4},
                {"word": "VIDEOS", "start": 1.42, "end": 1.8},
                {"word": "RIGHT", "start": 1.82, "end": 2.2},
                {"word": "NOW", "start": 2.22, "end": 2.8},
            ]
        },
        {
            "start": 2.9,
            "end": 5.8,
            "text": "USE PREMIERE PRO EFFECTS AND AI VOICEOVER",
            "words": [
                {"word": "USE", "start": 2.9, "end": 3.3},
                {"word": "PREMIERE", "start": 3.35, "end": 3.8},
                {"word": "PRO", "start": 3.85, "end": 4.1},
                {"word": "EFFECTS", "start": 4.15, "end": 4.6},
                {"word": "AND", "start": 4.65, "end": 4.8},
                {"word": "AI", "start": 4.85, "end": 5.1},
                {"word": "VOICEOVER", "start": 5.15, "end": 5.8},
            ]
        }
    ]

    clip_info = {
        "id": "voiceover_fx_test",
        "title": "THE $10,000,000 LESSON 💰",
        "start_time": 0.0,
        "end_time": 5.5,
        "viral_score": 99,
        "punch_keywords": ["BORING", "PREMIERE", "VOICEOVER"]
    }

    out_mp4 = str(OUTPUT_DIR / "voiceover_ducking_9x16.mp4")
    print("✓ Rendering with Neural AI Voiceover (Deep Narrator) + Audio Ducking + Premiere Pro Effects...")

    result = render_viral_clip(
        source_video_path=test_src,
        clip_info=clip_info,
        transcript_segments=sample_segments,
        output_mp4_path=out_mp4,
        options={
            "enable_color_grade": True,
            "enable_impact_flash": True,
            "enable_progress_bar": True,
            "progress_bar_color": "yellow",
            "enable_punch_zoom": True,
            "enable_hook_banner": True,
            "hook_style": "gold",
            "custom_hook_title": "THE $10,000,000 LESSON 💰",
            "enable_voiceover": True,
            "voice_key": "deep_narrator",
            "voiceover_text": "Stop scrolling right now! This is the ten million dollar lesson!",
            "caption_style": {
                "font_name": "Arial Black",
                "font_size": 44,
                "highlight_color": "&H0000FFFF",
                "bounce_animation": True,
                "uppercase": True
            }
        }
    )

    print(f"✓ Render complete: {result['video_path']}")
    assert Path(out_mp4).exists(), "Output MP4 does not exist"

    out_meta = get_video_metadata(out_mp4)
    print(f"✓ Output Video Probe: {out_meta['width']}x{out_meta['height']} ({out_meta['aspect_ratio']}), Duration: {out_meta['duration']:.2f}s")
    assert out_meta["width"] == 1080 and out_meta["height"] == 1920, f"Expected 1080x1920, got {out_meta['width']}x{out_meta['height']}"

    print(f"✓ Output file size: {Path(out_mp4).stat().st_size / 1024:.1f} KB")
    print(f"✓ Voiceover info: {result.get('voiceover')}")
    print(f"✓ Effects applied: {result.get('effects_applied')}")
    print("=== AI VOICEOVER & PREMIERE PRO EFFECTS TEST PASSED! ===")

if __name__ == "__main__":
    test_voiceover_and_effects_pipeline()
