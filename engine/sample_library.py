"""
DUBFORGE Engine — Sample Library Manager

Downloads, catalogs, and manages drum & FX samples from free sources.
Supports Freesound.org API, direct URL downloads, and local file import.

Sample Categories:
  kick, snare, clap, hat_closed, hat_open, crash, ride, perc, tom,
  fx_riser, fx_downlifter, fx_impact, fx_sweep, fx_noise, fx_transition,
  vocal, foley, texture, one_shot

Storage: output/samples/<category>/<filename>.wav
Index:   output/samples/sample_index.json

Usage:
    from engine.sample_library import SampleLibrary
    lib = SampleLibrary()
    lib.download_starter_pack()  # downloads curated free samples
    kick = lib.get_random("kick")  # random kick sample path
    snares = lib.list_category("snare")  # all snare paths
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from engine.log import get_logger

_log = get_logger("dubforge.sample_library")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    _log.warning("requests not installed. Run: pip install requests")


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_SAMPLE_DIR = "output/samples"
INDEX_FILE = "sample_index.json"
DEFAULT_EXTERNAL_ROOT = Path(r"C:\dev\DUBFORGE GALATCIA")

CATEGORIES = [
    "kick", "snare", "clap", "hat_closed", "hat_open",
    "crash", "ride", "perc", "tom", "rimshot", "shaker",
    "fx_riser", "fx_downlifter", "fx_impact", "fx_sweep",
    "fx_noise", "fx_transition", "fx_stab", "fx_shepard",
    "fx_tonal_rise", "fx_tonal_fall",
    "vocal", "foley", "texture", "one_shot", "bass_hit",
    "808", "cymbal", "tambourine",
    # Loop categories (GALATCIA / external packs)
    "loop_beat", "loop_buildup", "loop_perc", "loop_hihat",
    "loop_kick_snare",
    # Wavetable & preset categories
    "wavetable_neuro", "preset_serum",
]

# GALATCIA subfolder names → SampleLibrary category mapping.
# Keys are subfolder names found under the GALATCIA Samples tree;
# values must be members of CATEGORIES above.
_EXTERNAL_CATEGORY_MAP: dict[str, str] = {
    # Drum one-shots
    "KICKS":               "kick",
    "Snares":              "snare",
    "Claps":               "clap",
    "Closed":              "hat_closed",
    "Open":                "hat_open",
    # FX — Impacts
    "Booms":               "fx_impact",
    "Reverses":            "fx_transition",
    # FX — Shepard tones
    "Shepard Tones":       "fx_shepard",
    # FX — Noise risers / downlifters
    "Noise":               None,           # parent — children override
    # FX — Tonal risers / downlifters
    "Tonal":               None,           # parent — children override
    # Drum loops
    "Beat Loops":          "loop_beat",
    "Build Ups":           "loop_buildup",
    "Fill & Perc Loops":   "loop_perc",
    "Hihat Loops":         "loop_hihat",
    "Kick And Snare Loops": "loop_kick_snare",
    # Neuro wavetables
    "ERB NEURO WT":        "wavetable_neuro",
}

# Disambiguation map: when a file lives under BOTH a parent (Noise / Tonal)
# and a child (Falling / Rising), the *child+parent* combo determines the
# category.  Keys are (child_folder, parent_folder).
_TONAL_NOISE_MAP: dict[tuple[str, str], str] = {
    ("Falling", "Noise"): "fx_downlifter",
    ("Rising",  "Noise"): "fx_riser",
    ("Falling", "Tonal"): "fx_tonal_fall",
    ("Rising",  "Tonal"): "fx_tonal_rise",
}

# Freesound.org API
FREESOUND_API_BASE = "https://freesound.org/apiv2"

# ═══════════════════════════════════════════════════════════════════════════
# CURATED FREE SAMPLE URLS (CC0 / Royalty-Free)
# ═══════════════════════════════════════════════════════════════════════════
#
# These are direct URLs to well-known free sample packs and individual
# CC0-licensed samples. Users should verify licenses before commercial use.
#
# NOTE: For Freesound.org downloads, an API key is required.
# Get one at: https://freesound.org/apiv2/apply/

CURATED_SOURCES = {
    # GitHub-hosted CC0 sample repositories
    "drums_99sounds": {
        "description": "99Sounds free drum samples (CC0)",
        "base_url": "https://raw.githubusercontent.com",
        "type": "github_repo",
        "note": "Manual download from 99sounds.org",
    },
}

# Freesound query templates for each category
FREESOUND_QUERIES = {
    "kick":          {"query": "kick drum electronic", "filter": "duration:[0.1 TO 2.0]"},
    "snare":         {"query": "snare electronic dubstep", "filter": "duration:[0.1 TO 2.0]"},
    "clap":          {"query": "clap electronic", "filter": "duration:[0.1 TO 2.0]"},
    "hat_closed":    {"query": "closed hi-hat electronic", "filter": "duration:[0.05 TO 1.0]"},
    "hat_open":      {"query": "open hi-hat electronic", "filter": "duration:[0.1 TO 3.0]"},
    "crash":         {"query": "crash cymbal", "filter": "duration:[0.5 TO 5.0]"},
    "ride":          {"query": "ride cymbal electronic", "filter": "duration:[0.1 TO 3.0]"},
    "perc":          {"query": "percussion electronic hit", "filter": "duration:[0.05 TO 2.0]"},
    "tom":           {"query": "tom drum electronic", "filter": "duration:[0.1 TO 2.0]"},
    "808":           {"query": "808 bass drum", "filter": "duration:[0.2 TO 4.0]"},
    "fx_riser":      {"query": "riser tension build", "filter": "duration:[1.0 TO 10.0]"},
    "fx_downlifter": {"query": "downlifter drop effect", "filter": "duration:[0.5 TO 8.0]"},
    "fx_impact":     {"query": "impact hit boom", "filter": "duration:[0.2 TO 4.0]"},
    "fx_sweep":      {"query": "sweep filter whoosh", "filter": "duration:[0.5 TO 6.0]"},
    "fx_noise":      {"query": "noise burst texture", "filter": "duration:[0.5 TO 5.0]"},
    "fx_transition": {"query": "transition effect dj", "filter": "duration:[0.5 TO 5.0]"},
    "vocal":         {"query": "vocal chop electronic", "filter": "duration:[0.1 TO 3.0]"},
    "foley":         {"query": "foley sound effect", "filter": "duration:[0.1 TO 5.0]"},
    "texture":       {"query": "texture ambient noise", "filter": "duration:[1.0 TO 15.0]"},
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SampleMeta:
    """Metadata for a single sample."""
    filename: str
    category: str
    path: str
    source: str = "local"
    source_id: str = ""
    license: str = "unknown"
    duration: float = 0.0
    sample_rate: int = 44100
    channels: int = 1
    bpm: float = 0.0
    key: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    downloaded: str = ""  # ISO timestamp

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "category": self.category,
            "path": self.path,
            "source": self.source,
            "source_id": self.source_id,
            "license": self.license,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bpm": self.bpm,
            "key": self.key,
            "tags": self.tags,
            "description": self.description,
            "downloaded": self.downloaded,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SampleMeta":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════════
# SAMPLE LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

class SampleLibrary:
    """Sample download, catalog, and retrieval manager."""

    def __init__(self, sample_dir: str = DEFAULT_SAMPLE_DIR,
                 freesound_api_key: str = ""):
        self.sample_dir = Path(sample_dir)
        self.freesound_api_key = freesound_api_key or os.environ.get("FREESOUND_API_KEY", "")
        self._index: dict[str, list[SampleMeta]] = {cat: [] for cat in CATEGORIES}
        self._index_path = self.sample_dir / INDEX_FILE

        # Create directory structure
        self._ensure_dirs()
        # Load existing index
        self._load_index()
        # Auto-scan external sample packs (e.g. GALATCIA) if present
        if self.total_count == 0:
            self._auto_scan_external()

    def _ensure_dirs(self):
        """Create category directories."""
        for cat in CATEGORIES:
            (self.sample_dir / cat).mkdir(parents=True, exist_ok=True)

    def _load_index(self):
        """Load sample index from disk."""
        if self._index_path.exists():
            try:
                data = json.loads(self._index_path.read_text())
                for cat, samples in data.items():
                    if cat in self._index:
                        self._index[cat] = [SampleMeta.from_dict(s) for s in samples]
                _log.info(f"Loaded sample index: {self.total_count} samples")
            except Exception as e:
                _log.warning(f"Could not load sample index: {e}")

    def _save_index(self):
        """Save sample index to disk."""
        data = {cat: [s.to_dict() for s in samples]
                for cat, samples in self._index.items()}
        self._index_path.write_text(json.dumps(data, indent=2))

    def _auto_scan_external(self):
        """Auto-discover GALATCIA (or similar) external sample packs."""
        root = DEFAULT_EXTERNAL_ROOT
        if not root.is_dir():
            return
        _log.info("Auto-scanning external sample pack: %s", root)
        self.scan_external_dir(root)

    def _resolve_category(self, filepath: Path) -> str | None:
        """Determine the SampleLibrary category for *filepath*.

        Uses the parent-folder walk plus the Tonal/Noise disambiguation
        map so that ``FX/Noise/Rising`` and ``FX/Tonal/Rising`` land in
        different categories.
        """
        parts = [p.name for p in filepath.parents]
        # Check (child, parent) disambiguation first
        for i in range(len(parts) - 1):
            key = (parts[i], parts[i + 1])
            if key in _TONAL_NOISE_MAP:
                return _TONAL_NOISE_MAP[key]
        # Fall through to the flat map
        for folder in parts:
            if folder in _EXTERNAL_CATEGORY_MAP:
                cat = _EXTERNAL_CATEGORY_MAP[folder]
                if cat is not None:
                    return cat
        return None

    def scan_external_dir(self, root: Path) -> int:
        """Walk *root* for .wav and .fxp files, index in-place.

        .wav → drum one-shots, FX, loops, wavetables (by subfolder).
        .fxp → Serum 2 presets (all mapped to ``preset_serum``).

        Files are NOT copied — the index stores absolute paths pointing
        at the original location so there is zero duplication.

        Returns the number of new samples indexed.
        """
        root = Path(root)
        added = 0
        existing_paths: set[str] = set()
        for samples in self._index.values():
            for s in samples:
                existing_paths.add(s.path)

        # ── WAV samples (drums, FX, loops, wavetables) ──────────────
        for wav in root.rglob("*.wav"):
            if wav.name.startswith("._") or "__MACOSX" in str(wav):
                continue
            abs_path = str(wav.resolve())
            if abs_path in existing_paths:
                continue

            category = self._resolve_category(wav)
            if category is None or category not in self._index:
                continue

            meta = SampleMeta(
                filename=wav.name,
                category=category,
                path=abs_path,
                source="external",
            )
            self._index[category].append(meta)
            existing_paths.add(abs_path)
            added += 1

        # ── FXP presets (Serum 2) ────────────────────────────────────
        for fxp in root.rglob("*.fxp"):
            if fxp.name.startswith("._") or "__MACOSX" in str(fxp):
                continue
            abs_path = str(fxp.resolve())
            if abs_path in existing_paths:
                continue

            meta = SampleMeta(
                filename=fxp.name,
                category="preset_serum",
                path=abs_path,
                source="external",
            )
            self._index["preset_serum"].append(meta)
            existing_paths.add(abs_path)
            added += 1

        if added:
            self._save_index()
            _log.info("Indexed %d external assets from %s (total: %d)",
                      added, root, self.total_count)
        return added

    # ── PROPERTIES ───────────────────────────────────────────────────────

    @property
    def total_count(self) -> int:
        return sum(len(samples) for samples in self._index.values())

    def category_count(self, category: str) -> int:
        return len(self._index.get(category, []))

    def summary(self) -> dict[str, int]:
        return {cat: len(samples) for cat, samples in self._index.items()
                if samples}

    # ── RETRIEVAL ────────────────────────────────────────────────────────

    def get_random(self, category: str) -> str | None:
        """Get a random sample path from a category."""
        samples = self._index.get(category, [])
        if not samples:
            return None
        sample = random.choice(samples)
        path = Path(sample.path)
        return str(path) if path.exists() else None

    def get_all(self, category: str) -> list[str]:
        """Get all sample paths in a category."""
        samples = self._index.get(category, [])
        return [s.path for s in samples if Path(s.path).exists()]

    def get_by_tag(self, tag: str) -> list[str]:
        """Get all samples matching a tag."""
        results = []
        for samples in self._index.values():
            for s in samples:
                if tag.lower() in [t.lower() for t in s.tags]:
                    if Path(s.path).exists():
                        results.append(s.path)
        return results

    def list_category(self, category: str) -> list[SampleMeta]:
        """List all samples in a category with metadata."""
        return self._index.get(category, [])

    def search(self, query: str) -> list[SampleMeta]:
        """Search samples by filename, description, or tags."""
        q = query.lower()
        results = []
        for samples in self._index.values():
            for s in samples:
                if (q in s.filename.lower() or
                    q in s.description.lower() or
                    any(q in t.lower() for t in s.tags)):
                    results.append(s)
        return results

    # ── LOCAL IMPORT ─────────────────────────────────────────────────────

    def import_file(self, src_path: str, category: str,
                    tags: list[str] | None = None,
                    description: str = "") -> SampleMeta:
        """Import a local audio file into the library."""
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src_path}")

        dest_dir = self.sample_dir / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name

        # Copy file
        shutil.copy2(src, dest)

        # Create metadata
        meta = SampleMeta(
            filename=src.name,
            category=category,
            path=str(dest),
            source="local",
            tags=tags or [],
            description=description,
            downloaded=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        # Try to get audio info
        meta = self._analyze_sample(meta)

        self._index[category].append(meta)
        self._save_index()
        _log.info(f"Imported: {src.name} → {category}")
        return meta

    def import_directory(self, src_dir: str, category: str,
                         extensions: tuple = (".wav", ".aif", ".aiff", ".mp3", ".flac")) -> int:
        """Import all audio files from a directory."""
        count = 0
        for f in Path(src_dir).iterdir():
            if f.suffix.lower() in extensions:
                self.import_file(str(f), category)
                count += 1
        return count

    # ── DOWNLOAD ─────────────────────────────────────────────────────────

    def download_url(self, url: str, category: str, filename: str = "",
                     tags: list[str] | None = None) -> SampleMeta | None:
        """Download a sample from a direct URL."""
        if not HAS_REQUESTS:
            _log.error("requests package required for downloads")
            return None

        if not filename:
            filename = Path(urlparse(url).path).name or "sample.wav"

        dest_dir = self.sample_dir / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename

        if dest.exists():
            _log.info(f"Already exists: {dest}")
            return None

        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            meta = SampleMeta(
                filename=filename,
                category=category,
                path=str(dest),
                source=urlparse(url).netloc,
                source_id=hashlib.md5(url.encode()).hexdigest()[:12],
                tags=tags or [],
                downloaded=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )
            meta = self._analyze_sample(meta)
            self._index[category].append(meta)
            self._save_index()
            _log.info(f"Downloaded: {filename} → {category}")
            return meta

        except Exception as e:
            _log.error(f"Download failed: {url} — {e}")
            return None

    # ── FREESOUND.ORG ────────────────────────────────────────────────────

    def freesound_search(self, category: str, max_results: int = 5) -> list[dict]:
        """Search Freesound.org for samples in a category.

        Requires FREESOUND_API_KEY set in environment or constructor.
        """
        if not self.freesound_api_key:
            _log.warning("No Freesound API key. Set FREESOUND_API_KEY env var or "
                          "pass freesound_api_key= to constructor.\n"
                          "Get a key at: https://freesound.org/apiv2/apply/")
            return []

        if not HAS_REQUESTS:
            return []

        query_config = FREESOUND_QUERIES.get(category, {"query": category})
        params = {
            "token": self.freesound_api_key,
            "query": query_config["query"],
            "filter": query_config.get("filter", ""),
            "fields": "id,name,previews,tags,duration,samplerate,channels,license,description",
            "page_size": max_results,
            "sort": "rating_desc",
        }

        try:
            response = requests.get(f"{FREESOUND_API_BASE}/search/text/",
                                     params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            _log.error(f"Freesound search failed: {e}")
            return []

    def freesound_download(self, sound_id: int, category: str) -> SampleMeta | None:
        """Download a specific Freesound sample by ID.

        Uses preview quality (128kbps MP3 or HQ OGG).
        For full quality WAV, OAuth2 authentication is required.
        """
        if not self.freesound_api_key or not HAS_REQUESTS:
            return None

        try:
            # Get sound details
            response = requests.get(
                f"{FREESOUND_API_BASE}/sounds/{sound_id}/",
                params={"token": self.freesound_api_key,
                        "fields": "id,name,previews,tags,duration,samplerate,channels,license,description"},
                timeout=15)
            response.raise_for_status()
            sound = response.json()

            # Get HQ preview URL
            preview_url = sound.get("previews", {}).get(
                "preview-hq-ogg", sound.get("previews", {}).get("preview-hq-mp3", ""))

            if not preview_url:
                _log.warning(f"No preview available for sound {sound_id}")
                return None

            # Download
            filename = f"freesound_{sound_id}_{sound['name']}"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            ext = ".ogg" if "ogg" in preview_url else ".mp3"
            filename = filename[:100] + ext

            dest_dir = self.sample_dir / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / filename

            if dest.exists():
                _log.info(f"Already exists: {dest}")
                return None

            dl_response = requests.get(preview_url, stream=True, timeout=30)
            dl_response.raise_for_status()

            with open(dest, 'wb') as f:
                for chunk in dl_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            meta = SampleMeta(
                filename=filename,
                category=category,
                path=str(dest),
                source="freesound.org",
                source_id=str(sound_id),
                license=sound.get("license", "CC0"),
                duration=sound.get("duration", 0),
                sample_rate=sound.get("samplerate", 44100),
                channels=sound.get("channels", 1),
                tags=sound.get("tags", [])[:10],
                description=sound.get("description", "")[:200],
                downloaded=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )

            self._index[category].append(meta)
            self._save_index()
            _log.info(f"Downloaded from Freesound: {filename} → {category}")
            return meta

        except Exception as e:
            _log.error(f"Freesound download failed for {sound_id}: {e}")
            return None

    def freesound_build_category(self, category: str,
                                  count: int = 5) -> list[SampleMeta]:
        """Search and download samples for a category from Freesound."""
        results = self.freesound_search(category, max_results=count)
        downloaded = []
        for sound in results:
            meta = self.freesound_download(sound["id"], category)
            if meta:
                downloaded.append(meta)
                time.sleep(0.5)  # Rate limiting
        return downloaded

    def freesound_build_all(self, count_per_category: int = 3) -> dict[str, int]:
        """Build sample library from Freesound for all categories."""
        if not self.freesound_api_key:
            _log.error("No Freesound API key configured. Cannot download samples.\n"
                       "Get a key at: https://freesound.org/apiv2/apply/\n"
                       "Set via: export FREESOUND_API_KEY=your_key")
            return {}

        stats = {}
        for cat in FREESOUND_QUERIES:
            _log.info(f"Building category: {cat}")
            downloaded = self.freesound_build_category(cat, count_per_category)
            stats[cat] = len(downloaded)
            time.sleep(1)  # Rate limiter

        return stats

    # ── STARTER PACK ─────────────────────────────────────────────────────

    def download_starter_pack(self) -> dict:
        """Download a curated starter pack of free drum samples.

        If Freesound API key is set, downloads from there.
        Otherwise, creates placeholder structure for manual import.
        """
        if self.freesound_api_key:
            print("  ◆ Downloading from Freesound.org with API key...")
            stats = self.freesound_build_all(count_per_category=3)
            return {"source": "freesound", "downloaded": stats}
        else:
            print("  ◆ No Freesound API key — creating import structure")
            print("  ◆ To download free samples:")
            print("    1. Get API key: https://freesound.org/apiv2/apply/")
            print("    2. Export: FREESOUND_API_KEY=your_key")
            print("    3. Or import manually: lib.import_directory('path/', 'kick')")
            print()
            print("  ◆ Free sample sources to download from:")
            print("    • https://99sounds.org/free-drum-samples/")
            print("    • https://www.musicradar.com/news/free-music-samples")
            print("    • https://samplefocus.com/")
            print("    • https://splice.com/features/free-samples")
            print("    • https://cymatics.fm/pages/free-download-vault")
            print()

            # Create README in sample directory
            readme = self.sample_dir / "README.md"
            readme.write_text(
                "# DUBFORGE Sample Library\n\n"
                "## Directory Structure\n\n"
                "Place audio samples (.wav, .aif, .mp3) in category folders:\n\n"
                + "\n".join(f"- `{cat}/` — {cat.replace('_', ' ').title()}" for cat in CATEGORIES)
                + "\n\n## Import via Python\n\n"
                "```python\n"
                "from engine.sample_library import SampleLibrary\n"
                "lib = SampleLibrary()\n"
                "lib.import_directory('/path/to/kicks/', 'kick')\n"
                "```\n\n"
                "## Free Sample Sources\n\n"
                "- [99Sounds](https://99sounds.org/) — High quality CC0 drums\n"
                "- [Freesound.org](https://freesound.org/) — CC0 audio database\n"
                "- [SampleFocus](https://samplefocus.com/) — Community samples\n"
                "- [Cymatics](https://cymatics.fm/pages/free-download-vault) — Free packs\n"
            )

            return {"source": "manual", "structure_created": True,
                    "categories": len(CATEGORIES)}

    # ── AUTO-SCAN ────────────────────────────────────────────────────────

    def scan_directory(self, base_dir: str = "") -> int:
        """Scan sample directory for new files not in the index."""
        base = Path(base_dir) if base_dir else self.sample_dir
        new_count = 0

        for cat in CATEGORIES:
            cat_dir = base / cat
            if not cat_dir.exists():
                continue

            indexed_files = {s.filename for s in self._index.get(cat, [])}

            for f in cat_dir.iterdir():
                if f.suffix.lower() in (".wav", ".aif", ".aiff", ".mp3",
                                         ".flac", ".ogg"):
                    if f.name not in indexed_files:
                        meta = SampleMeta(
                            filename=f.name,
                            category=cat,
                            path=str(f),
                            source="scan",
                            downloaded=time.strftime("%Y-%m-%dT%H:%M:%S"),
                        )
                        meta = self._analyze_sample(meta)
                        self._index[cat].append(meta)
                        new_count += 1

        if new_count:
            self._save_index()
            _log.info(f"Scanned and indexed {new_count} new samples")

        return new_count

    # ── ANALYSIS ─────────────────────────────────────────────────────────

    def _analyze_sample(self, meta: SampleMeta) -> SampleMeta:
        """Try to analyze sample audio properties."""
        path = Path(meta.path)
        if not path.exists():
            return meta

        # Try to read WAV header for basic info
        if path.suffix.lower() == ".wav":
            try:
                import wave
                with wave.open(str(path), 'rb') as wf:
                    meta.sample_rate = wf.getframerate()
                    meta.channels = wf.getnchannels()
                    frames = wf.getnframes()
                    meta.duration = frames / meta.sample_rate if meta.sample_rate else 0
            except Exception:
                pass

        return meta

    # ── CLEANUP ──────────────────────────────────────────────────────────

    def cleanup_missing(self) -> int:
        """Remove index entries for files that no longer exist."""
        removed = 0
        for cat in CATEGORIES:
            before = len(self._index[cat])
            self._index[cat] = [s for s in self._index[cat]
                                if Path(s.path).exists()]
            removed += before - len(self._index[cat])

        if removed:
            self._save_index()
            _log.info(f"Cleaned up {removed} missing sample entries")
        return removed

    def delete_category(self, category: str) -> int:
        """Delete all samples in a category."""
        count = 0
        for sample in self._index.get(category, []):
            p = Path(sample.path)
            if p.exists():
                p.unlink()
                count += 1
        self._index[category] = []
        self._save_index()
        return count

    # ── DRUM KIT BUILDER ─────────────────────────────────────────────────

    def build_drum_kit(self, name: str = "default") -> dict[str, str]:
        """Build a drum kit by selecting one sample per essential category.

        Returns: {category: path} dict for use in production pipeline.
        """
        essential = ["kick", "snare", "hat_closed", "hat_open", "clap", "perc"]
        kit = {}
        for cat in essential:
            sample = self.get_random(cat)
            if sample:
                kit[cat] = sample
        if kit:
            _log.info(f"Built drum kit '{name}' with {len(kit)} samples")
        return kit

    def build_fx_set(self) -> dict[str, str]:
        """Build an FX sample set by selecting one per FX category."""
        fx_cats = ["fx_riser", "fx_downlifter", "fx_impact", "fx_sweep"]
        fxset = {}
        for cat in fx_cats:
            sample = self.get_random(cat)
            if sample:
                fxset[cat] = sample
        return fxset

    # ── REPORT ───────────────────────────────────────────────────────────

    def report(self) -> str:
        """Generate a text report of the sample library."""
        lines = [
            "═══════════════════════════════════════════════",
            "  DUBFORGE SAMPLE LIBRARY REPORT",
            f"  Total Samples: {self.total_count}",
            f"  Location: {self.sample_dir}",
            "═══════════════════════════════════════════════",
        ]
        for cat, samples in self._index.items():
            if samples:
                lines.append(f"\n  {cat.upper()} ({len(samples)} samples):")
                for s in samples[:5]:
                    dur = f" ({s.duration:.1f}s)" if s.duration else ""
                    lines.append(f"    • {s.filename}{dur}")
                if len(samples) > 5:
                    lines.append(f"    ... and {len(samples) - 5} more")

        return "\n".join(lines)

    def __repr__(self):
        return f"SampleLibrary(samples={self.total_count}, dir={self.sample_dir})"


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    lib = SampleLibrary()
    print(f"\nDUBFORGE Sample Library")
    print(f"Location: {lib.sample_dir}")
    print(f"Total samples: {lib.total_count}")

    if "--scan" in sys.argv:
        new = lib.scan_directory()
        print(f"Scanned: {new} new samples found")

    elif "--download" in sys.argv:
        result = lib.download_starter_pack()
        print(f"Download result: {result}")

    elif "--report" in sys.argv:
        print(lib.report())

    else:
        print(f"\nCategories: {', '.join(CATEGORIES)}")
        print(f"\nUsage:")
        print(f"  python -m engine.sample_library --scan      # Scan for new files")
        print(f"  python -m engine.sample_library --download  # Download starter pack")
        print(f"  python -m engine.sample_library --report    # Full report")

    summary = lib.summary()
    if summary:
        print(f"\nLibrary contents:")
        for cat, count in summary.items():
            print(f"  {cat}: {count}")
