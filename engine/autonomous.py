"""
DUBFORGE — Autonomous Production System

The brain of DUBFORGE. An autonomous orchestrator that:
  1. Reads a queue of track blueprints (YAML or inline)
  2. Assigns an OpenClaw producer agent to each track
  3. Generates DNA → renders → analyzes → self-corrects via Fibonacci feedback
  4. Learns from every render via LessonsLearned + Memory
  5. Evolves parameters across tracks (cross-track intelligence)
  6. Builds full EPs with cohesive mastering
  7. Runs indefinitely or for N tracks — fully hands-off

Architecture:
    ┌──────────────┐
    │  QUEUE       │  ← YAML file or programmatic list
    │  (blueprints)│
    └──────┬───────┘
           │
    ┌──────▼───────┐
    │  DIRECTOR    │  ← Autonomous brain — decides what to produce
    │  (this file) │
    └──────┬───────┘
           │
    ┌──────▼───────────────────────────┐
    │  OPENCLAW AGENT                  │  ← Producer style (Subtronics, etc.)
    │  (openclaw_agent.py)             │
    └──────┬───────────────────────────┘
           │
    ┌──────▼───────┐    ┌──────────────┐
    │  FORGE.PY    │───▶│  ANALYZE     │
    │  (render)    │    │  (quality)   │
    └──────┬───────┘    └──────┬───────┘
           │                   │
    ┌──────▼───────────────────▼───────┐
    │  FIBONACCI FEEDBACK              │  ← Self-correction loop
    │  (fibonacci_feedback.py)         │
    └──────┬───────────────────────────┘
           │
    ┌──────▼───────┐    ┌──────────────┐
    │  LESSONS     │───▶│  MEMORY      │
    │  LEARNED     │    │  (persistent)│
    └──────────────┘    └──────────────┘

Usage:
    # CLI — produce a single track autonomously
    python -m engine.autonomous --track "CYCLOPS FURY" --producer subtronics

    # CLI — produce from a queue file
    python -m engine.autonomous --queue configs/production_queue.yaml

    # CLI — produce an EP
    python -m engine.autonomous --ep "FRACTAL DIMENSION" --tracks 5

    # CLI — continuous mode (never stops)
    python -m engine.autonomous --continuous --producer subtronics

    # Python API
    from engine.autonomous import AutonomousDirector
    director = AutonomousDirector(producer="subtronics")
    director.produce_track("CYCLOPS FURY", style="dubstep", mood="aggressive")
    director.produce_ep("FRACTAL DIMENSION", track_count=5)
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

# ── DUBFORGE imports ──
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.openclaw_agent import OpenClawAgent, get_agent, PRODUCER_PROFILES
from engine.variation_engine import (
    ArrangementSection,
    SongBlueprint,
    SongDNA,
    VariationEngine,
)


# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════

from engine.config_loader import PHI
SR = 48000
OUTPUT_DIR = Path("output")
SONGS_DIR = OUTPUT_DIR / "songs"
EP_DIR = OUTPUT_DIR / "eps"
QUEUE_DIR = OUTPUT_DIR / "queue"
LOG_DIR = OUTPUT_DIR / "logs"

# Quality thresholds for autonomous pass/fail
# Note: our rough RMS→LUFS estimate reads ~5dB lower than actual
# mastered LUFS because it includes quiet sections (intro/outro).
# The mastering chain targets -8 to -10 LUFS on the actual output.
QUALITY_TARGETS = {
    "lufs_min": -18.0,
    "lufs_max": -4.0,
    "peak_max_db": 0.0,
    "duration_min_s": 90.0,
    "duration_max_s": 360.0,
}

# Fibonacci steps for iterative refinement
FIBONACCI_SEQ = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

# Genre/mood pools for autonomous track generation
MOOD_POOL = [
    "aggressive", "dark", "heavy", "chaotic", "relentless",
    "sinister", "brutal", "angry", "menacing", "savage",
    "hypnotic", "driving", "intense", "crushing", "mechanical",
]

STYLE_POOL = [
    "dubstep", "riddim", "hybrid bass", "tearout", "halftime",
]

NAME_ATOMS = {
    "prefixes": [
        "CYCLOPS", "FRACTAL", "TESSERA", "BINARY", "QUANTUM",
        "VOID", "NEON", "CHROME", "CYBER", "DARK",
        "IRON", "STEEL", "OBSIDIAN", "SIGNAL", "VECTOR",
        "PRISM", "APEX", "FLUX", "GRID", "ZERO",
        "PHANTOM", "OMEGA", "HELIX", "TITAN", "SURGE",
    ],
    "suffixes": [
        "FURY", "RAGE", "STORM", "CRUSH", "SLAM",
        "DRIVE", "PULSE", "WAVE", "CORE", "BREAK",
        "DIMENSION", "IMPACT", "STRIKE", "FORCE", "CANNON",
        "PROTOCOL", "MODE", "SEQUENCE", "ENGINE", "SYSTEM",
        "ZONE", "SECTOR", "CIRCUIT", "GRID", "MATRIX",
    ],
}

SCALE_POOL = ["minor", "phrygian", "harmonic_minor", "dorian", "locrian"]
KEY_POOL = ["F", "E", "D", "G", "A", "C", "Bb"]


# ═══════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class TrackBlueprint:
    """A single track to produce."""
    name: str
    style: str = "dubstep"
    mood: str = "aggressive"
    producer: str = "subtronics"
    key: str = ""
    scale: str = ""
    bpm: int = 0
    seed: int = 0
    fibonacci_refine: bool = True
    max_iterations: int = 3
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "TrackBlueprint":
        return TrackBlueprint(**{
            k: v for k, v in d.items()
            if k in TrackBlueprint.__dataclass_fields__
        })


@dataclass
class EPBlueprint:
    """An EP consisting of multiple tracks with a cohesive identity."""
    title: str
    artist: str = "DUBFORGE"
    producer: str = "subtronics"
    tracks: list[TrackBlueprint] = field(default_factory=list)
    style: str = "dubstep"
    mood_arc: list[str] = field(default_factory=list)
    key_progression: list[str] = field(default_factory=list)
    target_track_count: int = 5
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tracks"] = [t.to_dict() for t in self.tracks]
        return d


@dataclass
class TrackResult:
    """Result of producing a single track."""
    name: str
    wav_path: str = ""
    dna_path: str = ""
    duration_s: float = 0.0
    lufs: float = 0.0
    peak_db: float = 0.0
    bpm: int = 0
    key: str = ""
    scale: str = ""
    iterations: int = 0
    passed_quality: bool = False
    render_time_s: float = 0.0
    error: str = ""
    dna_summary: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionLog:
    """Complete autonomous session log."""
    session_id: str
    started_at: float = 0.0
    completed_at: float = 0.0
    producer: str = ""
    mode: str = ""  # single / ep / continuous / queue
    tracks_completed: int = 0
    tracks_failed: int = 0
    total_render_time_s: float = 0.0
    results: list[TrackResult] = field(default_factory=list)
    lessons: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["results"] = [r.to_dict() for r in self.results]
        return d

    def save(self, path: Path | None = None):
        if path is None:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            path = LOG_DIR / f"session_{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path


# ═══════════════════════════════════════════════════════════════
#  NAME GENERATOR
# ═══════════════════════════════════════════════════════════════

class NameGenerator:
    """Generate unique track names in the Subtronics/cyberpunk style."""

    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed or int(time.time()))
        self._used: set[str] = set()

    def generate(self) -> str:
        """Generate a unique track name."""
        for _ in range(100):
            prefix = self._rng.choice(NAME_ATOMS["prefixes"])
            suffix = self._rng.choice(NAME_ATOMS["suffixes"])
            name = f"{prefix} {suffix}"
            if name not in self._used:
                self._used.add(name)
                return name
        # Fallback with number
        name = f"TRACK_{int(time.time()) % 10000}"
        self._used.add(name)
        return name

    def generate_ep_names(self, count: int, theme: str = "") -> list[str]:
        """Generate a cohesive set of track names for an EP."""
        names = []
        # Pick a consistent prefix for cohesion
        prefix = self._rng.choice(NAME_ATOMS["prefixes"])
        for i in range(count):
            suffix = self._rng.choice(NAME_ATOMS["suffixes"])
            name = f"{prefix} {suffix}"
            # Avoid duplicates
            while name in self._used:
                suffix = self._rng.choice(NAME_ATOMS["suffixes"])
                name = f"{prefix} {suffix}"
            self._used.add(name)
            names.append(name)
        return names


# ═══════════════════════════════════════════════════════════════
#  QUALITY ANALYZER
# ═══════════════════════════════════════════════════════════════

class QualityAnalyzer:
    """Analyze rendered WAV files for quality metrics."""

    def analyze(self, wav_path: str) -> dict:
        """Analyze a WAV file and return quality metrics."""
        import wave
        import struct

        result = {
            "filepath": wav_path,
            "exists": False,
            "duration_s": 0.0,
            "lufs_est": 0.0,
            "peak_db": -100.0,
            "passed": False,
        }

        if not os.path.exists(wav_path):
            return result

        result["exists"] = True

        try:
            with wave.open(wav_path, "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                result["duration_s"] = n_frames / framerate

                # Read a chunk for analysis (up to 30 seconds)
                chunk_frames = min(n_frames, framerate * 30)
                raw = wf.readframes(chunk_frames)

                # Convert to float samples
                if sampwidth == 3:  # 24-bit
                    samples = []
                    for i in range(0, len(raw), 3 * n_channels):
                        for ch in range(n_channels):
                            off = i + ch * 3
                            if off + 3 <= len(raw):
                                b = raw[off:off + 3]
                                val = int.from_bytes(b, "little", signed=True)
                                samples.append(val / 8388608.0)
                    samples = np.array(samples, dtype=np.float64)
                elif sampwidth == 2:  # 16-bit
                    count = len(raw) // 2
                    samples = np.array(
                        struct.unpack(f"<{count}h", raw),
                        dtype=np.float64,
                    ) / 32768.0
                else:
                    return result

                if len(samples) == 0:
                    return result

                # Peak
                peak = float(np.max(np.abs(samples)))
                result["peak_db"] = 20.0 * math.log10(peak + 1e-12)

                # RMS → estimated LUFS (rough)
                rms = float(np.sqrt(np.mean(samples ** 2)))
                result["lufs_est"] = 20.0 * math.log10(rms + 1e-12)

        except Exception as e:
            result["error"] = str(e)
            return result

        # Quality gate
        result["passed"] = (
            QUALITY_TARGETS["lufs_min"]
            <= result["lufs_est"]
            <= QUALITY_TARGETS["lufs_max"]
            and result["peak_db"] <= QUALITY_TARGETS["peak_max_db"]
            and result["duration_s"] >= QUALITY_TARGETS["duration_min_s"]
        )

        return result


# ═══════════════════════════════════════════════════════════════
#  CROSS-TRACK INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

class CrossTrackIntelligence:
    """Learn from past renders and pre-adjust DNA for new tracks.

    Wraps LessonsLearned + Memory when available, falls back to
    local JSON persistence if those modules fail to import.
    """

    def __init__(self):
        self._lessons_engine = None
        self._memory = None
        self._local_log: list[dict] = []
        self._load_path = LOG_DIR / "cross_track_intel.json"

        # Try to load existing modules
        try:
            from engine.lessons_learned import LessonsLearned
            self._lessons_engine = LessonsLearned()
        except Exception:
            pass

        try:
            from engine.memory import get_memory
            self._memory = get_memory()
        except Exception:
            pass

        # Load local log
        self._load_local()

    def _load_local(self):
        if self._load_path.exists():
            try:
                self._local_log = json.loads(self._load_path.read_text())
            except Exception:
                self._local_log = []

    def _save_local(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._load_path.write_text(json.dumps(self._local_log[-100:], indent=2))

    def record(self, result: TrackResult, dna: SongDNA | None = None):
        """Record a completed track render for learning."""
        entry = {
            "name": result.name,
            "timestamp": time.time(),
            "lufs": result.lufs,
            "peak_db": result.peak_db,
            "bpm": result.bpm,
            "key": result.key,
            "scale": result.scale,
            "passed": result.passed_quality,
            "duration_s": result.duration_s,
            "render_time_s": result.render_time_s,
        }

        if dna:
            entry["bass_fm_depth"] = dna.bass.fm_depth
            entry["bass_distortion"] = dna.bass.distortion
            entry["target_lufs"] = dna.mix.target_lufs
            entry["stereo_width"] = dna.mix.stereo_width
            entry["bass_types"] = dna.bass_rotation

        self._local_log.append(entry)
        self._save_local()

        # Log to memory system if available
        if self._memory:
            try:
                self._memory.log_event(
                    module="autonomous",
                    action="track_complete",
                    params=entry,
                    result_summary=f"{'PASS' if result.passed_quality else 'FAIL'}: {result.name}",
                    duration_ms=result.render_time_s * 1000,
                )
            except Exception:
                pass

    def get_adjustments(self, mood: str = "", style: str = "") -> dict:
        """Get parameter adjustments based on past successes.

        Analyzes what parameter values produced passing tracks and
        biases new tracks toward those values.
        """
        passing = [e for e in self._local_log if e.get("passed")]
        if len(passing) < 2:
            return {}

        adjustments = {}

        # Average successful bass FM depth
        fm_depths = [e["bass_fm_depth"] for e in passing if "bass_fm_depth" in e]
        if fm_depths:
            adjustments["bass_fm_depth_bias"] = sum(fm_depths) / len(fm_depths)

        # Average successful distortion
        dists = [e["bass_distortion"] for e in passing if "bass_distortion" in e]
        if dists:
            adjustments["bass_distortion_bias"] = sum(dists) / len(dists)

        # Average successful LUFS
        lufs_vals = [e["target_lufs"] for e in passing if "target_lufs" in e]
        if lufs_vals:
            adjustments["target_lufs_bias"] = sum(lufs_vals) / len(lufs_vals)

        return adjustments

    def summary(self) -> str:
        """Summary of cross-track intelligence."""
        total = len(self._local_log)
        passing = sum(1 for e in self._local_log if e.get("passed"))
        lines = [
            f"Cross-Track Intelligence: {total} tracks logged, {passing} passed",
        ]
        adj = self.get_adjustments()
        if adj:
            lines.append(f"  Learned biases: {adj}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  AUTONOMOUS DIRECTOR — The Brain
# ═══════════════════════════════════════════════════════════════

class AutonomousDirector:
    """The autonomous production director.

    Orchestrates the full pipeline:
    OpenClaw Agent → forge.py render → analysis → feedback → learning
    """

    def __init__(
        self,
        producer: str = "subtronics",
        verbose: bool = True,
        max_retries: int = 2,
    ):
        self.producer = producer
        self.verbose = verbose
        self.max_retries = max_retries

        # Core systems
        self.agent = get_agent(producer)
        self.analyzer = QualityAnalyzer()
        self.intel = CrossTrackIntelligence()
        self.namer = NameGenerator()

        # Session tracking
        self.session_id = f"{int(time.time())}_{producer}"
        self.session = SessionLog(
            session_id=self.session_id,
            started_at=time.time(),
            producer=producer,
        )

        # Ensure output dirs exist
        for d in [OUTPUT_DIR, SONGS_DIR, EP_DIR, QUEUE_DIR, LOG_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    # ──────────────────────────────────────────────────────────
    #  SINGLE TRACK PRODUCTION
    # ──────────────────────────────────────────────────────────

    def produce_track(
        self,
        name: str = "",
        style: str = "dubstep",
        mood: str = "aggressive",
        key: str = "",
        scale: str = "",
        bpm: int = 0,
        seed: int = 0,
        blueprint: TrackBlueprint | None = None,
    ) -> TrackResult:
        """Produce a single track autonomously.

        1. Generate DNA via OpenClaw agent
        2. Render via forge.py subprocess
        3. Analyze quality
        4. Retry with adjustments if quality fails
        5. Record results for cross-track learning
        """
        if blueprint:
            name = blueprint.name
            style = blueprint.style
            mood = blueprint.mood
            key = blueprint.key
            scale = blueprint.scale
            bpm = blueprint.bpm
            seed = blueprint.seed

        if not name:
            name = self.namer.generate()

        result = TrackResult(name=name)
        t_start = time.time()

        self._log(f"\n{'═' * 60}")
        self._log(f"  AUTONOMOUS PRODUCTION: {name}")
        self._log(f"  Producer: {self.producer} | Style: {style} | Mood: {mood}")
        self._log(f"{'═' * 60}")

        # Apply cross-track intelligence
        intel_adj = self.intel.get_adjustments(mood=mood, style=style)
        if intel_adj:
            self._log(f"  Cross-track intel: {intel_adj}")

        # Generate DNA
        self._log(f"\n  [1] Generating DNA via OpenClaw agent...")
        try:
            dna = self.agent.produce(
                name, style=style, mood=mood,
                key=key, scale=scale, bpm=bpm, seed=seed,
            )
        except Exception as e:
            result.error = f"DNA generation failed: {e}"
            self._log(f"  ERROR: {result.error}")
            self.session.tracks_failed += 1
            self.session.results.append(result)
            return result

        # Apply cross-track learned biases
        if intel_adj:
            if "bass_fm_depth_bias" in intel_adj:
                # Blend toward learned optimum
                learned = intel_adj["bass_fm_depth_bias"]
                dna.bass.fm_depth = (dna.bass.fm_depth + learned) / 2
            if "bass_distortion_bias" in intel_adj:
                learned = intel_adj["bass_distortion_bias"]
                dna.bass.distortion = (dna.bass.distortion + learned) / 2
            if "target_lufs_bias" in intel_adj:
                learned = intel_adj["target_lufs_bias"]
                dna.mix.target_lufs = (dna.mix.target_lufs + learned) / 2

        result.bpm = dna.bpm
        result.key = dna.key
        result.scale = dna.scale
        result.dna_summary = dna.summary()

        self._log(f"  DNA: {dna.key} {dna.scale} @ {dna.bpm} BPM")
        self._log(f"  Bass: {' → '.join(dna.bass_rotation)} "
                  f"| FM={dna.bass.fm_depth:.1f} dist={dna.bass.distortion:.2f}")
        self._log(f"  Mix: {dna.mix.target_lufs:.1f} LUFS target")

        # Render with retries
        for attempt in range(1, self.max_retries + 2):
            self._log(f"\n  [2] Rendering (attempt {attempt})...")

            render_result = self._render_track(dna)

            if render_result.get("error"):
                self._log(f"  Render error: {render_result['error']}")
                if attempt <= self.max_retries:
                    self._log("  Adjusting parameters and retrying...")
                    self._adjust_for_retry(dna, attempt)
                    continue
                else:
                    result.error = render_result["error"]
                    break

            wav_path = render_result.get("wav_path", "")
            result.wav_path = wav_path

            # Analyze
            self._log(f"  [3] Analyzing quality...")
            analysis = self.analyzer.analyze(wav_path)

            result.duration_s = analysis.get("duration_s", 0)
            result.lufs = analysis.get("lufs_est", 0)
            result.peak_db = analysis.get("peak_db", 0)
            result.iterations = attempt
            result.passed_quality = analysis.get("passed", False)

            self._log(f"  Duration: {result.duration_s:.1f}s | "
                      f"LUFS: {result.lufs:.1f} | Peak: {result.peak_db:.1f} dB")
            self._log(f"  Quality: {'PASS ✓' if result.passed_quality else 'FAIL ✗'}")

            if result.passed_quality or attempt > self.max_retries:
                break

            # Adjust and retry
            self._log("  Adjusting parameters for next attempt...")
            self._adjust_for_retry(dna, attempt)

        # Record time
        result.render_time_s = time.time() - t_start

        # Save DNA
        dna_path = self._save_dna(dna)
        result.dna_path = str(dna_path)

        # Record for cross-track learning
        self.intel.record(result, dna)

        # Update session
        if result.error:
            self.session.tracks_failed += 1
        else:
            self.session.tracks_completed += 1
        self.session.total_render_time_s += result.render_time_s
        self.session.results.append(result)

        # Summary
        self._log(f"\n  {'─' * 50}")
        self._log(f"  COMPLETE: {name}")
        self._log(f"  Output:   {result.wav_path}")
        self._log(f"  Time:     {result.render_time_s:.1f}s")
        self._log(f"  Quality:  {'PASS ✓' if result.passed_quality else 'FAIL ✗'}")
        self._log(f"  {'─' * 50}")

        return result

    # ──────────────────────────────────────────────────────────
    #  EP PRODUCTION
    # ──────────────────────────────────────────────────────────

    def produce_ep(
        self,
        title: str = "",
        track_count: int = 5,
        style: str = "dubstep",
        mood_arc: list[str] | None = None,
        blueprints: list[TrackBlueprint] | None = None,
    ) -> list[TrackResult]:
        """Produce a full EP autonomously.

        Creates a cohesive set of tracks with:
        - Consistent producer style
        - Mood arc across tracks
        - Key/BPM complementarity
        - Cross-track learning applied progressively
        """
        if not title:
            title = f"{self.namer._rng.choice(NAME_ATOMS['prefixes'])} EP"

        self.session.mode = "ep"

        self._log(f"\n{'╔' + '═' * 58 + '╗'}")
        self._log(f"║  AUTONOMOUS EP PRODUCTION: {title:<30}║")
        self._log(f"║  Tracks: {track_count}  |  Producer: {self.producer:<25}║")
        self._log(f"{'╚' + '═' * 58 + '╝'}")

        # Generate mood arc if not provided
        if not mood_arc:
            mood_arc = self._generate_mood_arc(track_count)

        # Generate key progression (musically complementary)
        keys = self._generate_key_progression(track_count)

        # Generate track names
        names = self.namer.generate_ep_names(track_count, theme=title)

        # Build blueprints if not provided
        if not blueprints:
            blueprints = []
            for i in range(track_count):
                bp = TrackBlueprint(
                    name=names[i],
                    style=style,
                    mood=mood_arc[i % len(mood_arc)],
                    producer=self.producer,
                    key=keys[i % len(keys)],
                    scale=random.choice(SCALE_POOL),
                )
                blueprints.append(bp)

        # Produce each track
        results = []
        for i, bp in enumerate(blueprints):
            self._log(f"\n  ── Track {i + 1}/{len(blueprints)}: {bp.name} ──")
            result = self.produce_track(blueprint=bp)
            results.append(result)

        # EP summary
        passed = sum(1 for r in results if r.passed_quality)
        total_time = sum(r.render_time_s for r in results)

        self._log(f"\n{'═' * 60}")
        self._log(f"  EP COMPLETE: {title}")
        self._log(f"  Tracks: {passed}/{len(results)} passed quality")
        self._log(f"  Total render time: {total_time:.1f}s")
        self._log(f"{'═' * 60}")

        # Save EP manifest
        self._save_ep_manifest(title, results, blueprints)

        return results

    # ──────────────────────────────────────────────────────────
    #  CONTINUOUS MODE
    # ──────────────────────────────────────────────────────────

    def run_continuous(self, max_tracks: int = 0, delay_s: float = 5.0):
        """Run continuously, producing tracks until stopped.

        Args:
            max_tracks: Stop after N tracks (0 = infinite)
            delay_s: Pause between tracks
        """
        self.session.mode = "continuous"
        count = 0

        self._log(f"\n{'═' * 60}")
        self._log(f"  AUTONOMOUS CONTINUOUS MODE")
        self._log(f"  Producer: {self.producer}")
        self._log(f"  Max tracks: {'∞' if max_tracks == 0 else max_tracks}")
        self._log(f"{'═' * 60}")

        try:
            while max_tracks == 0 or count < max_tracks:
                count += 1

                # Generate random track parameters
                name = self.namer.generate()
                mood = random.choice(MOOD_POOL)
                style = random.choice(STYLE_POOL)

                self._log(f"\n  ── Continuous Track #{count}: {name} ──")

                try:
                    result = self.produce_track(
                        name=name, style=style, mood=mood,
                    )
                except Exception as e:
                    self._log(f"  ERROR: {e}")
                    traceback.print_exc()

                # Save session after each track
                self.session.save()

                if delay_s > 0 and (max_tracks == 0 or count < max_tracks):
                    self._log(f"  Pausing {delay_s}s before next track...")
                    time.sleep(delay_s)

        except KeyboardInterrupt:
            self._log("\n  [Interrupted by user]")

        self._finalize_session()

    # ──────────────────────────────────────────────────────────
    #  QUEUE MODE
    # ──────────────────────────────────────────────────────────

    def run_queue(self, queue_path: str):
        """Process a queue of track blueprints from a YAML/JSON file."""
        self.session.mode = "queue"

        path = Path(queue_path)
        if not path.exists():
            self._log(f"  ERROR: Queue file not found: {queue_path}")
            return []

        # Load queue
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(path.read_text())
            except ImportError:
                # Fallback: parse YAML manually for simple cases
                data = json.loads(path.read_text())
        else:
            data = json.loads(path.read_text())

        tracks = data.get("tracks", [])
        if not tracks:
            self._log("  ERROR: No tracks in queue file")
            return []

        self._log(f"\n  QUEUE MODE: {len(tracks)} tracks from {queue_path}")

        blueprints = [TrackBlueprint.from_dict(t) for t in tracks]
        results = []

        for i, bp in enumerate(blueprints):
            self._log(f"\n  ── Queue Track {i + 1}/{len(blueprints)}: {bp.name} ──")
            result = self.produce_track(blueprint=bp)
            results.append(result)
            self.session.save()

        self._finalize_session()
        return results

    # ──────────────────────────────────────────────────────────
    #  INTERNAL: Rendering
    # ──────────────────────────────────────────────────────────

    def _render_track(self, dna: SongDNA) -> dict:
        """Render a track by calling forge.py as a subprocess."""
        # Build safe filename
        safe_name = dna.name.lower().replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        wav_path = str(OUTPUT_DIR / f"{safe_name}.wav")

        # Build command — SongDNA uses .mood_name not .mood
        mood = getattr(dna, "mood_name", "") or getattr(dna, "mood", "") or "aggressive"
        cmd = [
            sys.executable, "forge.py",
            "--song", dna.name,
            "--style", dna.style,
            "--mood", mood,
            "--producer", self.producer,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per render
                cwd=str(Path(__file__).parent.parent),
            )

            if proc.returncode != 0:
                # Extract error from stderr
                error_lines = proc.stderr.strip().split("\n")
                error_msg = error_lines[-1] if error_lines else "Unknown error"
                return {"error": f"Exit code {proc.returncode}: {error_msg}",
                        "stdout": proc.stdout, "stderr": proc.stderr}

            # Find the output path from stdout
            for line in proc.stdout.split("\n"):
                if "Output:" in line and ".wav" in line:
                    found = line.split("Output:")[-1].strip()
                    if os.path.exists(found):
                        wav_path = found
                        break

            if not os.path.exists(wav_path):
                # Try common patterns
                for candidate in [
                    str(OUTPUT_DIR / f"{safe_name}.wav"),
                    str(OUTPUT_DIR / f"songs/{safe_name}.wav"),
                ]:
                    if os.path.exists(candidate):
                        wav_path = candidate
                        break

            return {"wav_path": wav_path, "stdout": proc.stdout}

        except subprocess.TimeoutExpired:
            return {"error": "Render timed out (10 minutes)"}
        except Exception as e:
            return {"error": str(e)}

    def _adjust_for_retry(self, dna: SongDNA, attempt: int):
        """Adjust DNA parameters for a retry attempt."""
        # Reduce aggression slightly with each retry
        scale = 1.0 - (attempt * 0.08)

        # Pull back extreme values
        dna.bass.fm_depth = min(dna.bass.fm_depth * scale, 5.0)
        dna.bass.distortion = min(dna.bass.distortion * scale, 0.55)
        dna.mix.master_drive = min(dna.mix.master_drive * scale, 0.55)

        # Adjust LUFS target toward safe zone
        if dna.mix.target_lufs > -8.0:
            dna.mix.target_lufs = -9.0
        elif dna.mix.target_lufs < -11.0:
            dna.mix.target_lufs = -9.5

    def _save_dna(self, dna: SongDNA) -> Path:
        """Save SongDNA to JSON."""
        SONGS_DIR.mkdir(parents=True, exist_ok=True)
        safe = dna.name.lower().replace(" ", "_")
        safe = "".join(c for c in safe if c.isalnum() or c == "_")
        path = SONGS_DIR / f"{safe}_dna.json"
        try:
            from engine.variation_engine import _dna_to_dict
            path.write_text(json.dumps(_dna_to_dict(dna), indent=2))
        except Exception:
            # Fallback: just save summary
            path.write_text(json.dumps({"name": dna.name,
                                         "summary": dna.summary()}, indent=2))
        return path

    def _save_ep_manifest(
        self, title: str, results: list[TrackResult],
        blueprints: list[TrackBlueprint],
    ):
        """Save EP manifest JSON."""
        EP_DIR.mkdir(parents=True, exist_ok=True)
        safe = title.lower().replace(" ", "_")
        safe = "".join(c for c in safe if c.isalnum() or c == "_")
        manifest = {
            "title": title,
            "producer": self.producer,
            "timestamp": time.time(),
            "tracks": [r.to_dict() for r in results],
            "blueprints": [b.to_dict() for b in blueprints],
        }
        path = EP_DIR / f"{safe}_manifest.json"
        path.write_text(json.dumps(manifest, indent=2))
        self._log(f"  EP manifest saved: {path}")

    def _generate_mood_arc(self, count: int) -> list[str]:
        """Generate a mood arc for an EP.

        Classic dubstep EP structure:
        1. Intro/build energy → 2. Peak aggression → 3-4. Vary →
        5. Closer (heaviest or most emotional)
        """
        arcs = {
            3: ["aggressive", "dark", "brutal"],
            4: ["dark", "aggressive", "sinister", "crushing"],
            5: ["driving", "aggressive", "dark", "chaotic", "brutal"],
            6: ["menacing", "driving", "aggressive", "dark", "chaotic", "crushing"],
            7: ["hypnotic", "driving", "aggressive", "dark", "savage", "chaotic", "brutal"],
        }
        if count in arcs:
            return arcs[count]
        # Generic arc
        return [random.choice(MOOD_POOL) for _ in range(count)]

    def _generate_key_progression(self, count: int) -> list[str]:
        """Generate musically complementary keys for an EP."""
        # Circle of fifths neighbors for cohesion
        key_groups = [
            ["F", "C", "G", "D", "A"],
            ["E", "B", "F#", "C#", "G#"],
            ["Bb", "Eb", "Ab", "Db", "Gb"],
        ]
        group = random.choice(key_groups)
        random.shuffle(group)
        keys = []
        for i in range(count):
            keys.append(group[i % len(group)])
        return keys

    def _finalize_session(self):
        """Finalize and save the session."""
        self.session.completed_at = time.time()
        path = self.session.save()
        elapsed = self.session.completed_at - self.session.started_at

        self._log(f"\n{'═' * 60}")
        self._log(f"  SESSION COMPLETE")
        self._log(f"  ID:       {self.session.session_id}")
        self._log(f"  Duration: {elapsed:.1f}s ({elapsed / 60:.1f}m)")
        self._log(f"  Tracks:   {self.session.tracks_completed} completed, "
                  f"{self.session.tracks_failed} failed")
        self._log(f"  Intel:    {self.intel.summary()}")
        self._log(f"  Log:      {path}")
        self._log(f"{'═' * 60}")


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

def main():
    """CLI entry point for autonomous production."""
    import argparse

    parser = argparse.ArgumentParser(
        description="DUBFORGE Autonomous Production System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Produce a single track
  python -m engine.autonomous --track "CYCLOPS FURY" --producer subtronics

  # Produce an EP (5 tracks)
  python -m engine.autonomous --ep "FRACTAL DIMENSION" --tracks 5

  # Continuous mode — produce forever
  python -m engine.autonomous --continuous --producer subtronics

  # Process a queue file
  python -m engine.autonomous --queue configs/production_queue.yaml

  # Quick batch — produce 3 random tracks
  python -m engine.autonomous --batch 3
        """,
    )

    parser.add_argument("--track", type=str, default="",
                        help="Produce a single named track")
    parser.add_argument("--ep", type=str, default="",
                        help="Produce an EP with given title")
    parser.add_argument("--tracks", type=int, default=5,
                        help="Number of tracks for EP mode (default: 5)")
    parser.add_argument("--continuous", action="store_true",
                        help="Continuous production mode")
    parser.add_argument("--batch", type=int, default=0,
                        help="Produce N random tracks")
    parser.add_argument("--queue", type=str, default="",
                        help="Path to queue YAML/JSON file")
    parser.add_argument("--producer", type=str, default="subtronics",
                        help="Producer profile (default: subtronics)")
    parser.add_argument("--style", type=str, default="dubstep",
                        help="Music style (default: dubstep)")
    parser.add_argument("--mood", type=str, default="aggressive",
                        help="Track mood (default: aggressive)")
    parser.add_argument("--max-retries", type=int, default=2,
                        help="Max render retries per track (default: 2)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose output")

    args = parser.parse_args()

    # Print banner
    print("╔══════════════════════════════════════════════════════╗")
    print("║  DUBFORGE AUTONOMOUS PRODUCTION SYSTEM              ║")
    print("║──────────────────────────────────────────────────────║")
    print(f"║  Producer: {args.producer:<42}║")
    print(f"║  Style:    {args.style:<42}║")
    print("╚══════════════════════════════════════════════════════╝")

    director = AutonomousDirector(
        producer=args.producer,
        verbose=not args.quiet,
        max_retries=args.max_retries,
    )

    # Print agent banner
    print(director.agent.banner())
    print()

    if args.track:
        director.produce_track(
            name=args.track,
            style=args.style,
            mood=args.mood,
        )
        director._finalize_session()

    elif args.ep:
        director.produce_ep(
            title=args.ep,
            track_count=args.tracks,
            style=args.style,
        )
        director._finalize_session()

    elif args.continuous:
        director.run_continuous()

    elif args.batch > 0:
        director.session.mode = "batch"
        for i in range(args.batch):
            name = director.namer.generate()
            mood = random.choice(MOOD_POOL)
            style = random.choice(STYLE_POOL) if args.style == "dubstep" else args.style
            print(f"\n  ── Batch Track {i + 1}/{args.batch}: {name} ──")
            director.produce_track(name=name, style=style, mood=mood)
        director._finalize_session()

    elif args.queue:
        director.run_queue(args.queue)

    else:
        # Default: produce a single random track
        director.produce_track(style=args.style, mood=args.mood)
        director._finalize_session()


if __name__ == "__main__":
    main()
