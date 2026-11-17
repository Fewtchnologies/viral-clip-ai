import os
import re
from pathlib import Path
from backend.config import DEFAULT_CAPTION_STYLE

EMOJI_KEYWORD_MAP = {
    r"\b(money|dollar|rich|cash|wealth|billion|million)\b": "💰",
    r"\b(fire|hot|crazy|insane|viral|hype)\b": "🔥",
    r"\b(rocket|launch|growth|grow|fast)\b": "🚀",
    r"\b(shock|omg|wow|unbelievable|crazy)\b": "😱",
    r"\b(dead|death|kill|lost|worst)\b": "💀",
    r"\b(secret|truth|mystery|revealed)\b": "🤫",
    r"\b(brain|smart|mind|think|idea)\b": "🧠",
    r"\b(win|winner|first|best|king)\b": "👑",
    r"\b(target|goal|focus|lock)\b": "🎯",
    r"\b(love|heart|favorite)\b": "❤️",
}

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def attach_emojis_to_text(text: str) -> str:
    """Detect keywords and append appropriate dynamic emojis."""
    matched_emojis = []
    lower = text.lower()
    for pattern, emoji in EMOJI_KEYWORD_MAP.items():
        if re.search(pattern, lower):
            matched_emojis.append(emoji)
            if len(matched_emojis) >= 2:
                break
    if matched_emojis:
        return f"{text} {' '.join(matched_emojis)}"
    return text

def generate_hormozi_ass_subtitles(
    segments: list,
    output_ass_path: str,
    clip_start_offset: float = 0.0,
    style_opts: dict = None
) -> str:
    """
    Generates an Advanced SubStation Alpha (.ass) subtitle file featuring
    Premiere Pro / Alex Hormozi dynamic word-by-word highlighted captions.
    
    Each word lights up with the highlight color (e.g. Neon Yellow/Green) and
    bounces slightly when spoken, while surrounding words in the current phrase stay white.
    """
    opts = {**DEFAULT_CAPTION_STYLE, **(style_opts or {})}

    font_name = opts.get("font_name", "Arial Black")
    font_size = opts.get("font_size", 42)
    primary_color = opts.get("primary_color", "&H00FFFFFF")       # White
    highlight_color = opts.get("highlight_color", "&H0000FFFF")   # Neon Yellow
    outline_color = opts.get("outline_color", "&H00000000")       # Black
    outline_width = opts.get("outline_width", 4.0)
    shadow_width = opts.get("shadow_width", 2.0)
    max_words_per_group = opts.get("max_words_per_line", 3)
    uppercase = opts.get("uppercase", True)
    bounce = opts.get("bounce_animation", True)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HormoziMain,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,{outline_width},{shadow_width},2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []

    # Flatten all words with clip start offset adjustment
    all_words = []
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # Fallback if no word tokens: split text evenly
            seg_text = seg.get("text", "").strip()
            if not seg_text:
                continue
            split_w = seg_text.split()
            s_time = seg.get("start", 0.0)
            e_time = seg.get("end", s_time + 1.0)
            dur = max(0.1, (e_time - s_time) / len(split_w))
            for i, w in enumerate(split_w):
                all_words.append({
                    "word": w,
                    "start": s_time + i * dur,
                    "end": s_time + (i + 1) * dur
                })
        else:
            for w in words:
                all_words.append(w)

    # Filter words relevant to this clip (with small padding)
    clip_words = []
    for w in all_words:
        w_start = w.get("start", 0.0) - clip_start_offset
        w_end = w.get("end", 0.0) - clip_start_offset
        if w_end > 0:
            text_val = w.get("word", "").strip()
            if text_val:
                clip_words.append({
                    "word": text_val.upper() if uppercase else text_val,
                    "start": max(0.0, w_start),
                    "end": max(0.05, w_end)
                })

    # Group words into short punchy 2-4 word phrases
    groups = []
    for i in range(0, len(clip_words), max_words_per_group):
        group = clip_words[i:i + max_words_per_group]
        if group:
            groups.append(group)

    # For each group, create events where the currently spoken word is highlighted
    for group in groups:
        g_start = group[0]["start"]
        g_end = group[-1]["end"]
        group_text_raw = " ".join([item["word"] for item in group])
        group_text_with_emojis = attach_emojis_to_text(group_text_raw)
        extra_emoji = group_text_with_emojis[len(group_text_raw):] if len(group_text_with_emojis) > len(group_text_raw) else ""

        for active_idx, active_item in enumerate(group):
            w_s = active_item["start"]
            w_e = active_item["end"]
            
            # Format text: active word has highlight color + optional bounce scale
            formatted_words = []
            for idx, item in enumerate(group):
                word_str = item["word"]
                if idx == active_idx:
                    if bounce:
                        # Pop animation: scale to 118% then settle to 100%
                        formatted_words.append(
                            f"{{\\c{highlight_color}\\t(0,60,\\fscx118\\fscy118)\\t(60,140,\\fscx100\\fscy100)}}{word_str}{{\\c{primary_color}\\fscx100\\fscy100}}"
                        )
                    else:
                        formatted_words.append(f"{{\\c{highlight_color}}}{word_str}{{\\c{primary_color}}}")
                else:
                    formatted_words.append(word_str)

            full_line_text = " ".join(formatted_words)
            if extra_emoji:
                full_line_text += f" {extra_emoji}"

            start_ass = format_ass_time(w_s)
            end_ass = format_ass_time(w_e)
            dialogue_lines.append(
                f"Dialogue: 0,{start_ass},{end_ass},HormoziMain,,0,0,0,,{full_line_text}"
            )

    full_ass_content = header + "\n".join(dialogue_lines) + "\n"
    
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_ass_content)

    return output_ass_path
