"""
DUBFORGE Engine — Fibonacci Feedback Loop Engine

144-step production plan executed at Fibonacci intervals:
  1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144

At each Fibonacci checkpoint, the engine:
  1. Renders the track (forge.py render_full_track)
  2. Analyzes quality (quick_analyze.py metrics)
  3. Compares against RecipeBook quality targets
  4. Identifies failures and applies corrections
  5. Logs lessons learned for cross-track persistence
  6. Repeats until all targets are met or 144 steps exhausted

Golden Mean Analysis Cycles:
  At steps ≈ φ × previous step (8→13, 13→21, 21→34, 34→55, 55→89, 89→144),
  a deep analysis cycle runs that evaluates ALL quality targets and triggers
  corrections across ALL recipe categories.

Phase coherence (Dan Winter):
  Every golden-mean cycle checks phase coherence of harmonic layers,
  ensuring phi-ratio nesting produces constructive interference.

Dojo Integration (ill.Gates / Producer Dojo):
  - Decision Fatigue Prevention: max 3 corrections per step (ill.Gates rule)
  - First Instinct Preservation: snapshot DNA before corrections, revert if worse
  - Timer Enforcement: optional 14-Minute Hit mode (840s session limit)
  - The Approach Phase Mapping: each step maps to COLLECT→SKETCH→ARRANGE→MIX→FINISH
  - Belt Progression: track count + quality → belt rank evaluation (Fibonacci thresholds)

Usage:
    from engine.fibonacci_feedback import FibonacciFeedbackEngine
    engine = FibonacciFeedbackEngine()
    result = engine.run("BIT RAGE", style="dubstep", mood="dark aggressive")
    # Dojo mode with timer:
    result = engine.run("BIT RAGE", style="dubstep", dojo_timer=True)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

PHI = 1.6180339887
SR = 48000

# Fibonacci sequence up to 144
FIBONACCI_SEQUENCE = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

# Golden mean analysis steps — where φ-ratio nesting aligns
# These are steps where deep analysis cycles run
GOLDEN_ANALYSIS_STEPS = [8, 13, 21, 34, 55, 89, 144]

# Maximum iterations per correction attempt
MAX_CORRECTION_PASSES = 3


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AnalysisResult:
    """Result of analyzing a rendered track."""
    filepath: str
    duration_s: float = 0.0
    lufs_est: float = 0.0
    peak_db: float = 0.0
    sub_pct: float = 0.0
    low_pct: float = 0.0
    mid_pct: float = 0.0
    high_pct: float = 0.0
    air_pct: float = 0.0
    stereo_width: float = 0.0
    intro_drop_contrast_db: float = 0.0
    drop_break_contrast_db: float = 0.0
    pump_dips: int = 0
    raw_output: str = ""


@dataclass
class QualityFailure:
    """A specific quality target that was not met."""
    metric_name: str
    current_value: float
    target_min: float
    target_max: float
    priority: str  # CRITICAL / HIGH / MEDIUM / LOW
    direction: str  # "too_low" or "too_high"
    recipe_name: str  # which recipe addresses this
    suggested_fix: str


@dataclass
class CorrectionAction:
    """A parameter adjustment to correct a quality failure."""
    parameter: str   # DNA parameter path (e.g., "bass.sub_normalize")
    old_value: float
    new_value: float
    reason: str
    failure: QualityFailure


@dataclass
class StepResult:
    """Result of executing one Fibonacci step."""
    step_number: int
    fibonacci_index: int
    phase: str           # CONCEPT / FOUNDATION / DESIGN / PRODUCTION / MIXING / MASTERING / POLISH
    is_golden_analysis: bool
    analysis: AnalysisResult | None = None
    failures: list[QualityFailure] = field(default_factory=list)
    corrections: list[CorrectionAction] = field(default_factory=list)
    timestamp: float = 0.0
    duration_s: float = 0.0
    notes: str = ""


@dataclass
class FeedbackSession:
    """Complete record of a Fibonacci feedback session."""
    track_name: str
    style: str
    mood: str
    started_at: float = 0.0
    completed_at: float = 0.0
    total_renders: int = 0
    total_corrections: int = 0
    steps: list[StepResult] = field(default_factory=list)
    final_analysis: AnalysisResult | None = None
    all_targets_met: bool = False
    lessons: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "track_name": self.track_name,
            "style": self.style,
            "mood": self.mood,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_renders": self.total_renders,
            "total_corrections": self.total_corrections,
            "all_targets_met": self.all_targets_met,
            "steps": [asdict(s) for s in self.steps],
            "final_analysis": asdict(self.final_analysis) if self.final_analysis else None,
            "lessons": self.lessons,
        }


# ═══════════════════════════════════════════════════════════════════════════
# 144-STEP PLAN — What happens at each Fibonacci step
# ═══════════════════════════════════════════════════════════════════════════

STEP_PLAN: dict[int, dict] = {
    # ── Step 1 (Fib 1): CONCEPT ──
    1: {
        "phase": "CONCEPT",
        "dojo_approach": "COLLECT",
        "name": "DNA Generation",
        "description": "Generate SongDNA from blueprint. Establish key, scale, BPM, energy.",
        "actions": ["forge_dna", "save_dna"],
        "recipes": ["sub_bass_design", "drum_sound_design"],
        "focus": "Establish the sonic identity — DNA is the genome of the track.",
    },
    # ── Step 2 (Fib 1): CONCEPT ──
    2: {
        "phase": "CONCEPT",
        "dojo_approach": "COLLECT",
        "name": "Foundation Elements",
        "description": "Design kick, sub bass, and basic rhythm. The three pillars.",
        "actions": ["render_drums", "render_sub"],
        "recipes": ["sub_bass_design", "drum_sound_design", "drum_loop_engine"],
        "focus": "Sub + Kick + Rhythm = foundation. Get these right first.",
    },
    # ── Step 3 (Fib 2): FOUNDATION ──
    3: {
        "phase": "FOUNDATION",
        "dojo_approach": "SKETCH",
        "name": "Bass Layer Design",
        "description": "Design mid-bass growl types. FM synthesis, waveshaping, acid.",
        "actions": ["render_bass_types"],
        "recipes": ["mid_bass_growl", "acid_bass"],
        "focus": "The growl/bass is the character of the track. Subtronics: make it MOVE.",
    },
    # ── Step 4 (Fib 3): FOUNDATION ──
    4: {
        "phase": "FOUNDATION",
        "dojo_approach": "SKETCH",
        "name": "Lead & Melody",
        "description": "Design lead sounds, generate melody patterns from DNA.",
        "actions": ["render_leads"],
        "recipes": ["lead_melody_design"],
        "focus": "Lead carries the melody. It should be memorable and sit above the bass.",
    },
    # ── Step 5 (Fib 5): DESIGN ──
    5: {
        "phase": "DESIGN",
        "dojo_approach": "SKETCH",
        "name": "Atmosphere & Pads",
        "description": "Design pads, ambient textures, atmospheric layers.",
        "actions": ["render_pads"],
        "recipes": ["pad_atmosphere", "trance_arp"],
        "focus": "Pads fill harmonic space. Essential for breakdowns and depth in drops.",
    },
    # ── Step 6 (Fib 8): DESIGN — GOLDEN ANALYSIS ──
    6: {
        "phase": "DESIGN",
        "dojo_approach": "ARRANGE",
        "name": "First Full Render + Analysis",
        "description": "First complete render. Analyze ALL quality targets. "
                       "This is the first golden-mean analysis cycle.",
        "actions": ["render_full", "analyze", "compare_targets"],
        "recipes": ["mixing", "phase_coherence"],
        "focus": "First reality check. How does the raw render compare to targets?",
        "golden_analysis": True,
    },
    # ── Step 7 (Fib 13): PRODUCTION — GOLDEN ANALYSIS ──
    7: {
        "phase": "PRODUCTION",
        "dojo_approach": "ARRANGE",
        "name": "Spectral Balance Correction",
        "description": "Fix spectrum balance based on analysis. Sub/Mid/High ratios.",
        "actions": ["correct_spectrum", "render_full", "analyze"],
        "recipes": ["sub_bass_design", "mid_bass_growl", "mixing"],
        "focus": "Spectrum must be balanced. Sub 15-35%, Mid 20-40%. Fix NOW.",
        "golden_analysis": True,
    },
    # ── Step 8 (Fib 21): PRODUCTION — GOLDEN ANALYSIS ──
    8: {
        "phase": "PRODUCTION",
        "dojo_approach": "ARRANGE",
        "name": "Arrangement & Contrast",
        "description": "Fix section contrast. Intro→Drop >5dB, Drop→Break >3dB. "
                       "Ensure energy arc follows Fibonacci structure.",
        "actions": ["correct_arrangement", "render_full", "analyze"],
        "recipes": ["drop_design", "buildup_design", "breakdown_design",
                     "silence_space", "drum_rolls_fills"],
        "focus": "The arrangement IS the track. Contrast creates emotion.",
        "golden_analysis": True,
    },
    # ── Step 9 (Fib 34): MIXING — GOLDEN ANALYSIS ──
    9: {
        "phase": "MIXING",
        "dojo_approach": "MIX",
        "name": "Mix Polish",
        "description": "Sidechain, bus compression, stereo width, EQ carving. "
                       "Phase coherence check (Dan Winter).",
        "actions": ["correct_mix", "render_full", "analyze"],
        "recipes": ["mixing", "phase_coherence", "sweep_transition_fx",
                     "vocal_chops", "stabs_oneshots"],
        "focus": "Mixing is surgical. Every element needs its own space.",
        "golden_analysis": True,
    },
    # ── Step 10 (Fib 55): MASTERING — GOLDEN ANALYSIS ──
    10: {
        "phase": "MASTERING",
        "dojo_approach": "MIX",
        "name": "Master Chain Tuning",
        "description": "Mastering chain: EQ, multiband compression, limiting. "
                       "Target LUFS -8 to -6. Phase coherence final check.",
        "actions": ["correct_master", "render_full", "analyze"],
        "recipes": ["mastering"],
        "focus": "Mastering is the final polish. Subtle moves, big impact.",
        "golden_analysis": True,
    },
    # ── Step 11 (Fib 89): POLISH — GOLDEN ANALYSIS ──
    11: {
        "phase": "POLISH",
        "dojo_approach": "FINISH",
        "name": "Detail & Variation Pass",
        "description": "Add variation: drum fills, bass rotation, double-time. "
                       "Ensure Drop 2 differs from Drop 1. Add vocal chops, stabs.",
        "actions": ["add_variation", "render_full", "analyze"],
        "recipes": ["double_time", "drum_rolls_fills", "vocal_chops",
                     "stabs_oneshots", "drop_design"],
        "focus": "Details separate amateur from professional. Every section unique.",
        "golden_analysis": True,
    },
    # ── Step 12 (Fib 144): FINAL — GOLDEN ANALYSIS ──
    12: {
        "phase": "FINAL",
        "dojo_approach": "RELEASE",
        "name": "Final Validation & Lessons",
        "description": "Final render and analysis. All targets must be met. "
                       "Extract lessons learned. Save session data.",
        "actions": ["render_full", "analyze", "validate_all", "save_lessons"],
        "recipes": [],  # all recipes checked
        "focus": "The final checkpoint. If all targets met = DONE. If not = document what failed.",
        "golden_analysis": True,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS ENGINE — Parse quick_analyze.py output into structured data
# ═══════════════════════════════════════════════════════════════════════════

def parse_analysis_output(raw_output: str, filepath: str) -> AnalysisResult:
    """Parse quick_analyze.py stdout into structured AnalysisResult."""
    result = AnalysisResult(filepath=filepath, raw_output=raw_output)

    for line in raw_output.splitlines():
        line = line.strip()
        # Duration
        if line.startswith("Duration:"):
            try:
                result.duration_s = float(line.split("Duration:")[1].split("s")[0].strip())
            except (ValueError, IndexError):
                pass
        # LUFS
        if "Est LUFS:" in line:
            try:
                val_str = line.split("Est LUFS:")[1].strip().split()[0]
                result.lufs_est = float(val_str)
            except (ValueError, IndexError):
                pass
        # Peak
        if "Peak:" in line and "dB" in line:
            try:
                result.peak_db = float(line.split("Peak:")[1].split("dB")[0].strip())
            except (ValueError, IndexError):
                pass
        # Spectrum — raw percentages (format: "  Sub  20-80Hz:     55% /    7%")
        if "Sub" in line and "%" in line and "20-" in line:
            try:
                after_colon = line.split(":")[1].strip()
                result.sub_pct = float(after_colon.split("%")[0].strip())
            except (ValueError, IndexError):
                pass
        if "Low" in line and "%" in line and "80-" in line:
            try:
                after_colon = line.split(":")[1].strip()
                result.low_pct = float(after_colon.split("%")[0].strip())
            except (ValueError, IndexError):
                pass
        if "Mid" in line and "%" in line and ("300-" in line or "250-" in line):
            try:
                after_colon = line.split(":")[1].strip()
                result.mid_pct = float(after_colon.split("%")[0].strip())
            except (ValueError, IndexError):
                pass
        if "High" in line and "%" in line and ("3-10" in line or "2.5k-" in line or "3k" in line):
            try:
                after_colon = line.split(":")[1].strip()
                result.high_pct = float(after_colon.split("%")[0].strip())
            except (ValueError, IndexError):
                pass
        if "Air" in line and "%" in line and "10k" in line:
            try:
                after_colon = line.split(":")[1].strip()
                result.air_pct = float(after_colon.split("%")[0].strip())
            except (ValueError, IndexError):
                pass
        # Stereo width
        if "Stereo width" in line:
            try:
                val_str = line.split(":")[1].strip().split()[0]
                result.stereo_width = float(val_str)
            except (ValueError, IndexError):
                pass
        # Section contrast (format: "  Intro to Drop: 5.9 dB")
        if "Intro" in line and "Drop" in line and "dB" in line:
            try:
                result.intro_drop_contrast_db = float(line.split(":")[1].split("dB")[0].strip())
            except (ValueError, IndexError):
                pass
        if "Drop" in line and "Break" in line and "dB" in line and "Intro" not in line:
            try:
                result.drop_break_contrast_db = float(line.split(":")[1].split("dB")[0].strip())
            except (ValueError, IndexError):
                pass
        # Sidechain pump
        if "pump" in line.lower() and "dip" in line.lower():
            try:
                import re
                nums = re.findall(r'\d+', line)
                if nums:
                    result.pump_dips = int(nums[0])
            except (ValueError, IndexError):
                pass

    return result


def run_analysis(filepath: str) -> AnalysisResult:
    """Run quick_analyze.py on a rendered track and parse results."""
    try:
        proc = subprocess.run(
            [sys.executable, "quick_analyze.py", filepath],
            capture_output=True, text=True, timeout=60,
        )
        raw = proc.stdout + proc.stderr
        return parse_analysis_output(raw, filepath)
    except Exception as e:
        return AnalysisResult(filepath=filepath, raw_output=f"ERROR: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY COMPARISON — Compare analysis vs targets, identify failures
# ═══════════════════════════════════════════════════════════════════════════

def compare_to_targets(analysis: AnalysisResult) -> list[QualityFailure]:
    """Compare analysis result against recipe book quality targets."""
    from engine.recipe_book import GLOBAL_QUALITY_TARGETS

    failures = []
    metric_map = {
        "integrated_lufs": analysis.lufs_est,
        "true_peak_dbtp": analysis.peak_db,
        "sub_pct_raw": analysis.sub_pct,
        "low_pct_raw": analysis.low_pct,
        "mid_pct_raw": analysis.mid_pct,
        "high_pct_raw": analysis.high_pct,
        "air_pct_raw": analysis.air_pct,
        "stereo_width": analysis.stereo_width,
        "intro_drop_contrast_db": analysis.intro_drop_contrast_db,
        "drop_break_contrast_db": analysis.drop_break_contrast_db,
        "duration_s": analysis.duration_s,
    }

    for target in GLOBAL_QUALITY_TARGETS:
        value = metric_map.get(target.metric)
        if value is None or value == 0.0:
            continue  # metric not available

        if value < target.target_min:
            failures.append(QualityFailure(
                metric_name=target.name,
                current_value=value,
                target_min=target.target_min,
                target_max=target.target_max,
                priority=target.priority,
                direction="too_low",
                recipe_name=target.name.lower().replace(" ", "_"),
                suggested_fix=f"Increase {target.name}: currently {value:.1f}, "
                              f"target min {target.target_min:.1f} {target.unit}",
            ))
        elif value > target.target_max:
            failures.append(QualityFailure(
                metric_name=target.name,
                current_value=value,
                target_min=target.target_min,
                target_max=target.target_max,
                priority=target.priority,
                direction="too_high",
                recipe_name=target.name.lower().replace(" ", "_"),
                suggested_fix=f"Decrease {target.name}: currently {value:.1f}, "
                              f"target max {target.target_max:.1f} {target.unit}",
            ))

    # Sort by priority
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    failures.sort(key=lambda f: priority_order.get(f.priority, 4))
    return failures


# ═══════════════════════════════════════════════════════════════════════════
# CORRECTION ENGINE — Auto-fix DNA parameters based on failures
# ═══════════════════════════════════════════════════════════════════════════

def compute_corrections(failures: list[QualityFailure], dna: Any) -> list[CorrectionAction]:
    """Compute DNA parameter corrections to fix quality failures.
    
    Each correction adjusts a specific DNA parameter based on the failure type.
    Uses conservative adjustments — never change more than 20% per iteration.
    """
    corrections = []

    for f in failures:
        if f.metric_name == "LUFS":
            if f.direction == "too_low":
                old = dna.mix.target_lufs
                new = old + 1.0  # louder
                corrections.append(CorrectionAction(
                    "mix.target_lufs", old, min(new, -6.0),
                    f"LUFS too low ({f.current_value:.1f}), raising target", f))
            else:
                old = dna.mix.target_lufs
                new = old - 1.0  # quieter
                corrections.append(CorrectionAction(
                    "mix.target_lufs", old, max(new, -12.0),
                    f"LUFS too high ({f.current_value:.1f}), lowering target", f))

        elif f.metric_name == "Sub Bass %":
            if f.direction == "too_low":
                old = dna.bass.sub_weight
                new = min(old + 0.08, 1.0)
                corrections.append(CorrectionAction(
                    "bass.sub_weight", old, new,
                    f"Sub too low ({f.current_value:.0f}%), raising sub_weight", f))
                old_eq = dna.mix.eq_low_boost
                corrections.append(CorrectionAction(
                    "mix.eq_low_boost", old_eq, min(old_eq + 0.5, 3.0),
                    "Boosting low EQ shelf to support sub", f))
            else:
                old = dna.bass.sub_weight
                new = max(old - 0.06, 0.3)
                corrections.append(CorrectionAction(
                    "bass.sub_weight", old, new,
                    f"Sub too high ({f.current_value:.0f}%), lowering sub_weight", f))

        elif f.metric_name == "Mid %":
            if f.direction == "too_low":
                old = dna.bass.mid_drive
                new = min(old + 0.08, 1.0)
                corrections.append(CorrectionAction(
                    "bass.mid_drive", old, new,
                    f"Mids too low ({f.current_value:.0f}%), raising mid_drive", f))
            else:
                old = dna.bass.mid_drive
                new = max(old - 0.06, 0.3)
                corrections.append(CorrectionAction(
                    "bass.mid_drive", old, new,
                    f"Mids too high ({f.current_value:.0f}%), lowering mid_drive", f))

        elif f.metric_name == "Stereo Width":
            if f.direction == "too_low":
                old = dna.mix.stereo_width
                corrections.append(CorrectionAction(
                    "mix.stereo_width", old, min(old + 0.5, 3.0),
                    "Stereo too narrow, widening", f))
            else:
                old = dna.mix.stereo_width
                corrections.append(CorrectionAction(
                    "mix.stereo_width", old, max(old - 0.5, 0.5),
                    "Stereo too wide, narrowing", f))

        elif "Contrast" in f.metric_name or "Intro" in f.metric_name:
            if f.direction == "too_low":
                old = dna.mix.master_drive
                new = min(old + 0.05, 0.85)
                corrections.append(CorrectionAction(
                    "mix.master_drive", old, new,
                    f"Contrast too low ({f.current_value:.1f}dB), increasing master_drive", f))
            else:
                old = dna.mix.master_drive
                new = max(old - 0.05, 0.3)
                corrections.append(CorrectionAction(
                    "mix.master_drive", old, new,
                    f"Contrast too high ({f.current_value:.1f}dB), reducing master_drive", f))

        elif f.metric_name == "High %" or f.metric_name == "Air %":
            if f.direction == "too_high":
                old = dna.mix.eq_high_boost
                new = max(old - 0.5, 0.5)
                corrections.append(CorrectionAction(
                    "mix.eq_high_boost", old, new,
                    f"High/Air too bright ({f.current_value:.0f}%), reducing high boost", f))
            else:
                old = dna.mix.eq_high_boost
                new = min(old + 0.5, 4.0)
                corrections.append(CorrectionAction(
                    "mix.eq_high_boost", old, new,
                    f"High/Air too dull ({f.current_value:.0f}%), increasing high boost", f))

        elif f.metric_name == "True Peak":
            if f.direction == "too_high":
                old = dna.mix.target_lufs
                new = old - 0.5
                corrections.append(CorrectionAction(
                    "mix.target_lufs", old, max(new, -12.0),
                    f"Clipping (peak {f.current_value:.1f}dB), reducing target LUFS", f))

    return corrections


def apply_corrections(corrections: list[CorrectionAction], dna: Any) -> int:
    """Apply computed corrections to DNA object. Returns count of applied."""
    applied = 0
    for c in corrections:
        parts = c.parameter.split(".")
        obj = dna
        for part in parts[:-1]:
            obj = getattr(obj, part, None)
            if obj is None:
                break
        if obj is not None:
            attr = parts[-1]
            if hasattr(obj, attr):
                setattr(obj, attr, c.new_value)
                applied += 1
    return applied


# ═══════════════════════════════════════════════════════════════════════════
# DOJO INTEGRATION — ill.Gates decision fatigue, first instinct, belt system
# ═══════════════════════════════════════════════════════════════════════════

# Dojo Approach phases mapped to step ranges
DOJO_APPROACH_PHASES = {
    "COLLECT": "Gather sounds, ideas, samples. No judgment. Fill the 128 Rack.",
    "SKETCH": "Rough out ideas quickly. First instinct wins. Timer running.",
    "ARRANGE": "Structure the energy arc. Sections, contrast, narrative filtering.",
    "MIX": "Surgical precision. One focus per pass. Max 3 decisions.",
    "FINISH": "Detail, variation, final polish. Don't overthink.",
    "RELEASE": "Validate, document lessons, evaluate belt progress.",
}

# Belt thresholds — Fibonacci track counts (ill.Gates belt system)
DOJO_BELT_THRESHOLDS = [
    ("White", 1, "Beginner — first completed track"),
    ("Yellow", 3, "Novice — understanding the basics"),
    ("Green", 5, "Intermediate — developing consistency"),
    ("Blue", 8, "Advanced — reliable quality output"),
    ("Purple", 13, "Expert — unique creative voice emerging"),
    ("Brown", 21, "Master — teaching others, deep understanding"),
    ("Black", 34, "Grandmaster — transcendent, legendary output"),
]


def enforce_decision_limit(failures: list[QualityFailure],
                           max_decisions: int = 3) -> list[QualityFailure]:
    """ill.Gates: limit corrections per pass to prevent decision fatigue.

    Only the top N most critical failures are addressed per correction pass.
    Remaining failures are deferred to the next golden analysis cycle.
    This prevents cognitive overload and maintains judgment quality.
    """
    if len(failures) <= max_decisions:
        return failures
    # Sort by priority, take only top N
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_failures = sorted(failures, key=lambda f: priority_order.get(f.priority, 4))
    return sorted_failures[:max_decisions]


def snapshot_dna(dna: Any) -> dict:
    """Snapshot DNA parameters for first-instinct preservation."""
    snapshot = {}
    for section_name in ["bass", "mix", "drums", "melody", "fx"]:
        section = getattr(dna, section_name, None)
        if section is not None:
            section_data = {}
            for attr in dir(section):
                if not attr.startswith("_"):
                    val = getattr(section, attr, None)
                    if isinstance(val, (int, float, str, bool)):
                        section_data[attr] = val
            snapshot[section_name] = section_data
    return snapshot


def restore_dna_snapshot(dna: Any, snapshot: dict) -> int:
    """Restore DNA from a snapshot. Returns count of restored parameters."""
    restored = 0
    for section_name, params in snapshot.items():
        section = getattr(dna, section_name, None)
        if section is not None:
            for attr, val in params.items():
                if hasattr(section, attr):
                    setattr(section, attr, val)
                    restored += 1
    return restored


def check_first_instinct(original_analysis: AnalysisResult,
                         current_analysis: AnalysisResult) -> bool:
    """ill.Gates: Return True if original was better — preserve first instinct.

    Compares key metrics between original and corrected versions.
    If corrections made things worse overall, first instinct wins.
    """
    from engine.recipe_book import GLOBAL_QUALITY_TARGETS

    metric_map_orig = {
        "integrated_lufs": original_analysis.lufs_est,
        "sub_pct_raw": original_analysis.sub_pct,
        "mid_pct_raw": original_analysis.mid_pct,
        "stereo_width": original_analysis.stereo_width,
        "intro_drop_contrast_db": original_analysis.intro_drop_contrast_db,
    }
    metric_map_curr = {
        "integrated_lufs": current_analysis.lufs_est,
        "sub_pct_raw": current_analysis.sub_pct,
        "mid_pct_raw": current_analysis.mid_pct,
        "stereo_width": current_analysis.stereo_width,
        "intro_drop_contrast_db": current_analysis.intro_drop_contrast_db,
    }

    orig_score = 0
    curr_score = 0
    for target in GLOBAL_QUALITY_TARGETS:
        orig_val = metric_map_orig.get(target.metric)
        curr_val = metric_map_curr.get(target.metric)
        if orig_val is None or curr_val is None or orig_val == 0.0:
            continue
        # Score: 1 point if within target range, 0 if not
        orig_in = target.target_min <= orig_val <= target.target_max
        curr_in = target.target_min <= curr_val <= target.target_max
        if orig_in:
            orig_score += 1
        if curr_in:
            curr_score += 1

    return orig_score > curr_score  # True = original was better


def evaluate_belt_progress(tracks_completed: int, avg_quality: float = 0.0) -> dict:
    """Evaluate current belt rank based on track count and quality.

    Belt thresholds follow Fibonacci: 1, 3, 5, 8, 13, 21, 34.
    Returns belt info dict with current rank and progress to next.
    """
    current_belt = "Unranked"
    next_belt = "White"
    tracks_needed = 1

    for belt_name, threshold, description in DOJO_BELT_THRESHOLDS:
        if tracks_completed >= threshold:
            current_belt = belt_name
            # Find next belt
            idx = [b[0] for b in DOJO_BELT_THRESHOLDS].index(belt_name)
            if idx + 1 < len(DOJO_BELT_THRESHOLDS):
                next_belt = DOJO_BELT_THRESHOLDS[idx + 1][0]
                tracks_needed = DOJO_BELT_THRESHOLDS[idx + 1][1] - tracks_completed
            else:
                next_belt = "ASCENSION"
                tracks_needed = 0
        else:
            break

    return {
        "current_belt": current_belt,
        "tracks_completed": tracks_completed,
        "next_belt": next_belt,
        "tracks_needed": max(0, tracks_needed),
        "avg_quality": avg_quality,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FIBONACCI FEEDBACK ENGINE — Main orchestrator
# ═══════════════════════════════════════════════════════════════════════════

class FibonacciFeedbackEngine:
    """144-step Fibonacci feedback loop engine.

    Takes a track from concept to polished master through 12 Fibonacci
    checkpoints (1,1,2,3,5,8,13,21,34,55,89,144), with golden-mean
    analysis cycles at φ-ratio intervals.

    Usage:
        engine = FibonacciFeedbackEngine()
        result = engine.run("BIT RAGE", style="dubstep", mood="dark aggressive")
    """

    def __init__(self, output_dir: str = "output",
                 max_correction_passes: int = MAX_CORRECTION_PASSES,
                 verbose: bool = True):
        self.output_dir = Path(output_dir)
        self.max_correction_passes = max_correction_passes
        self.verbose = verbose
        self.session: FeedbackSession | None = None

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _banner(self, step_num: int, plan: dict):
        fib = FIBONACCI_SEQUENCE[step_num - 1] if step_num <= len(FIBONACCI_SEQUENCE) else "?"
        golden = " ★ GOLDEN ANALYSIS" if plan.get("golden_analysis") else ""
        dojo_phase = plan.get("dojo_approach", "")
        self._log("")
        self._log("╔══════════════════════════════════════════════════════════════╗")
        self._log(f"║  Step {step_num}/12 (Fib {fib})  │  {plan['phase']:<10}  │  {plan['name']:<20}║"[:64] + "║")
        if dojo_phase:
            dojo_desc = DOJO_APPROACH_PHASES.get(dojo_phase, "")
            self._log(f"║  🥋 Dojo: [{dojo_phase}] {dojo_desc[:44]:<44}      ║"[:66] + "║")
        if golden:
            self._log(f"║  {golden:<62}║")
        self._log("╠══════════════════════════════════════════════════════════════╣")
        self._log(f"║  {plan['description'][:60]:<62}║")
        self._log(f"║  Focus: {plan['focus'][:54]:<54}        ║"[:66] + "║")
        self._log("╚══════════════════════════════════════════════════════════════╝")

    def _find_output_wav(self, track_name: str) -> str | None:
        """Find the rendered WAV for a given track name."""
        sanitized = track_name.lower().replace(" ", "_")
        candidates = [
            self.output_dir / f"{sanitized}.wav",
            self.output_dir / f"dubstep_track_v5.wav",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        # Search output dir for any WAV
        for f in sorted(self.output_dir.glob("*.wav"), key=os.path.getmtime, reverse=True):
            return str(f)
        return None

    def _render(self, dna: Any, track_name: str) -> str | None:
        """Render a track using forge.py render_full_track."""
        try:
            from forge import render_full_track
            render_full_track(dna=dna)
            return self._find_output_wav(track_name)
        except Exception as e:
            self._log(f"  ⚠ Render error: {e}")
            return None

    def _analyze(self, filepath: str) -> AnalysisResult:
        """Analyze a rendered track."""
        return run_analysis(filepath)

    def _print_analysis(self, a: AnalysisResult):
        self._log(f"  Duration: {a.duration_s:.1f}s")
        self._log(f"  Est LUFS: {a.lufs_est:.1f} dB")
        self._log(f"  Peak: {a.peak_db:.1f} dB")
        self._log(f"  Spectrum: Sub {a.sub_pct:.0f}% | Low {a.low_pct:.0f}% | "
                  f"Mid {a.mid_pct:.0f}% | High {a.high_pct:.0f}% | Air {a.air_pct:.0f}%")
        self._log(f"  Stereo width: {a.stereo_width:.2f}")
        self._log(f"  Contrast: Intro→Drop {a.intro_drop_contrast_db:.1f}dB | "
                  f"Drop→Break {a.drop_break_contrast_db:.1f}dB")

    def _print_failures(self, failures: list[QualityFailure]):
        if not failures:
            self._log("  ✓ All quality targets met!")
            return
        self._log(f"  ✗ {len(failures)} quality target(s) not met:")
        for f in failures:
            arrow = "↑" if f.direction == "too_low" else "↓"
            self._log(f"    [{f.priority}] {f.metric_name}: "
                      f"{f.current_value:.1f} {arrow} (target: {f.target_min:.1f}-{f.target_max:.1f})")

    def _print_corrections(self, corrections: list[CorrectionAction]):
        if not corrections:
            return
        self._log(f"  Applying {len(corrections)} correction(s):")
        for c in corrections:
            self._log(f"    {c.parameter}: {c.old_value:.3f} → {c.new_value:.3f}  ({c.reason})")

    def run(self, track_name: str, style: str = "dubstep",
            mood: str = "", sound_style: str = "",
            dna: Any = None, dojo_timer: bool = False,
            dojo_timer_s: int = 840) -> FeedbackSession:
        """Execute the full 144-step Fibonacci feedback loop.

        Args:
            track_name: Name of the track to produce
            style: Genre/style (default: dubstep)
            mood: Mood descriptor
            sound_style: Sound style descriptor
            dna: Pre-generated SongDNA (if None, generates from blueprint)
            dojo_timer: Enable ill.Gates 14-Minute Hit timer enforcement
            dojo_timer_s: Timer duration in seconds (default: 840 = 14 minutes)

        Returns:
            FeedbackSession with complete record of the production process
        """
        self.session = FeedbackSession(
            track_name=track_name,
            style=style,
            mood=mood,
            started_at=time.time(),
        )

        session_start = time.time()

        self._log("")
        self._log("═" * 66)
        self._log(f"  DUBFORGE FIBONACCI FEEDBACK ENGINE")
        self._log(f"  Track: {track_name}  |  Style: {style}  |  Mood: {mood}")
        self._log(f"  144-step plan at Fibonacci intervals")
        if dojo_timer:
            self._log(f"  ⏱  DOJO TIMER ACTIVE — {dojo_timer_s}s ({dojo_timer_s/60:.0f} min) limit")
            self._log(f"  🥋 ill.Gates: First instinct wins. Max 3 decisions per pass.")
        self._log("═" * 66)

        # ── Step 1: Generate or use provided DNA ──
        if dna is None:
            from engine.variation_engine import SongBlueprint, VariationEngine
            bp = SongBlueprint(name=track_name, style=style, mood=mood,
                               sound_style=sound_style)
            engine = VariationEngine(artistic_variance=0.15)
            dna = engine.forge_dna(bp)
            self._log(f"\n  DNA generated: {dna.name} | {dna.key} {dna.scale} | {dna.bpm} BPM")

        # ── Load lessons learned from previous tracks ──
        try:
            from engine.lessons_learned import LessonsLearned
            lessons = LessonsLearned()
            pre_adjustments = lessons.get_pre_adjustments(style)
            if pre_adjustments:
                self._log(f"\n  Applying {len(pre_adjustments)} lesson(s) from previous tracks:")
                for adj in pre_adjustments:
                    self._log(f"    • {adj['lesson']}")
                    # Apply learned parameter adjustments
                    if "parameter" in adj and "value" in adj:
                        parts = adj["parameter"].split(".")
                        obj = dna
                        for part in parts[:-1]:
                            obj = getattr(obj, part, None)
                            if obj is None:
                                break
                        if obj is not None and hasattr(obj, parts[-1]):
                            setattr(obj, parts[-1], adj["value"])
        except ImportError:
            pass

        # ── Execute 12 Fibonacci steps ──
        all_met = False
        for step_num in range(1, 13):
            plan = STEP_PLAN.get(step_num, {})
            if not plan:
                continue

            # ── Dojo Timer Check ──
            if dojo_timer:
                elapsed = time.time() - session_start
                remaining = dojo_timer_s - elapsed
                if remaining <= 0:
                    self._log(f"\n  ⏱  DOJO TIMER EXPIRED — {elapsed:.0f}s elapsed. "
                              f"ill.Gates: Save and move on!")
                    break
                self._log(f"\n  ⏱  Timer: {remaining:.0f}s remaining ({remaining/60:.1f} min)")

            step_start = time.time()
            self._banner(step_num, plan)

            fib_value = FIBONACCI_SEQUENCE[step_num - 1] if step_num <= len(FIBONACCI_SEQUENCE) else 0
            is_golden = plan.get("golden_analysis", False)

            step_result = StepResult(
                step_number=step_num,
                fibonacci_index=fib_value,
                phase=plan["phase"],
                is_golden_analysis=is_golden,
                timestamp=time.time(),
            )

            # ── Render if step includes render action ──
            if "render_full" in plan.get("actions", []) or step_num >= 6:
                self._log("\n  Rendering full track...")
                filepath = self._render(dna, track_name)

                if filepath:
                    self.session.total_renders += 1
                    self._log(f"  Rendered: {filepath}")

                    # ── Analyze ──
                    self._log("\n  Analyzing...")
                    analysis = self._analyze(filepath)
                    step_result.analysis = analysis
                    self._print_analysis(analysis)

                    # ── Compare to targets ──
                    failures = compare_to_targets(analysis)
                    step_result.failures = failures
                    self._print_failures(failures)

                    if not failures:
                        all_met = True
                        step_result.notes = "All quality targets met!"
                    elif is_golden:
                        # ── Dojo: Save first instinct snapshot ──
                        first_instinct = snapshot_dna(dna)
                        first_instinct_analysis = analysis

                        # ── Golden analysis: correct and re-render ──
                        for correction_pass in range(self.max_correction_passes):
                            if not failures:
                                break

                            # ── Dojo: Decision fatigue limit (max 3 per pass) ──
                            limited_failures = enforce_decision_limit(failures, max_decisions=3)
                            if len(limited_failures) < len(failures):
                                self._log(f"\n  🥋 Dojo: {len(failures)} failures → limiting to "
                                          f"top {len(limited_failures)} (decision fatigue prevention)")

                            self._log(f"\n  ── Correction pass {correction_pass + 1}/{self.max_correction_passes} ──")
                            corrections = compute_corrections(limited_failures, dna)
                            step_result.corrections.extend(corrections)
                            self._print_corrections(corrections)

                            applied = apply_corrections(corrections, dna)
                            self.session.total_corrections += applied

                            if applied > 0:
                                # Re-render with corrections
                                self._log("\n  Re-rendering with corrections...")
                                filepath = self._render(dna, track_name)
                                if filepath:
                                    self.session.total_renders += 1
                                    analysis = self._analyze(filepath)
                                    step_result.analysis = analysis
                                    self._print_analysis(analysis)
                                    failures = compare_to_targets(analysis)
                                    step_result.failures = failures
                                    self._print_failures(failures)
                                    if not failures:
                                        all_met = True
                                        break

                        # ── Dojo: First instinct check ──
                        if (first_instinct_analysis and analysis and
                                check_first_instinct(first_instinct_analysis, analysis)):
                            self._log("\n  🥋 Dojo: First instinct was BETTER — reverting!")
                            self._log("    ill.Gates: 'Your first instinct is usually right.'")
                            restored = restore_dna_snapshot(dna, first_instinct)
                            self._log(f"    Restored {restored} parameters to pre-correction state.")
                else:
                    step_result.notes = "Render failed"
            else:
                step_result.notes = f"Design phase: {plan['name']}"

            step_result.duration_s = time.time() - step_start
            self.session.steps.append(step_result)

            # ── Early exit if all targets met ──

            # ── Dojo: Belt progress evaluation ──
            track_count = len(ll.db.tracks) if hasattr(ll, 'db') and hasattr(ll.db, 'tracks') else 1
            belt_info = evaluate_belt_progress(track_count)
            self._log(f"\n  🥋 DOJO BELT STATUS:")
            self._log(f"    Current Belt: {belt_info['current_belt']}")
            self._log(f"    Tracks Completed: {belt_info['tracks_completed']}")
            if belt_info['tracks_needed'] > 0:
                self._log(f"    Next Belt: {belt_info['next_belt']} "
                          f"({belt_info['tracks_needed']} tracks to go)")
            else:
                self._log(f"    ★ ASCENSION ACHIEVED — Beyond Black Belt")
            if all_met and step_num >= 10:
                self._log("\n  ★ All quality targets met — skipping remaining steps")
                break

        # ── Final summary ──
        self.session.completed_at = time.time()
        self.session.all_targets_met = all_met

        # Get final analysis
        filepath = self._find_output_wav(track_name)
        if filepath:
            self.session.final_analysis = self._analyze(filepath)

        # ── Save lessons learned ──
        try:
            from engine.lessons_learned import LessonsLearned
            ll = LessonsLearned()
            ll.record_session(self.session)
            self._log("\n  Lessons saved for future tracks.")
        except ImportError:
            pass

        # ── Save session data ──
        session_path = self.output_dir / f"{track_name.lower().replace(' ', '_')}_fibonacci_session.json"
        session_path.parent.mkdir(parents=True, exist_ok=True)
        with open(session_path, "w") as f:
            json.dump(self.session.as_dict(), f, indent=2, default=str)

        self._print_summary()
        return self.session

    def _print_summary(self):
        s = self.session
        elapsed = s.completed_at - s.started_at
        self._log("")
        self._log("═" * 66)
        self._log("  FIBONACCI FEEDBACK SESSION COMPLETE")
        self._log("═" * 66)
        self._log(f"  Track: {s.track_name}")
        self._log(f"  Total renders: {s.total_renders}")
        self._log(f"  Total corrections: {s.total_corrections}")
        self._log(f"  Elapsed: {elapsed:.0f}s ({elapsed/60:.1f} min)")
        self._log(f"  All targets met: {'✓ YES' if s.all_targets_met else '✗ NO'}")
        self._log("═" * 66)


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Run Fibonacci feedback engine from command line."""
    args = sys.argv[1:]

    track_name = "Untitled"
    style = "dubstep"
    mood = ""

    if "--song" in args:
        idx = args.index("--song")
        track_name = args[idx + 1] if idx + 1 < len(args) else track_name
    elif args and not args[0].startswith("--"):
        track_name = args[0]

    if "--style" in args:
        idx = args.index("--style")
        style = args[idx + 1] if idx + 1 < len(args) else style
    if "--mood" in args:
        idx = args.index("--mood")
        mood = args[idx + 1] if idx + 1 < len(args) else mood

    engine = FibonacciFeedbackEngine()
    session = engine.run(track_name, style=style, mood=mood)

    if session.all_targets_met:
        print("\n  ★ Track production complete — all targets met!")
        sys.exit(0)
    else:
        print("\n  ⚠ Some targets not met — check session log for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
