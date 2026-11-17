import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Sparkles,
  Youtube,
  Upload,
  Play,
  Download,
  Flame,
  Clock,
  Layers,
  CheckCircle2,
  AlertCircle,
  Sliders,
  Scissors,
  ZoomIn,
  Key,
  Palette,
  Zap,
  Timer,
  Lightbulb,
  ShieldAlert,
  HelpCircle,
  Coins,
  Mic,
  Volume2,
  VolumeX,
  Radio
} from 'lucide-react';

// Configure API base URL for live deployments (Vercel, Render, Railway, etc.)
if (import.meta.env.VITE_API_URL) {
  axios.defaults.baseURL = import.meta.env.VITE_API_URL;
}

const HIGHLIGHT_COLORS = [
  { name: 'Neon Yellow', value: '&H0000FFFF', hex: '#FFE600' },
  { name: 'Neon Green', value: '&H0000FF00', hex: '#00FF66' },
  { name: 'Cyan Blue', value: '&H00FFFF00', hex: '#00E5FF' },
  { name: 'Hot Pink', value: '&H00FF00FF', hex: '#FF007F' },
];

const HOOK_STYLES = [
  { id: 'gold', name: 'Gold Trophy', icon: Coins, border: 'border-yellow-400', badge: 'bg-yellow-500/10 text-yellow-400' },
  { id: 'warning', name: 'Red Alert', icon: ShieldAlert, border: 'border-red-500', badge: 'bg-red-500/10 text-red-400' },
  { id: 'secret', name: 'Purple Secret', icon: HelpCircle, border: 'border-purple-500', badge: 'bg-purple-500/10 text-purple-400' },
  { id: 'cyan', name: 'Cyber Cyan', icon: Zap, border: 'border-cyan-400', badge: 'bg-cyan-500/10 text-cyan-400' },
];

const VOICES = [
  { key: 'deep_narrator', name: 'Deep Dramatic Narrator', style: 'Cinematic & Authoritative', gender: 'Male (Christopher)' },
  { key: 'energetic_host', name: 'Energetic Shorts Host', style: 'Fast & High Dopamine', gender: 'Male (Guy)' },
  { key: 'storyteller_female', name: 'Engaging Storyteller', style: 'Warm & Expressive', gender: 'Female (Jenny)' },
  { key: 'british_accent', name: 'British Sophisticate', style: 'Refined & Modern UK', gender: 'Male (Ryan)' },
];

export default function App() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('gemini_api_key') || '');
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  
  // Job & Processing State
  const [jobId, setJobId] = useState(null);
  const [jobData, setJobData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [renderingClipId, setRenderingClipId] = useState(null);

  // Active Preview Clip
  const [activePreview, setActivePreview] = useState(null);

  // Premiere Pro Style, FX & Voiceover Customizer
  const [styleSettings, setStyleSettings] = useState({
    font_name: 'Arial Black',
    font_size: 42,
    highlight_color: '&H0000FFFF',
    max_words_per_line: 3,
    uppercase: true,
    bounce_animation: true,
    enable_punch_zoom: true,
    enable_hook_banner: true,
    enable_color_grade: true,
    enable_impact_flash: true,
    enable_progress_bar: true,
    progress_bar_color: 'yellow',
    hook_style: 'gold',
    enable_voiceover: false,
    voice_key: 'deep_narrator',
    custom_voiceover_script: '',
  });

  // Selected Hook per Clip
  const [selectedHooks, setSelectedHooks] = useState({});

  // Save API key
  const handleSaveApiKey = (key) => {
    setApiKey(key);
    localStorage.setItem('gemini_api_key', key);
    setShowKeyModal(false);
  };

  // Poll Job Status
  useEffect(() => {
    let interval = null;
    if (jobId && jobData?.status !== 'ready_for_render' && jobData?.status !== 'failed') {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`/api/job/${jobId}`);
          setJobData(res.data);
          if (res.data.status === 'failed') {
            setError(res.data.message || 'Processing failed');
            setLoading(false);
            clearInterval(interval);
          } else if (res.data.status === 'ready_for_render') {
            setLoading(false);
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Polling error:', err);
          if (err.response?.status === 404) {
            clearInterval(interval);
            setLoading(false);
            setError('Session expired or job not found. Click "Load Demo" or start a new video analysis.');
          }
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [jobId, jobData?.status]);

  // Load Pre-rendered Demo on Mount
  useEffect(() => {
    if (!jobId) {
      handleLoadDemo();
    }
  }, []);

  const handleLoadDemo = async () => {
    try {
      const res = await axios.get('/api/demo');
      setJobId(res.data.job_id);
      setJobData(res.data);
      if (res.data.rendered_clips?.clip_1) {
        setActivePreview(res.data.rendered_clips.clip_1);
      }
    } catch (err) {
      console.error('Demo load error:', err);
    }
  };

  // Start URL Analysis
  const handleAnalyzeUrl = async (e) => {
    e.preventDefault();
    if (!videoUrl) return;
    setError(null);
    setLoading(true);
    setJobData(null);
    setActivePreview(null);

    try {
      const res = await axios.post('/api/analyze/url', {
        url: videoUrl,
        api_key: apiKey || undefined,
      });
      setJobId(res.data.job_id);
    } catch (err) {
      const msg = err.response?.data?.detail || (err.response?.status === 404 ? 'API backend endpoint not reached (404). If using a live deployment, ensure the Python/FFmpeg backend is running.' : err.message);
      setError(msg);
      setLoading(false);
    }
  };

  // Start File Upload Analysis
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setSelectedFile(file);
    setError(null);
    setLoading(true);
    setJobData(null);
    setActivePreview(null);

    const formData = new FormData();
    formData.append('file', file);
    if (apiKey) formData.append('api_key', apiKey);

    try {
      const res = await axios.post('/api/analyze/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setJobId(res.data.job_id);
    } catch (err) {
      const msg = err.response?.data?.detail || (err.response?.status === 404 ? 'API backend endpoint not reached (404). If using a live deployment, ensure the Python/FFmpeg backend is running.' : err.message);
      setError(msg);
      setLoading(false);
    }
  };

  // Render a specific viral clip
  const handleRenderClip = async (clip) => {
    setRenderingClipId(clip.id);
    const customTitle = selectedHooks[clip.id] || clip.title;
    const voText = styleSettings.custom_voiceover_script || `Wait till the end! ${customTitle}`;

    try {
      const res = await axios.post(`/api/job/${jobId}/render/${clip.id}`, {
        caption_style: {
          font_name: styleSettings.font_name,
          font_size: styleSettings.font_size,
          highlight_color: styleSettings.highlight_color,
          max_words_per_line: styleSettings.max_words_per_line,
          uppercase: styleSettings.uppercase,
          bounce_animation: styleSettings.bounce_animation,
        },
        enable_punch_zoom: styleSettings.enable_punch_zoom,
        enable_hook_banner: styleSettings.enable_hook_banner,
        enable_color_grade: styleSettings.enable_color_grade,
        enable_impact_flash: styleSettings.enable_impact_flash,
        enable_progress_bar: styleSettings.enable_progress_bar,
        progress_bar_color: styleSettings.progress_bar_color,
        hook_style: styleSettings.hook_style,
        custom_hook_title: customTitle,
        enable_voiceover: styleSettings.enable_voiceover,
        voice_key: styleSettings.voice_key,
        voiceover_text: styleSettings.enable_voiceover ? voText : undefined,
      });

      setJobData((prev) => ({
        ...prev,
        rendered_clips: {
          ...(prev?.rendered_clips || {}),
          [clip.id]: res.data,
        },
      }));

      setActivePreview(res.data);
    } catch (err) {
      alert(`Render failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setRenderingClipId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-brand-border/60 bg-[#0B0F17]/90 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-yellow via-brand-purple to-brand-cyan flex items-center justify-center shadow-lg shadow-brand-yellow/20">
            <Flame className="h-6 w-6 text-black" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight flex items-center gap-2">
              VIRAL CLIP <span className="text-brand-yellow">STUDIO PRO</span>
              <span className="text-xs bg-brand-purple/20 text-brand-purple border border-brand-purple/40 px-2 py-0.5 rounded-full font-semibold">
                AI Voiceover & FX
              </span>
            </h1>
            <p className="text-xs text-slate-400">9:16 Auto-Crop • Neural Voiceover • Lumetri Color Grade • Hormozi Captions • Viral Hooks</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleLoadDemo}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-brand-purple/40 bg-brand-purple/10 text-brand-purple hover:bg-brand-purple/20 text-xs font-bold transition cursor-pointer"
          >
            <Play className="h-3.5 w-3.5 fill-brand-purple" />
            Instant Demo Preview
          </button>
          <button
            onClick={() => setShowKeyModal(true)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg border text-xs font-semibold transition cursor-pointer ${
              apiKey
                ? 'border-brand-green/40 bg-brand-green/10 text-brand-green'
                : 'border-brand-yellow/40 bg-brand-yellow/10 text-brand-yellow hover:bg-brand-yellow/20'
            }`}
          >
            <Key className="h-4 w-4" />
            {apiKey ? 'Gemini 2.5 Active' : 'Set Gemini API Key'}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-8">
        {/* Hero & Ingestion Section */}
        <section className="bg-brand-card/70 border border-brand-border rounded-2xl p-6 sm:p-8 backdrop-blur shadow-2xl">
          <div className="max-w-2xl mx-auto text-center space-y-3 mb-8">
            <h2 className="text-3xl font-black tracking-tight text-white sm:text-4xl">
              Turn YouTube Videos Into <span className="text-brand-yellow">Viral Vertical Shorts</span>
            </h2>
            <p className="text-slate-400 text-sm sm:text-base">
              Extracts high-retention moments, applies active-speaker 9:16 tracking, adds neural AI voiceovers with smart audio ducking, burns in animated Hormozi captions, and applies Premiere Pro effects.
            </p>
          </div>

          <div className="max-w-3xl mx-auto space-y-4">
            <form onSubmit={handleAnalyzeUrl} className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-red-500" />
                <input
                  type="text"
                  placeholder="Paste YouTube Video URL (e.g. https://www.youtube.com/watch?v=...)"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  disabled={loading}
                  className="w-full bg-[#0B0F17] border border-brand-border rounded-xl pl-12 pr-4 py-3.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-yellow transition"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !videoUrl}
                className="bg-brand-yellow hover:bg-yellow-400 text-black font-extrabold px-6 py-3.5 rounded-xl transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-brand-yellow/20 cursor-pointer"
              >
                <Sparkles className="h-5 w-5" />
                {loading ? 'Analyzing Video...' : 'Extract Viral Clips'}
              </button>
            </form>

            <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
              <span className="h-px bg-brand-border flex-1" />
              <span>OR UPLOAD A LOCAL FILE</span>
              <span className="h-px bg-brand-border flex-1" />
            </div>

            <div className="flex justify-center">
              <label className="border-2 border-dashed border-brand-border hover:border-brand-yellow/60 rounded-xl px-6 py-4 flex items-center gap-3 cursor-pointer bg-[#0B0F17]/40 hover:bg-[#0B0F17]/80 transition group">
                <Upload className="h-5 w-5 text-slate-400 group-hover:text-brand-yellow transition" />
                <span className="text-xs font-semibold text-slate-300 group-hover:text-white">
                  {selectedFile ? selectedFile.name : 'Upload MP4, MOV, or WebM Video'}
                </span>
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={loading}
                />
              </label>
            </div>
          </div>
        </section>

        {/* Error Notification */}
        {error && (
          <div className="bg-red-950/40 border border-red-800/60 rounded-xl p-4 flex items-center gap-3 text-red-200 text-sm">
            <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Progress & Processing Indicator */}
        {loading && (
          <div className="bg-brand-card/90 border border-brand-border rounded-2xl p-6 sm:p-8 space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold text-brand-yellow flex items-center gap-2">
                <Sparkles className="h-4 w-4 animate-spin text-brand-yellow" />
                {jobData?.message || 'Processing Video...'}
              </span>
              <span className="text-slate-400 font-mono">{jobData?.progress || 15}%</span>
            </div>
            <div className="w-full bg-[#0B0F17] rounded-full h-2.5 overflow-hidden border border-brand-border">
              <div
                className="bg-gradient-to-r from-brand-yellow via-brand-green to-brand-purple h-full transition-all duration-500"
                style={{ width: `${jobData?.progress || 15}%` }}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs pt-2">
              <div className="flex items-center gap-2 text-slate-400">
                <CheckCircle2 className="h-4 w-4 text-brand-green" /> Ingest & Probe
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <CheckCircle2 className={`h-4 w-4 ${(jobData?.progress || 0) >= 40 ? 'text-brand-green' : 'text-slate-600'}`} /> 16kHz Audio Extraction
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <CheckCircle2 className={`h-4 w-4 ${(jobData?.progress || 0) >= 70 ? 'text-brand-green' : 'text-slate-600'}`} /> Word-Level Alignment
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <CheckCircle2 className={`h-4 w-4 ${(jobData?.progress || 0) >= 90 ? 'text-brand-green' : 'text-slate-600'}`} /> Gemini Viral Hooks & Scores
              </div>
            </div>
          </div>
        )}

        {/* 🎙️ AI Voiceover Studio Card */}
        <section className="bg-gradient-to-r from-brand-card via-[#161D2B] to-brand-card border border-brand-border rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-brand-border/60 pb-3">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-brand-yellow/10 border border-brand-yellow/30 flex items-center justify-center text-brand-yellow">
                <Mic className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-black text-white flex items-center gap-2">
                  AI Voiceover & Smart Audio Ducking Studio
                </h3>
                <p className="text-xs text-slate-400">
                  Adds cinematic neural narration at the hook start while automatically ducking background video audio
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-bold text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={styleSettings.enable_voiceover}
                  onChange={(e) => setStyleSettings({ ...styleSettings, enable_voiceover: e.target.checked })}
                  className="rounded accent-brand-yellow cursor-pointer h-4 w-4"
                />
                Enable AI Voiceover
              </label>
            </div>
          </div>

          {styleSettings.enable_voiceover && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs pt-1">
              {VOICES.map((v) => {
                const isSelected = styleSettings.voice_key === v.key;
                return (
                  <button
                    key={v.key}
                    onClick={() => setStyleSettings({ ...styleSettings, voice_key: v.key })}
                    className={`p-3.5 rounded-xl border text-left transition flex flex-col justify-between gap-1.5 cursor-pointer ${
                      isSelected
                        ? 'border-brand-yellow bg-brand-yellow/10 shadow-lg shadow-brand-yellow/10 font-bold'
                        : 'border-brand-border bg-[#0B0F17] text-slate-400 hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-black ${isSelected ? 'text-brand-yellow' : 'text-white'}`}>
                        {v.name}
                      </span>
                      {isSelected && <Radio className="h-3.5 w-3.5 text-brand-yellow shrink-0" />}
                    </div>
                    <span className="text-[11px] text-slate-300">{v.style}</span>
                    <span className="text-[10px] text-slate-500 uppercase">{v.gender}</span>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        {/* Premiere Pro FX & Customizer Suite */}
        <section className="bg-brand-card border border-brand-border rounded-2xl p-6 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-brand-border/60 pb-4">
            <div>
              <h3 className="text-base font-black uppercase tracking-wider text-white flex items-center gap-2">
                <Sliders className="h-5 w-5 text-brand-yellow" />
                Premiere Pro Video Effects Engine
              </h3>
              <p className="text-xs text-slate-400">Customize cinematic color grading, transitions, captions, and hook badges</p>
            </div>
            <span className="text-xs bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/30 px-3 py-1 rounded-full font-bold">
              Broadcast Ready
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            {/* Effect 1: Lumetri Color Grade */}
            <div className="bg-[#0B0F17] border border-brand-border rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 flex items-center gap-1.5">
                  <Palette className="h-4 w-4 text-brand-yellow" />
                  Lumetri Color Grade
                </span>
                <input
                  type="checkbox"
                  checked={styleSettings.enable_color_grade}
                  onChange={(e) => setStyleSettings({ ...styleSettings, enable_color_grade: e.target.checked })}
                  className="rounded accent-brand-yellow cursor-pointer h-4 w-4"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Enhances contrast (1.08x), boosts vibrance (+16%), and applies cinematic radial vignette.
              </p>
            </div>

            {/* Effect 2: Impact Hook Flash */}
            <div className="bg-[#0B0F17] border border-brand-border rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 flex items-center gap-1.5">
                  <Zap className="h-4 w-4 text-brand-cyan" />
                  Impact Flash Intro
                </span>
                <input
                  type="checkbox"
                  checked={styleSettings.enable_impact_flash}
                  onChange={(e) => setStyleSettings({ ...styleSettings, enable_impact_flash: e.target.checked })}
                  className="rounded accent-brand-cyan cursor-pointer h-4 w-4"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                High-energy 0.12s white exposure burst at clip start to stop the user from scrolling.
              </p>
            </div>

            {/* Effect 3: Dynamic Punch-In Zoom */}
            <div className="bg-[#0B0F17] border border-brand-border rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 flex items-center gap-1.5">
                  <ZoomIn className="h-4 w-4 text-brand-green" />
                  Dynamic Punch Zoom
                </span>
                <input
                  type="checkbox"
                  checked={styleSettings.enable_punch_zoom}
                  onChange={(e) => setStyleSettings({ ...styleSettings, enable_punch_zoom: e.target.checked })}
                  className="rounded accent-brand-green cursor-pointer h-4 w-4"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                1.15x camera cut on key emphasis words to maintain high dopamine retention.
              </p>
            </div>

            {/* Effect 4: Animated Bottom Progress Bar */}
            <div className="bg-[#0B0F17] border border-brand-border rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200 flex items-center gap-1.5">
                  <Timer className="h-4 w-4 text-brand-purple" />
                  Bottom Progress Bar
                </span>
                <input
                  type="checkbox"
                  checked={styleSettings.enable_progress_bar}
                  onChange={(e) => setStyleSettings({ ...styleSettings, enable_progress_bar: e.target.checked })}
                  className="rounded accent-brand-purple cursor-pointer h-4 w-4"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Smooth horizontal accent bar along the bottom frame tracking video playback time.
              </p>
            </div>
          </div>

          {/* Subtitle Styling & Hook Style Bar */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
            {/* Caption Highlight Color */}
            <div className="bg-[#0B0F17] border border-brand-border rounded-xl p-4 space-y-2">
              <label className="text-slate-300 font-bold flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-brand-yellow" />
                Hormozi Word-Highlight Color
              </label>
              <div className="flex items-center gap-3">
                {HIGHLIGHT_COLORS.map((col) => (
                  <button
                    key={col.value}
                    onClick={() => setStyleSettings({ ...styleSettings, highlight_color: col.value })}
                    className={`h-8 w-8 rounded-lg border flex items-center justify-center transition cursor-pointer ${
                      styleSettings.highlight_color === col.value
                        ? 'border-white scale-110 shadow-lg'
                        : 'border-transparent opacity-60 hover:opacity-100'
                    }`}
                    style={{ backgroundColor: col.hex }}
                    title={col.name}
                  />
                ))}
                <span className="text-slate-400 text-xs ml-2">
                  Pop/Bounce animation & auto-emojis active
                </span>
              </div>
            </div>

            {/* Hook Badge Style */}
            <div className="bg-[#0B0F17] border border-brand-border rounded-xl p-4 space-y-2">
              <label className="text-slate-300 font-bold flex items-center gap-2">
                <Layers className="h-4 w-4 text-brand-yellow" />
                Hook Banner Visual Badge Style
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {HOOK_STYLES.map((hs) => {
                  const Icon = hs.icon;
                  const isSelected = styleSettings.hook_style === hs.id;
                  return (
                    <button
                      key={hs.id}
                      onClick={() => setStyleSettings({ ...styleSettings, hook_style: hs.id })}
                      className={`p-2 rounded-lg border text-left transition flex items-center gap-1.5 cursor-pointer ${
                        isSelected
                          ? `${hs.border} bg-[#131A26] shadow-md font-bold text-white`
                          : 'border-brand-border bg-[#0B0F17] text-slate-400 opacity-70 hover:opacity-100'
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate text-[11px]">{hs.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Detected Viral Clips Showcase */}
        {jobData?.clips && jobData.clips.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left 2 Cols: Detected Viral Moments with Multi-Hook Selector */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-black tracking-tight text-white flex items-center gap-2">
                  <Flame className="h-5 w-5 text-brand-yellow" />
                  Detected Viral Clips & Hooks ({jobData.clips.length})
                </h3>
                <span className="text-xs text-slate-400">Ranked by AI Retention & Shareability Score</span>
              </div>

              <div className="space-y-5">
                {jobData.clips.map((clip) => {
                  const isRendered = Boolean(jobData?.rendered_clips?.[clip.id]);
                  const isRendering = renderingClipId === clip.id;
                  const currentCustomTitle = selectedHooks[clip.id] || clip.title;

                  return (
                    <div
                      key={clip.id}
                      className="bg-brand-card/80 border border-brand-border hover:border-brand-border/80 rounded-2xl p-5 transition space-y-4 shadow-xl"
                    >
                      {/* Top Bar: Score, Time & Action */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/30 flex items-center gap-1">
                              <Flame className="h-3 w-3" />
                              {clip.viral_score}% VIRAL SCORE
                            </span>
                            <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {clip.start_time.toFixed(1)}s - {clip.end_time.toFixed(1)}s ({(clip.end_time - clip.start_time).toFixed(0)}s)
                            </span>
                          </div>
                          <h4 className="text-base font-extrabold text-white">{currentCustomTitle}</h4>
                          <p className="text-xs text-slate-300 leading-relaxed">{clip.hook_summary}</p>
                        </div>

                        {/* Render / Preview Button */}
                        <div className="shrink-0">
                          {isRendered ? (
                            <button
                              onClick={() => setActivePreview(jobData.rendered_clips[clip.id])}
                              className="bg-brand-green hover:bg-emerald-400 text-black font-extrabold px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5 transition shadow-lg shadow-brand-green/20 cursor-pointer"
                            >
                              <Play className="h-4 w-4 fill-black" />
                              Preview 9:16
                            </button>
                          ) : (
                            <button
                              onClick={() => handleRenderClip(clip)}
                              disabled={isRendering}
                              className="bg-brand-yellow hover:bg-yellow-400 text-black font-extrabold px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer shadow-lg shadow-brand-yellow/20"
                            >
                              <Scissors className="h-4 w-4" />
                              {isRendering ? 'Rendering FX + Voice...' : 'Render 9:16 Short'}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* AI Viral Hooks Multi-Variant Selector */}
                      {clip.hooks && (
                        <div className="space-y-2 pt-2 border-t border-brand-border/40">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-brand-yellow flex items-center gap-1">
                            <Lightbulb className="h-3.5 w-3.5" />
                            AI Viral Hook Variations (Click to select for top banner & voiceover):
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                            {Object.entries(clip.hooks).map(([category, hookText]) => {
                              const isSelected = currentCustomTitle === hookText;
                              return (
                                <button
                                  key={category}
                                  onClick={() => setSelectedHooks({ ...selectedHooks, [clip.id]: hookText })}
                                  className={`p-2 rounded-lg border text-left transition flex items-start gap-2 cursor-pointer ${
                                    isSelected
                                      ? 'border-brand-yellow bg-brand-yellow/10 text-brand-yellow font-bold'
                                      : 'border-brand-border bg-[#0B0F17] text-slate-300 hover:border-slate-500'
                                  }`}
                                >
                                  <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-black/40 text-slate-400">
                                    {category}
                                  </span>
                                  <span className="truncate">{hookText}</span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Punch Keywords */}
                      {clip.punch_keywords && clip.punch_keywords.length > 0 && (
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <span className="font-semibold text-slate-500">Zoom Emphasis Words:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {clip.punch_keywords.map((kw, i) => (
                              <span key={i} className="bg-[#0B0F17] border border-brand-border px-2 py-0.5 rounded text-[11px] text-brand-cyan">
                                #{kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right 1 Col: 9:16 Smartphone Vertical Video Preview Player */}
            <div className="space-y-4">
              <h3 className="text-lg font-black tracking-tight text-white flex items-center gap-2">
                <Play className="h-5 w-5 text-brand-green" />
                9:16 Vertical Preview
              </h3>

              {activePreview ? (
                <div className="bg-brand-card border border-brand-border rounded-2xl p-4 space-y-4 shadow-2xl">
                  <div className="relative mx-auto w-full max-w-[280px] aspect-[9/16] bg-black rounded-3xl overflow-hidden border-4 border-slate-700 shadow-2xl">
                    <video
                      key={activePreview.filename}
                      src={`/api/video/${activePreview.filename}`}
                      controls
                      autoPlay
                      loop
                      className="w-full h-full object-cover"
                    />
                  </div>

                  <div className="space-y-2 pt-2 text-center">
                    <a
                      href={`/api/video/${activePreview.filename}`}
                      download={activePreview.filename}
                      className="w-full bg-brand-yellow hover:bg-yellow-400 text-black font-extrabold py-3 rounded-xl text-sm flex items-center justify-center gap-2 transition shadow-lg shadow-brand-yellow/20 cursor-pointer"
                    >
                      <Download className="h-4 w-4" />
                      Download 1080x1920 MP4
                    </a>
                    <div className="text-[11px] text-slate-400 space-y-1">
                      <p>
                        Hook: <span className="text-brand-yellow font-bold">{activePreview.hook_title}</span>
                      </p>
                      {activePreview.voiceover && (
                        <p className="text-brand-green flex items-center justify-center gap-1">
                          <Mic className="h-3 w-3" />
                          Voice: {activePreview.voiceover.voice_name} (Ducked BG)
                        </p>
                      )}
                      <p>
                        Effects: Lumetri Grade • Impact Flash • Dynamic Zoom • Bottom Progress
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-brand-card/40 border border-dashed border-brand-border rounded-2xl p-12 text-center space-y-3">
                  <Play className="h-10 w-10 text-slate-600 mx-auto" />
                  <p className="text-xs text-slate-400">
                    Click <span className="text-brand-yellow font-bold">"Render 9:16 Short"</span> on any viral moment to generate the vertical video with Premiere Pro visual effects and original crystal-clear audio.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* API Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-brand-card border border-brand-border rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Key className="h-5 w-5 text-brand-yellow" />
                Google Gemini API Key
              </h3>
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-300">
              Enter your Gemini API key to power speech transcription, viral hook generation, and retention scoring with Gemini 2.5 Flash.
            </p>
            <input
              type="password"
              placeholder="AIzaSy..."
              defaultValue={apiKey}
              id="gemini-key-input"
              className="w-full bg-[#0B0F17] border border-brand-border rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-yellow"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowKeyModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const val = document.getElementById('gemini-key-input')?.value;
                  handleSaveApiKey(val);
                }}
                className="bg-brand-yellow hover:bg-yellow-400 text-black font-extrabold px-5 py-2 rounded-xl text-xs transition"
              >
                Save Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
