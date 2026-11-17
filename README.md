# 🚀 AI Viral Clip Studio PRO

An autonomous, full-stack AI video production system that transforms long-form YouTube videos (or local uploads) into high-retention 9:16 vertical shorts (TikTok, Reels, YouTube Shorts) with:
- **🎙️ Neural AI Voiceovers & Smart Audio Ducking:** Cinematic voiceover narration with automatic background audio ducking.
- **🎯 Multi-Category Viral Hook Intelligence:** Gemini 2.5 Flash scans transcripts for Curiosity, Warning, Secret, and High-Value hooks.
- **📱 Smart 9:16 Auto-Crop:** Face tracking to keep speakers centered + dual-speaker podcast split-screen.
- **🔥 Animated Hormozi / MrBeast Captions:** Word-by-word synced highlights, pop bounce scale, and auto-attached sentiment emojis.
- **🎬 Premiere Pro Effects Suite:** Lumetri cinematic color grade, 0.12s impact hook flash, animated bottom progress bar, and 1.15x dynamic punch-in zoom cuts.

---

## 🎙️ AI Voiceover Studio

| Voice Preset | Voice Engine | Style / Character |
|---|---|---|
| **Deep Dramatic Narrator** | `en-US-ChristopherNeural` | Deep, authoritative, movie trailer / documentarian |
| **Energetic Shorts Host** | `en-US-GuyNeural` | Fast, punchy, high-energy TikTok / Shorts creator |
| **Engaging Storyteller** | `en-US-JennyNeural` | Warm, captivating, friendly female narrator |
| **British Sophisticate** | `en-GB-RyanNeural` | Refined, modern UK accent for business/podcasts |

### Smart Audio Ducking
When the voiceover speaks, the original background video audio automatically ducks to **20% volume (-14dB)** with a smooth fade-in restore and EBU R128 broadcast loudness compression.

---

## 🚀 Quickstart Guide

### 1. Launch the Server
```powershell
cd "C:\Users\roshni paikhwar\.gemini\antigravity\scratch\viral-clip-ai"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 2. Enter Gemini API Key
Click **"Set Gemini API Key"** in the top-right header (saved in your local browser).

### 3. Generate Clips with Voiceover
1. Paste a YouTube URL or upload an MP4/MOV file.
2. Click **"Extract Viral Clips"**.
3. Choose your desired **AI Voiceover** (Christopher, Guy, Jenny, Ryan) and hook title.
4. Click **"Render 9:16 Short"** to download the finished video with voiceover and audio ducking!
