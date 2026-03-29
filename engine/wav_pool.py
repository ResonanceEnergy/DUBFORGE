"""
DUBFORGE — WAV Pool Manager Engine  (Session 190)

Manages a library of WAV files: indexing, categorization,
search, and automatic tagging.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field

from engine.config_loader import PHI
from engine.frequency_analyzer import FrequencyAnalyzer, SpectralFeatures
from engine.turboquant import SpectralVectorIndex, TurboQuantConfig

SAMPLE_RATE = 48000


@dataclass
class WavFile:
    """Entry in the WAV pool."""
    path: str
    name: str = ""
    duration_s: float = 0.0
    sample_rate: int = 44100
    channels: int = 1
    bit_depth: int = 16
    size_bytes: int = 0
    category: str = "misc"
    tags: list[str] = field(default_factory=list)
    rms_db: float = -60.0
    peak_db: float = -60.0
    spectral_features: SpectralFeatures | None = None

    def __post_init__(self):
        if not self.name:
            self.name = os.path.splitext(os.path.basename(self.path))[0]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "duration_s": round(self.duration_s, 2),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "category": self.category,
            "tags": self.tags,
            "rms_db": round(self.rms_db, 1),
            "peak_db": round(self.peak_db, 1),
            "size_bytes": self.size_bytes,
        }


# Category detection keywords
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bass": ["bass", "sub", "low", "808", "reese", "wobble"],
    "drums": ["drum", "kick", "snare", "hat", "hihat", "clap",
              "perc", "cymbal", "tom", "ride"],
    "leads": ["lead", "synth", "saw", "square"],
    "pads": ["pad", "ambient", "atmosphere", "atmo", "drone"],
    "fx": ["fx", "riser", "downlifter", "sweep", "impact",
           "hit", "noise", "transition"],
    "vocals": ["vocal", "vox", "voice", "chop"],
    "loops": ["loop", "pattern", "groove"],
    "oneshots": ["oneshot", "one_shot", "single", "shot"],
}


def _detect_category(name: str) -> str:
    """Auto-detect category from filename."""
    lower = name.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "misc"


def _detect_tags(name: str) -> list[str]:
    """Auto-detect tags from filename."""
    tags: list[str] = []
    lower = name.lower()
    all_keywords = set()
    for keywords in CATEGORY_KEYWORDS.values():
        all_keywords.update(keywords)
    for kw in all_keywords:
        if kw in lower:
            tags.append(kw)
    return tags


def scan_wav(path: str) -> WavFile | None:
    """Scan a WAV file and extract info."""
    if not os.path.exists(path) or not path.lower().endswith(".wav"):
        return None

    try:
        size = os.path.getsize(path)
        with wave.open(path, "r") as wf:
            sr = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            frames = wf.getnframes()
            duration = frames / sr if sr > 0 else 0

            # Read frames for analysis (first 1s)
            n_read = min(frames, sr)
            raw = wf.readframes(n_read)

        # Analyze levels
        samples: list[float] = []
        if sw == 2:
            for i in range(0, len(raw) - 1, 2 * ch):
                val = struct.unpack_from("<h", raw, i)[0] / 32768.0
                samples.append(val)
        elif sw == 1:
            for i in range(0, len(raw), ch):
                val = (raw[i] - 128) / 128.0
                samples.append(val)

        if samples:
            rms = math.sqrt(sum(x * x for x in samples) / len(samples))
            peak = max(abs(x) for x in samples)
            rms_db = 20 * math.log10(max(rms, 1e-10))
            peak_db = 20 * math.log10(max(peak, 1e-10))
        else:
            rms_db = -60.0
            peak_db = -60.0

        name = os.path.splitext(os.path.basename(path))[0]
        return WavFile(
            path=path,
            name=name,
            duration_s=duration,
            sample_rate=sr,
            channels=ch,
            bit_depth=sw * 8,
            size_bytes=size,
            category=_detect_category(name),
            tags=_detect_tags(name),
            rms_db=rms_db,
            peak_db=peak_db,
        )
    except Exception:
        return None


class WavPool:
    """Manages a pool of WAV files."""

    def __init__(self):
        self.files: dict[str, WavFile] = {}

    def add(self, wav: WavFile) -> None:
        self.files[wav.path] = wav

    def scan_directory(self, directory: str,
                        recursive: bool = True) -> int:
        """Scan directory and add all WAV files."""
        count = 0
        if not os.path.exists(directory):
            return 0

        if recursive:
            for root, _, filenames in os.walk(directory):
                for fname in filenames:
                    path = os.path.join(root, fname)
                    wav = scan_wav(path)
                    if wav:
                        self.add(wav)
                        count += 1
        else:
            for fname in os.listdir(directory):
                path = os.path.join(directory, fname)
                wav = scan_wav(path)
                if wav:
                    self.add(wav)
                    count += 1

        return count

    def search(self, query: str = "", category: str = "",
               min_duration: float = 0, max_duration: float = 0,
               tags: list[str] | None = None) -> list[WavFile]:
        """Search the pool."""
        results: list[WavFile] = []
        for wav in self.files.values():
            if query and query.lower() not in wav.name.lower():
                continue
            if category and wav.category != category:
                continue
            if min_duration > 0 and wav.duration_s < min_duration:
                continue
            if max_duration > 0 and wav.duration_s > max_duration:
                continue
            if tags and not any(t in wav.tags for t in tags):
                continue
            results.append(wav)
        return results

    def by_category(self) -> dict[str, list[WavFile]]:
        """Group files by category."""
        cats: dict[str, list[WavFile]] = {}
        for wav in self.files.values():
            cats.setdefault(wav.category, []).append(wav)
        return cats

    def get_stats(self) -> dict:
        """Get pool statistics."""
        total_size = sum(w.size_bytes for w in self.files.values())
        total_duration = sum(w.duration_s for w in self.files.values())
        cats = self.by_category()
        return {
            "total_files": len(self.files),
            "total_size_mb": round(total_size / 1024 / 1024, 1),
            "total_duration_s": round(total_duration, 1),
            "categories": {k: len(v) for k, v in cats.items()},
        }

    def build_timbre_index(self,
                           config: TurboQuantConfig | None = None) -> SpectralVectorIndex:
        """Build a TurboQuant spectral index from all WAV files with features.

        Only includes files that have spectral_features computed.

        Returns:
            SpectralVectorIndex ready for timbre-based search.
        """
        idx = SpectralVectorIndex(config)
        for wav in self.files.values():
            if wav.spectral_features is not None:
                vec = wav.spectral_features.to_feature_vector()
                idx.add(wav.name, vec, metadata={
                    "path": wav.path,
                    "category": wav.category,
                    "tags": wav.tags,
                })
        return idx

    def analyze_all(self) -> int:
        """Compute spectral features for all WAV files in the pool.

        Returns the number of files analyzed.
        """
        analyzer = FrequencyAnalyzer()
        count = 0
        for wav in self.files.values():
            if wav.spectral_features is not None:
                continue
            try:
                with wave.open(wav.path, "r") as wf:
                    sw = wf.getsampwidth()
                    n_frames = min(wf.getnframes(), wf.getframerate())
                    raw = wf.readframes(n_frames)
                samples: list[float] = []
                if sw == 2:
                    for i in range(0, len(raw) - 1, 2):
                        val = struct.unpack_from("<h", raw, i)[0] / 32768.0
                        samples.append(val)
                if samples:
                    wav.spectral_features = analyzer.analyze(samples)
                    count += 1
            except Exception:
                pass
        return count

    def search_by_timbre(self, query_samples: list[float],
                         top_k: int = 5,
                         config: TurboQuantConfig | None = None) -> list[tuple[str, float, dict]]:
        """Find WAV files most similar in timbre to the query audio.

        Args:
            query_samples: Audio samples to match against.
            top_k: Number of results.
            config: TurboQuant config for the search index.

        Returns:
            List of (name, similarity, metadata) tuples.
        """
        analyzer = FrequencyAnalyzer()
        features = analyzer.analyze(query_samples)
        vec = features.to_feature_vector()

        idx = self.build_timbre_index(config)
        return idx.search(vec, top_k=top_k)


def main() -> None:
    print("WAV Pool Manager Engine")

    pool = WavPool()
    count = pool.scan_directory("output", recursive=True)
    print(f"  Scanned: {count} WAV files")

    stats = pool.get_stats()
    print(f"  Stats: {stats}")

    # Category detection tests
    for name in ["deep_sub_bass", "dubstep_kick_01", "lead_synth_saw",
                  "ambient_pad", "vocal_chop_fx", "drum_loop_140"]:
        cat = _detect_category(name)
        tags = _detect_tags(name)
        print(f"  {name:>25} → {cat:<8} tags={tags}")

    print("Done.")


if __name__ == "__main__":
    main()
