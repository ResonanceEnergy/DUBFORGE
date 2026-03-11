"""
DUBFORGE — Project Manager Engine  (Session 183)

Manages DUBFORGE projects: tracks, metadata, assets,
versions, and export configurations.
"""

import json
import os
import time
from dataclasses import dataclass, field

from engine.config_loader import PHI
@dataclass
class Asset:
    """A project asset (audio file, preset, etc.)."""
    name: str
    asset_type: str  # "audio", "preset", "midi", "wavetable"
    path: str
    size_bytes: int = 0
    created_at: float = 0.0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.asset_type,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "tags": self.tags,
        }


@dataclass
class TrackSlot:
    """A track in the project."""
    name: str
    module: str  # Engine module used
    muted: bool = False
    solo: bool = False
    volume: float = 0.8
    pan: float = 0.0
    params: dict = field(default_factory=dict)
    assets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "module": self.module,
            "muted": self.muted,
            "solo": self.solo,
            "volume": self.volume,
            "pan": self.pan,
            "params": self.params,
            "assets": self.assets,
        }


@dataclass
class ProjectVersion:
    """A project version snapshot."""
    version: str
    timestamp: float
    description: str
    track_count: int
    asset_count: int

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "description": self.description,
            "tracks": self.track_count,
            "assets": self.asset_count,
        }


@dataclass
class Project:
    """A DUBFORGE project."""
    name: str
    bpm: float = 140.0
    key: str = "F"
    scale: str = "minor"
    created_at: float = 0.0
    modified_at: float = 0.0
    tracks: list[TrackSlot] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    versions: list[ProjectVersion] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        self.modified_at = time.time()

    def add_track(self, name: str, module: str, **params) -> TrackSlot:
        track = TrackSlot(name=name, module=module, params=params)
        self.tracks.append(track)
        self.modified_at = time.time()
        return track

    def remove_track(self, name: str) -> bool:
        for i, t in enumerate(self.tracks):
            if t.name == name:
                self.tracks.pop(i)
                self.modified_at = time.time()
                return True
        return False

    def add_asset(self, name: str, asset_type: str, path: str,
                   tags: list[str] | None = None) -> Asset:
        size = 0
        if os.path.exists(path):
            size = os.path.getsize(path)
        asset = Asset(name, asset_type, path, size, time.time(), tags or [])
        self.assets.append(asset)
        self.modified_at = time.time()
        return asset

    def snapshot(self, version: str, description: str = "") -> ProjectVersion:
        pv = ProjectVersion(
            version=version,
            timestamp=time.time(),
            description=description,
            track_count=len(self.tracks),
            asset_count=len(self.assets),
        )
        self.versions.append(pv)
        return pv

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bpm": self.bpm,
            "key": self.key,
            "scale": self.scale,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "tracks": [t.to_dict() for t in self.tracks],
            "assets": [a.to_dict() for a in self.assets],
            "versions": [v.to_dict() for v in self.versions],
            "metadata": self.metadata,
        }


class ProjectManager:
    """Manages multiple projects."""

    def __init__(self, projects_dir: str = "output/projects"):
        self.projects_dir = projects_dir
        self.projects: dict[str, Project] = {}
        self.active_project: str | None = None

    def create_project(self, name: str, bpm: float = 140.0,
                        key: str = "F") -> Project:
        project = Project(name=name, bpm=bpm, key=key)
        self.projects[name] = project
        self.active_project = name
        return project

    def get_active(self) -> Project | None:
        if self.active_project:
            return self.projects.get(self.active_project)
        return None

    def list_projects(self) -> list[str]:
        return list(self.projects.keys())

    def save_project(self, name: str | None = None) -> str:
        pname = name or self.active_project
        if not pname or pname not in self.projects:
            return ""

        project = self.projects[pname]
        os.makedirs(self.projects_dir, exist_ok=True)
        path = os.path.join(self.projects_dir,
                             f"{pname.replace(' ', '_').lower()}.json")

        with open(path, "w") as f:
            json.dump(project.to_dict(), f, indent=2)

        return path

    def load_project(self, path: str) -> Project | None:
        if not os.path.exists(path):
            return None

        with open(path) as f:
            data = json.load(f)

        project = Project(
            name=data.get("name", "Untitled"),
            bpm=data.get("bpm", 140.0),
            key=data.get("key", "F"),
            scale=data.get("scale", "minor"),
            created_at=data.get("created_at", 0),
            modified_at=data.get("modified_at", 0),
            metadata=data.get("metadata", {}),
        )

        for t in data.get("tracks", []):
            track = TrackSlot(
                name=t.get("name", ""),
                module=t.get("module", ""),
                muted=t.get("muted", False),
                solo=t.get("solo", False),
                volume=t.get("volume", 0.8),
                pan=t.get("pan", 0.0),
                params=t.get("params", {}),
                assets=t.get("assets", []),
            )
            project.tracks.append(track)

        self.projects[project.name] = project
        self.active_project = project.name
        return project

    def delete_project(self, name: str) -> bool:
        if name in self.projects:
            del self.projects[name]
            if self.active_project == name:
                self.active_project = None
            return True
        return False

    def get_summary(self) -> dict:
        return {
            "projects": self.list_projects(),
            "active": self.active_project,
            "total_tracks": sum(
                len(p.tracks) for p in self.projects.values()
            ),
            "total_assets": sum(
                len(p.assets) for p in self.projects.values()
            ),
        }


def create_default_project(name: str = "DUBFORGE Session") -> Project:
    """Create a project with standard dubstep tracks."""
    project = Project(name=name, bpm=140.0, key="F", scale="minor")

    project.add_track("Sub Bass", "sub_bass", frequency=55, drive=0.3)
    project.add_track("Wobble", "wobble_bass", rate=4.0, depth=0.8)
    project.add_track("Drums", "drum_generator", pattern="dubstep_140")
    project.add_track("Sidechain", "sidechain", depth=0.7, release=0.15)
    project.add_track("Pad", "pad_synth", cutoff=2000, resonance=0.3)
    project.add_track("Lead", "lead_synth", waveform="saw")
    project.add_track("FX", "fx_generator", type="riser")
    project.add_track("Reverb Send", "reverb_delay", mix=0.4)

    project.metadata = {
        "genre": "dubstep",
        "phi_tuned": True,
        "dubforge_version": "5.0.0",
    }

    return project


def main() -> None:
    print("Project Manager Engine")

    mgr = ProjectManager()
    project = mgr.create_project("Test Session", 140.0, "F")

    project.add_track("Sub", "sub_bass", frequency=55)
    project.add_track("Drums", "drum_generator")
    project.add_track("Lead", "lead_synth")
    print(f"  Tracks: {len(project.tracks)}")

    project.snapshot("0.1.0", "Initial layout")
    print(f"  Versions: {len(project.versions)}")

    path = mgr.save_project()
    print(f"  Saved: {path}")

    # Default project
    default = create_default_project()
    print(f"\n  Default project: {default.name}")
    print(f"    Tracks: {[t.name for t in default.tracks]}")
    print(f"    Metadata: {default.metadata}")

    summary = mgr.get_summary()
    print(f"\n  Manager: {summary}")
    print("Done.")


if __name__ == "__main__":
    main()
