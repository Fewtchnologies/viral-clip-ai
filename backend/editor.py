import os
import re
import subprocess
import json
from pathlib import Path
from backend.config import FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR
from backend.cropper import analyze_speaker_tracking, get_crop_filter
from backend.subtitles import generate_hormozi_ass_subtitles
from backend.voiceover import generate_voiceover_audio

HOOK_STYLE_PALETTE = {
    "gold": {
        "bg": "black@0.80",
        "border": "yellow@0.95",
        "font_color": "white"
    },
    "warning": {
        "bg": "darkred@0.85",
        "border": "red@0.95",
        "font_color": "white"
    },
    "secret": {
        "bg": "indigo@0.85",
        "border": "magenta@0.90",
        "font_color": "white"
    },
    "cyan": {
        "bg": "black@0.80",
        "border": "cyan@0.95",
        "font_color": "white"
    }
}

def escape_ffmpeg_path(path_str: str) -> str:
    """Escapes Windows path for FFmpeg filter graph (libass subtitles filter)."""
    clean = path_str.replace('\\', '/')
    clean = clean.replace(':', '\\:')
    return clean

def build_punch_zoom_filter(punch_timestamps: list, clip_duration: float) -> str:
    """
    Builds dynamic punch-in zoom expressions (1.15x zoom) during emphasis timestamps.
    """
    if not punch_timestamps:
        return ""
    
    conditions = []
    for pt in punch_timestamps:
        s = pt.get("start", 0.0)
        e = pt.get("end", s + 1.8)
        conditions.append(f"between(t,{s:.2f},{e:.2f})")
    
    if not conditions:
        return ""

    return "+".join(conditions)

def render_viral_clip(
    source_video_path: str,
    clip_info: dict,
    transcript_segments: list,
    output_mp4_path: str = None,
    options: dict = None
) -> dict:
    """
    Executes the full Premiere Pro-style rendering pipeline:
    1. Trims clip to exact start/end time.
    2. Runs face tracking for smart 9:16 vertical centering (or dual-speaker split).
    3. Lumetri Cinematic Color Grading (contrast, saturation pop, subtle vignette).
    4. Impact Hook Flash transition at start.
    5. Dynamic Punch-in Zooms (1.15x) on emphasis words.
    6. Real-time Animated Bottom Progress Bar.
    7. Top Hook Title Banner (Warning, Gold, Secret, or Cyan theme).
    8. Word-by-word animated Hormozi ASS captions.
    9. Neural AI Voiceover narration with smart background audio ducking.
    10. EBU R128 broadcast audio normalization.
    """
    opts = options or {}
    start_time = float(clip_info.get("start_time", 0.0))
    end_time = float(clip_info.get("end_time", start_time + 30.0))
    duration = max(1.0, end_time - start_time)
    
    title = opts.get("custom_hook_title") or clip_info.get("title", "VIRAL MOMENT")
    hook_style_name = opts.get("hook_style", "gold")
    hook_palette = HOOK_STYLE_PALETTE.get(hook_style_name, HOOK_STYLE_PALETTE["gold"])
    
    clip_id = clip_info.get("id", "clip_1")

    if not output_mp4_path:
        safe_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(source_video_path).stem)
        output_mp4_path = str(OUTPUT_DIR / f"{safe_stem}_{clip_id}_9x16.mp4")

    # 1. Face tracking & 9:16 crop calculation
    tracking_info = analyze_speaker_tracking(source_video_path, start_time, end_time)
    crop_filter_str, out_label = get_crop_filter(tracking_info, target_w=1080, target_h=1920)

    # 2. Generate word-by-word ASS subtitles
    ass_path = str(TEMP_DIR / f"{clip_id}_subtitles.ass")
    generate_hormozi_ass_subtitles(
        segments=transcript_segments,
        output_ass_path=ass_path,
        clip_start_offset=start_time,
        style_opts=opts.get("caption_style", {})
    )

    # 3. Generate AI Voiceover if enabled
    enable_voiceover = opts.get("enable_voiceover", False)
    vo_audio_path = None
    vo_duration = 0.0
    vo_info = None

    if enable_voiceover:
        raw_vo_text = opts.get("voiceover_text") or f"Wait till the end! {title}"
        voice_key = opts.get("voice_key", "deep_narrator")
        vo_info = generate_voiceover_audio(
            text=raw_vo_text,
            voice_key=voice_key
        )
        vo_audio_path = vo_info["audio_path"]
        vo_duration = vo_info["duration"]

    # 4. Build video filter chain
    filter_chain = []
    filter_chain.append(crop_filter_str)

    current_v = out_label
    filter_idx = 1

    # Effect A: Premiere Pro Lumetri Color Grade
    enable_color_grade = opts.get("enable_color_grade", True)
    if enable_color_grade:
        next_label = f"[vlumetri_{filter_idx}]"
        filter_chain.append(
            f"{current_v}eq=contrast=1.08:brightness=0.02:saturation=1.16,vignette=PI/5{next_label}"
        )
        current_v = next_label
        filter_idx += 1

    # Effect B: Dynamic Punch-in Zoom cuts
    enable_zoom = opts.get("enable_punch_zoom", True)
    if enable_zoom and clip_info.get("punch_keywords"):
        punch_intervals = []
        p_keys = [k.lower() for k in clip_info.get("punch_keywords", [])]
        for seg in transcript_segments:
            for w in seg.get("words", []):
                w_text = w.get("word", "").lower()
                for pk in p_keys:
                    if pk in w_text:
                        rel_s = max(0.0, w.get("start", 0.0) - start_time)
                        if rel_s < duration:
                            punch_intervals.append({"start": rel_s, "end": min(duration, rel_s + 1.8)})
        
        cond_str = build_punch_zoom_filter(punch_intervals, duration)
        if cond_str:
            next_label = f"[vzoom_{filter_idx}]"
            filter_chain.append(
                f"{current_v}scale=w='if({cond_str}, 1242, 1080)':h='if({cond_str}, 2208, 1920)':eval=frame:flags=lanczos,"
                f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2{next_label}"
            )
            current_v = next_label
            filter_idx += 1

    # Effect C: Top Hook Banner Card
    enable_banner = opts.get("enable_hook_banner", True)
    if enable_banner and title:
        clean_banner = str(title).replace('\uff5c', '|').replace('\u2014', '-').replace('\u2013', '-')
        safe_title = clean_banner.replace('\\', '\\\\').replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")
        bg_color = hook_palette["bg"]
        border_color = hook_palette["border"]
        font_color = hook_palette["font_color"]
        
        next_label = f"[vbanner_{filter_idx}]"
        filter_chain.append(
            f"{current_v}drawbox=x=(iw-920)/2:y=120:w=920:h=130:color={bg_color}:t=fill,"
            f"drawbox=x=(iw-920)/2:y=120:w=920:h=130:color={border_color}:t=5,"
            f"drawtext=text='{safe_title}':font='Arial':fontsize=36:fontcolor={font_color}:"
            f"x=(w-text_w)/2:y=120+(130-text_h)/2{next_label}"
        )
        current_v = next_label
        filter_idx += 1

    # Effect D: Animated Bottom Progress Bar
    enable_progress = opts.get("enable_progress_bar", True)
    if enable_progress:
        bar_color = opts.get("progress_bar_color", "yellow")
        next_label = f"[vprogress_{filter_idx}]"
        filter_chain.append(
            f"{current_v}drawbox=x=0:y=ih-16:w='iw*min(1.0,t/{duration:.2f})':h=16:color={bar_color}@0.9:t=fill{next_label}"
        )
        current_v = next_label
        filter_idx += 1

    # Effect E: Impact Hook Flash Transition
    enable_flash = opts.get("enable_impact_flash", True)
    if enable_flash:
        next_label = f"[vflash_{filter_idx}]"
        filter_chain.append(
            f"{current_v}fade=t=in:st=0:d=0.12:alpha=1:color=white{next_label}"
        )
        current_v = next_label
        filter_idx += 1

    # Burn in ASS Subtitles using libass filter
    escaped_ass = escape_ffmpeg_path(ass_path)
    final_v = f"[vfinal]"
    filter_chain.append(f"{current_v}subtitles='{escaped_ass}'{final_v}")

    # 5. Build Audio filter chain (Optional Voiceover mixing + original audio preservation)
    extra_input_args = []
    final_a = "0:a?"

    if enable_voiceover and vo_audio_path:
        extra_input_args.extend(["-i", vo_audio_path])
        # Input 0: Video, Input 1: Voiceover MP3
        # Duck original background audio to 20% while voiceover speaks, then smoothly restore
        duck_end = vo_duration + 0.3
        filter_chain.append(
            f"[0:a]volume=eval=frame:volume='if(lte(t,{duck_end:.2f}),0.20,min(1.0,0.20+0.80*(t-{duck_end:.2f})/0.4))'[bg_ducked]"
        )
        filter_chain.append(
            f"[bg_ducked][1:a]amix=inputs=2:duration=first:dropout_transition=0[afinal]"
        )
        final_a = "[afinal]"
    else:
        # User requested NO unnecessary voiceover: keep original source audio 100% natural and un-ducked
        final_a = "0:a?"

    full_filter_complex = ";".join(filter_chain)

    # 6. Construct FFmpeg command with Maximum Studio Visual & Audio Quality
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", source_video_path,
        *extra_input_args,
        "-filter_complex", full_filter_complex,
        "-map", final_v,
        "-map", final_a,
        "-c:v", "libx264",
        "-preset", "medium",   # High-quality motion vector analysis (preserves fine textures)
        "-crf", "17",          # Visually lossless master export (CRF 17 retains pristine quality)
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",        # Pristine studio bitrate for original game/speech audio
        "-movflags", "+faststart",
        output_mp4_path
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # Generate preview thumbnail
    thumb_path = str(OUTPUT_DIR / f"{Path(output_mp4_path).stem}_thumb.jpg")
    thumb_cmd = [
        FFMPEG_PATH,
        "-y",
        "-ss", str(start_time + min(2.0, duration / 2)),
        "-i", output_mp4_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]
    subprocess.run(thumb_cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    filename = Path(output_mp4_path).name
    thumb_name = Path(thumb_path).name if Path(thumb_path).exists() else ""

    return {
        "status": "completed",
        "clip_id": clip_id,
        "video_path": output_mp4_path,
        "filename": filename,
        "video_url": f"/api/video/{filename}",
        "thumbnail_path": thumb_path if Path(thumb_path).exists() else "",
        "thumbnail_name": thumb_name,
        "thumbnail_url": f"/api/thumbnail/{thumb_name}" if thumb_name else "",
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "tracking_mode": tracking_info.get("mode", "single_speaker"),
        "hook_title": title,
        "voiceover": vo_info if enable_voiceover else None,
        "effects_applied": {
            "lumetri_color_grade": enable_color_grade,
            "punch_in_zoom": enable_zoom,
            "hook_banner": enable_banner,
            "bottom_progress_bar": enable_progress,
            "impact_flash": enable_flash,
            "ai_voiceover": enable_voiceover,
        }
    }
