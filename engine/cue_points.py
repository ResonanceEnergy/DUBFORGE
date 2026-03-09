"""
DUBFORGE — Cue Point Manager  (Session 200)

Manage cue points, markers, and regions in audio files.
Support for DJ cue points, arrangement markers,
loop regions, and PHI-aligned cue placement.
"""

import json
import os
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class CuePoint:
    """A single cue point."""
    position: float  # seconds
    label: str = ""
    color: str = "#FFD700"
    cue_type: str = "marker"  # marker, loop_start, loop_end, hot_cue

    def to_dict(self) -> dict:
        return {
            "position": round(self.position, 3),
            "label": self.label,
            "color": self.color,
            "type": self.cue_type,
        }


@dataclass
class Region:
    """A labeled region."""
    start: float
    end: float
    label: str = ""
    color: str = "#4CAF50"
    region_type: str = "section"  # section, loop, selection

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "label": self.label,
            "color": self.color,
            "type": self.region_type,
        }


@dataclass
class CueMap:
    """Complete cue/marker map for a file."""
    filepath: str
    duration: float = 0.0
    bpm: float = 140.0
    cues: list[CuePoint] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "file": self.filepath,
            "duration": round(self.duration, 3),
            "bpm": self.bpm,
            "cues": [c.to_dict() for c in self.cues],
            "regions": [r.to_dict() for r in self.regions],
        }


# Standard dubstep arrangement sections
DUBSTEP_SECTIONS = [
    ("Intro", 0.0, 16),
    ("Build", 16, 8),
    ("Drop 1", 24, 16),
    ("Breakdown", 40, 8),
    ("Build 2", 48, 8),
    ("Drop 2", 56, 16),
    ("Outro", 72, 8),
]

# Color palette
SECTION_COLORS = {
    "Intro": "#2196F3",
    "Build": "#FF9800",
    "Drop": "#F44336",
    "Breakdown": "#9C27B0",
    "Outro": "#607D8B",
    "Bridge": "#00BCD4",
    "Verse": "#4CAF50",
    "Chorus": "#E91E63",
}


class CuePointManager:
    """Manage cue points and regions."""

    def __init__(self, data_dir: str = "output/cues"):
        self.data_dir = data_dir
        self.cue_maps: dict[str, CueMap] = {}
        os.makedirs(data_dir, exist_ok=True)

    def create_map(self, filepath: str, duration: float,
                   bpm: float = 140.0) -> CueMap:
        """Create a new cue map."""
        cmap = CueMap(
            filepath=filepath,
            duration=duration,
            bpm=bpm,
        )
        self.cue_maps[filepath] = cmap
        return cmap

    def add_cue(self, filepath: str, position: float,
                label: str = "", **kwargs) -> CuePoint | None:
        """Add a cue point."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return None

        cue = CuePoint(
            position=position,
            label=label or f"Cue {len(cmap.cues) + 1}",
            color=kwargs.get("color", "#FFD700"),
            cue_type=kwargs.get("cue_type", "marker"),
        )
        cmap.cues.append(cue)
        cmap.cues.sort(key=lambda c: c.position)
        return cue

    def add_region(self, filepath: str, start: float, end: float,
                   label: str = "", **kwargs) -> Region | None:
        """Add a region."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return None

        region = Region(
            start=start,
            end=end,
            label=label or f"Region {len(cmap.regions) + 1}",
            color=kwargs.get("color", "#4CAF50"),
            region_type=kwargs.get("region_type", "section"),
        )
        cmap.regions.append(region)
        cmap.regions.sort(key=lambda r: r.start)
        return region

    def generate_beat_cues(self, filepath: str) -> list[CuePoint]:
        """Generate cue points at each beat."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return []

        beat_duration = 60.0 / cmap.bpm
        cues: list[CuePoint] = []
        t = 0.0
        beat = 1

        while t < cmap.duration:
            bar = (beat - 1) // 4 + 1
            beat_in_bar = (beat - 1) % 4 + 1
            label = f"Bar {bar}.{beat_in_bar}"
            cue = CuePoint(
                position=t, label=label,
                color="#888888" if beat_in_bar != 1 else "#FFD700",
                cue_type="marker",
            )
            cues.append(cue)
            t += beat_duration
            beat += 1

        cmap.cues.extend(cues)
        cmap.cues.sort(key=lambda c: c.position)
        return cues

    def generate_dubstep_sections(self, filepath: str) -> list[Region]:
        """Generate standard dubstep arrangement sections."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return []

        bar_duration = 4 * 60.0 / cmap.bpm  # 4 beats per bar
        regions: list[Region] = []

        for name, start_bar, length_bars in DUBSTEP_SECTIONS:
            start = start_bar * bar_duration
            end = (start_bar + length_bars) * bar_duration

            if start >= cmap.duration:
                break

            end = min(end, cmap.duration)
            color = "#F44336"  # default
            for key, col in SECTION_COLORS.items():
                if key.lower() in name.lower():
                    color = col
                    break

            region = Region(
                start=start, end=end,
                label=name, color=color,
                region_type="section",
            )
            regions.append(region)

        cmap.regions.extend(regions)
        cmap.regions.sort(key=lambda r: r.start)
        return regions

    def generate_phi_cues(self, filepath: str) -> list[CuePoint]:
        """Generate cue points at PHI-ratio positions."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return []

        cues: list[CuePoint] = []
        positions = [
            cmap.duration / PHI,                    # ~61.8%
            cmap.duration / (PHI ** 2),             # ~38.2%
            cmap.duration / (PHI ** 3),             # ~23.6%
            cmap.duration * (1 - 1 / PHI),          # ~38.2% from end
            cmap.duration * (1 - 1 / (PHI ** 2)),   # ~61.8% from end
        ]

        labels = ["PHI", "PHI²", "PHI³", "1-PHI⁻¹", "1-PHI⁻²"]

        for pos, label in zip(positions, labels):
            if 0 < pos < cmap.duration:
                cue = CuePoint(
                    position=pos,
                    label=f"Φ {label}",
                    color="#FFD700",
                    cue_type="marker",
                )
                cues.append(cue)

        cmap.cues.extend(cues)
        cmap.cues.sort(key=lambda c: c.position)
        return cues

    def find_cue_at(self, filepath: str, position: float,
                    tolerance: float = 0.1) -> CuePoint | None:
        """Find cue point near position."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return None

        for cue in cmap.cues:
            if abs(cue.position - position) <= tolerance:
                return cue
        return None

    def find_region_at(self, filepath: str,
                       position: float) -> Region | None:
        """Find region containing position."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return None

        for region in cmap.regions:
            if region.start <= position <= region.end:
                return region
        return None

    def snap_to_beat(self, filepath: str,
                     position: float) -> float:
        """Snap position to nearest beat."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return position

        beat_duration = 60.0 / cmap.bpm
        beats = position / beat_duration
        snapped_beats = round(beats)
        return snapped_beats * beat_duration

    def save(self, filepath: str) -> None:
        """Save cue map to JSON."""
        cmap = self.cue_maps.get(filepath)
        if not cmap:
            return

        name = os.path.splitext(os.path.basename(filepath))[0]
        out = os.path.join(self.data_dir, f"{name}_cues.json")
        with open(out, "w") as f:
            json.dump(cmap.to_dict(), f, indent=2)

    def load(self, json_path: str) -> CueMap | None:
        """Load cue map from JSON."""
        if not os.path.exists(json_path):
            return None

        with open(json_path) as f:
            data = json.load(f)

        cmap = CueMap(
            filepath=data["file"],
            duration=data["duration"],
            bpm=data.get("bpm", 140.0),
        )

        for cd in data.get("cues", []):
            cmap.cues.append(CuePoint(
                position=cd["position"],
                label=cd.get("label", ""),
                color=cd.get("color", "#FFD700"),
                cue_type=cd.get("type", "marker"),
            ))

        for rd in data.get("regions", []):
            cmap.regions.append(Region(
                start=rd["start"],
                end=rd["end"],
                label=rd.get("label", ""),
                color=rd.get("color", "#4CAF50"),
                region_type=rd.get("type", "section"),
            ))

        self.cue_maps[cmap.filepath] = cmap
        return cmap

    def get_summary(self) -> dict:
        """Get cue point manager summary."""
        total_cues = sum(len(c.cues) for c in self.cue_maps.values())
        total_regions = sum(len(c.regions) for c in self.cue_maps.values())
        return {
            "maps": len(self.cue_maps),
            "total_cues": total_cues,
            "total_regions": total_regions,
        }


def main() -> None:
    print("Cue Point Manager")

    mgr = CuePointManager()

    # Create map for a 3-minute track
    duration = 180.0
    _cmap = mgr.create_map("test_track.wav", duration, bpm=140)

    # Generate sections
    sections = mgr.generate_dubstep_sections("test_track.wav")
    print(f"  Sections: {len(sections)}")
    for s in sections:
        print(f"    {s.label}: {s.start:.1f}s → {s.end:.1f}s")

    # PHI cues
    phi_cues = mgr.generate_phi_cues("test_track.wav")
    print(f"\n  PHI cues: {len(phi_cues)}")
    for c in phi_cues:
        print(f"    {c.label}: {c.position:.2f}s")

    # Snap
    snapped = mgr.snap_to_beat("test_track.wav", 5.3)
    print(f"\n  Snap 5.3s → {snapped:.3f}s")

    # Summary
    print(f"  Summary: {mgr.get_summary()}")
    print("Done.")


if __name__ == "__main__":
    main()
