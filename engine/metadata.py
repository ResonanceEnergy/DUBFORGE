"""
DUBFORGE — Metadata Engine  (Session 189)

Manages audio file metadata: ID3-like tags, project info,
PHI metrics, and export metadata for sample packs.
"""

import json
import os
import time
from dataclasses import dataclass, field

from engine.config_loader import PHI
@dataclass
class AudioMetadata:
    """Metadata for an audio file."""
    title: str = ""
    artist: str = "DUBFORGE"
    album: str = ""
    genre: str = "Dubstep"
    bpm: float = 140.0
    key: str = "F"
    scale: str = "minor"
    duration_s: float = 0.0
    sample_rate: int = 44100
    bit_depth: int = 16
    channels: int = 1
    created_at: float = 0.0
    tags: list[str] = field(default_factory=list)
    phi_metrics: dict = field(default_factory=dict)
    custom: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "genre": self.genre,
            "bpm": self.bpm,
            "key": self.key,
            "scale": self.scale,
            "duration_s": round(self.duration_s, 2),
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
            "channels": self.channels,
            "created_at": self.created_at,
            "tags": self.tags,
            "phi_metrics": self.phi_metrics,
            "custom": self.custom,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(data: dict) -> 'AudioMetadata':
        return AudioMetadata(
            title=data.get("title", ""),
            artist=data.get("artist", "DUBFORGE"),
            album=data.get("album", ""),
            genre=data.get("genre", "Dubstep"),
            bpm=data.get("bpm", 140.0),
            key=data.get("key", "F"),
            scale=data.get("scale", "minor"),
            duration_s=data.get("duration_s", 0),
            sample_rate=data.get("sample_rate", 44100),
            bit_depth=data.get("bit_depth", 16),
            channels=data.get("channels", 1),
            created_at=data.get("created_at", 0),
            tags=data.get("tags", []),
            phi_metrics=data.get("phi_metrics", {}),
            custom=data.get("custom", {}),
        )


@dataclass
class PackMetadata:
    """Metadata for a sample pack."""
    name: str
    version: str = "1.0.0"
    author: str = "DUBFORGE"
    description: str = ""
    genre: str = "Dubstep"
    bpm_range: tuple[float, float] = (138.0, 150.0)
    total_files: int = 0
    total_duration_s: float = 0.0
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "genre": self.genre,
            "bpm_range": list(self.bpm_range),
            "total_files": self.total_files,
            "total_duration_s": round(self.total_duration_s, 1),
            "categories": self.categories,
            "tags": self.tags,
            "files": self.files,
        }


class MetadataManager:
    """Manages metadata for audio files."""

    def __init__(self, base_dir: str = "output"):
        self.base_dir = base_dir
        self.metadata_cache: dict[str, AudioMetadata] = {}

    def create(self, path: str, **kwargs) -> AudioMetadata:
        """Create metadata for a file."""
        meta = AudioMetadata(**kwargs)
        if not meta.title:
            meta.title = os.path.splitext(os.path.basename(path))[0]
        self.metadata_cache[path] = meta
        return meta

    def save_sidecar(self, audio_path: str,
                       meta: AudioMetadata | None = None) -> str:
        """Save metadata as a JSON sidecar file."""
        m = meta or self.metadata_cache.get(audio_path)
        if not m:
            return ""
        json_path = audio_path.rsplit(".", 1)[0] + ".meta.json"
        os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
        with open(json_path, "w") as f:
            f.write(m.to_json())
        return json_path

    def load_sidecar(self, audio_path: str) -> AudioMetadata | None:
        """Load metadata from sidecar file."""
        json_path = audio_path.rsplit(".", 1)[0] + ".meta.json"
        if not os.path.exists(json_path):
            return None
        with open(json_path) as f:
            data = json.load(f)
        meta = AudioMetadata.from_dict(data)
        self.metadata_cache[audio_path] = meta
        return meta

    def build_pack_metadata(self, pack_name: str,
                              files: list[str]) -> PackMetadata:
        """Build pack metadata from a list of files."""
        pack = PackMetadata(name=pack_name)
        categories: set[str] = set()
        all_tags: set[str] = set()
        bpms: list[float] = []

        for path in files:
            meta = self.metadata_cache.get(path)
            if not meta:
                meta = self.create(path)

            pack.files.append({
                "path": os.path.basename(path),
                "title": meta.title,
                "bpm": meta.bpm,
                "key": meta.key,
                "duration_s": meta.duration_s,
                "tags": meta.tags,
            })

            pack.total_duration_s += meta.duration_s
            bpms.append(meta.bpm)
            all_tags.update(meta.tags)
            if meta.tags:
                categories.add(meta.tags[0] if meta.tags else "misc")

        pack.total_files = len(files)
        pack.categories = sorted(categories)
        pack.tags = sorted(all_tags)
        if bpms:
            pack.bpm_range = (min(bpms), max(bpms))

        return pack

    def search(self, **criteria) -> list[str]:
        """Search metadata cache by criteria."""
        results: list[str] = []
        for path, meta in self.metadata_cache.items():
            match = True
            for key, val in criteria.items():
                if key == "tag" and val not in meta.tags:
                    match = False
                elif key == "genre" and meta.genre.lower() != val.lower():
                    match = False
                elif key == "bpm" and abs(meta.bpm - val) > 5:
                    match = False
                elif key == "key" and meta.key != val:
                    match = False
            if match:
                results.append(path)
        return results


def main() -> None:
    print("Metadata Engine")

    mgr = MetadataManager()

    # Create test metadata
    _m1 = mgr.create("output/bass_drop.wav",
                      title="Bass Drop", bpm=140.0, key="F",
                      tags=["bass", "dubstep", "heavy"],
                      duration_s=4.0)
    _m2 = mgr.create("output/wobble_lead.wav",
                      title="Wobble Lead", bpm=140.0, key="F",
                      tags=["lead", "wobble", "dubstep"],
                      duration_s=2.0)
    _m3 = mgr.create("output/pad_atmo.wav",
                      title="Pad Atmosphere", bpm=140.0, key="Am",
                      tags=["pad", "ambient"],
                      duration_s=8.0)

    print(f"  Files: {len(mgr.metadata_cache)}")

    # Search
    bass = mgr.search(tag="bass")
    print(f"  Bass files: {bass}")

    # Build pack
    pack = mgr.build_pack_metadata("DUBFORGE Vol.1",
                                     list(mgr.metadata_cache.keys()))
    print(f"\n  Pack: {pack.name}")
    print(f"    Files: {pack.total_files}")
    print(f"    Duration: {pack.total_duration_s:.1f}s")
    print(f"    Categories: {pack.categories}")
    print(f"    Tags: {pack.tags}")

    print("Done.")


if __name__ == "__main__":
    main()
