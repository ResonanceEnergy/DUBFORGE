"""
DUBFORGE Engine — Memory System (Long-Term Persistence)

Persistent memory engine that tracks sessions, catalogs assets,
records parameter evolution, stores insights, and enables recall
across the entire DUBFORGE lifecycle.

All memory follows DUBFORGE phi/Fibonacci doctrine:
  - Fibonacci-indexed snapshot intervals (sessions 1,2,3,5,8,13,21…)
  - Phi-weighted recency scoring for recall relevance
  - Fractal self-similarity: micro-events mirror macro-session structure
  - Golden ratio decay for forgetting curves

Storage:
    output/memory/sessions/         — per-session JSON logs
    output/memory/asset_registry.json  — master catalog of all generated assets
    output/memory/evolution.json    — parameter evolution timeline
    output/memory/insights.json     — user notes, ratings, favorites
    output/memory/growth.json       — phi growth / belt progress tracker
    output/memory/index.json        — master index for fast recall

Usage:
    from engine.memory import MemoryEngine
    mem = MemoryEngine()
    mem.begin_session()
    mem.log_event("phi_core", "generate", {"frames": 256, "partials": 13})
    mem.register_asset("wavetable", "DUBFORGE_PHI_CORE.wav", {...})
    mem.rate_asset("DUBFORGE_PHI_CORE.wav", score=0.9, notes="fat sub")
    mem.end_session()
    results = mem.recall(module="phi_core", min_score=0.8, limit=5)
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS — DUBFORGE DOCTRINE
# ═══════════════════════════════════════════════════════════════════════════
from engine.config_loader import FIBONACCI, PHI, get_config_value

FIBONACCI_SET = set(FIBONACCI)

# ─── Config-driven defaults ───────────────────────────────────────────────
_RECALL_HALF_LIFE = float(get_config_value(
    "memory_v1", "recall", "recency_half_life_s", default=86400))
_RECALL_LIMIT = int(get_config_value(
    "memory_v1", "recall", "default_limit", default=13))
_MAX_SESSION_FILES = int(get_config_value(
    "memory_v1", "sessions", "max_session_files", default=233))

MEMORY_DIR = Path(__file__).parent.parent / "output" / "memory"
SESSIONS_DIR = MEMORY_DIR / "sessions"

# Files
INDEX_FILE = MEMORY_DIR / "index.json"
ASSET_REGISTRY_FILE = MEMORY_DIR / "asset_registry.json"
EVOLUTION_FILE = MEMORY_DIR / "evolution.json"
INSIGHTS_FILE = MEMORY_DIR / "insights.json"
GROWTH_FILE = MEMORY_DIR / "growth.json"


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_dirs():
    """Create memory directories if they don't exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any = None) -> Any:
    """Load JSON file, returning default if missing or corrupt."""
    if default is None:
        default = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    return default


def _save_json(path: Path, data: Any, indent: int = 2):
    """Atomically write JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)
    tmp.replace(path)


def _timestamp() -> str:
    """ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _hash_params(params: dict) -> str:
    """Deterministic short hash of parameter dict for dedup."""
    raw = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _is_fibonacci(n: int) -> bool:
    """Check if n is a Fibonacci number."""
    if n <= 0:
        return False
    # A positive integer is Fibonacci iff one of (5n²+4) or (5n²-4) is a perfect square
    def is_perfect_square(x):
        s = int(math.isqrt(x))
        return s * s == x
    return is_perfect_square(5 * n * n + 4) or is_perfect_square(5 * n * n - 4)


def phi_recency_score(age_seconds: float, half_life: float = _RECALL_HALF_LIFE) -> float:
    """
    Phi-weighted recency score.
    Uses golden-ratio decay instead of exponential:
        score = 1 / (1 + (age / half_life) ^ PHI)
    Returns 0.0–1.0 where 1.0 = just now, decays toward 0.
    """
    if age_seconds <= 0:
        return 1.0
    ratio = age_seconds / half_life
    return 1.0 / (1.0 + ratio ** PHI)


def phi_relevance(recency: float, quality: float, frequency: float) -> float:
    """
    Combined relevance score using phi-weighted factors.
    relevance = recency^(1/φ) × quality^φ × (1 + log_φ(frequency+1))
    """
    r = recency ** (1.0 / PHI)
    q = quality ** PHI if quality > 0 else 0.0
    f = 1.0 + math.log(frequency + 1, PHI) if frequency > 0 else 1.0
    return r * q * f


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryEvent:
    """A single event within a session."""
    timestamp: str
    module: str           # e.g. "phi_core", "rco", "psbs"
    action: str           # e.g. "generate", "analyze", "configure"
    params: dict = field(default_factory=dict)
    result_summary: str = ""
    output_files: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    param_hash: str = ""

    def __post_init__(self):
        if not self.param_hash and self.params:
            self.param_hash = _hash_params(self.params)


@dataclass
class Session:
    """A complete engine session (one run_all or manual invocation)."""
    session_id: str
    started_at: str
    ended_at: str = ""
    session_number: int = 0
    is_fibonacci_session: bool = False  # True if session_number ∈ Fibonacci
    events: list[dict] = field(default_factory=list)
    modules_used: list[str] = field(default_factory=list)
    total_events: int = 0
    total_assets: int = 0
    duration_s: float = 0.0
    notes: str = ""
    snapshot: bool = False  # Full state snapshot at Fibonacci sessions


@dataclass
class Asset:
    """A generated output asset (wavetable, preset, JSON, etc.)."""
    asset_id: str
    asset_type: str       # "wavetable", "preset", "analysis", "arrangement", "config"
    filename: str
    path: str
    module: str
    created_at: str
    session_id: str
    params: dict = field(default_factory=dict)
    param_hash: str = ""
    size_bytes: int = 0
    score: float = 0.0           # user quality rating (0–1)
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    generation: int = 1          # version/generation counter
    parent_asset_id: str = ""    # for VIP delta lineage

    def __post_init__(self):
        if not self.param_hash and self.params:
            self.param_hash = _hash_params(self.params)
        if not self.asset_id:
            self.asset_id = f"{self.module}_{self.param_hash}_{int(time.time())}"


@dataclass
class ParamSnapshot:
    """A point-in-time record of parameters for evolution tracking."""
    timestamp: str
    module: str
    param_key: str        # e.g. "phi_core.n_partials" or "rco.weapon.drop_1.bars"
    old_value: Any = None
    new_value: Any = None
    session_id: str = ""
    delta_magnitude: float = 0.0  # normalized difference

    def compute_delta(self):
        """Compute magnitude of parameter change."""
        if isinstance(self.old_value, (int, float)) and isinstance(self.new_value, (int, float)):
            if self.old_value != 0:
                self.delta_magnitude = abs(self.new_value - self.old_value) / abs(self.old_value)
            else:
                self.delta_magnitude = abs(self.new_value)


@dataclass
class Insight:
    """A user observation, rating, or learning stored for recall."""
    insight_id: str
    timestamp: str
    category: str         # "rating", "note", "favorite", "lesson", "goal"
    module: str = ""
    asset_id: str = ""
    content: str = ""
    score: float = 0.0    # 0–1 for ratings
    tags: list[str] = field(default_factory=list)
    session_id: str = ""


@dataclass
class GrowthMilestone:
    """A tracked milestone in the DUBFORGE journey."""
    milestone_id: str
    timestamp: str
    belt_rank: str = ""
    milestone_type: str = ""  # "fibonacci_session", "asset_count", "belt_promotion"
    description: str = ""
    session_number: int = 0
    total_assets: int = 0
    total_sessions: int = 0
    modules_mastered: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# MEMORY ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class MemoryEngine:
    """
    DUBFORGE Long-Term Memory System.

    Provides:
      - Session logging with Fibonacci-interval snapshots
      - Asset registry with lineage tracking
      - Parameter evolution timeline
      - Insight/rating storage
      - Growth milestone tracking
      - Phi-weighted recall for querying past outputs

    Usage:
        mem = MemoryEngine()
        mem.begin_session()
        mem.log_event("phi_core", "generate", {"frames": 256})
        mem.register_asset("wavetable", "output.wav", "phi_core", {...})
        mem.end_session()
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir or MEMORY_DIR
        self.sessions_dir = self.memory_dir / "sessions"
        self.index_file = self.memory_dir / "index.json"
        self.asset_file = self.memory_dir / "asset_registry.json"
        self.evolution_file = self.memory_dir / "evolution.json"
        self.insights_file = self.memory_dir / "insights.json"
        self.growth_file = self.memory_dir / "growth.json"

        _ensure_dirs()

        # Load master index
        self._index = _load_json(self.index_file, {
            "total_sessions": 0,
            "total_assets": 0,
            "total_events": 0,
            "total_insights": 0,
            "first_session_at": "",
            "last_session_at": "",
            "fibonacci_snapshots": [],
            "module_usage_counts": {},
            "growth_milestones": [],
        })

        # Current session state
        self._session: Optional[Session] = None
        self._session_events: list[MemoryEvent] = []
        self._session_start_time: float = 0.0

    # ─── Session Lifecycle ────────────────────────────────────────────

    def begin_session(self, notes: str = "") -> str:
        """Start a new memory session. Returns session_id."""
        _ensure_dirs()
        self._index = _load_json(self.index_file, self._index)

        session_num = self._index.get("total_sessions", 0) + 1
        session_id = f"session_{session_num:04d}_{int(time.time())}"
        is_fib = _is_fibonacci(session_num)

        self._session = Session(
            session_id=session_id,
            started_at=_timestamp(),
            session_number=session_num,
            is_fibonacci_session=is_fib,
            snapshot=is_fib,
            notes=notes,
        )
        self._session_events = []
        self._session_start_time = time.time()

        if is_fib:
            print(f"  [MEMORY] ✦ Fibonacci session #{session_num} — full snapshot will be taken")
        else:
            print(f"  [MEMORY] Session #{session_num} started")

        return session_id

    def end_session(self, notes: str = "") -> dict:
        """End the current session, persist all data, return summary."""
        if not self._session:
            return {"error": "No active session"}

        elapsed = time.time() - self._session_start_time
        self._session.ended_at = _timestamp()
        self._session.duration_s = round(elapsed, 2)
        self._session.total_events = len(self._session_events)
        self._session.events = [asdict(e) for e in self._session_events]
        self._session.modules_used = list(set(
            e.module for e in self._session_events
        ))
        if notes:
            self._session.notes = notes

        # Count assets generated this session
        asset_reg = _load_json(self.asset_file, {"assets": []})
        session_assets = [
            a for a in asset_reg.get("assets", [])
            if a.get("session_id") == self._session.session_id
        ]
        self._session.total_assets = len(session_assets)

        # Save session file
        session_file = self.sessions_dir / f"{self._session.session_id}.json"
        _save_json(session_file, asdict(self._session))

        # Update master index
        self._index["total_sessions"] = self._session.session_number
        self._index["last_session_at"] = self._session.ended_at
        if not self._index.get("first_session_at"):
            self._index["first_session_at"] = self._session.started_at
        self._index["total_events"] = self._index.get("total_events", 0) + len(self._session_events)

        # Track module usage
        for mod in self._session.modules_used:
            self._index["module_usage_counts"][mod] = \
                self._index.get("module_usage_counts", {}).get(mod, 0) + 1

        # Fibonacci snapshot marker
        if self._session.is_fibonacci_session:
            self._index.setdefault("fibonacci_snapshots", []).append({
                "session_number": self._session.session_number,
                "session_id": self._session.session_id,
                "timestamp": self._session.ended_at,
                "total_assets": self._index.get("total_assets", 0),
            })
            self._take_fibonacci_snapshot()

        _save_json(self.index_file, self._index)

        # Check for growth milestones
        self._check_milestones()

        summary = {
            "session_id": self._session.session_id,
            "session_number": self._session.session_number,
            "duration_s": self._session.duration_s,
            "events": self._session.total_events,
            "assets": self._session.total_assets,
            "modules": self._session.modules_used,
            "is_fibonacci": self._session.is_fibonacci_session,
        }

        print(f"  [MEMORY] Session #{self._session.session_number} complete — "
              f"{self._session.total_events} events, "
              f"{self._session.total_assets} assets, "
              f"{self._session.duration_s:.1f}s")

        self._session = None
        self._session_events = []
        return summary

    # ─── Event Logging ────────────────────────────────────────────────

    def log_event(self, module: str, action: str, params: Optional[dict] = None,
                  result_summary: str = "", output_files: Optional[list[str]] = None,
                  duration_ms: float = 0.0) -> MemoryEvent:
        """Log a single event in the current session."""
        event = MemoryEvent(
            timestamp=_timestamp(),
            module=module,
            action=action,
            params=params or {},
            result_summary=result_summary,
            output_files=output_files or [],
            duration_ms=duration_ms,
        )
        self._session_events.append(event)
        return event

    # ─── Asset Registry ───────────────────────────────────────────────

    def register_asset(self, asset_type: str, filename: str, module: str,
                       params: Optional[dict] = None, tags: Optional[list[str]] = None,
                       notes: str = "", parent_asset_id: str = "") -> Asset:
        """Register a generated asset in the master registry."""
        _ensure_dirs()

        # Determine file path and size
        filepath = Path(filename)
        size_bytes = filepath.stat().st_size if filepath.exists() else 0

        # Check for existing versions (lineage)
        registry = _load_json(self.asset_file, {"assets": [], "total": 0})
        existing = [
            a for a in registry.get("assets", [])
            if a.get("filename") == str(filename) and a.get("module") == module
        ]
        generation = len(existing) + 1

        session_id = self._session.session_id if self._session else "manual"

        asset = Asset(
            asset_id="",  # auto-generated in __post_init__
            asset_type=asset_type,
            filename=str(filename),
            path=str(filepath.resolve()) if filepath.exists() else str(filename),
            module=module,
            created_at=_timestamp(),
            session_id=session_id,
            params=params or {},
            size_bytes=size_bytes,
            tags=tags or [],
            notes=notes,
            generation=generation,
            parent_asset_id=parent_asset_id,
        )

        registry["assets"].append(asdict(asset))
        registry["total"] = len(registry["assets"])
        _save_json(self.asset_file, registry)

        # Update index
        self._index["total_assets"] = registry["total"]
        _save_json(self.index_file, self._index)

        return asset

    def get_asset_lineage(self, filename: str) -> list[dict]:
        """Get all versions/generations of an asset by filename."""
        registry = _load_json(self.asset_file, {"assets": []})
        lineage = [
            a for a in registry.get("assets", [])
            if a.get("filename") == filename
        ]
        return sorted(lineage, key=lambda a: a.get("generation", 0))

    def get_assets_by_module(self, module: str) -> list[dict]:
        """Get all assets generated by a specific module."""
        registry = _load_json(self.asset_file, {"assets": []})
        return [a for a in registry.get("assets", []) if a.get("module") == module]

    def get_assets_by_type(self, asset_type: str) -> list[dict]:
        """Get all assets of a specific type."""
        registry = _load_json(self.asset_file, {"assets": []})
        return [a for a in registry.get("assets", []) if a.get("asset_type") == asset_type]

    # ─── Parameter Evolution ─────────────────────────────────────────

    def track_param_change(self, module: str, param_key: str,
                           old_value: Any, new_value: Any):
        """Record a parameter change for evolution tracking."""
        _ensure_dirs()
        evolution = _load_json(self.evolution_file, {"changes": [], "param_history": {}})

        snap = ParamSnapshot(
            timestamp=_timestamp(),
            module=module,
            param_key=param_key,
            old_value=old_value,
            new_value=new_value,
            session_id=self._session.session_id if self._session else "manual",
        )
        snap.compute_delta()

        evolution["changes"].append(asdict(snap))
        # Cap changes list at Fibonacci-1597 to prevent unbounded growth
        _MAX_EVOLUTION_ENTRIES = 1597
        if len(evolution["changes"]) > _MAX_EVOLUTION_ENTRIES:
            evolution["changes"] = evolution["changes"][-_MAX_EVOLUTION_ENTRIES:]

        # Update param history (latest value per key)
        full_key = f"{module}.{param_key}"
        if full_key not in evolution["param_history"]:
            evolution["param_history"][full_key] = []
        evolution["param_history"][full_key].append({
            "value": new_value,
            "timestamp": snap.timestamp,
            "delta": snap.delta_magnitude,
        })
        # Cap per-key history at Fibonacci-233
        _MAX_PARAM_HISTORY = 233
        if len(evolution["param_history"][full_key]) > _MAX_PARAM_HISTORY:
            evolution["param_history"][full_key] = evolution["param_history"][full_key][-_MAX_PARAM_HISTORY:]

        _save_json(self.evolution_file, evolution)
        return snap

    def get_param_evolution(self, module: str, param_key: str) -> list[dict]:
        """Get the full history of a parameter over time."""
        evolution = _load_json(self.evolution_file, {"param_history": {}})
        full_key = f"{module}.{param_key}"
        return evolution.get("param_history", {}).get(full_key, [])

    def get_evolution_summary(self) -> dict:
        """Summary of all parameter changes across all sessions."""
        evolution = _load_json(self.evolution_file, {"changes": [], "param_history": {}})
        changes = evolution.get("changes", [])
        param_history = evolution.get("param_history", {})

        return {
            "total_changes": len(changes),
            "unique_params_tracked": len(param_history),
            "params": list(param_history.keys()),
            "avg_delta": (
                sum(c.get("delta_magnitude", 0) for c in changes) / len(changes)
                if changes else 0
            ),
            "most_volatile": sorted(
                param_history.keys(),
                key=lambda k: len(param_history[k]),
                reverse=True
            )[:10],
        }

    # ─── Insights & Ratings ──────────────────────────────────────────

    def add_insight(self, category: str, content: str, module: str = "",
                    asset_id: str = "", score: float = 0.0,
                    tags: Optional[list[str]] = None) -> Insight:
        """Store an insight, note, rating, or favorite."""
        _ensure_dirs()
        insights_data = _load_json(self.insights_file, {"insights": [], "total": 0})

        insight = Insight(
            insight_id=f"insight_{int(time.time())}_{len(insights_data.get('insights', []))}",
            timestamp=_timestamp(),
            category=category,
            module=module,
            asset_id=asset_id,
            content=content,
            score=score,
            tags=tags or [],
            session_id=self._session.session_id if self._session else "manual",
        )

        insights_data["insights"].append(asdict(insight))
        insights_data["total"] = len(insights_data["insights"])
        _save_json(self.insights_file, insights_data)

        self._index["total_insights"] = insights_data["total"]
        _save_json(self.index_file, self._index)

        return insight

    def rate_asset(self, asset_id_or_filename: str, score: float,
                   notes: str = "") -> Optional[Insight]:
        """Rate an asset (0–1 score). Also updates the asset registry."""
        # Update asset registry
        registry = _load_json(self.asset_file, {"assets": []})
        for asset in registry.get("assets", []):
            if (asset.get("asset_id") == asset_id_or_filename or
                    asset.get("filename") == asset_id_or_filename):
                asset["score"] = score
                if notes:
                    asset["notes"] = notes
                break
        _save_json(self.asset_file, registry)

        # Store as insight too
        return self.add_insight(
            category="rating",
            content=notes or f"Rated {score:.2f}",
            asset_id=asset_id_or_filename,
            score=score,
        )

    def get_top_rated(self, module: str = "", asset_type: str = "",
                      limit: int = 10) -> list[dict]:
        """Get highest-rated assets, optionally filtered by module/type."""
        registry = _load_json(self.asset_file, {"assets": []})
        assets = registry.get("assets", [])

        if module:
            assets = [a for a in assets if a.get("module") == module]
        if asset_type:
            assets = [a for a in assets if a.get("asset_type") == asset_type]

        # Sort by score descending
        return sorted(assets, key=lambda a: a.get("score", 0), reverse=True)[:limit]

    # ─── Recall System ────────────────────────────────────────────────

    def recall(self, module: str = "", action: str = "", min_score: float = 0.0,
               tags: Optional[list[str]] = None, limit: int = 10,
               recency_weight: bool = True) -> list[dict]:
        """
        Query past sessions and assets with phi-weighted relevance scoring.

        Returns a ranked list of assets/events matching the query,
        scored by recency × quality × frequency (phi-weighted).
        """
        registry = _load_json(self.asset_file, {"assets": []})
        assets = registry.get("assets", [])

        results = []
        for asset in assets:
            # Filter
            if module and asset.get("module") != module:
                continue
            if min_score > 0 and asset.get("score", 0) < min_score:
                continue
            if tags:
                asset_tags = set(asset.get("tags", []))
                if not asset_tags.intersection(set(tags)):
                    continue

            # Compute relevance score
            created = asset.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created)
                age_s = (datetime.now(timezone.utc) - created_dt).total_seconds()
            except (ValueError, TypeError):
                age_s = 86400 * 30  # default to 30 days old

            recency = phi_recency_score(age_s) if recency_weight else 1.0
            quality = asset.get("score", 0.5)
            generation = asset.get("generation", 1)

            relevance = phi_relevance(recency, quality, generation)

            results.append({
                **asset,
                "_relevance": round(relevance, 6),
                "_recency": round(recency, 4),
                "_age_hours": round(age_s / 3600, 1),
            })

        # Sort by relevance descending
        results.sort(key=lambda r: r["_relevance"], reverse=True)
        return results[:limit]

    def recall_events(self, module: str = "", action: str = "",
                      last_n_sessions: int = 5) -> list[dict]:
        """Recall events from recent sessions."""
        session_files = sorted(
            self.sessions_dir.glob("session_*.json"),
            reverse=True
        )[:last_n_sessions]

        events = []
        for sf in session_files:
            session_data = _load_json(sf, {})
            for event in session_data.get("events", []):
                if module and event.get("module") != module:
                    continue
                if action and event.get("action") != action:
                    continue
                event["_session_id"] = session_data.get("session_id", "")
                events.append(event)

        return events

    def recall_sessions(self, last_n: int = 10) -> list[dict]:
        """Get summaries of the last N sessions."""
        session_files = sorted(
            self.sessions_dir.glob("session_*.json"),
            reverse=True
        )[:last_n]

        summaries = []
        for sf in session_files:
            data = _load_json(sf, {})
            summaries.append({
                "session_id": data.get("session_id"),
                "session_number": data.get("session_number"),
                "started_at": data.get("started_at"),
                "duration_s": data.get("duration_s"),
                "total_events": data.get("total_events"),
                "total_assets": data.get("total_assets"),
                "modules_used": data.get("modules_used"),
                "is_fibonacci": data.get("is_fibonacci_session"),
                "notes": data.get("notes"),
            })

        return summaries

    # ─── Growth Tracking ─────────────────────────────────────────────

    def get_growth_status(self) -> dict:
        """Get current growth status and progress toward milestones."""
        growth = _load_json(self.growth_file, {
            "milestones": [],
            "current_belt": "White Belt",
            "total_tracks": 0,
        })

        total_sessions = self._index.get("total_sessions", 0)
        total_assets = self._index.get("total_assets", 0)
        module_counts = self._index.get("module_usage_counts", {})
        modules_used = [m for m, c in module_counts.items() if c >= 3]

        # Next Fibonacci milestone
        next_fib = 1
        for f in FIBONACCI:
            if f > total_sessions:
                next_fib = f
                break

        return {
            "current_belt": growth.get("current_belt", "White Belt"),
            "total_sessions": total_sessions,
            "total_assets": total_assets,
            "total_events": self._index.get("total_events", 0),
            "total_insights": self._index.get("total_insights", 0),
            "modules_experienced": modules_used,
            "module_usage": module_counts,
            "next_fibonacci_session": next_fib,
            "sessions_until_fibonacci": next_fib - total_sessions,
            "milestones_reached": len(growth.get("milestones", [])),
            "first_session": self._index.get("first_session_at", ""),
            "last_session": self._index.get("last_session_at", ""),
        }

    def promote_belt(self, new_rank: str, description: str = ""):
        """Record a belt promotion milestone."""
        growth = _load_json(self.growth_file, {"milestones": [], "current_belt": "White Belt"})

        milestone = GrowthMilestone(
            milestone_id=f"belt_{new_rank.lower().replace(' ', '_')}_{int(time.time())}",
            timestamp=_timestamp(),
            belt_rank=new_rank,
            milestone_type="belt_promotion",
            description=description or f"Promoted to {new_rank}",
            session_number=self._index.get("total_sessions", 0),
            total_assets=self._index.get("total_assets", 0),
            total_sessions=self._index.get("total_sessions", 0),
        )

        growth["milestones"].append(asdict(milestone))
        growth["current_belt"] = new_rank
        _save_json(self.growth_file, growth)

        print(f"  [MEMORY] ★ BELT PROMOTION: {new_rank} — {description}")

    # ─── Fibonacci Snapshots ─────────────────────────────────────────

    def _take_fibonacci_snapshot(self):
        """Take a full state snapshot at Fibonacci-numbered sessions."""
        if not self._session:
            return

        snapshot_dir = self.memory_dir / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot = {
            "session_number": self._session.session_number,
            "timestamp": _timestamp(),
            "index": dict(self._index),
            "asset_count": self._index.get("total_assets", 0),
            "evolution_summary": self.get_evolution_summary(),
            "growth_status": self.get_growth_status(),
            "top_assets": self.get_top_rated(limit=5),
        }

        snapshot_file = snapshot_dir / f"snapshot_fib_{self._session.session_number:04d}.json"
        _save_json(snapshot_file, snapshot)
        print(f"  [MEMORY] ✦ Fibonacci snapshot saved: {snapshot_file.name}")

    # ─── Milestone Checks ────────────────────────────────────────────

    def _check_milestones(self):
        """Check for and record any new growth milestones."""
        growth = _load_json(self.growth_file, {"milestones": [], "current_belt": "White Belt"})
        existing_types = {
            m.get("milestone_type") + "_" + str(m.get("session_number", 0))
            for m in growth.get("milestones", [])
        }

        total_sessions = self._index.get("total_sessions", 0)
        total_assets = self._index.get("total_assets", 0)

        new_milestones = []

        # Fibonacci session milestones
        if _is_fibonacci(total_sessions):
            key = f"fibonacci_session_{total_sessions}"
            if key not in existing_types:
                new_milestones.append(GrowthMilestone(
                    milestone_id=f"fib_session_{total_sessions}_{int(time.time())}",
                    timestamp=_timestamp(),
                    milestone_type="fibonacci_session",
                    description=f"Reached Fibonacci session #{total_sessions}",
                    session_number=total_sessions,
                    total_assets=total_assets,
                    total_sessions=total_sessions,
                ))

        # Asset count milestones (at Fibonacci numbers)
        for fib in FIBONACCI:
            if total_assets >= fib:
                key = f"asset_count_{fib}"
                if key not in existing_types:
                    new_milestones.append(GrowthMilestone(
                        milestone_id=f"assets_{fib}_{int(time.time())}",
                        timestamp=_timestamp(),
                        milestone_type="asset_count",
                        description=f"Generated {fib}+ assets (Fibonacci milestone)",
                        session_number=total_sessions,
                        total_assets=total_assets,
                        total_sessions=total_sessions,
                    ))

        # Auto-promote belt using Dojo belt progression thresholds
        current_belt = growth.get("current_belt", "White Belt")
        belt_thresholds = [
            ("White Belt",  1,  1),
            ("Yellow Belt", 3,  8),
            ("Green Belt",  8,  21),
            ("Blue Belt",   13, 55),
            ("Purple Belt", 21, 89),
            ("Brown Belt",  55, 144),
            ("Black Belt",  89, 233),
        ]
        for belt_name, sessions_req, assets_req in belt_thresholds:
            if total_sessions >= sessions_req and total_assets >= assets_req:
                if belt_name != current_belt:
                    # Only promote forward, never demote
                    belt_order = [b[0] for b in belt_thresholds]
                    if belt_order.index(belt_name) > belt_order.index(current_belt):
                        current_belt = belt_name
        if current_belt != growth.get("current_belt", "White Belt"):
            promo_key = f"belt_promotion_{current_belt}"
            if promo_key not in existing_types:
                new_milestones.append(GrowthMilestone(
                    milestone_id=f"belt_{current_belt.lower().replace(' ', '_')}_{int(time.time())}",
                    timestamp=_timestamp(),
                    belt_rank=current_belt,
                    milestone_type="belt_promotion",
                    description=f"Auto-promoted to {current_belt}",
                    session_number=total_sessions,
                    total_assets=total_assets,
                    total_sessions=total_sessions,
                ))
                growth["current_belt"] = current_belt
                print(f"  [MEMORY] ★ BELT PROMOTION: {current_belt}")

        for ms in new_milestones:
            growth["milestones"].append(asdict(ms))
            print(f"  [MEMORY] ★ Milestone: {ms.description}")

        if new_milestones:
            _save_json(self.growth_file, growth)

    # ─── Status & Diagnostics ────────────────────────────────────────

    def status(self) -> dict:
        """Full memory system status."""
        _ensure_dirs()
        self._index = _load_json(self.index_file, self._index)

        session_files = list(self.sessions_dir.glob("session_*.json"))
        registry = _load_json(self.asset_file, {"assets": []})
        evolution = _load_json(self.evolution_file, {"changes": []})
        insights = _load_json(self.insights_file, {"insights": []})
        growth = _load_json(self.growth_file, {"milestones": []})

        return {
            "memory_dir": str(self.memory_dir),
            "total_sessions": self._index.get("total_sessions", 0),
            "total_assets": len(registry.get("assets", [])),
            "total_events": self._index.get("total_events", 0),
            "total_param_changes": len(evolution.get("changes", [])),
            "total_insights": len(insights.get("insights", [])),
            "total_milestones": len(growth.get("milestones", [])),
            "session_files_on_disk": len(session_files),
            "active_session": self._session.session_id if self._session else None,
            "module_usage": self._index.get("module_usage_counts", {}),
            "first_session": self._index.get("first_session_at", ""),
            "last_session": self._index.get("last_session_at", ""),
        }

    def print_status(self):
        """Print a human-readable memory status report."""
        s = self.status()
        growth = self.get_growth_status()

        print()
        print("═" * 60)
        print("  DUBFORGE MEMORY — Long-Term Persistence Status")
        print("═" * 60)
        print(f"  Belt Rank:        {growth.get('current_belt', 'White Belt')}")
        print(f"  Total Sessions:   {s['total_sessions']}")
        print(f"  Total Assets:     {s['total_assets']}")
        print(f"  Total Events:     {s['total_events']}")
        print(f"  Param Changes:    {s['total_param_changes']}")
        print(f"  Insights:         {s['total_insights']}")
        print(f"  Milestones:       {s['total_milestones']}")
        print(f"  Active Session:   {s['active_session'] or 'None'}")
        print(f"  Next Fibonacci:   Session #{growth.get('next_fibonacci_session', '?')}")
        print(f"  First Session:    {s['first_session'] or 'Never'}")
        print(f"  Last Session:     {s['last_session'] or 'Never'}")

        if s.get("module_usage"):
            print()
            print("  Module Usage:")
            for mod, count in sorted(s["module_usage"].items(),
                                      key=lambda x: x[1], reverse=True):
                bar = "█" * min(count, 30)
                print(f"    {mod:20s}  {bar} ({count})")

        print("═" * 60)
        print()


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE — Global instance
# ═══════════════════════════════════════════════════════════════════════════

_global_memory: Optional[MemoryEngine] = None


def get_memory() -> MemoryEngine:
    """Get or create the global MemoryEngine instance."""
    global _global_memory
    if _global_memory is None:
        _global_memory = MemoryEngine()
    return _global_memory


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Print memory status and run a diagnostic session."""
    print("[MEMORY ENGINE] DUBFORGE Long-Term Memory System")
    print("-" * 40)

    mem = get_memory()
    mem.print_status()

    # Demo: start/end a diagnostic session
    mem.begin_session(notes="Memory system diagnostic run")
    mem.log_event("memory", "diagnostic", {"test": True},
                  result_summary="Memory engine initialized and running")
    summary = mem.end_session(notes="Diagnostic complete")

    print()
    print("Diagnostic summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print()

    # Show growth
    growth = mem.get_growth_status()
    print("Growth Status:")
    for k, v in growth.items():
        print(f"  {k}: {v}")
    print()
    print("[MEMORY ENGINE] Done.")


if __name__ == "__main__":
    main()
