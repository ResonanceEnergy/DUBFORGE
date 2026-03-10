"""
DUBFORGE Engine — Lessons Learned Persistence System

Saves and loads production insights across tracks, so each new track
benefits from every previous track's feedback cycles.

Storage: output/lessons_learned.json
  - Persists across sessions
  - Indexed by genre/style
  - Records parameter adjustments that improved quality
  - Records parameter adjustments that degraded quality
  - Tracks which recipe book targets are consistently missed

Usage:
    from engine.lessons_learned import LessonsLearned
    ll = LessonsLearned()

    # Before rendering: get pre-adjustments from past experience
    adjustments = ll.get_pre_adjustments("dubstep")

    # After rendering: record what happened
    ll.record_session(fibonacci_session)

    # Query: what have we learned?
    insights = ll.get_insights()
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ParameterLesson:
    """A single learned parameter adjustment."""
    parameter: str          # e.g., "bass.sub_normalize"
    old_value: float
    new_value: float
    metric_affected: str    # e.g., "Sub Bass %"
    metric_before: float
    metric_after: float
    improved: bool          # did the metric move toward target?
    style: str              # genre context
    track_name: str
    timestamp: float = 0.0


@dataclass
class RecurringFailure:
    """A quality target that fails across multiple tracks."""
    metric_name: str
    failure_count: int
    tracks_affected: list[str]
    common_direction: str  # "too_low" or "too_high"
    suggested_parameter: str
    suggested_value: float | None = None


@dataclass
class TrackRecord:
    """Summary of a single track's production history."""
    track_name: str
    style: str
    mood: str
    total_renders: int
    total_corrections: int
    all_targets_met: bool
    final_metrics: dict[str, float]
    parameter_lessons: list[ParameterLesson]
    timestamp: float = 0.0
    duration_s: float = 0.0


@dataclass
class LessonsDatabase:
    """Complete persistent database of production lessons."""
    version: int = 2
    tracks: list[dict] = field(default_factory=list)
    parameter_lessons: list[dict] = field(default_factory=list)
    recurring_failures: list[dict] = field(default_factory=list)
    golden_rules: list[dict] = field(default_factory=list)
    belt_progress: dict = field(default_factory=lambda: {
        "current_belt": "Unranked",
        "tracks_completed": 0,
        "skills_demonstrated": [],
        "belt_history": [],
    })
    last_updated: float = 0.0

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "tracks": self.tracks,
            "parameter_lessons": self.parameter_lessons,
            "recurring_failures": self.recurring_failures,
            "golden_rules": self.golden_rules,
            "belt_progress": self.belt_progress,
            "last_updated": self.last_updated,
        }


# ═══════════════════════════════════════════════════════════════════════════
# GOLDEN RULES — Hard-won production truths
# ═══════════════════════════════════════════════════════════════════════════

INITIAL_GOLDEN_RULES = [
    {
        "rule": "Sub bass normalize should be 0.50-0.60, not lower",
        "source": "BIT RAGE 29-issue overhaul",
        "parameter": "bass.sub_normalize",
        "value": 0.55,
        "style": "dubstep",
    },
    {
        "rule": "Never cut sub below 60Hz in pre-master EQ — kills PA translation",
        "source": "BIT RAGE C2 fix",
        "parameter": "mix.eq_pre_master_cut_60hz",
        "value": False,
        "style": "dubstep",
    },
    {
        "rule": "Sidechain should be ONE bus pass, not per-element (causes double-ducking)",
        "source": "BIT RAGE H1 fix",
        "parameter": "mix.sidechain_mode",
        "value": "bus",
        "style": "dubstep",
    },
    {
        "rule": "Bus compression threshold must not be near zero — use 1e-4 minimum",
        "source": "BIT RAGE H2 fix",
        "parameter": "mix.bus_comp_threshold",
        "value": 1e-4,
        "style": "dubstep",
    },
    {
        "rule": "Target LUFS -7.5 for dubstep (sweet spot between -8 and -6)",
        "source": "BIT RAGE mastering iterations",
        "parameter": "mix.target_lufs",
        "value": -7.5,
        "style": "dubstep",
    },
    {
        "rule": "Pads MUST play in drop sections — they provide harmonic fill",
        "source": "BIT RAGE C5 fix",
        "parameter": "arrangement.pads_in_drops",
        "value": True,
        "style": "dubstep",
    },
    {
        "rule": "Drum fills should accelerate (8th→16th→32nd), not be uniform 16th",
        "source": "BIT RAGE H4 fix",
        "parameter": "drums.fill_style",
        "value": "accelerating",
        "style": "dubstep",
    },
    {
        "rule": "High EQ boost should not exceed +2.5dB to avoid harshness",
        "source": "BIT RAGE C3 fix",
        "parameter": "mix.eq_high_boost",
        "value": 2.5,
        "style": "dubstep",
    },
    {
        "rule": "Sidechain depth 0.55 in drops for pump without over-ducking",
        "source": "BIT RAGE H1 fix",
        "parameter": "mix.sidechain_depth",
        "value": 0.55,
        "style": "dubstep",
    },
    {
        "rule": "Riser duration = max(BUILD, BUILD2, 8 bars) — never shorter than 8 bars",
        "source": "BIT RAGE C7 fix",
        "parameter": "fx.riser_min_bars",
        "value": 8,
        "style": "dubstep",
    },

    # ── ill.Gates / Producer Dojo Golden Rules ────────────────────────
    {
        "rule": "Always start with The Approach — Collect → Sketch → Arrange → Mix → Finish → Release",
        "source": "ill.Gates / Producer Dojo",
        "parameter": "workflow.use_approach",
        "value": True,
        "style": "",
    },
    {
        "rule": "Build a 128 Rack BEFORE starting sound design — instant palette access",
        "source": "ill.Gates / Producer Dojo — 128 Rack technique",
        "parameter": "workflow.use_128_rack",
        "value": True,
        "style": "",
    },
    {
        "rule": "Mudpies unlock creativity — chaos → chop → extract → resample",
        "source": "ill.Gates / Producer Dojo — Mudpies technique",
        "parameter": "creative.mudpie_sessions",
        "value": True,
        "style": "",
    },
    {
        "rule": "Timer prevents perfectionism — 14-Minute Hit for arrangement sketches",
        "source": "ill.Gates / Producer Dojo — 14-Minute Hit",
        "parameter": "workflow.timer_s",
        "value": 840,
        "style": "",
    },
    {
        "rule": "First instinct is usually right — if you undo more than once, revert to first choice",
        "source": "ill.Gates / Producer Dojo — Decision Fatigue",
        "parameter": "workflow.first_instinct",
        "value": True,
        "style": "",
    },
    {
        "rule": "Singer concept = track identity — one sound must carry the track alone",
        "source": "ill.Gates / Producer Dojo — Ninja Sounds (Singer/Band)",
        "parameter": "bass.singer_layer",
        "value": "MID",
        "style": "",
    },
    {
        "rule": "Never mix and master in the same session — separate passes, fresh ears",
        "source": "ill.Gates / Producer Dojo — Session Hygiene",
        "parameter": "workflow.separate_mix_master",
        "value": True,
        "style": "",
    },
    {
        "rule": "Low pass filter = narrative device — filter position tells story position",
        "source": "ill.Gates / Producer Dojo — Low Pass Techniques",
        "parameter": "mix.narrative_filtering",
        "value": True,
        "style": "",
    },
    {
        "rule": "Maximum 3 decisions per mixing pass — prevents decision fatigue",
        "source": "ill.Gates / Producer Dojo — Decision Fatigue Prevention",
        "parameter": "workflow.max_decisions_per_pass",
        "value": 3,
        "style": "",
    },
    {
        "rule": "VIP your best tracks — revisit winners, not losers",
        "source": "ill.Gates / Producer Dojo — VIP System",
        "parameter": "workflow.vip_best_tracks",
        "value": True,
        "style": "",
    },
    {
        "rule": "Constraints breed creativity — master stock devices before buying plugins",
        "source": "ill.Gates / Producer Dojo — Stock Device Mastery",
        "parameter": "workflow.stock_devices_first",
        "value": True,
        "style": "",
    },
    {
        "rule": "Resampling chain maximum 3 passes — diminishing returns after 3",
        "source": "ill.Gates / Producer Dojo — Resampling Chains",
        "parameter": "sound_design.max_resample_passes",
        "value": 3,
        "style": "",
    },
    {
        "rule": "Finish tracks, not loops — a done track teaches more than 100 loops",
        "source": "ill.Gates / Producer Dojo — The Producer's Path",
        "parameter": "workflow.finish_tracks",
        "value": True,
        "style": "",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# LESSONS LEARNED ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class LessonsLearned:
    """Persistent cross-track learning system.

    Saves production lessons to disk so each new track benefits
    from all previous tracks' feedback cycles.

    Usage:
        ll = LessonsLearned()
        adjustments = ll.get_pre_adjustments("dubstep")
        # ... produce track ...
        ll.record_session(fibonacci_session)
    """

    def __init__(self, db_path: str = "output/lessons_learned.json"):
        self.db_path = Path(db_path)
        self.db = self._load()

    def _load(self) -> LessonsDatabase:
        """Load lessons database from disk, or create with initial golden rules."""
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                db = LessonsDatabase(
                    version=data.get("version", 1),
                    tracks=data.get("tracks", []),
                    parameter_lessons=data.get("parameter_lessons", []),
                    recurring_failures=data.get("recurring_failures", []),
                    golden_rules=data.get("golden_rules", INITIAL_GOLDEN_RULES[:]),
                    belt_progress=data.get("belt_progress", {
                        "current_belt": "Unranked",
                        "tracks_completed": 0,
                        "skills_demonstrated": [],
                        "belt_history": [],
                    }),
                    last_updated=data.get("last_updated", 0.0),
                )
                return db
            except (json.JSONDecodeError, KeyError):
                pass

        # New database with initial golden rules
        return LessonsDatabase(
            golden_rules=INITIAL_GOLDEN_RULES[:],
            last_updated=time.time(),
        )

    def _save(self):
        """Save lessons database to disk."""
        self.db.last_updated = time.time()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self.db.as_dict(), f, indent=2, default=str)

    # ── Pre-production: apply learned adjustments ────

    def get_pre_adjustments(self, style: str = "dubstep") -> list[dict]:
        """Get parameter adjustments to apply before rendering, based on past lessons.

        Returns list of dicts with: parameter, value, lesson (description).
        """
        adjustments = []

        # 1. Apply golden rules for this style
        for rule in self.db.golden_rules:
            if rule.get("style", "") == style or rule.get("style", "") == "":
                if "parameter" in rule and "value" in rule:
                    adjustments.append({
                        "parameter": rule["parameter"],
                        "value": rule["value"],
                        "lesson": rule["rule"],
                        "source": rule.get("source", "golden rule"),
                    })

        # 2. Apply lessons from successful corrections
        # Find corrections that improved metrics, grouped by parameter
        param_successes: dict[str, list[dict]] = {}
        for lesson in self.db.parameter_lessons:
            if lesson.get("improved") and lesson.get("style") == style:
                param = lesson["parameter"]
                param_successes.setdefault(param, []).append(lesson)

        for param, lessons in param_successes.items():
            if len(lessons) >= 2:
                # Multiple successful corrections → use the most recent value
                latest = max(lessons, key=lambda l: l.get("timestamp", 0))
                adjustments.append({
                    "parameter": latest["parameter"],
                    "value": latest["new_value"],
                    "lesson": f"Learned from {len(lessons)} tracks: "
                              f"{latest['parameter']} = {latest['new_value']:.3f} "
                              f"improves {latest['metric_affected']}",
                    "source": f"cross-track learning ({len(lessons)} instances)",
                })

        # 3. Address recurring failures
        for rf in self.db.recurring_failures:
            if rf.get("failure_count", 0) >= 2:
                if rf.get("suggested_value") is not None:
                    adjustments.append({
                        "parameter": rf["suggested_parameter"],
                        "value": rf["suggested_value"],
                        "lesson": f"Recurring: {rf['metric_name']} fails "
                                  f"({rf['common_direction']}) in {rf['failure_count']} tracks",
                        "source": "recurring failure pattern",
                    })

        return adjustments

    # ── Post-production: record session results ──────

    def record_session(self, session: Any):
        """Record a FibonacciFeedbackEngine session's results.

        Extracts:
        - Parameter corrections that worked/didn't work
        - Final metrics
        - Track metadata
        """
        # Build track record
        final_metrics = {}
        if session.final_analysis:
            a = session.final_analysis
            final_metrics = {
                "lufs": a.lufs_est,
                "peak_db": a.peak_db,
                "sub_pct": a.sub_pct,
                "low_pct": a.low_pct,
                "mid_pct": a.mid_pct,
                "high_pct": a.high_pct,
                "air_pct": a.air_pct,
                "stereo_width": a.stereo_width,
                "intro_drop_contrast": a.intro_drop_contrast_db,
                "drop_break_contrast": a.drop_break_contrast_db,
            }

        track_record = {
            "track_name": session.track_name,
            "style": session.style,
            "mood": session.mood,
            "total_renders": session.total_renders,
            "total_corrections": session.total_corrections,
            "all_targets_met": session.all_targets_met,
            "final_metrics": final_metrics,
            "timestamp": time.time(),
            "duration_s": session.completed_at - session.started_at,
        }
        self.db.tracks.append(track_record)

        # Extract parameter lessons from correction steps
        for step in session.steps:
            if not step.corrections:
                continue

            # Compare analysis before and after corrections
            for correction in step.corrections:
                lesson = {
                    "parameter": correction.parameter,
                    "old_value": correction.old_value,
                    "new_value": correction.new_value,
                    "metric_affected": correction.failure.metric_name,
                    "metric_before": correction.failure.current_value,
                    "metric_after": 0.0,  # filled from step analysis if available
                    "improved": False,
                    "style": session.style,
                    "track_name": session.track_name,
                    "timestamp": time.time(),
                }

                # Check if the correction helped (metric moved toward target)
                if step.analysis:
                    # Map metric name to analysis value
                    metric_map = {
                        "LUFS": step.analysis.lufs_est,
                        "Sub Bass %": step.analysis.sub_pct,
                        "Mid %": step.analysis.mid_pct,
                        "High %": step.analysis.high_pct,
                        "Stereo Width": step.analysis.stereo_width,
                        "Intro→Drop Contrast": step.analysis.intro_drop_contrast_db,
                        "Intro→Drop": step.analysis.intro_drop_contrast_db,
                        "True Peak": step.analysis.peak_db,
                    }
                    after_val = metric_map.get(correction.failure.metric_name)
                    if after_val is not None:
                        lesson["metric_after"] = after_val
                        # Check if metric moved toward target range
                        if correction.failure.direction == "too_low":
                            lesson["improved"] = after_val > correction.failure.current_value
                        else:
                            lesson["improved"] = after_val < correction.failure.current_value

                self.db.parameter_lessons.append(lesson)

        # Update recurring failures
        self._update_recurring_failures(session)

        # Save to disk
        self._save()

    def _update_recurring_failures(self, session: Any):
        """Track which metrics consistently fail across tracks."""
        # Collect all failures from session (from the last step with analysis)
        session_failures: dict[str, str] = {}
        for step in session.steps:
            for f in step.failures:
                session_failures[f.metric_name] = f.direction

        # Update recurring failure counts
        existing_rf = {rf["metric_name"]: rf for rf in self.db.recurring_failures}

        for metric_name, direction in session_failures.items():
            if metric_name in existing_rf:
                existing_rf[metric_name]["failure_count"] += 1
                if session.track_name not in existing_rf[metric_name]["tracks_affected"]:
                    existing_rf[metric_name]["tracks_affected"].append(session.track_name)
            else:
                existing_rf[metric_name] = {
                    "metric_name": metric_name,
                    "failure_count": 1,
                    "tracks_affected": [session.track_name],
                    "common_direction": direction,
                    "suggested_parameter": "",
                    "suggested_value": None,
                }

        self.db.recurring_failures = list(existing_rf.values())

    # ── Query: what have we learned? ─────────────────

    def get_insights(self) -> dict:
        """Get a summary of all production insights learned."""
        total_tracks = len(self.db.tracks)
        successful = sum(1 for t in self.db.tracks if t.get("all_targets_met"))
        total_lessons = len(self.db.parameter_lessons)
        positive_lessons = sum(1 for l in self.db.parameter_lessons if l.get("improved"))

        # Most common corrections
        param_counts: dict[str, int] = {}
        for l in self.db.parameter_lessons:
            p = l.get("parameter", "")
            param_counts[p] = param_counts.get(p, 0) + 1

        top_corrections = sorted(param_counts.items(), key=lambda x: -x[1])[:10]

        # Recurring failures
        recurring = [rf for rf in self.db.recurring_failures if rf.get("failure_count", 0) >= 2]

        return {
            "total_tracks": total_tracks,
            "successful_tracks": successful,
            "success_rate": f"{successful/total_tracks*100:.0f}%" if total_tracks else "N/A",
            "total_lessons": total_lessons,
            "positive_lessons": positive_lessons,
            "learning_rate": f"{positive_lessons/total_lessons*100:.0f}%" if total_lessons else "N/A",
            "top_corrections": top_corrections,
            "recurring_failures": recurring,
            "golden_rules": len(self.db.golden_rules),
        }

    def add_golden_rule(self, rule: str, parameter: str, value: Any,
                        style: str = "dubstep", source: str = "manual"):
        """Add a new golden rule — a hard-won production truth."""
        self.db.golden_rules.append({
            "rule": rule,
            "source": source,
            "parameter": parameter,
            "value": value,
            "style": style,
        })
        self._save()

    # ── Dojo Belt System — Track progression ─────────

    # Belt thresholds follow Fibonacci: 1, 3, 5, 8, 13, 21, 34
    BELT_THRESHOLDS = [
        ("White", 1, "Beginner — first completed track"),
        ("Yellow", 3, "Novice — understanding the basics"),
        ("Green", 5, "Intermediate — developing consistency"),
        ("Blue", 8, "Advanced — reliable quality output"),
        ("Purple", 13, "Expert — unique creative voice emerging"),
        ("Brown", 21, "Master — teaching others, deep understanding"),
        ("Black", 34, "Grandmaster — transcendent, legendary output"),
    ]

    def evaluate_belt(self) -> dict:
        """Evaluate current belt rank based on track count and success rate.

        Belt thresholds follow Fibonacci: 1, 3, 5, 8, 13, 21, 34.
        Returns belt info with current rank, progress, and next milestone.
        """
        tracks_completed = len(self.db.tracks)
        successful = sum(1 for t in self.db.tracks if t.get("all_targets_met"))
        success_rate = successful / tracks_completed if tracks_completed > 0 else 0.0

        current_belt = "Unranked"
        next_belt = "White"
        tracks_needed = 1
        belt_description = "Complete your first track to earn White belt"

        for belt_name, threshold, description in self.BELT_THRESHOLDS:
            if tracks_completed >= threshold:
                current_belt = belt_name
                belt_description = description
                idx = [b[0] for b in self.BELT_THRESHOLDS].index(belt_name)
                if idx + 1 < len(self.BELT_THRESHOLDS):
                    next_belt = self.BELT_THRESHOLDS[idx + 1][0]
                    tracks_needed = self.BELT_THRESHOLDS[idx + 1][1] - tracks_completed
                else:
                    next_belt = "ASCENSION"
                    tracks_needed = 0
            else:
                break

        # Update persistent belt progress
        old_belt = self.db.belt_progress.get("current_belt", "Unranked")
        self.db.belt_progress = {
            "current_belt": current_belt,
            "tracks_completed": tracks_completed,
            "skills_demonstrated": list(set(
                t.get("style", "") for t in self.db.tracks if t.get("all_targets_met")
            )),
            "belt_history": self.db.belt_progress.get("belt_history", []),
        }

        # Record belt promotion
        if current_belt != old_belt and current_belt != "Unranked":
            self.db.belt_progress["belt_history"].append({
                "from": old_belt,
                "to": current_belt,
                "track_count": tracks_completed,
                "timestamp": time.time(),
            })

        self._save()

        return {
            "current_belt": current_belt,
            "description": belt_description,
            "tracks_completed": tracks_completed,
            "successful_tracks": successful,
            "success_rate": f"{success_rate*100:.0f}%",
            "next_belt": next_belt,
            "tracks_needed": max(0, tracks_needed),
            "belt_history": self.db.belt_progress.get("belt_history", []),
        }

    def add_dojo_rules(self):
        """Import all ill.Gates golden rules that aren't already in the database."""
        existing_rules = {r.get("rule", "") for r in self.db.golden_rules}
        added = 0
        for rule in INITIAL_GOLDEN_RULES:
            if rule["rule"] not in existing_rules:
                self.db.golden_rules.append(rule)
                added += 1
        if added > 0:
            self._save()
        return added

    def print_summary(self):
        """Print a human-readable summary of lessons learned."""
        insights = self.get_insights()
        belt = self.evaluate_belt()

        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║  DUBFORGE LESSONS LEARNED                                  ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║  Tracks produced: {insights['total_tracks']:<42}║")
        print(f"║  Success rate:    {insights['success_rate']:<42}║")
        print(f"║  Total lessons:   {insights['total_lessons']:<42}║")
        print(f"║  Learning rate:   {insights['learning_rate']:<42}║")
        print(f"║  Golden rules:    {insights['golden_rules']:<42}║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║  🥋 DOJO BELT STATUS                                       ║")
        print(f"║  Belt:     {belt['current_belt']:<49}║")
        print(f"║  Tracks:   {belt['tracks_completed']:<49}║")
        if belt['tracks_needed'] > 0:
            print(f"║  Next:     {belt['next_belt']} ({belt['tracks_needed']} tracks to go)"
                  f"{'':40}"[:60] + "  ║")
        else:
            print("║  ★ ASCENSION ACHIEVED — Beyond Black Belt                  ║")
        print("╠══════════════════════════════════════════════════════════════╣")

        if insights["top_corrections"]:
            print("║  Top corrections:                                          ║")
            for param, count in insights["top_corrections"][:5]:
                print(f"║    {param:<40} ({count}x)       ║"[:64] + "║")

        if insights["recurring_failures"]:
            print("║  Recurring failures:                                       ║")
            for rf in insights["recurring_failures"]:
                print(f"║    {rf['metric_name']:<30} ({rf['failure_count']}x, "
                      f"{rf['common_direction']})  ║"[:64] + "║")

        print("╚══════════════════════════════════════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Print lessons learned summary."""
    ll = LessonsLearned()
    ll.print_summary()


if __name__ == "__main__":
    main()
