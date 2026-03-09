"""
DUBFORGE — Preset Browser Engine  (Session 152)

Browse, search, and preview presets for all DUBFORGE modules.
Aggregates .yaml, .json, and Python-dict presets into a unified catalog.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class Preset:
    """A single preset entry."""
    name: str
    module: str
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    source: str = ""  # file path or "builtin"
    uid: str = ""

    def __post_init__(self):
        if not self.uid:
            h = hashlib.md5(
                f"{self.module}:{self.name}".encode()
            ).hexdigest()[:8]
            self.uid = h

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "module": self.module,
            "category": self.category,
            "tags": self.tags,
            "params": self.params,
            "source": self.source,
        }


# Built-in presets for core modules
BUILTIN_PRESETS: list[dict] = [
    # Sub Bass
    {"name": "Deep Sub", "module": "sub_bass", "category": "bass",
     "tags": ["deep", "sub", "low"], "params": {"freq": 36, "decay": 2.0}},
    {"name": "Phi Sub", "module": "sub_bass", "category": "bass",
     "tags": ["phi", "sub", "golden"], "params": {"freq": 36 * PHI,
                                                    "decay": 1.618}},
    {"name": "Rumble Sub", "module": "sub_bass", "category": "bass",
     "tags": ["rumble", "distorted"], "params": {"freq": 30, "drive": 0.8}},
    # Wobble Bass
    {"name": "Classic Wobble", "module": "wobble_bass", "category": "bass",
     "tags": ["wobble", "dubstep"], "params": {"rate": 4, "depth": 0.8}},
    {"name": "Fast Wobble", "module": "wobble_bass", "category": "bass",
     "tags": ["wobble", "fast", "neuro"],
     "params": {"rate": 8, "depth": 0.9}},
    {"name": "Phi Wobble", "module": "wobble_bass", "category": "bass",
     "tags": ["phi", "wobble", "golden"],
     "params": {"rate": PHI * 3, "depth": 1.0 / PHI}},
    # Lead Synth
    {"name": "Screech Lead", "module": "lead_synth", "category": "lead",
     "tags": ["screech", "aggressive"], "params": {"freq": 440,
                                                     "harmonics": 8}},
    {"name": "Smooth Lead", "module": "lead_synth", "category": "lead",
     "tags": ["smooth", "melodic"], "params": {"freq": 440, "drive": 0.3}},
    # Pad Synth
    {"name": "Evolving Pad", "module": "pad_synth", "category": "pad",
     "tags": ["evolving", "ambient"], "params": {"voices": 5,
                                                   "detune": 0.03}},
    {"name": "Dark Pad", "module": "pad_synth", "category": "pad",
     "tags": ["dark", "moody"], "params": {"voices": 3, "cutoff": 800}},
    # Drums
    {"name": "Heavy Kit", "module": "drum_generator", "category": "drums",
     "tags": ["heavy", "hard"], "params": {"bpm": 140}},
    {"name": "Trap Kit", "module": "drum_generator", "category": "drums",
     "tags": ["trap", "808"], "params": {"bpm": 140, "style": "trap"}},
    {"name": "Halftime Kit", "module": "drum_generator", "category": "drums",
     "tags": ["halftime", "dnb"], "params": {"bpm": 170}},
    # Arp Synth
    {"name": "Fast Arp", "module": "arp_synth", "category": "arp",
     "tags": ["fast", "arp"], "params": {"rate": 16, "octaves": 2}},
    {"name": "Phi Arp", "module": "arp_synth", "category": "arp",
     "tags": ["phi", "golden", "arp"],
     "params": {"rate": int(PHI * 8), "octaves": 3}},
    # Riser
    {"name": "8 Bar Riser", "module": "riser_synth", "category": "fx",
     "tags": ["riser", "buildup"], "params": {"duration": 8.0}},
    {"name": "Phi Riser", "module": "riser_synth", "category": "fx",
     "tags": ["phi", "riser"], "params": {"duration": PHI * 3}},
    # Impact
    {"name": "Heavy Impact", "module": "impact_hit", "category": "fx",
     "tags": ["impact", "drop"], "params": {"intensity": 1.0}},
    # Drone
    {"name": "Deep Drone", "module": "drone_synth", "category": "ambient",
     "tags": ["drone", "deep"], "params": {"freq": 55, "harmonics": 6}},
    # Glitch
    {"name": "Stutter Glitch", "module": "glitch_engine", "category": "fx",
     "tags": ["glitch", "stutter"], "params": {"slices": 16,
                                                 "probability": 0.7}},
    # Riddim
    {"name": "Riddim Growl", "module": "riddim_engine", "category": "bass",
     "tags": ["riddim", "growl", "aggressive"],
     "params": {"freq": 80, "drive": 0.9}},
]


class PresetBrowser:
    """Unified preset browser."""

    def __init__(self, presets_dir: str = "output/presets"):
        self._presets: list[Preset] = []
        self._presets_dir = presets_dir
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Load built-in presets."""
        for p in BUILTIN_PRESETS:
            self._presets.append(Preset(
                name=p["name"],
                module=p["module"],
                category=p.get("category", "general"),
                tags=p.get("tags", []),
                params=p.get("params", {}),
                source="builtin",
            ))

    def scan_directory(self, path: str | None = None) -> int:
        """Scan a directory for preset files."""
        scan_path = path or self._presets_dir
        count = 0
        if not os.path.isdir(scan_path):
            return 0

        for root, _dirs, files in os.walk(scan_path):
            for f in files:
                fp = os.path.join(root, f)
                if f.endswith(".json"):
                    count += self._load_json_preset(fp)
        return count

    def _load_json_preset(self, path: str) -> int:
        """Load preset(s) from a JSON file."""
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return 0

        presets = data if isinstance(data, list) else [data]
        count = 0
        for p in presets:
            if "name" in p and "module" in p:
                self._presets.append(Preset(
                    name=p["name"],
                    module=p["module"],
                    category=p.get("category", "general"),
                    tags=p.get("tags", []),
                    params=p.get("params", {}),
                    source=path,
                ))
                count += 1
        return count

    def search(self, query: str) -> list[Preset]:
        """Search presets by name, module, category, or tags."""
        q = query.lower()
        results = []
        for p in self._presets:
            if (q in p.name.lower()
                    or q in p.module.lower()
                    or q in p.category.lower()
                    or any(q in t for t in p.tags)):
                results.append(p)
        return results

    def by_module(self, module: str) -> list[Preset]:
        """Get all presets for a specific module."""
        m = module.lower()
        return [p for p in self._presets if m in p.module.lower()]

    def by_category(self, category: str) -> list[Preset]:
        """Get all presets in a category."""
        c = category.lower()
        return [p for p in self._presets if c == p.category.lower()]

    def by_tag(self, tag: str) -> list[Preset]:
        """Get all presets with a specific tag."""
        t = tag.lower()
        return [p for p in self._presets if t in p.tags]

    def get(self, uid: str) -> Preset | None:
        """Get a preset by UID."""
        for p in self._presets:
            if p.uid == uid:
                return p
        return None

    def all_presets(self) -> list[Preset]:
        """Return all presets."""
        return list(self._presets)

    def categories(self) -> list[str]:
        """List all categories."""
        return sorted({p.category for p in self._presets})

    def modules(self) -> list[str]:
        """List all modules with presets."""
        return sorted({p.module for p in self._presets})

    def tags(self) -> list[str]:
        """List all tags."""
        all_tags: set[str] = set()
        for p in self._presets:
            all_tags.update(p.tags)
        return sorted(all_tags)

    def add(self, preset: Preset) -> None:
        """Add a preset."""
        self._presets.append(preset)

    def remove(self, uid: str) -> bool:
        """Remove a preset by UID."""
        for i, p in enumerate(self._presets):
            if p.uid == uid:
                self._presets.pop(i)
                return True
        return False

    def count(self) -> int:
        return len(self._presets)

    def to_dict(self) -> dict:
        return {
            "count": self.count(),
            "categories": self.categories(),
            "modules": self.modules(),
            "presets": [p.to_dict() for p in self._presets],
        }

    def summary_text(self) -> str:
        """Human-readable summary."""
        lines = [
            f"**Preset Browser** — {self.count()} presets",
            f"Categories: {', '.join(self.categories())}",
            f"Modules: {', '.join(self.modules())}",
            f"Tags: {', '.join(self.tags()[:20])}",
        ]
        return "\n".join(lines)


# Module-level singleton
_browser: PresetBrowser | None = None


def get_browser() -> PresetBrowser:
    global _browser
    if _browser is None:
        _browser = PresetBrowser()
    return _browser


def main() -> None:
    print("Preset Browser Engine")
    b = get_browser()
    print(f"  Loaded {b.count()} presets")
    print(f"  Categories: {b.categories()}")
    print(f"  Modules: {b.modules()}")

    results = b.search("wobble")
    print(f"  Search 'wobble': {len(results)} results")
    for r in results:
        print(f"    {r.name} ({r.module}) — {r.tags}")

    results = b.by_tag("phi")
    print(f"  Tag 'phi': {len(results)} results")
    for r in results:
        print(f"    {r.name} ({r.module})")
    print("Done.")


if __name__ == "__main__":
    main()
