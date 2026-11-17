# AI Viral Clip Studio — System Specification (SPEC.md)

**Status:** EXPANDED — AI NEURAL VOICEOVER & AUDIO DUCKING  
**Project Path:** `C:\Users\roshni paikhwar\.gemini\antigravity\scratch\viral-clip-ai`  
**Architecture:** Modern Decoupled Full-Stack (FastAPI Python Backend + React/Vite/Tailwind Frontend)

## 1. Executive Summary
AI Viral Clip Studio is an end-to-end autonomous video processing system designed to ingest long-form YouTube videos or uploaded files, analyze them for viral potential using Gemini AI & Whisper, automatically reframe them to 9:16 vertical video using active-speaker face tracking, generate dynamic animated captions (Hormozi/MrBeast style), and apply Premiere Pro-style professional effects (cinematic color grade, impact hook flashes, animated progress bars, punch-in zooms, multi-style viral hooks, and AI neural voiceovers).

## 2. AI Voiceover & Smart Audio Ducking Engine
1. **Neural Voice Synthesis:**
   - Multiple broadcast-quality neural voices powered by Microsoft Azure Edge Neural engine (`edge-tts`):
     - **Deep Dramatic Narrator** (`en-US-ChristopherNeural`): Rich, authoritative, trailer-style voice.
     - **Energetic Shorts Host** (`en-US-GuyNeural`): Fast, punchy, high-energy TikTok/Shorts style.
     - **Engaging Storyteller** (`en-US-JennyNeural`): Warm, captivating female voice.
     - **British Sophisticate** (`en-GB-RyanNeural`): Classy UK accent for podcasts and documentary shorts.
2. **Voiceover Modes:**
   - **Hook Intro Narration:** AI voice speaks the hook title during the first 2-3 seconds to dramatically boost initial retention.
   - **Custom Narration / Dubbing:** Voiceover generated from custom user text or script.
3. **Smart Audio Ducking (Premiere Pro Style):**
   - Automatically ducks (compresses/lowers) the original video's audio background to 20-30% volume while the AI voiceover speaks, then smoothly restores it to 100% when finished using FFmpeg's `volume` and `amix` audio filters with EBU R128 loudness normalization.
