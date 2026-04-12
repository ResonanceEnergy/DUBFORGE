# pyright: basic
"""
DUBFORGE — Reference Intake Module

URL → Download → Analysis → Internet Research → SongDNA

Takes a SoundCloud (or any supported) URL, downloads the audio,
runs the full DUBFORGE analysis pipeline, scrapes the internet for
production breakdowns / chord progressions / song metadata, and
produces a SongDNA populated from REAL DATA instead of guessing.

Single entry point:  python forge.py --ref URL

Internal API:
    from engine.reference_intake import intake_from_url
    result = intake_from_url("https://soundcloud.com/artist/track")
    dna = result.song_dna
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import struct
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency flags
# ---------------------------------------------------------------------------
try:
    import requests as _requests  # type: ignore[import-untyped]

    HAS_REQUESTS = True
except ModuleNotFoundError:
    _requests: Any = None
    HAS_REQUESTS = False

try:
    import librosa as _librosa  # type: ignore[import-untyped]

    HAS_LIBROSA = True
except ModuleNotFoundError:
    _librosa: Any = None
    HAS_LIBROSA = False

# ---------------------------------------------------------------------------
# New ML modules (Basic Pitch, Demucs, madmom wrappers)
# ---------------------------------------------------------------------------
try:
    from engine.audio_to_midi import (
        HAS_BASIC_PITCH,
        TranscriptionResult,
    )
    from engine.audio_to_midi import (
        transcribe_bass as _bp_transcribe_bass,
    )
    from engine.audio_to_midi import (
        transcribe_melody as _bp_transcribe_melody,
    )

    HAS_AUDIO_TO_MIDI = True
except ImportError:
    HAS_AUDIO_TO_MIDI = False
    HAS_BASIC_PITCH = False

try:
    from engine.beat_tracker import (
        HAS_MADMOM,
    )
    from engine.beat_tracker import (
        track_beats as _track_beats,
    )

    HAS_BEAT_TRACKER = True
except ImportError:
    HAS_BEAT_TRACKER = False
    HAS_MADMOM = False

try:
    from engine.stem_separator import (
        HAS_DEMUCS,
    )
    from engine.stem_separator import (
        separate_demucs_to_files as _demucs_to_files,
    )

    HAS_STEM_SEP = True
except ImportError:
    HAS_STEM_SEP = False
    HAS_DEMUCS = False

try:
    from engine.chord_db import (
        query_progressions as _query_chord_db,
    )

    HAS_CHORD_DB = True
except ImportError:
    HAS_CHORD_DB = False

# ---------------------------------------------------------------------------
# API keys — loaded from environment variables (all optional)
# ---------------------------------------------------------------------------
_SERP_API_KEY     = os.getenv("SERPAPI_KEY", "")           # SerpAPI for Google
_GOOGLE_CSE_KEY   = os.getenv("GOOGLE_CSE_KEY", "")        # Google Custom Search key
_GOOGLE_CSE_ID    = os.getenv("GOOGLE_CSE_ID", "")         # Google Custom Search engine ID
_GROK_API_KEY     = os.getenv("GROK_API_KEY", "")          # xAI Grok
_ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY", "")     # Anthropic Claude
_GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")        # Google Gemini
_PERPLEXITY_KEY   = os.getenv("PERPLEXITY_API_KEY", "")    # Perplexity

# ---------------------------------------------------------------------------
# Engine imports (always available)
# ---------------------------------------------------------------------------
from engine.reference_analyzer import (  # noqa: E402
    ReferenceAnalysis,
    analyze_reference,
)
from engine.variation_engine import (  # noqa: E402
    ArrangementSection,
    AtmosphereDNA,
    BassDNA,
    DrumDNA,
    FxDNA,
    LeadDNA,
    MixDNA,
    SongDNA,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_OUTPUT_DIR = Path("output/reference_intake")
_CACHE_DIR = _OUTPUT_DIR / "cache"
_DEFAULT_SR = 48000
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# yt-dlp search paths
_YTDLP_PATHS = [
    "yt-dlp",
    os.path.expanduser("~/ai-dev/venv/bin/yt-dlp"),
    "/usr/local/bin/yt-dlp",
    "/opt/homebrew/bin/yt-dlp",
]

# ---------------------------------------------------------------------------
# Dataclasses — Intake results
# ---------------------------------------------------------------------------


@dataclass
class TrackMetadata:
    """Metadata extracted from the URL source + internet research."""

    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""
    tags: list[str] = field(default_factory=list)
    bpm: float = 0.0
    key: str = ""
    duration_s: float = 0.0
    url: str = ""
    description: str = ""
    upload_date: str = ""
    like_count: int = 0
    play_count: int = 0
    comment_count: int = 0


@dataclass
class ChordInfo:
    """Chord progression extracted from analysis + internet."""

    chords: list[str] = field(default_factory=list)  # e.g. ["Cm", "Ab", "Eb", "Bb"]
    progression_roman: list[str] = field(default_factory=list)  # ["i", "VI", "III", "VII"]
    key: str = ""
    scale: str = ""
    source: str = ""  # "audio_analysis" | "web_lookup" | "combined"
    confidence: float = 0.0


@dataclass
class MelodyInfo:
    """Melody line extracted from audio analysis."""

    notes: list[dict[str, Any]] = field(default_factory=list)
    # Each note: {"pitch_hz": float, "midi": int, "start_s": float,
    #             "duration_s": float, "velocity": float}
    scale_degrees: list[int] = field(default_factory=list)  # 0-6 within scale
    phrase_length_bars: int = 4
    contour: str = ""  # "ascending" | "descending" | "arch" | "flat" | "complex"
    source: str = "audio_analysis"


@dataclass
class SynthProfile:
    """Synth character extracted from spectral analysis."""

    # Wavetable estimation
    estimated_waveform: str = "complex"  # saw | square | sine | complex | noise
    harmonic_content: str = "rich"  # thin | moderate | rich | dense
    odd_even_ratio: float = 0.5  # >0.5 = more odd harmonics (square-ish)

    # Filter
    filter_cutoff_est: float = 0.7  # normalized 0-1
    filter_resonance_est: float = 0.3
    filter_movement: float = 0.0  # how much filter moves over time

    # Modulation
    mod_rate_hz: float = 0.0  # dominant LFO rate
    mod_depth: float = 0.0  # modulation amount 0-1
    mod_shape: str = "sine"  # sine | saw | square | random

    # Character
    distortion_amount: float = 0.0
    noise_content: float = 0.0
    formant_presence: float = 0.0
    inharmonicity: float = 0.0

    # Layer
    layer_type: str = ""  # "bass" | "lead" | "pad" | "fx"


@dataclass
class WebResearchResult:
    """Results from internet research about the track."""

    production_notes: list[str] = field(default_factory=list)
    chord_progressions_found: list[ChordInfo] = field(default_factory=list)
    bpm_sources: list[dict[str, Any]] = field(default_factory=list)
    key_sources: list[dict[str, Any]] = field(default_factory=list)
    synth_info: list[str] = field(default_factory=list)
    sample_pack_info: list[str] = field(default_factory=list)
    genre_tags: list[str] = field(default_factory=list)
    similar_tracks: list[str] = field(default_factory=list)
    sources_consulted: list[str] = field(default_factory=list)
    raw_snippets: list[str] = field(default_factory=list)
    # AI source raw summaries — keyed by source name
    ai_summaries: dict[str, str] = field(default_factory=dict)


@dataclass
class IntakeResult:
    """Complete reference intake result — everything extracted from URL/file."""

    # Source
    url: str = ""
    local_path: str = ""

    # Metadata
    metadata: TrackMetadata = field(default_factory=TrackMetadata)

    # Audio DNA (from reference_analyzer — 13 categories)
    audio_dna: ReferenceAnalysis = field(default_factory=ReferenceAnalysis)

    # Deep extraction
    chords: ChordInfo = field(default_factory=ChordInfo)
    melody: MelodyInfo = field(default_factory=MelodyInfo)
    bass_synth: SynthProfile = field(default_factory=SynthProfile)
    lead_synth: SynthProfile = field(default_factory=SynthProfile)
    pad_synth: SynthProfile = field(default_factory=SynthProfile)

    # ML-enhanced analysis (new)
    stem_paths: dict[str, str] = field(default_factory=dict)  # Demucs stem files
    bass_midi: list[dict] = field(default_factory=list)       # Basic Pitch bass notes
    lead_midi: list[dict] = field(default_factory=list)       # Basic Pitch lead notes
    beat_grid: dict = field(default_factory=dict)             # madmom/native beat data
    chord_db_suggestions: list[dict] = field(default_factory=list)  # CHORDONOMICON matches

    # Internet research
    web_research: WebResearchResult = field(default_factory=WebResearchResult)

    # Final mapped SongDNA
    song_dna: SongDNA | None = None

    def to_dict(self) -> dict:
        """Serialize everything to a dict (JSON-safe)."""
        d: dict[str, Any] = {}
        d["url"] = self.url
        d["local_path"] = self.local_path
        d["metadata"] = asdict(self.metadata)
        d["audio_dna"] = self.audio_dna.to_dict()
        d["chords"] = asdict(self.chords)
        d["melody"] = asdict(self.melody)
        d["bass_synth"] = asdict(self.bass_synth)
        d["lead_synth"] = asdict(self.lead_synth)
        d["pad_synth"] = asdict(self.pad_synth)
        d["stem_paths"] = self.stem_paths
        d["bass_midi"] = self.bass_midi
        d["lead_midi"] = self.lead_midi
        d["beat_grid"] = self.beat_grid
        d["chord_db_suggestions"] = self.chord_db_suggestions
        d["web_research"] = asdict(self.web_research)
        if self.song_dna:
            d["song_dna"] = self.song_dna.to_dict()
        return d


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1: DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════


def _find_ytdlp() -> str | None:
    """Locate the yt-dlp binary."""
    for p in _YTDLP_PATHS:
        try:
            result = subprocess.run(
                [p, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return p
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def download_audio(url: str, output_dir: Path | None = None) -> Path:
    """
    Download audio from a URL using yt-dlp.

    Returns path to the downloaded WAV file.
    Raises RuntimeError if yt-dlp is not found or download fails.
    """
    ytdlp = _find_ytdlp()
    if ytdlp is None:
        raise RuntimeError(
            "yt-dlp not found. Install with: pip install yt-dlp\n"
            "Or: brew install yt-dlp"
        )

    out_dir = output_dir or _OUTPUT_DIR / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use URL hash for deterministic filename (cache-friendly)
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    out_template = str(out_dir / f"ref_{url_hash}_%(title)s")

    cmd = [
        ytdlp,
        "--no-playlist",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--output", out_template + ".%(ext)s",
        "--write-info-json",
        "--no-overwrites",
        "--restrict-filenames",
        url,
    ]

    log.info("Downloading: %s", url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr}")

    # Find the output file
    wav_files = sorted(out_dir.glob(f"ref_{url_hash}_*.wav"), key=os.path.getmtime)
    if not wav_files:
        raise RuntimeError(f"No WAV file found after download in {out_dir}")

    wav_path = wav_files[-1]
    log.info("Downloaded: %s", wav_path)
    return wav_path


def _load_ytdlp_metadata(wav_path: Path) -> TrackMetadata:
    """Load metadata from yt-dlp's .info.json sidecar file."""
    meta = TrackMetadata()

    # Try to find the .info.json next to the wav
    stem = wav_path.stem
    info_candidates = [
        wav_path.with_suffix(".info.json"),
        wav_path.parent / (stem + ".info.json"),
    ]
    # yt-dlp may name the json without the .wav extension
    for candidate in wav_path.parent.glob(f"{stem.rsplit('.', 1)[0]}*.info.json"):
        info_candidates.append(candidate)

    info_path = None
    for c in info_candidates:
        if c.exists():
            info_path = c
            break

    if info_path is None:
        log.warning("No .info.json found for %s", wav_path)
        return meta

    try:
        with open(info_path, encoding="utf-8") as f:
            info = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to read info.json: %s", e)
        return meta

    meta.title = info.get("title", "")
    meta.artist = info.get("uploader", info.get("artist", ""))
    meta.album = info.get("album", "")
    meta.genre = info.get("genre", "")
    meta.tags = info.get("tags", []) or []
    meta.duration_s = float(info.get("duration", 0) or 0)
    meta.url = info.get("webpage_url", info.get("url", ""))
    meta.description = info.get("description", "")
    meta.upload_date = info.get("upload_date", "")
    meta.like_count = int(info.get("like_count", 0) or 0)
    meta.play_count = int(info.get("view_count", 0) or 0)
    meta.comment_count = int(info.get("comment_count", 0) or 0)

    return meta


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2: AUDIO ANALYSIS (leverages reference_analyzer)
# ═══════════════════════════════════════════════════════════════════════════


def _ensure_wav(path: Path) -> Path:
    """Convert non-WAV files to WAV using ffmpeg/yt-dlp if needed."""
    if path.suffix.lower() == ".wav":
        return path

    wav_path = path.with_suffix(".wav")
    if wav_path.exists():
        return wav_path

    # Try ffmpeg first
    try:
        subprocess.run(
            ["ffmpeg", "-i", str(path), "-ar", str(_DEFAULT_SR), "-ac", "2",
             "-sample_fmt", "s16", str(wav_path), "-y"],
            capture_output=True, timeout=120, check=True,
        )
        return wav_path
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    raise RuntimeError(f"Cannot convert {path.suffix} to WAV. Install ffmpeg.")


def _load_wav_samples(path: Path) -> tuple[np.ndarray, int]:
    """Load WAV file → (mono float64 array, sample_rate)."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        fmt = f"<{n_frames * n_channels}h"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float64) / 32768.0
    elif sampwidth == 3:
        # 24-bit
        samples = np.zeros(n_frames * n_channels, dtype=np.float64)
        for i in range(n_frames * n_channels):
            b = raw[i * 3:(i + 1) * 3]
            val = int.from_bytes(b, "little", signed=True)
            samples[i] = val / 8388608.0
    elif sampwidth == 4:
        fmt = f"<{n_frames * n_channels}i"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return samples, sr


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: DEEP EXTRACTION — Chords, Melody, Synth Character
# ═══════════════════════════════════════════════════════════════════════════

# ── Note names for chromagram → chord detection ──
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "pentatonic_minor": [0, 3, 5, 7, 10],
}


def _compute_chromagram(samples: np.ndarray, sr: int,
                        hop_length: int = 2048) -> np.ndarray:
    """
    Compute a 12-bin chromagram from audio samples.

    Returns shape (12, n_frames) — energy per pitch class per time frame.
    Uses Goertzel-like frequency targeting per semitone across 5 octaves.
    """
    n_frames = max(1, len(samples) // hop_length)
    chroma = np.zeros((12, n_frames), dtype=np.float64)
    fft_size = 4096

    for frame_idx in range(n_frames):
        start = frame_idx * hop_length
        end = min(start + fft_size, len(samples))
        if end - start < 256:
            continue
        chunk = samples[start:end]
        # Apply Hann window
        window = np.hanning(len(chunk))
        windowed = chunk * window
        spectrum = np.abs(np.fft.rfft(windowed))

        # Sum energy for each pitch class across octaves 1-6
        for pc in range(12):
            energy = 0.0
            for octave in range(1, 7):
                f = 440.0 * (2.0 ** ((pc - 9 + (octave - 4) * 12) / 12.0))
                if f > sr / 2:
                    break
                # Find nearest bin
                bin_idx = int(round(f * len(windowed) / sr))
                if 0 < bin_idx < len(spectrum):
                    # Sum ±2 bins for spectral leakage
                    lo = max(0, bin_idx - 2)
                    hi = min(len(spectrum), bin_idx + 3)
                    energy += float(np.sum(spectrum[lo:hi] ** 2))
            chroma[pc, frame_idx] = energy

    # Normalize each frame
    for i in range(n_frames):
        total = chroma[:, i].sum()
        if total > 0:
            chroma[:, i] /= total

    return chroma


def _detect_chords_from_chroma(chroma: np.ndarray,
                               beats_per_chord: int = 8) -> list[str]:
    """
    Detect chord sequence from chromagram using template matching.

    Returns list of chord symbols like ["Cm", "Ab", "Eb", "Bb"].
    """
    n_frames = chroma.shape[1]
    frames_per_chord = max(1, beats_per_chord)

    # Chord templates — major and minor triads for all 12 roots
    templates: dict[str, np.ndarray] = {}
    for root in range(12):
        name_maj = _NOTE_NAMES[root]
        name_min = _NOTE_NAMES[root] + "m"
        # Major: root + 4 + 7
        t_maj = np.zeros(12)
        t_maj[root] = 1.0
        t_maj[(root + 4) % 12] = 0.8
        t_maj[(root + 7) % 12] = 0.8
        templates[name_maj] = t_maj / np.linalg.norm(t_maj)
        # Minor: root + 3 + 7
        t_min = np.zeros(12)
        t_min[root] = 1.0
        t_min[(root + 3) % 12] = 0.8
        t_min[(root + 7) % 12] = 0.8
        templates[name_min] = t_min / np.linalg.norm(t_min)

    chords: list[str] = []
    for i in range(0, n_frames, frames_per_chord):
        chunk = chroma[:, i:i + frames_per_chord]
        avg_chroma = chunk.mean(axis=1)
        norm = np.linalg.norm(avg_chroma)
        if norm < 1e-10:
            chords.append("N")  # no chord / silence
            continue
        avg_chroma = avg_chroma / norm

        best_chord = "N"
        best_score = -1.0
        for name, tmpl in templates.items():
            score = float(np.dot(avg_chroma, tmpl))
            if score > best_score:
                best_score = score
                best_chord = name
        chords.append(best_chord)

    return chords


def _chords_to_roman(chords: list[str], key: str) -> list[str]:
    """Convert chord symbols to Roman numeral notation relative to key."""
    # Parse key (e.g. "C minor" → root=0, mode=minor)
    parts = key.strip().split()
    root_name = parts[0] if parts else "C"

    root_idx = _NOTE_NAMES.index(root_name) if root_name in _NOTE_NAMES else 0

    roman_map = ["I", "bII", "II", "bIII", "III", "IV", "bV", "V", "bVI", "VI", "bVII", "VII"]

    result: list[str] = []
    for chord in chords:
        if chord == "N":
            result.append("N")
            continue
        is_minor = chord.endswith("m")
        chord_root = chord.rstrip("m")
        try:
            chord_root_idx = _NOTE_NAMES.index(chord_root)
        except ValueError:
            result.append("?")
            continue
        interval = (chord_root_idx - root_idx) % 12
        numeral = roman_map[interval]
        if is_minor:
            numeral = numeral.lower()
        result.append(numeral)

    return result


def _deduplicate_chords(chords: list[str]) -> list[str]:
    """Remove consecutive duplicates: [Cm, Cm, Ab, Ab] → [Cm, Ab]."""
    if not chords:
        return []
    result = [chords[0]]
    for c in chords[1:]:
        if c != result[-1]:
            result.append(c)
    return result


def extract_chords(samples: np.ndarray, sr: int,
                   bpm: float = 140.0, key: str = "") -> ChordInfo:
    """Extract chord progression from audio samples."""
    hop = sr // 4  # ~4 chroma frames per second
    chroma = _compute_chromagram(samples, sr, hop_length=hop)

    # Estimate frames per bar  (~2 beats per chord for dubstep = half bar)
    fps = sr / hop
    beats_per_sec = bpm / 60.0
    frames_per_beat = fps / beats_per_sec if beats_per_sec > 0 else 4
    frames_per_chord = max(1, int(frames_per_beat * 2))  # chords change every 2 beats

    raw_chords = _detect_chords_from_chroma(chroma, frames_per_chord)
    deduped = _deduplicate_chords(raw_chords)
    # Filter silence
    deduped = [c for c in deduped if c != "N"]

    roman = _chords_to_roman(deduped, key) if key else []

    # Simple confidence: how consistent are the top chords?
    if raw_chords:
        from collections import Counter  # noqa: PLC0415

        counts = Counter(c for c in raw_chords if c != "N")
        top4 = counts.most_common(4)
        total = sum(counts.values())
        confidence = sum(c for _, c in top4) / total if total > 0 else 0.0
    else:
        confidence = 0.0

    return ChordInfo(
        chords=deduped[:8],  # first 8 unique chords
        progression_roman=roman[:8],
        key=key,
        scale="minor" if "minor" in key.lower() else "major",
        source="audio_analysis",
        confidence=round(confidence, 3),
    )


def _extract_melody_contour(samples: np.ndarray, sr: int,
                            bpm: float = 140.0) -> MelodyInfo:
    """
    Extract melody contour from audio using spectral peak tracking.

    This works best on isolated lead stems; on full mixes it finds
    the most prominent melodic line above ~200Hz.
    """
    hop = sr // 8  # ~8 frames per second
    fft_size = 4096
    n_frames = len(samples) // hop

    notes: list[dict[str, Any]] = []
    min_freq = 200.0  # ignore sub/bass
    max_freq = 6000.0  # upper lead range

    prev_freq = 0.0

    for i in range(n_frames):
        start = i * hop
        end = min(start + fft_size, len(samples))
        if end - start < 256:
            continue
        chunk = samples[start:end]
        window = np.hanning(len(chunk))
        spectrum = np.abs(np.fft.rfft(chunk * window))
        freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)

        # Find dominant frequency in lead range
        mask = (freqs >= min_freq) & (freqs <= max_freq)
        if not np.any(mask):
            continue
        lead_spectrum = spectrum.copy()
        lead_spectrum[~mask] = 0

        peak_bin = int(np.argmax(lead_spectrum))
        peak_freq = float(freqs[peak_bin])
        peak_mag = float(lead_spectrum[peak_bin])

        # Skip quiet frames
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms < 0.01:
            continue

        # Quantize to nearest MIDI note
        if peak_freq > 0:
            midi = int(round(12 * math.log2(peak_freq / 440.0) + 69))
            midi = max(0, min(127, midi))
            quant_freq = 440.0 * (2 ** ((midi - 69) / 12.0))

            time_s = start / sr

            # Only add if frequency changed significantly (new note)
            if abs(quant_freq - prev_freq) > 10 or not notes:
                notes.append({
                    "pitch_hz": round(quant_freq, 1),
                    "midi": midi,
                    "start_s": round(time_s, 3),
                    "duration_s": round(hop / sr, 3),
                    "velocity": round(min(1.0, peak_mag / 100.0), 3),
                })
                prev_freq = quant_freq

    # Update durations based on note spacing
    for i in range(len(notes) - 1):
        notes[i]["duration_s"] = round(notes[i + 1]["start_s"] - notes[i]["start_s"], 3)

    # Determine contour shape
    if len(notes) >= 4:
        pitches = [n["midi"] for n in notes[:16]]
        diffs = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        if avg_diff > 1:
            contour = "ascending"
        elif avg_diff < -1:
            contour = "descending"
        elif max(pitches) - min(pitches) > 12:
            contour = "arch"
        elif max(pitches) - min(pitches) < 3:
            contour = "flat"
        else:
            contour = "complex"
    else:
        contour = "flat"

    # Estimate phrase length
    beats_per_sec = bpm / 60.0
    if notes and len(notes) > 1:
        total_dur = notes[-1]["start_s"] - notes[0]["start_s"]
        bars = total_dur * beats_per_sec / 4.0
        phrase_bars = max(1, min(16, int(round(bars / max(1, len(notes) // 8)))))
    else:
        phrase_bars = 4

    return MelodyInfo(
        notes=notes[:64],  # cap at 64 notes
        contour=contour,
        phrase_length_bars=phrase_bars,
        source="audio_analysis",
    )


def _analyze_synth_character(samples: np.ndarray, sr: int,
                             freq_range: tuple[float, float] = (30.0, 20000.0),
                             layer_type: str = "") -> SynthProfile:
    """
    Analyze synth character from audio (spectral shape → wavetable/filter/mod).

    freq_range limits the analysis band:
      bass: (30, 500)
      lead: (200, 8000)
      pad:  (100, 12000)
    """
    fft_size = 8192
    n_chunks = max(1, len(samples) // fft_size)
    min_freq, max_freq = freq_range

    # Collect spectral snapshots
    spectra: list[np.ndarray] = []
    for i in range(min(n_chunks, 64)):
        start = i * fft_size
        chunk = samples[start:start + fft_size]
        if len(chunk) < fft_size:
            chunk = np.pad(chunk, (0, fft_size - len(chunk)))
        window = np.hanning(fft_size)
        spectrum = np.abs(np.fft.rfft(chunk * window))
        spectra.append(spectrum)

    if not spectra:
        return SynthProfile(layer_type=layer_type)

    spectra_arr = np.array(spectra)
    mean_spectrum = spectra_arr.mean(axis=0)
    freqs = np.fft.rfftfreq(fft_size, 1.0 / sr)

    # Band-limit
    mask = (freqs >= min_freq) & (freqs <= max_freq)
    band_spectrum = mean_spectrum.copy()
    band_spectrum[~mask] = 0

    # --- Waveform estimation ---
    # Find fundamental
    peak_bin = int(np.argmax(band_spectrum))
    fundamental = float(freqs[peak_bin]) if peak_bin > 0 else 100.0

    # Analyze harmonics
    odd_energy = 0.0
    even_energy = 0.0
    total_harmonic_energy = 0.0
    for h in range(2, 17):
        h_freq = fundamental * h
        h_bin = int(round(h_freq * fft_size / sr))
        if 0 < h_bin < len(band_spectrum):
            e = float(band_spectrum[h_bin] ** 2)
            total_harmonic_energy += e
            if h % 2 == 1:
                odd_energy += e
            else:
                even_energy += e

    fundamental_energy = float(band_spectrum[peak_bin] ** 2) if peak_bin > 0 else 1e-10
    harmonic_ratio = total_harmonic_energy / (fundamental_energy + 1e-10)

    if total_harmonic_energy > 0:
        odd_even = odd_energy / (odd_energy + even_energy + 1e-10)
    else:
        odd_even = 0.5

    # Estimate waveform type
    if harmonic_ratio < 0.1:
        waveform = "sine"
    elif odd_even > 0.8 and harmonic_ratio > 0.5:
        waveform = "square"
    elif harmonic_ratio > 1.0:
        waveform = "saw"
    else:
        waveform = "complex"

    # Harmonic density descriptor
    if harmonic_ratio < 0.2:
        harmonic_content = "thin"
    elif harmonic_ratio < 0.6:
        harmonic_content = "moderate"
    elif harmonic_ratio < 1.5:
        harmonic_content = "rich"
    else:
        harmonic_content = "dense"

    # --- Filter estimation ---
    # Spectral rolloff as proxy for filter cutoff (higher = brighter)
    total_energy = float(np.sum(band_spectrum ** 2))
    cumulative = 0.0
    rolloff_bin = len(band_spectrum) - 1
    for k in range(len(band_spectrum)):
        cumulative += float(band_spectrum[k] ** 2)
        if cumulative >= 0.85 * total_energy:
            rolloff_bin = k
            break
    rolloff_freq = float(freqs[rolloff_bin]) if rolloff_bin < len(freqs) else max_freq
    filter_cutoff_norm = min(1.0, rolloff_freq / max_freq)

    # Resonance: look for spectral peak near rolloff
    if rolloff_bin > 5:
        local = band_spectrum[max(0, rolloff_bin - 5):rolloff_bin + 5]
        local_peak = float(np.max(local))
        local_mean = float(np.mean(local))
        resonance_est = min(1.0, (local_peak / (local_mean + 1e-10) - 1) / 5)
    else:
        resonance_est = 0.0

    # --- Filter movement (spectral flux in the filter region) ---
    if len(spectra_arr) > 1:
        flux_values = []
        for j in range(1, len(spectra_arr)):
            diff = np.abs(spectra_arr[j] - spectra_arr[j - 1])
            flux_values.append(float(np.mean(diff[mask])))
        filter_movement = min(1.0, np.mean(flux_values) * 10) if flux_values else 0.0
    else:
        filter_movement = 0.0

    # --- Modulation detection ---
    # Look for amplitude modulation rate (wobble)
    rms_envelope: list[float] = []
    env_hop = sr // 100  # 100 fps envelope
    for i in range(0, len(samples) - env_hop, env_hop):
        rms_envelope.append(float(np.sqrt(np.mean(samples[i:i + env_hop] ** 2))))

    mod_rate = 0.0
    mod_depth = 0.0
    if len(rms_envelope) > 32:
        env_arr = np.array(rms_envelope)
        env_arr = env_arr - np.mean(env_arr)
        env_spectrum = np.abs(np.fft.rfft(env_arr))
        env_freqs = np.fft.rfftfreq(len(env_arr), 1.0 / 100.0)

        # Look for modulation in 0.5-20 Hz range (wobble/tremolo)
        mod_mask = (env_freqs >= 0.5) & (env_freqs <= 20.0)
        if np.any(mod_mask):
            mod_spectrum = env_spectrum.copy()
            mod_spectrum[~mod_mask] = 0
            mod_peak_bin = int(np.argmax(mod_spectrum))
            mod_rate = float(env_freqs[mod_peak_bin])
            mod_depth = min(1.0, float(mod_spectrum[mod_peak_bin]) / (np.mean(env_spectrum) + 1e-10) / 5)

    # Guess LFO shape from modulation waveform
    if mod_rate > 0 and mod_depth > 0.1:
        # Check duty cycle of envelope
        env_norm = np.array(rms_envelope)
        env_norm = (env_norm - env_norm.min()) / (env_norm.max() - env_norm.min() + 1e-10)
        above_mid = np.sum(env_norm > 0.5) / len(env_norm)
        if abs(above_mid - 0.5) < 0.1:
            mod_shape = "sine"
        elif above_mid > 0.6:
            mod_shape = "saw"
        elif above_mid < 0.3:
            mod_shape = "square"
        else:
            mod_shape = "random"
    else:
        mod_shape = "sine"

    # --- Noise / distortion / formant ---
    spectral_flatness = float(
        np.exp(np.mean(np.log(band_spectrum[mask] + 1e-10)))
        / (np.mean(band_spectrum[mask]) + 1e-10)
    )
    noise_content = min(1.0, spectral_flatness * 2)  # flat = noisy

    # Formant: look for vocal-like resonances (300-3000 Hz)
    formant_mask = (freqs >= 300) & (freqs <= 3000)
    if np.any(formant_mask):
        formant_energy = float(np.sum(band_spectrum[formant_mask] ** 2))
        formant_presence = min(1.0, formant_energy / (total_energy + 1e-10) * 3)
    else:
        formant_presence = 0.0

    # Distortion: ratio of high harmonics to fundamental
    distortion = min(1.0, harmonic_ratio / 3.0)

    return SynthProfile(
        estimated_waveform=waveform,
        harmonic_content=harmonic_content,
        odd_even_ratio=round(odd_even, 3),
        filter_cutoff_est=round(filter_cutoff_norm, 3),
        filter_resonance_est=round(max(0, resonance_est), 3),
        filter_movement=round(float(filter_movement), 3),
        mod_rate_hz=round(mod_rate, 2),
        mod_depth=float(mod_depth),
        mod_shape=mod_shape,
        distortion_amount=round(distortion, 3),
        noise_content=round(noise_content, 3),
        formant_presence=round(formant_presence, 3),
        inharmonicity=round(min(1.0, 1.0 - odd_even if odd_even > 0.5 else odd_even), 3),
        layer_type=layer_type,
    )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4: INTERNET RESEARCH
# ═══════════════════════════════════════════════════════════════════════════


def _safe_fetch(url: str, timeout: int = 10) -> str | None:
    """Fetch a URL safely, returns text or None."""
    if not HAS_REQUESTS:
        return None
    try:
        resp = _requests.get(  # type: ignore[union-attr]
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        log.debug("Fetch failed for %s: %s", url, e)
    return None


def _extract_text_snippets(html: str, keywords: list[str],
                           max_snippets: int = 10) -> list[str]:
    """
    Extract text snippets from HTML near keyword matches.

    Simple regex-based extraction — no BeautifulSoup needed.
    """
    # Strip HTML tags
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Decode HTML entities
    text = re.sub(r"&#?\w+;", " ", text)

    snippets: list[str] = []
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        for match in pattern.finditer(text):
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 200)
            snippet = text[start:end].strip()
            if len(snippet) > 30 and snippet not in snippets:
                snippets.append(snippet)
                if len(snippets) >= max_snippets:
                    return snippets
    return snippets


def _search_web(query: str, max_results: int = 5) -> list[str]:
    """
    Search the web using DuckDuckGo HTML (no API key needed).

    Returns list of result URLs.
    """
    if not HAS_REQUESTS:
        log.warning("requests not installed — web research disabled")
        return []

    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html = _safe_fetch(search_url, timeout=15)
    if not html:
        return []

    # Extract result URLs from DuckDuckGo HTML
    urls: list[str] = []
    # DuckDuckGo wraps results in <a class="result__a" href="...">
    for match in re.finditer(r'href="(https?://[^"]+)"', html):
        url = match.group(1)
        # Skip DuckDuckGo internal links
        if "duckduckgo.com" in url:
            continue
        if url not in urls:
            urls.append(url)
        if len(urls) >= max_results:
            break

    return urls


_RESEARCH_PROMPT = (
    "You are an expert music production analyst. Research the song '{title}' by {artist}. "
    "Return a JSON object with these fields (all optional — only include what you know):\n"
    "  bpm: number\n"
    "  key: string (e.g. 'F# minor')\n"
    "  chord_progression: array of chord strings (e.g. ['Am', 'F', 'C', 'G'])\n"
    "  genre_tags: array of strings\n"
    "  production_notes: string (production style, sound design, arrangement details)\n"
    "  synth_info: string (synths, presets, effects used)\n"
    "  mood: string\n"
    "Be technically specific. Return ONLY valid JSON, no markdown fences."
)


def _parse_ai_response(text: str, source_url: str, result: WebResearchResult) -> None:
    """Parse JSON or freeform AI response and merge into result."""
    if not text:
        return

    # Try JSON first
    try:
        # Strip any markdown fences if model ignored instructions
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
        data = json.loads(clean)

        bpm_val = data.get("bpm")
        if isinstance(bpm_val, (int, float)) and 60 <= bpm_val <= 200:
            result.bpm_sources.append({"bpm": int(bpm_val), "source": source_url})

        key_val = data.get("key", "")
        if key_val:
            result.key_sources.append({"key": key_val, "source": source_url})

        chords = data.get("chord_progression", [])
        if isinstance(chords, list) and chords:
            result.chord_progressions_found.append(
                ChordInfo(chords=[str(c) for c in chords], source="ai_research", confidence=0.8)
            )

        for tag in data.get("genre_tags", []):
            if tag and tag not in result.genre_tags:
                result.genre_tags.append(str(tag))

        prod = data.get("production_notes", "")
        if prod:
            result.production_notes.append(str(prod)[:500])

        synth = data.get("synth_info", "")
        if synth:
            result.synth_info.append(str(synth)[:500])

        return
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: raw regex extraction from freeform text
    result.raw_snippets.append(text[:600])
    for bpm_str in re.findall(r"(\d{2,3})\s*(?:bpm|BPM)", text):
        bpm_val = int(bpm_str)
        if 60 <= bpm_val <= 200:
            result.bpm_sources.append({"bpm": bpm_val, "source": source_url})
    for key_root, key_mode in re.findall(
        r"\b([A-G][#b]?)\s*(minor|major|min|maj)\b", text, re.IGNORECASE
    ):
        mode = "minor" if "min" in key_mode.lower() else "major"
        result.key_sources.append({"key": f"{key_root} {mode}", "source": source_url})


def _query_google(search_name: str) -> tuple[str, list[str]]:
    """
    Query Google via SerpAPI or Google Custom Search JSON API.
    Falls back to DuckDuckGo if no API keys are configured.
    Returns (source_label, list_of_urls).
    """
    if not HAS_REQUESTS:
        return "google", []

    # SerpAPI (returns JSON)
    if _SERP_API_KEY:
        try:
            resp = _requests.get(
                "https://serpapi.com/search",
                params={
                    "q": f"{search_name} production BPM key chords",
                    "api_key": _SERP_API_KEY,
                    "num": 5,
                    "output": "json",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                items = resp.json().get("organic_results", [])
                return "google_serp", [r["link"] for r in items if "link" in r]
        except Exception as exc:
            log.debug("SerpAPI error: %s", exc)

    # Google Custom Search JSON API
    if _GOOGLE_CSE_KEY and _GOOGLE_CSE_ID:
        try:
            resp = _requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": _GOOGLE_CSE_KEY,
                    "cx": _GOOGLE_CSE_ID,
                    "q": f"{search_name} production BPM key chords",
                    "num": 5,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                return "google_cse", [r["link"] for r in items if "link" in r]
        except Exception as exc:
            log.debug("Google CSE error: %s", exc)

    # Fallback: DuckDuckGo (no key required)
    return "duckduckgo", _search_web(f"{search_name} production BPM key chords", max_results=5)


def _query_grok(title: str, artist: str) -> tuple[str, str]:
    """Query xAI Grok API. Returns (source_label, response_text)."""
    if not _GROK_API_KEY or not HAS_REQUESTS:
        return "grok", ""
    prompt = _RESEARCH_PROMPT.format(title=title, artist=artist)
    try:
        resp = _requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_GROK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-3",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 600,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return "grok", resp.json()["choices"][0]["message"]["content"]
        log.debug("Grok API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.debug("Grok query error: %s", exc)
    return "grok", ""


def _query_claude(title: str, artist: str) -> tuple[str, str]:
    """Query Anthropic Claude API. Returns (source_label, response_text)."""
    if not _ANTHROPIC_KEY or not HAS_REQUESTS:
        return "claude", ""
    prompt = _RESEARCH_PROMPT.format(title=title, artist=artist)
    try:
        resp = _requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": _ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return "claude", resp.json()["content"][0]["text"]
        log.debug("Claude API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.debug("Claude query error: %s", exc)
    return "claude", ""


def _query_gemini(title: str, artist: str) -> tuple[str, str]:
    """Query Google Gemini API. Returns (source_label, response_text)."""
    if not _GEMINI_API_KEY or not HAS_REQUESTS:
        return "gemini", ""
    prompt = _RESEARCH_PROMPT.format(title=title, artist=artist)
    try:
        resp = _requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            f"?key={_GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                return "gemini", text
        log.debug("Gemini API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.debug("Gemini query error: %s", exc)
    return "gemini", ""


def _query_perplexity(title: str, artist: str) -> tuple[str, str]:
    """Query Perplexity API. Returns (source_label, response_text)."""
    if not _PERPLEXITY_KEY or not HAS_REQUESTS:
        return "perplexity", ""
    prompt = _RESEARCH_PROMPT.format(title=title, artist=artist)
    try:
        resp = _requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {_PERPLEXITY_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
                "temperature": 0.3,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return "perplexity", resp.json()["choices"][0]["message"]["content"]
        log.debug("Perplexity API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.debug("Perplexity query error: %s", exc)
    return "perplexity", ""


def research_track(title: str, artist: str) -> WebResearchResult:
    """
    Research a track using Google/DuckDuckGo + AI APIs (Grok, Claude, Gemini, Perplexity).

    All sources run concurrently. Missing API keys cause that source to be silently skipped.
    At least the DuckDuckGo fallback always runs when `requests` is available.
    """
    result = WebResearchResult()

    if not title and not artist:
        return result

    if not HAS_REQUESTS:
        log.warning("requests not installed — skipping web research")
        return result

    search_name = f"{artist} {title}".strip()

    # ── Concurrent fetch: Google + 4 AI sources ──────────────────────────
    def _do_google() -> None:
        source_label, urls = _query_google(search_name)
        keywords_all = [
            "bpm", "tempo", "key", "minor", "major",
            "chord", "progression", "harmony",
            "production", "sound design", "preset", "synth", "serum",
            "bass", "lead", "wavetable", "filter", "lfo", "sidechain",
        ]
        for url in urls:
            result.sources_consulted.append(url)
            html = _safe_fetch(url)
            if not html:
                continue
            snippets = _extract_text_snippets(html, keywords_all, max_snippets=5)
            result.raw_snippets.extend(snippets)
            _parse_snippets_into_result(snippets, url, result)

    def _do_ai(fn: Any) -> None:
        src, text = fn(title, artist)
        if text:
            result.ai_summaries[src] = text
            _parse_ai_response(text, f"ai:{src}", result)

    futures_map: dict[Any, str] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures_map[pool.submit(_do_google)] = "google"
        futures_map[pool.submit(_do_ai, _query_grok)] = "grok"
        futures_map[pool.submit(_do_ai, _query_claude)] = "claude"
        futures_map[pool.submit(_do_ai, _query_gemini)] = "gemini"
        futures_map[pool.submit(_do_ai, _query_perplexity)] = "perplexity"

        for future in as_completed(futures_map, timeout=45):
            src_name = futures_map[future]
            try:
                future.result()
                log.debug("Web research source '%s' completed", src_name)
            except Exception as exc:
                log.debug("Web research source '%s' failed: %s", src_name, exc)

    # ── Also run supplemental DuckDuckGo queries (BPM/chords/synths) ──────
    # Only if we didn't get rich AI summaries (saves time when keys are set)
    ai_count = len(result.ai_summaries)
    if ai_count < 2:
        supplemental_queries = [
            (f"{search_name} BPM key tempo",
             ["bpm", "tempo", "key", "minor", "major"]),
            (f"{search_name} chord progression chords",
             ["chord", "progression", "harmony", "chords"]),
            (f"{search_name} production breakdown sound design",
             ["production", "sound design", "preset", "synth", "serum", "bass"]),
        ]
        for query, keywords in supplemental_queries:
            urls = _search_web(query, max_results=2)
            for url in urls:
                if url in result.sources_consulted:
                    continue
                result.sources_consulted.append(url)
                html = _safe_fetch(url)
                if html:
                    snippets = _extract_text_snippets(html, keywords, max_snippets=4)
                    result.raw_snippets.extend(snippets)
                    _parse_snippets_into_result(snippets, url, result)

    # Deduplicate
    result.production_notes = list(dict.fromkeys(result.production_notes))[:10]
    result.synth_info = list(dict.fromkeys(result.synth_info))[:10]
    result.sample_pack_info = list(dict.fromkeys(result.sample_pack_info))[:5]

    sources_used = list(result.ai_summaries.keys())
    if result.sources_consulted:
        sources_used.append("web")
    log.info(
        "Web research for '%s': %d URLs, %d AI sources (%s)",
        search_name, len(result.sources_consulted), len(result.ai_summaries),
        ", ".join(sources_used) or "none",
    )

    return result


def _parse_snippets_into_result(
    snippets: list[str], source_url: str, result: WebResearchResult
) -> None:
    """Extract BPM / key / chords / genre from web-scraped text snippets."""
    for snippet in snippets:
        # BPM
        for bpm_str in re.findall(r"(\d{2,3})\s*(?:bpm|BPM|Bpm)", snippet):
            bpm_val = int(bpm_str)
            if 60 <= bpm_val <= 200:
                result.bpm_sources.append({"bpm": bpm_val, "source": source_url})

        # Key
        for key_root, key_mode in re.findall(
            r"\b([A-G][#b]?)\s*(minor|major|min|maj)\b", snippet, re.IGNORECASE
        ):
            mode = "minor" if "min" in key_mode.lower() else "major"
            result.key_sources.append({"key": f"{key_root} {mode}", "source": source_url})

        # Chord progressions
        for cm in re.findall(
            r"\b([A-G][#b]?m?(?:7|maj7|min7)?)\s*[-–—]\s*"
            r"([A-G][#b]?m?(?:7|maj7|min7)?)\s*[-–—]\s*"
            r"([A-G][#b]?m?(?:7|maj7|min7)?)",
            snippet,
        ):
            result.chord_progressions_found.append(
                ChordInfo(chords=list(cm), source="web_lookup", confidence=0.5)
            )

        lower = snippet.lower()
        if any(k in lower for k in ["production", "sound design", "how to", "tutorial", "breakdown"]):
            result.production_notes.append(snippet[:300])
        if any(k in lower for k in ["serum", "preset", "wavetable", "patch", "massive", "vital"]):
            result.synth_info.append(snippet[:300])
        if any(k in lower for k in ["sample pack", "splice", "samples"]):
            result.sample_pack_info.append(snippet[:300])
        for tag in ["dubstep", "riddim", "dnb", "trap", "edm", "bass music", "melodic", "tearout"]:
            if tag in lower and tag not in result.genre_tags:
                result.genre_tags.append(tag)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5: MAP EVERYTHING → SongDNA
# ═══════════════════════════════════════════════════════════════════════════


def _key_to_note_and_scale(key_str: str) -> tuple[str, str]:
    """Parse 'C# minor' → ('C#', 'minor')."""
    parts = key_str.strip().split()
    note = parts[0] if parts else "C"
    scale = parts[1] if len(parts) > 1 else "minor"
    return note, scale


def _map_to_song_dna(intake: IntakeResult) -> SongDNA:
    """
    Map all extracted data to a complete SongDNA.

    Priority: audio analysis > web research > defaults
    """
    adna = intake.audio_dna
    meta = intake.metadata
    web = intake.web_research

    # ── Key and scale ──
    detected_key = adna.harmonic.key or ""
    # Prefer web consensus if multiple sources agree
    if web.key_sources:
        from collections import Counter  # noqa: PLC0415

        key_votes = Counter(s["key"] for s in web.key_sources)
        web_key, web_count = key_votes.most_common(1)[0]
        # Use web key if: audio confidence is low, multiple sources agree,
        # or audio key detection failed entirely
        key_confidence = adna.harmonic.key_confidence
        if web_count >= 2 or not detected_key or key_confidence < 0.35:
            detected_key = web_key
        elif web_count >= 1 and key_confidence < 0.6:
            # Low audio confidence — web wins even with 1 source
            detected_key = web_key

    note, scale = _key_to_note_and_scale(detected_key or "C minor")

    # ── BPM ──
    bpm = adna.rhythm.bpm
    if web.bpm_sources:
        from collections import Counter  # noqa: PLC0415

        bpm_votes = Counter(s["bpm"] for s in web.bpm_sources)
        web_bpm, web_count = bpm_votes.most_common(1)[0]
        # Use web BPM if audio detection has low confidence or web agrees
        if (adna.rhythm.bpm_confidence < 0.5 and web_count >= 2) or abs(web_bpm - bpm) < 2:
            bpm = web_bpm

    bpm = int(round(bpm)) if bpm > 0 else 140

    # ── Root frequency ──
    note_freq_map = {
        "C": 32.70, "C#": 34.65, "Db": 34.65, "D": 36.71, "D#": 38.89,
        "Eb": 38.89, "E": 41.20, "F": 43.65, "F#": 46.25, "Gb": 46.25,
        "G": 49.00, "G#": 51.91, "Ab": 51.91, "A": 55.00, "A#": 58.27,
        "Bb": 58.27, "B": 61.74,
    }
    root_freq = note_freq_map.get(note, 32.70)

    # Refine root_freq using bass_note_histogram — the dominant bass note
    # in the harmonic analysis often reveals the true fundamental more accurately
    bass_hist = adna.harmonic.bass_note_histogram
    if bass_hist and len(bass_hist) == 12 and max(bass_hist) > 0:
        dominant_semi = bass_hist.index(max(bass_hist))
        # chromatic semitone index → freq (C1 = 32.70 Hz, each semi * 2^(1/12))
        _C1_HZ = 32.70
        hist_freq = round(_C1_HZ * (2 ** (dominant_semi / 12.0)), 2)
        # Only override if histogram dominant matches within 3 semitones of detected note
        if abs(dominant_semi - list(note_freq_map.keys()).index(note)
               if note in list(note_freq_map.keys()) else 99) <= 3:
            root_freq = hist_freq

    # ── Style from genre tags ──
    all_tags = list(meta.tags or []) + web.genre_tags
    all_tags_lower = [t.lower() for t in all_tags]
    if "riddim" in all_tags_lower:
        style = "riddim"
    elif "melodic" in all_tags_lower or "melodic dubstep" in all_tags_lower:
        style = "melodic"
    elif "tearout" in all_tags_lower:
        style = "tearout"
    elif "hybrid" in all_tags_lower:
        style = "hybrid"
    else:
        style = "dubstep"

    # ── Mood from style DNA ──
    mood_map = {
        (True, True): "aggressive",    # dark + high energy
        (True, False): "dark",          # dark + low energy
        (False, True): "euphoric",      # bright + high energy
        (False, False): "dreamy",       # bright + low energy
    }
    is_dark = adna.style.darkness > 0.5
    is_high_energy = adna.style.energy_level > 0.5
    mood = mood_map.get((is_dark, is_high_energy), "dark")

    # ── Drums DNA ──
    drums = DrumDNA()
    drums.pattern_swing = round(adna.rhythm.swing_ratio - 0.5, 3)  # 0.5 = straight
    drums.silence_gap_beats = 4
    if adna.bass.sidechain_pump_count > 0:
        drums.kick_sub_weight = min(1.0, adna.bass.sidechain_pump_count / 100.0)
    if adna.production.transient_sharpness > 0.7:
        drums.kick_sample_category = "heavy"
        drums.snare_sample_category = "metallic"
    elif adna.production.transient_sharpness < 0.3:
        drums.kick_sample_category = "clean"
        drums.snare_sample_category = "organic"
    drums.hat_density = 16 if adna.rhythm.onset_rate > 8 else 8
    # Aggression → kick punch and snare presence
    drums.kick_drive = round(min(0.95, 0.3 + adna.style.aggression * 0.65), 3)
    drums.kick_fm_depth = round(2.0 + adna.style.aggression * 5.0, 1)
    drums.snare_ott = round(min(0.8, adna.style.aggression * 0.55), 3)
    drums.snare_metallic = round(min(0.6, adna.style.aggression * 0.5), 3)
    # Groove strength → hat separation for humanization
    if adna.rhythm.groove_strength > 0.0:
        drums.hi_hat_separation_ms = round(10.0 + adna.rhythm.groove_strength * 20.0, 1)
    # Beat stability → humanize variance (unstable = looser hi-hat timing)
    if adna.rhythm.beat_stability > 0:
        drums.hi_hat_separation_ms = round(
            drums.hi_hat_separation_ms * (0.5 + adna.rhythm.beat_stability * 0.5), 1
        )
    # Onset regularity → hat density (irregular onsets → sparser pattern)
    if adna.rhythm.onset_regularity > 0 and adna.rhythm.onset_regularity < 0.4:
        drums.hat_density = 8  # sparse, irregular feel
    elif adna.rhythm.onset_regularity > 0.85:
        drums.hat_density = 32  # very tight, machine-gun hats
    # Rhythm complexity → snare variation and OTT tightness
    if adna.style.rhythm_complexity > 0.6:
        drums.snare_ott = round(min(0.9, drums.snare_ott + adna.style.rhythm_complexity * 0.25), 3)
        drums.snare_metallic = round(min(0.8, drums.snare_metallic + adna.style.rhythm_complexity * 0.2), 3)
    # Danceability → swing blend (high danceability pushes straight/locked groove)
    if adna.style.danceability > 0:
        # High danceability = less swing (tighter grid), low = more swing
        dance_swing_nudge = round((1.0 - adna.style.danceability) * 0.15, 3)
        drums.pattern_swing = round(max(-0.1, min(0.3, drums.pattern_swing + dance_swing_nudge)), 3)

    # ── Drums DNA — additional wiring ──
    # Bass fundamental → kick pitch (match sub frequency)
    if adna.bass.fundamental_hz > 20:
        drums.kick_pitch = round(max(30.0, min(80.0, adna.bass.fundamental_hz)), 1)

    # ── Bass DNA ──
    bass = BassDNA()
    bp = intake.bass_synth
    bass.distortion = round(bp.distortion_amount, 3)
    bass.filter_cutoff = round(bp.filter_cutoff_est, 3)
    bass.filter_resonance = round(bp.filter_resonance_est, 3)
    bass.sub_weight = round(adna.bass.sub_weight, 3)
    # Prefer direct wobble measurement over synth profile estimate
    _wobble_hz = adna.bass.wobble_rate_hz if adna.bass.wobble_rate_hz > 0 else bp.mod_rate_hz
    bass.lfo_rate = round(_wobble_hz, 2) if _wobble_hz > 0 else 2.5
    bass.lfo_depth = round(bp.mod_depth, 3)
    bass.wobble_lfo_shape = bp.mod_shape
    bass.wavefold_mix = round(min(1.0, bp.distortion_amount * 0.5), 3)
    # FM depth: combine synth profile inharmonicity + direct sound_design measurement
    sd = adna.sound_design
    _inharmonicity = max(bp.inharmonicity, sd.inharmonicity)  # take higher of both estimates
    bass.fm_depth = round(4.0 + _inharmonicity * 6, 2)
    # Odd/even harmonic ratio → refine FM feedback character (odd-dominant = more metallic FM)
    if sd.odd_even_ratio > 0:
        bass.fm_depth = round(bass.fm_depth * (0.8 + sd.odd_even_ratio * 0.4), 2)
    bass.mid_drive = round(adna.spectral.mid * 2, 3)
    # Classify bass type from spectral analysis
    if bp.mod_rate_hz > 2.0 and bp.mod_depth > 0.3:
        bass.primary_type = "wobble"
    elif bp.distortion_amount > 0.5:
        bass.primary_type = "neuro"
    elif bp.formant_presence > 0.3:
        bass.primary_type = "formant"
    else:
        bass.primary_type = "dist_fm"
    # Saturation from production DNA
    if adna.production.distortion_amount > 0.5:
        bass.saturation_type = "digital"
        bass.saturation_drive = round(adna.production.distortion_amount, 3)
    elif adna.production.distortion_amount > 0.2:
        bass.saturation_type = "tube"
        bass.saturation_drive = round(adna.production.distortion_amount, 3)
    # Riddim style
    if style == "riddim":
        bass.riddim_style = "heavy"
    # Gap ratio from density + onset rate: dense/fast tracks → tighter bass (less gap)
    _density = getattr(adna.style, 'density', 0.5)
    _onset_norm = min(1.0, getattr(adna.rhythm, 'onset_rate', 4.0) / 12.0)
    bass.riddim_gap_ratio = round(max(0.15, min(0.70, 1.0 - _density * 0.6 - _onset_norm * 0.3)), 3)

    # ── Extract bass rhythm pattern from analysis ──
    # Use onset rate + rhythm complexity to build bass_riff patterns
    _rhythm_complexity = getattr(adna.style, 'rhythm_complexity', 0.5)
    _onset_rate = getattr(adna.rhythm, 'onset_rate', 4.0)
    _swing = getattr(adna.rhythm, 'swing_ratio', 0.5)
    _bass_riff: list[list[tuple[int, float, float]]] = []

    if _rhythm_complexity > 0.6 and _onset_rate > 6.0:
        # Complex / fast → syncopated 16th patterns
        _bass_riff = [
            [(0, 0.0, 0.25), (0, 0.5, 0.25), (6, 0.75, 0.25),
             (0, 1.0, 0.25), (0, 1.5, 0.125), (0, 2.0, 0.25),
             (6, 2.75, 0.25), (0, 3.0, 0.25), (4, 3.5, 0.25)],
            [(0, 0.0, 0.25), (4, 0.5, 0.25), (0, 1.0, 0.5),
             (0, 2.0, 0.25), (6, 2.5, 0.25), (0, 3.0, 0.25),
             (0, 3.5, 0.125), (0, 3.75, 0.125)],
        ]
    elif _rhythm_complexity > 0.3:
        # Medium → 8th note patterns with occasional rests
        _bass_riff = [
            [(0, 0.0, 0.5), (0, 1.0, 0.5), (6, 2.0, 0.25),
             (0, 2.5, 0.5), (4, 3.0, 0.5), (0, 3.5, 0.25)],
            [(0, 0.0, 1.0), (0, 1.0, 0.5), (0, 2.0, 1.0),
             (0, 3.0, 0.5), (6, 3.5, 0.5)],
        ]
    else:
        # Simple → sustained / sparse
        _bass_riff = [
            [(0, 0.0, 2.0), (0, 2.0, 2.0)],
            [(0, 0.0, 1.0), (0, 1.0, 1.0), (4, 2.0, 1.0), (0, 3.0, 1.0)],
        ]

    # Apply swing to beat positions if detected
    if _swing > 0.55:
        for bar in _bass_riff:
            for i, (deg, pos, dur) in enumerate(bar):
                # Swing offbeat 8ths: push every other 8th note slightly late
                if (pos * 2) % 2 == 1:
                    bar[i] = (deg, round(pos + (_swing - 0.5) * 0.1, 3), dur)

    bass.bass_riff = _bass_riff

    # ── Bass DNA — additional reference wiring ──
    # Reference fundamental frequency for sub pitch tuning
    if adna.bass.fundamental_hz > 20:
        bass.reference_fundamental_hz = round(adna.bass.fundamental_hz, 2)
    # Harmonic ratio → saturation drive + FM character (more harmonics = dirtier)
    if adna.bass.harmonic_ratio > 0:
        bass.harmonic_ratio = round(adna.bass.harmonic_ratio, 3)
        bass.saturation_drive = round(
            max(bass.saturation_drive, min(0.9, adna.bass.harmonic_ratio * 0.6)), 3
        )
        bass.fm_depth = round(bass.fm_depth + adna.bass.harmonic_ratio * 2.0, 2)
    # Bass_weight (60-250Hz fraction) → refine mid_drive balance
    if adna.bass.bass_weight > 0:
        bass.mid_drive = round(
            max(0.2, min(1.0, bass.mid_drive * (0.5 + adna.bass.bass_weight))), 3
        )
    # Spectral kurtosis → filter resonance (peaky spectrum = more resonant bass)
    if adna.spectral.spectral_kurtosis > 0:
        bass.filter_resonance = round(
            min(0.95, bass.filter_resonance + adna.spectral.spectral_kurtosis * 0.1), 3
        )

    # ── Lead DNA ──
    lead = LeadDNA()
    lp = intake.lead_synth
    lead.brightness = round(adna.style.brightness, 3)
    # Spectral centroid → filter cutoff (direct measurement, more accurate than synth profile)
    if adna.spectral.centroid_hz > 0:
        # Log-scale normalize: 200Hz→0.1, 12kHz→1.0 (musical feel)
        import math as _math  # noqa: PLC0415
        lead.filter_cutoff = round(
            max(0.1, min(1.0, _math.log2(max(1.0, adna.spectral.centroid_hz) / 200.0)
                         / _math.log2(60.0))),  # log2(60) ≈ 5.9, maps 200–12000Hz to 0–1
            3,
        )
    else:
        lead.filter_cutoff = round(lp.filter_cutoff_est, 3)
    lead.filter_resonance = round(lp.filter_resonance_est, 3)
    lead.reverb_decay = round(adna.production.reverb_amount, 3)
    # Sound design → lead modulation character
    sd = adna.sound_design
    if sd.modulation_depth > 0.2:
        lead.fm_depth = round(2.0 + sd.modulation_depth * 6.0, 1)
    if sd.modulation_rate_hz > 0.0:
        lead.supersaw_detune = round(max(5.0, min(50.0, sd.modulation_rate_hz * 10.0)), 1)
    # Spectral movement → additional modulation depth boost
    if sd.spectral_movement > 0.3:
        lead.fm_depth = round(min(8.0, lead.fm_depth + sd.spectral_movement * 2.0), 1)
        lead.supersaw_detune = round(min(55.0, lead.supersaw_detune + sd.spectral_movement * 10.0), 1)
    # Estimate envelope from transient sharpness + decay_character
    _decay_multiplier = 1.0 + sd.decay_character  # 1.0–2.0x envelope length
    if adna.sound_design.attack_sharpness > 0.7:
        lead.attack_ms = 1.0
        lead.decay_ms = round(150.0 * _decay_multiplier, 0)
    elif adna.sound_design.attack_sharpness > 0.3:
        lead.attack_ms = 10.0
        lead.decay_ms = round(400.0 * _decay_multiplier, 0)
    else:
        lead.attack_ms = 50.0
        lead.decay_ms = round(800.0 * _decay_multiplier, 0)

    # ── Lead DNA — spectral/harmonic wiring ──
    # Bandwidth → supersaw cutoff (wider bandwidth = higher cutoff)
    if adna.spectral.bandwidth_hz > 0:
        lead.supersaw_cutoff = round(
            max(2000.0, min(12000.0, adna.spectral.bandwidth_hz * 1.5)), 0
        )
    # Spectral complexity → additive partial count
    if adna.spectral.spectral_complexity > 0:
        lead.additive_partials = max(4, min(64, adna.spectral.spectral_complexity))
    # High freq content → brightness refinement
    if adna.spectral.high_freq_content > 0:
        lead.brightness = round(
            min(1.0, lead.brightness * 0.7 + adna.spectral.high_freq_content * 0.3), 3
        )
    # Spectral spread → filter resonance (wider spread = less resonant)
    if adna.spectral.spectral_spread > 0:
        _spread_norm = min(1.0, adna.spectral.spectral_spread / 5000.0)
        lead.filter_resonance = round(
            max(0.05, lead.filter_resonance * (1.0 - _spread_norm * 0.4)), 3
        )
    # MFCC signature → additive rolloff character
    if adna.spectral.mfcc and len(adna.spectral.mfcc) >= 3:
        # MFCC[1] positive = more energy in higher frequencies (sawtooth-like)
        # MFCC[1] negative = more energy in fundamentals (square/pulse-like)
        if adna.spectral.mfcc[1] > 10:
            lead.additive_rolloff = "sawtooth"
        elif adna.spectral.mfcc[1] < -10:
            lead.additive_rolloff = "square"
        else:
            lead.additive_rolloff = "triangle"
    # Harmonic dissonance → FM tension + detuning intensity
    if adna.harmonic.dissonance > 0:
        lead.harmonic_dissonance = round(adna.harmonic.dissonance, 3)
        lead.fm_depth = round(
            min(8.0, lead.fm_depth + adna.harmonic.dissonance * 3.0), 1
        )
        lead.supersaw_detune = round(
            min(60.0, lead.supersaw_detune + adna.harmonic.dissonance * 15.0), 1
        )
    # Chroma entropy → chord voicing density (complex harmony = more chord notes)
    if adna.harmonic.chroma_entropy > 0:
        if adna.harmonic.chroma_entropy > 3.0:
            lead.chord_note_count = 4
        elif adna.harmonic.chroma_entropy > 2.0:
            lead.chord_note_count = 3
        else:
            lead.chord_note_count = 2

    # Map melody data
    mel = intake.melody
    if mel.notes:
        # ── Proper scale-degree mapping using detected key ──
        # Build semitone→degree lookup for the detected scale
        _scale_iv = _SCALE_INTERVALS.get(scale, _SCALE_INTERVALS["minor"])
        _semi_to_deg: dict[int, int] = {}
        for deg_idx, semi in enumerate(_scale_iv):
            _semi_to_deg[semi] = deg_idx
        # For semitones between scale tones, snap to nearest
        for semi in range(12):
            if semi not in _semi_to_deg:
                # Find closest scale tone
                best_d, best_deg = 99, 0
                for s, d in _semi_to_deg.items():
                    dist = min(abs(semi - s), 12 - abs(semi - s))
                    if dist < best_d:
                        best_d, best_deg = dist, d
                _semi_to_deg[semi] = best_deg

        # Key root as MIDI pitch class (0=C, 1=C#, ... 11=B)
        _key_pc = _NOTE_NAMES.index(note) if note in _NOTE_NAMES else 0

        # ── Group notes into multi-note phrases (bars) ──
        beats_per_sec = bpm / 60.0
        phrases: list[list[tuple[int, float, float, float]]] = []
        current_phrase: list[tuple[int, float, float, float]] = []
        phrase_start_s = mel.notes[0].get("start_s", 0.0) if mel.notes else 0.0

        for n in mel.notes:
            midi_note = n.get("midi", 60)
            start_s = n.get("start_s", 0.0)
            dur_s = n.get("duration_s", 0.25)
            vel = n.get("velocity", 0.8)

            # Convert MIDI pitch → scale degree relative to detected key
            semis_from_root = (midi_note - _key_pc) % 12
            degree = _semi_to_deg.get(semis_from_root, 0)

            # Convert time to beat position within the current bar
            beat_abs = (start_s - phrase_start_s) * beats_per_sec
            beat_pos = beat_abs % 4.0  # position within bar

            # Duration in beats
            dur_beats = min(4.0, dur_s * beats_per_sec)

            current_phrase.append((
                degree,
                round(beat_pos, 3),
                round(dur_beats, 3),
                round(min(1.0, vel), 3),
            ))

            # Split into phrases every 4 beats (1 bar)
            if beat_abs >= 4.0:
                if current_phrase:
                    phrases.append(current_phrase)
                current_phrase = []
                phrase_start_s = start_s

        # Don't forget the last phrase
        if current_phrase:
            phrases.append(current_phrase)

        if phrases:
            lead.melody_patterns = phrases[:8]  # type: ignore[assignment]
    lead.phrase_length = mel.phrase_length_bars

    # Arp parameters from rhythm complexity + aggression
    _rhythm_complexity = getattr(adna.style, 'rhythm_complexity', 0.5)
    if _rhythm_complexity > 0.70:
        lead.arp_subdivision = "1/32"
    elif _rhythm_complexity > 0.40:
        lead.arp_subdivision = "1/16"
    else:
        lead.arp_subdivision = "1/8"
    _aggression = getattr(adna.style, 'aggression', 0.5)
    if _aggression > 0.70:
        lead.arp_style = "updown"
    elif _aggression > 0.40:
        lead.arp_style = "up"
    else:
        lead.arp_style = "random"

    # Map chord progression
    if intake.chords.chords:
        # ── Proper chord → scale degree mapping using detected key ──
        _scale_iv = _SCALE_INTERVALS.get(scale, _SCALE_INTERVALS["minor"])
        # Build semitone → scale degree lookup for chord roots
        _chord_semi_to_deg: dict[int, int] = {}
        for deg_idx, semi in enumerate(_scale_iv):
            _chord_semi_to_deg[semi] = deg_idx
        # Snap unmapped semitones to nearest scale degree
        for semi in range(12):
            if semi not in _chord_semi_to_deg:
                best_d, best_deg = 99, 0
                for s, d in _chord_semi_to_deg.items():
                    dist = min(abs(semi - s), 12 - abs(semi - s))
                    if dist < best_d:
                        best_d, best_deg = dist, d
                _chord_semi_to_deg[semi] = best_deg

        _key_pc = _NOTE_NAMES.index(note) if note in _NOTE_NAMES else 0
        chord_degrees: list[int] = []
        for c in intake.chords.chords[:8]:
            # Parse chord root: strip quality suffixes (m, 7, maj, dim, aug, sus)
            root_name = c
            for suffix in ("m7", "maj7", "dim", "aug", "sus4", "sus2", "7", "m", "maj"):
                if root_name.endswith(suffix):
                    root_name = root_name[:-len(suffix)]
                    break
            if root_name in _NOTE_NAMES:
                semis_from_key = (_NOTE_NAMES.index(root_name) - _key_pc) % 12
                chord_degrees.append(_chord_semi_to_deg.get(semis_from_key, 0))
        if chord_degrees:
            lead.chord_progression = chord_degrees

    # ── Atmosphere DNA ──
    atmos = AtmosphereDNA()
    pp = intake.pad_synth
    atmos.reverb_decay = round(adna.production.reverb_amount * 5, 2)
    atmos.stereo_width = round(adna.stereo.width * 2, 2)
    atmos.pad_brightness = round(pp.filter_cutoff_est, 3)
    atmos.pad_attack_ms = 2000.0 if pp.mod_rate_hz < 1.0 else 500.0
    if adna.production.reverb_amount > 0.5:
        atmos.reverb_type = "hall"
    elif adna.production.reverb_amount > 0.3:
        atmos.reverb_type = "plate"
    else:
        atmos.reverb_type = "room"
    atmos.reverb_width = round(adna.stereo.width_high, 3)
    # Formant presence → pad/atmos vocal character
    if sd.formant_presence > 0.5:
        atmos.pad_type = "vocal"
        atmos.drone_movement = round(min(0.9, 0.3 + sd.formant_presence * 0.6), 3)
    elif sd.formant_presence > 0.3:
        atmos.pad_type = "shimmer"
    else:
        atmos.pad_type = "dark"
    # Noise content + spectral flatness → noise bed level and type
    _noise_level = round(sd.noise_content * 0.4 + adna.spectral.flatness * 0.3, 3)
    atmos.noise_bed_level = round(min(0.4, 0.05 + _noise_level), 3)
    if sd.noise_content > 0.5:
        atmos.noise_bed_type = "white"   # more harsh, dense hiss
    elif sd.noise_content > 0.2 or adna.spectral.flatness > 0.3:
        atmos.noise_bed_type = "pink"    # natural noise floor
    else:
        atmos.noise_bed_type = "pink"    # default clean

    # ── Atmosphere DNA — additional stereo/production wiring ──
    # Stereo width_mid → refine pad stereo width
    if adna.stereo.width_mid > 0:
        atmos.stereo_width = round(
            max(0.5, min(2.5, atmos.stereo_width * (0.5 + adna.stereo.width_mid)), ), 2
        )
    # Mono compatibility → clamp atmosphere width for mono safety
    if adna.stereo.mono_compat < 0.7:
        atmos.stereo_width = round(min(1.2, atmos.stereo_width), 2)
    # Production noise_floor → refine noise bed level
    if adna.production.noise_floor_db > -96.0:
        # Higher noise floor in reference → slightly higher noise bed
        _nf_norm = max(0.0, min(1.0, (adna.production.noise_floor_db + 60.0) / 30.0))
        atmos.noise_bed_level = round(
            max(atmos.noise_bed_level, min(0.35, _nf_norm * 0.25)), 3
        )

    # ── FX DNA ──
    fx = FxDNA()
    if adna.arrangement.drop_count > 0:
        fx.riser_intensity = round(
            min(1.0, adna.arrangement.buildup_effectiveness), 3
        )
        # transition_sharpness is a more direct measurement than intro_drop_contrast_db
        if adna.arrangement.transition_sharpness > 0:
            fx.impact_intensity = round(
                min(1.0, adna.arrangement.transition_sharpness), 3
            )
        else:
            fx.impact_intensity = round(
                min(1.0, abs(adna.arrangement.intro_drop_contrast_db) / 12.0), 3
            )
    fx.glitch_amount = round(sd.texture_density * 0.5, 3)
    # Spectral flux → stutter rate (high flux = fast movement = faster stutters)
    if adna.spectral.flux_mean > 0:
        # flux_mean range ~0.001–0.05; map to stutter rate 4–32 subdivisions
        _flux_norm = min(1.0, adna.spectral.flux_mean * 40.0)
        fx.stutter_rate = round(4.0 + _flux_norm * 28.0, 1)

    # ── Mix DNA ──
    mix = MixDNA()
    mix.target_lufs = round(adna.loudness.lufs_estimate, 1)
    mix.stereo_width = round(adna.stereo.width, 3)
    mix.compression_ratio = round(adna.production.compression_ratio, 2)
    mix.sidechain_depth = round(abs(adna.production.sidechain_depth_db) / 12.0, 3)
    mix.sidechain_attack_ms = 1.0
    mix.sidechain_release_ms = 100.0
    mix.sidechain_mode = "pump" if adna.production.sidechain_depth_db < -3 else "gentle"
    # EQ boosts: spectral balance + tilt correction + air
    _tilt = adna.spectral.tilt_db_per_oct  # negative = bass-heavy (normal dubstep)
    _tilt_low_corr = round(1.0 + max(0.0, -_tilt) / 8.0, 2)   # bass-heavy → lower boost needed
    _tilt_high_corr = round(1.0 + max(0.0, _tilt) / 8.0, 2)    # air-heavy → raise boost
    mix.eq_low_boost = round(max(0.5, min(3.0, (1.0 + adna.spectral.sub * 2) * _tilt_low_corr)), 2)
    _air_bonus = round(adna.mixing.air_ratio * 1.5, 2) if adna.mixing.air_ratio > 0 else 0.0
    mix.eq_high_boost = round(max(0.5, min(4.0, (1.0 + adna.spectral.high * 3) * _tilt_high_corr + _air_bonus)), 2)
    # Per-element gain staging — spectral balance + bass_dominance weighting
    _bass_dom = adna.style.bass_dominance  # 0–1; higher = more sub/bass emphasis
    mix.sub_gain_db = round((adna.spectral.sub - 0.15) * 12 + _bass_dom * 2.0, 1)
    mix.bass_gain_db = round((adna.spectral.bass - 0.25) * 12 + _bass_dom * 1.0, 1)
    mix.lead_gain_db = round((adna.spectral.mid - 0.15) * 12 - _bass_dom * 1.5, 1)
    mix.pad_gain_db = round((adna.spectral.high_mid - 0.1) * 6, 1)
    # Separation score → spread lead/pad gain further from bass for clarity
    if adna.mixing.separation_score > 0.6:
        mix.lead_gain_db = round(mix.lead_gain_db + adna.mixing.separation_score * 1.5, 1)
        mix.pad_gain_db = round(mix.pad_gain_db + adna.mixing.separation_score * 0.5, 1)
    # Mastering ceiling: prefer true_peak measurement, fall back to headroom
    mast = adna.mastering
    mx = adna.mixing
    if mast.true_peak_db > -96.0:
        # Use true peak with a small safety margin
        mix.ceiling_db = round(max(-6.0, min(-0.1, mast.true_peak_db + 0.2)), 1)
    elif mx.headroom_db < 0:
        mix.ceiling_db = round(max(-6.0, mx.headroom_db - 0.1), 1)
    # Master drive from saturation reference
    if mast.saturation_amount > 0:
        mix.master_drive = round(min(0.9, 0.1 + mast.saturation_amount * 0.8), 3)
    # Reference EQ curve from mixing analysis
    if mx.eq_curve:
        mix.reference_eq_curve = [round(v, 3) for v in mx.eq_curve]
    # EQ frequency targets from mix quality
    if mx.mud_ratio > 0.3:
        mix.eq_low_freq = round(min(200.0, 80.0 + mx.mud_ratio * 160.0), 0)
    if mx.harshness_ratio > 0.3:
        mix.eq_high_freq = round(max(6000.0, 10000.0 - mx.harshness_ratio * 3000.0), 0)

    # ── Mix DNA — loudness/stereo/production wiring ──
    # Loudness: peak_db → refine ceiling (use actual peak if available and true_peak wasn't)
    if mix.ceiling_db == -0.3 and adna.loudness.peak_db > -96.0:
        mix.ceiling_db = round(max(-6.0, min(-0.1, adna.loudness.peak_db + 0.3)), 1)
    # RMS + A-weighted → cross-check target LUFS
    if adna.loudness.a_weighted_rms_db > -96.0 and adna.loudness.lufs_estimate <= -96.0:
        # LUFS approximation from A-weighted RMS when LUFS isn't available
        mix.target_lufs = round(adna.loudness.a_weighted_rms_db, 1)
    # Dynamic range → refine compression ratio (narrow DR = more compressed ref)
    if adna.loudness.dynamic_range_db > 0:
        # Map 3dB DR → ratio 8:1, 20dB DR → ratio 2:1
        _dr_ratio = round(max(1.5, min(10.0, 10.0 - adna.loudness.dynamic_range_db * 0.4)), 1)
        mix.compression_ratio = _dr_ratio
    # Crest factor → compression threshold (low crest = already squashed)
    if adna.loudness.crest_factor_db > 0:
        mix.compression_threshold = round(
            max(-24.0, min(-3.0, -6.0 - adna.loudness.crest_factor_db)), 1
        )
    # Loudness range → humanize strength (higher LRA = more dynamic = more humanization)
    if adna.loudness.loudness_range_db > 0:
        _lra_norm = min(1.0, adna.loudness.loudness_range_db / 12.0)
        mix.humanize_strength = round(max(0.05, min(0.4, _lra_norm * 0.35)), 3)
    # Stereo: correlation → safety clamp on stereo width
    if adna.stereo.correlation < 0.5:
        # Low correlation = wide/anti-phase reference → keep our mix wider
        mix.stereo_width = round(min(1.5, mix.stereo_width * 1.2), 3)
    # Mono compatibility + per-band stereo width
    mix.mono_compatibility = round(adna.stereo.mono_compat, 3)
    mix.stereo_width_low = round(adna.stereo.width_low, 3)
    mix.stereo_width_mid = round(adna.stereo.width_mid, 3)
    # If bass is wide in reference, keep our bass wider; if mono, mono it
    if adna.stereo.width_low > 0.2:
        mix.sub_gain_db = round(mix.sub_gain_db - 0.5, 1)  # slight cut to compensate width
    # Presence peak → EQ high freq target refinement
    if adna.production.presence_peak_hz > 2000:
        mix.eq_high_freq = round(
            max(5000.0, min(12000.0, adna.production.presence_peak_hz * 1.2)), 0
        )

    # ── Arrangement ──
    arr_dna = adna.arrangement
    sections: list[ArrangementSection] = []
    if arr_dna.section_labels:
        n_sects = len(arr_dna.section_labels)
        bars_per_section = max(1, int(round(
            (adna.arrangement.duration_s * bpm / 60.0 / 4.0) / n_sects
        )))
        # Interpolate energy_curve (20 pts) to per-section energy values
        _ecurve = arr_dna.energy_curve or []
        _tcurve = arr_dna.tension_curve or []
        for i, label in enumerate(arr_dna.section_labels):
            if _ecurve:
                curve_pos = int(i / max(1, n_sects - 1) * (len(_ecurve) - 1))
                _energy_val = _ecurve[min(curve_pos, len(_ecurve) - 1)]
            else:
                _energy_val = 0.5
            # Blend tension_curve for richer section dynamics (tension drives drops/builds)
            if _tcurve:
                _t_pos = int(i / max(1, n_sects - 1) * (len(_tcurve) - 1))
                _tension_val = _tcurve[min(_t_pos, len(_tcurve) - 1)]
                sect_energy = round(0.65 * _energy_val + 0.35 * _tension_val, 2)
            else:
                sect_energy = round(_energy_val, 2)
            sections.append(ArrangementSection(
                name=label,
                bars=bars_per_section,
                energy=sect_energy,
            ))

    total_bars = sum(s.bars for s in sections) if sections else 64

    # ── Arrangement — loudest/quietest section energy adjustment ──
    if sections and len(sections) > 1:
        _loud_idx = arr_dna.loudest_section_idx
        _quiet_idx = arr_dna.quietest_section_idx
        if 0 <= _loud_idx < len(sections):
            sections[_loud_idx].energy = round(min(1.0, sections[_loud_idx].energy * 1.15), 2)
        if 0 <= _quiet_idx < len(sections):
            sections[_quiet_idx].energy = round(max(0.05, sections[_quiet_idx].energy * 0.75), 2)

    # Map energy_arc_type → arrangement_template_type
    _arc_map = {
        "build-drop": "standard",
        "plateau": "drone",
        "chaotic": "experimental",
        "decay": "cinematic",
    }
    _arc_type = _arc_map.get(arr_dna.energy_arc_type.lower(), "") if arr_dna.energy_arc_type else ""

    # ── Build final SongDNA ──
    title = meta.title or "Reference Track"
    artist = meta.artist or "Unknown"

    # Compose enriched notes — wire density, quality, web context to notes
    # so _configure_stem_specs() and other phase_one consumers can read them
    _notes_parts = [f"Reference intake from: {meta.url or intake.local_path}"]
    _notes_parts.append(f"density={adna.style.density:.2f}")
    _notes_parts.append(f"danceability={adna.style.danceability:.2f}")
    _notes_parts.append(f"bass_dominance={adna.style.bass_dominance:.2f}")
    _notes_parts.append(f"section_diversity={arr_dna.section_diversity:.2f}")
    _notes_parts.append(f"breakdown_depth_db={arr_dna.breakdown_depth_db:.1f}")
    if adna.quality.overall > 0:
        _notes_parts.append(f"quality_score={adna.quality.overall:.0f}/100")
    # Web AI production context — aggregate the most useful snippets
    if web.production_notes or web.synth_info:
        _prod_ctx = " | ".join((web.production_notes or [])[:2] + (web.synth_info or [])[:2])
        if _prod_ctx:
            _notes_parts.append(f"web_context: {_prod_ctx[:280]}")
    # Store AI summary production snippets (Grok/Claude/Gemini/Perplexity)
    if web.ai_summaries:
        _ai_keys = [k for k in ("grok", "claude", "gemini", "perplexity") if web.ai_summaries.get(k)]
        if _ai_keys:
            # Extract the first sentence of each AI summary as context
            _ai_snippets = []
            for k in _ai_keys[:2]:  # max 2 AI sources to avoid bloating notes
                _summary = web.ai_summaries[k]
                _first_sent = _summary.split(".")[0][:120].strip()
                if _first_sent:
                    _ai_snippets.append(f"{k}: {_first_sent}")
            if _ai_snippets:
                _notes_parts.append("ai_ctx: " + " / ".join(_ai_snippets))

    dna = SongDNA(  # type: ignore[call-arg]
        name=f"{artist} - {title}",
        style=style,
        theme=f"emulation of {title}",
        mood_name=mood,
        tags=list(set(all_tags[:10])),
        seed=int(hashlib.sha256(title.encode()).hexdigest()[:8], 16),
        key=note,
        scale=scale,
        bpm=bpm,
        root_freq=root_freq,
        tuning_hz=440.0,
        energy=round(adna.style.energy_level, 3),
        arrangement=sections,
        total_bars=total_bars,
        arrangement_template_type=_arc_type,
        drums=drums,
        bass=bass,
        lead=lead,
        atmosphere=atmos,
        fx=fx,
        mix=mix,
        notes=" | ".join(_notes_parts),
    )

    return dna


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════


def intake_from_url(url: str,
                    research: bool = True) -> IntakeResult:
    """
    Run the full intake pipeline on a URL (SoundCloud, YouTube, etc.).

    Downloads audio via yt-dlp, then runs the full analysis pipeline.

    Args:
        url: SoundCloud/YouTube/etc URL
        research: Whether to do internet research

    Returns:
        IntakeResult with all analysis + SongDNA populated
    """
    result = IntakeResult(url=url)

    # ── 1. Download ──
    wav_path = download_audio(url)
    result.local_path = str(wav_path)

    # ── 2. Load metadata from yt-dlp sidecar ──
    result.metadata = _load_ytdlp_metadata(wav_path)
    result.metadata.url = url

    # ── 3–9. Shared analysis pipeline ──
    return _run_analysis(result, wav_path, research=research)


def _run_analysis(result: IntakeResult, wav_path: Path,
                  research: bool = False) -> IntakeResult:
    """Shared analysis pipeline for both URL and file intake.

    Pipeline order (ML-enhanced when available):
    1. Reference analyzer (spectral DNA — 13 categories)
    2. Demucs stem separation (if available) → per-stem analysis
    3. Beat/onset tracking (madmom or native)
    4. Audio→MIDI transcription (Basic Pitch or native spectral)
    5. Chord detection (chromagram + CHORDONOMICON DB)
    6. Synth character analysis
    7. Internet research (optional)
    8. Map → SongDNA
    """
    # ── 1. Audio DNA (reference analyzer) ──
    log.info("Running reference analysis on %s ...", wav_path.name)
    result.audio_dna = analyze_reference(str(wav_path))
    result.metadata.duration_s = result.audio_dna.arrangement.duration_s

    samples, sr = _load_wav_samples(wav_path)
    bpm = result.audio_dna.rhythm.bpm or 140.0
    key = result.audio_dna.harmonic.key or ""

    # ── 2. Demucs stem separation (ML) ──
    bass_samples = None
    lead_samples = None
    if HAS_STEM_SEP and HAS_DEMUCS:
        try:
            log.info("Running Demucs stem separation ...")
            stem_dir = wav_path.parent / "stems"
            stem_paths = _demucs_to_files(str(wav_path), output_dir=str(stem_dir))
            result.stem_paths = {k: str(v) for k, v in stem_paths.items()}
            log.info("Demucs: separated %d stems → %s", len(stem_paths), stem_dir)

            # Load bass/lead stems for targeted analysis
            for stem_name, stem_path in stem_paths.items():
                if stem_name.lower() == "bass" and Path(stem_path).exists():
                    bass_samples, _ = _load_wav_samples(Path(stem_path))
                elif stem_name.lower() == "other" and Path(stem_path).exists():
                    lead_samples, _ = _load_wav_samples(Path(stem_path))
        except Exception as e:
            log.warning("Demucs separation failed (%s), continuing with full mix", e)

    # ── 3. Beat tracking (madmom or native) ──
    if HAS_BEAT_TRACKER:
        try:
            log.info("Running beat/onset tracking ...")
            beat_result = _track_beats(audio_path=str(wav_path), samples=samples, sr=sr)
            result.beat_grid = beat_result.to_dict()

            # Use ML beat-tracked BPM if confident
            if beat_result.confidence > 0.5 and beat_result.bpm > 0:
                bpm_diff = abs(beat_result.bpm - bpm)
                if bpm_diff > 5 or bpm == 140.0:
                    log.info("Beat tracker BPM: %.1f (was %.1f, conf=%.2f)",
                             beat_result.bpm, bpm, beat_result.confidence)
                    bpm = beat_result.bpm
        except Exception as e:
            log.warning("Beat tracking failed (%s)", e)

    # ── 4. Audio→MIDI transcription (Basic Pitch or native) ──
    log.info("Running deep extraction (chords, melody, synth) ...")

    # Melody extraction: prefer separated lead stem → Basic Pitch → native
    if HAS_AUDIO_TO_MIDI:
        try:
            # Transcribe melody from lead stem (or full mix)
            melody_samples = lead_samples if lead_samples is not None else samples
            melody_result = _bp_transcribe_melody(melody_samples, sr, bpm=bpm)
            # Convert to MelodyInfo format
            result.melody = _transcription_to_melody(melody_result, bpm)
            result.lead_midi = melody_result.to_melody_info_notes()[:64]
            log.info("Audio→MIDI (melody): %d notes via %s",
                     melody_result.note_count, melody_result.backend)

            # Transcribe bass line
            bass_src = bass_samples if bass_samples is not None else samples
            bass_result = _bp_transcribe_bass(bass_src, sr)
            result.bass_midi = bass_result.to_melody_info_notes()[:32]
            log.info("Audio→MIDI (bass): %d notes via %s",
                     bass_result.note_count, bass_result.backend)
        except Exception as e:
            log.warning("Audio→MIDI failed (%s), using spectral fallback", e)
            result.melody = _extract_melody_contour(samples, sr, bpm=bpm)
    else:
        result.melody = _extract_melody_contour(samples, sr, bpm=bpm)

    # ── 5. Chord detection ──
    result.chords = extract_chords(samples, sr, bpm=bpm, key=key)

    # Enhance with CHORDONOMICON DB suggestions
    if HAS_CHORD_DB:
        try:
            suggestions = _query_chord_db(
                genre="dubstep",
                energy_min=0.5,
                max_results=5,
            )
            result.chord_db_suggestions = [s.to_dict() for s in suggestions]

            # If audio chord detection is low-confidence, use DB suggestion
            if result.chords.confidence < 0.4 and suggestions:
                best = suggestions[0]
                db_chords = best.to_chords(
                    key=key.split()[0] if key else "C",
                    scale="minor" if "minor" in key.lower() else "major",
                )
                log.info("Low chord confidence (%.2f), using DB: %s → %s",
                         result.chords.confidence, best.name, db_chords)
                result.chords = ChordInfo(
                    chords=db_chords,
                    progression_roman=best.roman,
                    key=key,
                    scale="minor" if "minor" in key.lower() else "major",
                    source="chord_db",
                    confidence=0.6,
                )
        except Exception as e:
            log.warning("Chord DB query failed: %s", e)

    # ── 6. Synth character analysis ──
    # Use separated stems if available for cleaner analysis
    bass_src = bass_samples if bass_samples is not None else samples
    lead_src = lead_samples if lead_samples is not None else samples

    result.bass_synth = _analyze_synth_character(
        bass_src, sr, freq_range=(30.0, 500.0), layer_type="bass"
    )
    result.lead_synth = _analyze_synth_character(
        lead_src, sr, freq_range=(200.0, 8000.0), layer_type="lead"
    )
    result.pad_synth = _analyze_synth_character(
        samples, sr, freq_range=(100.0, 12000.0), layer_type="pad"
    )

    # ── 7. Internet research (URL intake only) ──
    if research:
        log.info("Researching track online ...")
        result.web_research = research_track(
            result.metadata.title, result.metadata.artist
        )
        if (result.chords.confidence < 0.5
                and result.web_research.chord_progressions_found):
            web_chords = result.web_research.chord_progressions_found[0]
            result.chords = ChordInfo(
                chords=web_chords.chords or result.chords.chords,
                progression_roman=(web_chords.progression_roman
                                   or result.chords.progression_roman),
                key=result.chords.key,
                scale=result.chords.scale,
                source="combined",
                confidence=max(result.chords.confidence,
                               web_chords.confidence),
            )

    # ── 8. Map to SongDNA ──
    log.info("Mapping to SongDNA ...")
    result.song_dna = _map_to_song_dna(result)

    log.info("Intake complete: %s → %d BPM, %s, style=%s",
             result.metadata.title, result.song_dna.bpm,
             result.song_dna.key + " " + result.song_dna.scale,
             result.song_dna.style)

    return result


def _transcription_to_melody(tr: 'TranscriptionResult',
                             bpm: float = 140.0) -> MelodyInfo:
    """Convert TranscriptionResult to MelodyInfo for backward compatibility."""
    notes = tr.to_melody_info_notes()

    # Determine contour
    if len(notes) >= 4:
        pitches = [n["midi"] for n in notes[:16]]
        diffs = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        if avg_diff > 1:
            contour = "ascending"
        elif avg_diff < -1:
            contour = "descending"
        elif max(pitches) - min(pitches) > 12:
            contour = "arch"
        elif max(pitches) - min(pitches) < 3:
            contour = "flat"
        else:
            contour = "complex"
    else:
        contour = "flat"

    # Estimate phrase length
    beats_per_sec = bpm / 60.0
    if notes and len(notes) > 1:
        total_dur = notes[-1]["start_s"] - notes[0]["start_s"]
        bars = total_dur * beats_per_sec / 4.0
        phrase_bars = max(1, min(16, int(round(bars / max(1, len(notes) // 8)))))
    else:
        phrase_bars = 4

    return MelodyInfo(
        notes=notes[:64],
        contour=contour,
        phrase_length_bars=phrase_bars,
        source=f"audio_to_midi_{tr.backend}",
    )


def intake_from_file(path: str | Path) -> IntakeResult:
    """
    Run the full intake pipeline on a local audio file.

    Args:
        path: Path to a WAV (or ffmpeg-convertible) file.

    Returns:
        IntakeResult with audio DNA + SongDNA populated (no web research).
    """
    wav_path = _ensure_wav(Path(path))
    if not wav_path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    result = IntakeResult(local_path=str(wav_path))
    result.metadata = TrackMetadata(title=wav_path.stem)

    return _run_analysis(result, wav_path, research=False)


def save_intake_report(result: IntakeResult,
                       output_dir: Path | None = None) -> Path:
    """Save intake result as JSON report."""
    out_dir = output_dir or _OUTPUT_DIR / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    name = result.metadata.title or "unknown"
    safe_name = re.sub(r"[^\w\-]", "_", name)[:60]
    path = out_dir / f"intake_{safe_name}.json"

    data = result.to_dict()

    # Make numpy arrays JSON-serializable
    def _convert(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        return obj

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_convert)

    log.info("Report saved: %s", path)
    return path
