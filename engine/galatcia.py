"""
DUBFORGE Engine — GALATCIA Integration

Catalog, ingest, and wire external sample packs, Serum presets,
wavetables, and Ableton racks from the DUBFORGE GALATCIA collection.

Source collections:
    Black Octopus — Brutal Dubstep and Riddim  (95 .fxp Serum presets)
    ERB NEURO WT                               (12 neuro wavetables)
    Samples                                    (229 .wav drum + FX samples)
    Ableton Racks                              (2 .adg rack devices)
    ERB N DUB NEURO DNB.SerumPack              (Serum preset bundle)

Output:
    output/galatcia/samples/{category}/...     — Organized .wav files
    output/galatcia/wavetables/...             — Serum-compatible wavetables
    output/galatcia/presets/...                — .fxp presets (parsed + copied)
    output/galatcia/racks/...                  — Ableton .adg racks
    output/galatcia/serumpack/...              — .SerumPack file
    output/galatcia/galatcia_manifest.json     — Full catalog
    output/galatcia/splice_metadata.json       — Marketplace tags
"""

from __future__ import annotations

import json
import shutil
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from engine.config_loader import PHI
from engine.fxp_writer import FXPPreset, read_fxp
from engine.log import get_logger
from engine.marketplace_metadata import auto_tag_sample
from engine.phi_core import SAMPLE_RATE, WAVETABLE_SIZE

_log = get_logger("dubforge.galatcia")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_GALATCIA_ROOT = Path("/Users/natrix/dev/DUBFORGE/DUBFORGE GALACTICA")

# Relative paths inside GALATCIA root
_REL_PRESETS = Path("Black Octopus - Brutal Dubstep and Riddim")
_REL_WAVETABLES = Path("ERB NEURO WT")
_REL_SAMPLES = Path("Samples")
_REL_RACKS = Path("Ableton Racks")
_REL_SERUMPACK = Path("ERB N DUB NEURO DNB.SerumPack")

# FXP prefix → DUBFORGE category mapping
FXP_PREFIX_MAP: dict[str, str] = {
    "BS":  "bass",
    "LD":  "lead",
    "PAD": "pad",
    "PL":  "pluck",
    "SFX": "sfx",
    "SYN": "synth",
}

# Sample folder → DUBFORGE category mapping
SAMPLE_CATEGORY_MAP: dict[str, str] = {
    "Beat Loops":           "drum_loops",
    "Build Ups":            "buildups",
    "Fill & Perc Loops":    "perc_loops",
    "Hihat Loops":          "hihat_loops",
    "Kick And Snare Loops": "kick_snare_loops",
    "Claps":                "claps",
    "Closed":               "hihats_closed",
    "Open":                 "hihats_open",
    "KICKS":                "kicks",
    "Snares":               "snares",
    "Booms":                "impacts",
    "Reverses":             "reverses",
    # NOTE: "Falling" and "Rising" are ambiguous (Noise vs Tonal children).
    # galatcia.py resolves via parent: FX/Noise/Rising → fx_rising,
    # FX/Tonal/Rising → fx_tonal_rising, etc.  Flat map catches the
    # common Noise variants; Tonal variants override below.
    "Falling":              "fx_falling",
    "Rising":               "fx_rising",
    "Shepard Tones":        "shepard_tones",
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GalatciaPreset:
    """A cataloged Serum .fxp preset from the GALATCIA collection."""
    name: str
    filename: str
    prefix: str           # BS, LD, PAD, PL, SFX, SYN
    category: str         # mapped DUBFORGE category
    file_size: int = 0
    source_path: str = ""


@dataclass
class GalatciaSample:
    """A cataloged .wav sample from GALATCIA."""
    filename: str
    category: str         # mapped DUBFORGE category
    original_folder: str  # e.g. "Drum One Shots/KICKS"
    file_size: int = 0
    source_path: str = ""


@dataclass
class GalatciaWavetable:
    """A cataloged wavetable .wav from ERB NEURO WT."""
    name: str
    filename: str
    file_size: int = 0
    source_path: str = ""


@dataclass
class GalatciaRack:
    """A cataloged Ableton .adg rack."""
    name: str
    filename: str
    file_size: int = 0
    source_path: str = ""


@dataclass
class GalatciaCatalog:
    """Full inventory of the GALATCIA collection."""
    root: str
    presets: list[GalatciaPreset] = field(default_factory=list)
    samples: list[GalatciaSample] = field(default_factory=list)
    wavetables: list[GalatciaWavetable] = field(default_factory=list)
    racks: list[GalatciaRack] = field(default_factory=list)
    serumpack_path: str = ""

    @property
    def total_files(self) -> int:
        count = (len(self.presets) + len(self.samples)
                 + len(self.wavetables) + len(self.racks))
        if self.serumpack_path:
            count += 1
        return count

    def summary(self) -> dict:
        return {
            "presets": len(self.presets),
            "samples": len(self.samples),
            "wavetables": len(self.wavetables),
            "racks": len(self.racks),
            "has_serumpack": bool(self.serumpack_path),
            "total_files": self.total_files,
        }


# ═══════════════════════════════════════════════════════════════════════════
# CATALOG — discover and index all GALATCIA content
# ═══════════════════════════════════════════════════════════════════════════

def _classify_fxp_prefix(filename: str) -> tuple[str, str]:
    """Extract prefix (BS, LD, ...) and map to DUBFORGE category."""
    stem = Path(filename).stem
    prefix = stem.split(" ")[0].upper() if " " in stem else stem.upper()
    category = FXP_PREFIX_MAP.get(prefix, "bass")
    return prefix, category


def _classify_sample_folder(folder_name: str) -> str:
    """Map a leaf folder name to a DUBFORGE sample category."""
    return SAMPLE_CATEGORY_MAP.get(folder_name, "misc")


def catalog_galatcia(root: Path | None = None) -> GalatciaCatalog:
    """Scan the GALATCIA folder and return a full catalog.

    Parameters
    ----------
    root : Path, optional
        Override the GALATCIA root folder.  Defaults to
        ``DEFAULT_GALATCIA_ROOT``.

    Returns
    -------
    GalatciaCatalog
        Indexed inventory of all content types.
    """
    root = Path(root) if root else DEFAULT_GALATCIA_ROOT
    if not root.is_dir():
        _log.warning("GALATCIA root not found: %s", root)
        return GalatciaCatalog(root=str(root))

    catalog = GalatciaCatalog(root=str(root))

    # --- Serum .fxp presets ---
    presets_dir = root / _REL_PRESETS
    if presets_dir.is_dir():
        for fxp in sorted(presets_dir.glob("*.fxp")):
            prefix, category = _classify_fxp_prefix(fxp.name)
            catalog.presets.append(GalatciaPreset(
                name=fxp.stem,
                filename=fxp.name,
                prefix=prefix,
                category=category,
                file_size=fxp.stat().st_size,
                source_path=str(fxp),
            ))

    # --- Audio samples ---
    samples_dir = root / _REL_SAMPLES
    if samples_dir.is_dir():
        for wav in sorted(samples_dir.rglob("*.wav")):
            folder = wav.parent.name
            category = _classify_sample_folder(folder)
            rel = wav.relative_to(samples_dir)
            catalog.samples.append(GalatciaSample(
                filename=wav.name,
                category=category,
                original_folder=str(rel.parent),
                file_size=wav.stat().st_size,
                source_path=str(wav),
            ))

    # --- Wavetables ---
    wt_dir = root / _REL_WAVETABLES
    if wt_dir.is_dir():
        for wav in sorted(wt_dir.glob("*.wav")):
            catalog.wavetables.append(GalatciaWavetable(
                name=wav.stem,
                filename=wav.name,
                file_size=wav.stat().st_size,
                source_path=str(wav),
            ))

    # --- Ableton racks ---
    racks_dir = root / _REL_RACKS
    if racks_dir.is_dir():
        for adg in sorted(racks_dir.glob("*.adg")):
            catalog.racks.append(GalatciaRack(
                name=adg.stem,
                filename=adg.name,
                file_size=adg.stat().st_size,
                source_path=str(adg),
            ))

    # --- SerumPack ---
    sp = root / _REL_SERUMPACK
    if sp.is_file():
        catalog.serumpack_path = str(sp)

    _log.info("Cataloged GALATCIA: %s", catalog.summary())
    return catalog


# ═══════════════════════════════════════════════════════════════════════════
# INGEST — read external files into engine-native formats
# ═══════════════════════════════════════════════════════════════════════════

def read_wav_samples(path: str | Path) -> np.ndarray:
    """Read a .wav file and return a float64 numpy array normalized to [-1, 1].

    Parameters
    ----------
    path : str or Path
        Path to the .wav file.

    Returns
    -------
    np.ndarray
        Audio samples as float64, mono, normalized.
    """
    path = Path(path)
    try:
        with wave.open(str(path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
    except wave.Error:
        # IEEE float WAV (format 3) — wave module doesn't support it.
        # Parse RIFF header manually.
        data = path.read_bytes()
        if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            raise ValueError(f"Not a valid WAV file: {path}")
        # Walk chunks
        pos = 12
        n_channels = 1
        sampwidth = 4
        sample_rate = 44100
        audio_data = b""
        while pos < len(data) - 8:
            chunk_id = data[pos:pos + 4]
            chunk_size = int.from_bytes(data[pos + 4:pos + 8], "little")
            if chunk_id == b"fmt ":
                fmt_tag = int.from_bytes(data[pos + 8:pos + 10], "little")
                n_channels = int.from_bytes(data[pos + 10:pos + 12], "little")
                sample_rate = int.from_bytes(data[pos + 12:pos + 16], "little")
                sampwidth = int.from_bytes(data[pos + 22:pos + 24], "little") // 8
            elif chunk_id == b"data":
                audio_data = data[pos + 8:pos + 8 + chunk_size]
            pos += 8 + chunk_size
            if pos % 2:
                pos += 1  # word-align

        if not audio_data:
            raise ValueError(f"No audio data found in {path}")

        # IEEE float32 or float64
        if sampwidth == 4:
            samples = np.frombuffer(audio_data, dtype=np.float32)
        elif sampwidth == 8:
            samples = np.frombuffer(audio_data, dtype=np.float64)
        else:
            raise ValueError(f"Unsupported float sample width: {sampwidth}")
        audio = samples.astype(np.float64)
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)
        return audio

    if sampwidth == 2:
        dtype = np.int16
        max_val = 32767.0
    elif sampwidth == 3:
        # 24-bit: unpack manually
        raw_bytes = np.frombuffer(raw, dtype=np.uint8)
        n_samples = len(raw_bytes) // 3
        samples_24 = np.zeros(n_samples, dtype=np.int32)
        samples_24 = (raw_bytes[2::3].astype(np.int32) << 24
                       | raw_bytes[1::3].astype(np.int32) << 16
                       | raw_bytes[0::3].astype(np.int32) << 8) >> 8
        audio = samples_24.astype(np.float64) / 8388607.0
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)
        return audio
    elif sampwidth == 4:
        dtype = np.int32
        max_val = 2147483647.0
    else:
        dtype = np.int16
        max_val = 32767.0

    samples = np.frombuffer(raw, dtype=dtype)
    audio = samples.astype(np.float64) / max_val

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    return audio


def read_wavetable_frames(path: str | Path,
                          frame_size: int = WAVETABLE_SIZE
                          ) -> list[np.ndarray]:
    """Read a wavetable .wav and split into frames.

    The file is expected to be a single-cycle or multi-cycle
    wavetable where total samples = frame_size * N frames.

    Parameters
    ----------
    path : str or Path
        Path to the wavetable .wav file.
    frame_size : int
        Samples per frame (default 2048 for Serum).

    Returns
    -------
    list[np.ndarray]
        List of frame arrays, each of length *frame_size*.
    """
    audio = read_wav_samples(path)

    if len(audio) < frame_size:
        # Short file: pad to one frame
        padded = np.zeros(frame_size, dtype=np.float64)
        padded[:len(audio)] = audio
        return [padded]

    n_frames = len(audio) // frame_size
    frames = []
    for i in range(n_frames):
        start = i * frame_size
        frames.append(audio[start:start + frame_size].copy())
    return frames


def ingest_fxp_presets(catalog: GalatciaCatalog
                       ) -> dict[str, list[FXPPreset]]:
    """Read all .fxp presets from catalog and return grouped by category.

    Parameters
    ----------
    catalog : GalatciaCatalog
        A populated catalog from :func:`catalog_galatcia`.

    Returns
    -------
    dict[str, list[FXPPreset]]
        Category → list of parsed FXPPreset objects.
    """
    grouped: dict[str, list[FXPPreset]] = {}
    for entry in catalog.presets:
        try:
            preset = read_fxp(entry.source_path)
            grouped.setdefault(entry.category, []).append(preset)
        except Exception as exc:
            _log.warning("Failed to read %s: %s", entry.filename, exc)
    return grouped


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT — copy / organize everything into output/galatcia/
# ═══════════════════════════════════════════════════════════════════════════

def export_galatcia_samples(catalog: GalatciaCatalog,
                            output_dir: str = "output"
                            ) -> list[str]:
    """Copy all GALATCIA samples into output/galatcia/samples/{category}/.

    Returns list of destination paths.
    """
    out_root = Path(output_dir) / "galatcia" / "samples"
    paths: list[str] = []

    for sample in catalog.samples:
        cat_dir = out_root / sample.category
        cat_dir.mkdir(parents=True, exist_ok=True)
        dest = cat_dir / sample.filename
        shutil.copy2(sample.source_path, dest)
        paths.append(str(dest))

    _log.info("Exported %d samples to %s", len(paths), out_root)
    return paths


def export_galatcia_wavetables(catalog: GalatciaCatalog,
                               output_dir: str = "output"
                               ) -> list[str]:
    """Copy wavetables into output/galatcia/wavetables/."""
    out_dir = Path(output_dir) / "galatcia" / "wavetables"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for wt in catalog.wavetables:
        dest = out_dir / wt.filename
        shutil.copy2(wt.source_path, dest)
        paths.append(str(dest))

    _log.info("Exported %d wavetables to %s", len(paths), out_dir)
    return paths


def export_galatcia_presets(catalog: GalatciaCatalog,
                            output_dir: str = "output"
                            ) -> list[str]:
    """Copy .fxp presets into output/galatcia/presets/{category}/."""
    out_root = Path(output_dir) / "galatcia" / "presets"
    paths: list[str] = []

    for entry in catalog.presets:
        cat_dir = out_root / entry.category
        cat_dir.mkdir(parents=True, exist_ok=True)
        dest = cat_dir / entry.filename
        shutil.copy2(entry.source_path, dest)
        paths.append(str(dest))

    _log.info("Exported %d presets to %s", len(paths), out_root)
    return paths


def export_galatcia_racks(catalog: GalatciaCatalog,
                          output_dir: str = "output") -> list[str]:
    """Copy Ableton .adg racks into output/galatcia/racks/."""
    out_dir = Path(output_dir) / "galatcia" / "racks"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for rack in catalog.racks:
        dest = out_dir / rack.filename
        shutil.copy2(rack.source_path, dest)
        paths.append(str(dest))

    _log.info("Exported %d racks to %s", len(paths), out_dir)
    return paths


def export_galatcia_serumpack(catalog: GalatciaCatalog,
                              output_dir: str = "output") -> str:
    """Copy the .SerumPack file into output/galatcia/serumpack/."""
    if not catalog.serumpack_path:
        return ""
    out_dir = Path(output_dir) / "galatcia" / "serumpack"
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(catalog.serumpack_path)
    dest = out_dir / src.name
    shutil.copy2(src, dest)
    _log.info("Exported SerumPack to %s", dest)
    return str(dest)


def build_galatcia_manifest(catalog: GalatciaCatalog,
                            output_dir: str = "output") -> dict:
    """Build and write galatcia_manifest.json with full catalog."""
    manifest = {
        "name": "DUBFORGE × GALATCIA",
        "version": "1.0",
        "phi": PHI,
        "collections": {
            "black_octopus_brutal_dubstep": {
                "presets": len(catalog.presets),
                "categories": {},
            },
            "erb_neuro_wt": {
                "wavetables": len(catalog.wavetables),
                "names": [wt.name for wt in catalog.wavetables],
            },
            "samples": {
                "total": len(catalog.samples),
                "categories": {},
            },
            "ableton_racks": {
                "racks": [r.name for r in catalog.racks],
            },
        },
        "summary": catalog.summary(),
    }

    # Aggregate preset categories
    for p in catalog.presets:
        cat = p.category
        manifest["collections"]["black_octopus_brutal_dubstep"]["categories"]\
            .setdefault(cat, 0)
        manifest["collections"]["black_octopus_brutal_dubstep"]["categories"]\
            [cat] += 1

    # Aggregate sample categories
    for s in catalog.samples:
        cat = s.category
        manifest["collections"]["samples"]["categories"]\
            .setdefault(cat, 0)
        manifest["collections"]["samples"]["categories"][cat] += 1

    out_dir = Path(output_dir) / "galatcia"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "galatcia_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote manifest: %s", manifest_path)
    return manifest


def build_galatcia_marketplace_metadata(
    catalog: GalatciaCatalog,
    output_dir: str = "output",
) -> dict:
    """Auto-tag all GALATCIA samples for Splice / Loopcloud."""
    samples_meta = []
    for s in catalog.samples:
        meta = auto_tag_sample(
            filename=s.filename,
            category=s.category,
            subcategory=s.original_folder,
        )
        samples_meta.append(meta)

    pack_meta = {
        "name": "DUBFORGE × GALATCIA",
        "author": "DUBFORGE",
        "genre": "Dubstep",
        "bpm": 145.0,
        "tags": ["dubstep", "riddim", "neuro", "bass", "galatcia",
                 "brutal", "drum and bass"],
        "samples": [asdict(m) for m in samples_meta],
    }

    out_dir = Path(output_dir) / "galatcia"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "splice_metadata.json"
    meta_path.write_text(json.dumps(pack_meta, indent=2))
    _log.info("Wrote marketplace metadata: %s (%d samples)",
              meta_path, len(samples_meta))
    return pack_meta


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def export_all_galatcia(galatcia_root: str | Path | None = None,
                        output_dir: str = "output") -> dict:
    """Full GALATCIA integration pipeline.

    1. Catalog all content
    2. Export samples, wavetables, presets, racks, serumpack
    3. Build manifest + marketplace metadata

    Parameters
    ----------
    galatcia_root : str or Path, optional
        Override the GALATCIA source folder.
    output_dir : str
        Output directory (default ``output``).

    Returns
    -------
    dict
        Summary with file counts and paths.
    """
    root = Path(galatcia_root) if galatcia_root else None
    catalog = catalog_galatcia(root)

    if catalog.total_files == 0:
        _log.warning("No GALATCIA content found at %s", catalog.root)
        return {"error": "No GALATCIA content found", "root": catalog.root}

    sample_paths = export_galatcia_samples(catalog, output_dir)
    wt_paths = export_galatcia_wavetables(catalog, output_dir)
    preset_paths = export_galatcia_presets(catalog, output_dir)
    rack_paths = export_galatcia_racks(catalog, output_dir)
    sp_path = export_galatcia_serumpack(catalog, output_dir)
    manifest = build_galatcia_manifest(catalog, output_dir)
    marketplace = build_galatcia_marketplace_metadata(catalog, output_dir)

    result = {
        "samples_exported": len(sample_paths),
        "wavetables_exported": len(wt_paths),
        "presets_exported": len(preset_paths),
        "racks_exported": len(rack_paths),
        "serumpack_exported": bool(sp_path),
        "manifest": manifest,
        "total_files": catalog.total_files,
    }

    _log.info("GALATCIA integration complete: %d files exported",
              catalog.total_files)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# RACK ZONE MAPPING — Map Galactia samples → 128 Rack Fibonacci zones
# ═══════════════════════════════════════════════════════════════════════════
# Maps every Galactia sample category to a Rack128 zone for direct loading.
# Used by Stage 2E (rack build) and Stage 5A (rack load from raw audio).

# Galactia sample category → Rack zone name
SAMPLE_TO_ZONE: dict[str, str] = {
    # Drum one-shots
    "kicks":          "kicks",
    "snares":         "snares",
    "claps":          "snares",
    "hihats_closed":  "hats",
    "hihats_open":    "hats",
    # Drum loops
    "drum_loops":     "perc",
    "buildups":       "transitions",
    "perc_loops":     "perc",
    "hihat_loops":    "hats",
    "kick_snare_loops": "kicks",
    # FX
    "impacts":        "fx",
    "reverses":       "fx",
    "fx_falling":     "fx",
    "fx_rising":      "fx",
    "shepard_tones":  "fx",
    # Misc / default
    "misc":           "utility",
}

# Serum .fxp prefix → Rack zone name
PRESET_TO_ZONE: dict[str, str] = {
    "BS":  "mid_bass",      # bass presets
    "LD":  "melodic",       # leads
    "PAD": "atmos",         # pads → atmosphere
    "PL":  "melodic",       # plucks → melodic
    "SFX": "fx",            # sfx
    "SYN": "melodic",       # synth stabs
}


@dataclass
class GalactiaZoneMap:
    """Galactia samples organized by Rack128 zone for direct loading.

    Each zone entry is a list of (name, audio_array, source_path) tuples
    ready to pass to ``_rack_add()``.
    """
    zones: dict[str, list[tuple[str, np.ndarray, str]]] = field(
        default_factory=lambda: {
            "sub_bass": [], "low_bass": [], "mid_bass": [], "high_bass": [],
            "kicks": [], "snares": [], "hats": [], "perc": [],
            "fx": [], "melodic": [], "atmos": [], "vocal": [],
            "transitions": [], "utility": [],
        }
    )
    preset_zones: dict[str, list[tuple[str, str, str]]] = field(
        default_factory=dict
    )
    total_audio: int = 0
    total_presets: int = 0

    def summary(self) -> dict[str, int]:
        return {z: len(items) for z, items in self.zones.items() if items}


def map_galactia_to_zones(
    catalog: GalatciaCatalog | None = None,
    galatcia_root: Path | None = None,
    max_per_zone: int = 8,
) -> GalactiaZoneMap:
    """Scan Galactia and load samples into zone-mapped arrays.

    Parameters
    ----------
    catalog : GalatciaCatalog, optional
        Pre-built catalog.  If None, runs ``catalog_galatcia()``.
    galatcia_root : Path, optional
        Override Galactia root folder.
    max_per_zone : int
        Maximum samples to load per zone (prevents memory bloat).

    Returns
    -------
    GalactiaZoneMap
        Zone-organized samples ready for Rack128 insertion.
    """
    if catalog is None:
        catalog = catalog_galatcia(galatcia_root)

    zm = GalactiaZoneMap()

    # ── Audio samples → zones ──
    for sample in catalog.samples:
        zone = SAMPLE_TO_ZONE.get(sample.category)
        if zone is None or zone not in zm.zones:
            continue
        if len(zm.zones[zone]) >= max_per_zone:
            continue
        try:
            audio = read_wav_samples(sample.source_path)
            name = f"gal_{sample.category}_{Path(sample.filename).stem}"
            source = f"galactia:{sample.original_folder}/{sample.filename}"
            zm.zones[zone].append((name, audio, source))
            zm.total_audio += 1
        except Exception as exc:
            _log.warning("Failed to read %s: %s", sample.filename, exc)

    # ── Wavetables → utility zone ──
    for wt in catalog.wavetables:
        if len(zm.zones["utility"]) >= max_per_zone:
            break
        try:
            frames = read_wavetable_frames(wt.source_path)
            if frames:
                name = f"gal_wt_{wt.name}"
                source = f"galactia:wt/{wt.filename}"
                zm.zones["utility"].append((name, frames[0], source))
                zm.total_audio += 1
        except Exception as exc:
            _log.warning("Failed to read WT %s: %s", wt.filename, exc)

    # ── Presets → zone mapping (metadata only, no audio) ──
    for preset in catalog.presets:
        zone = PRESET_TO_ZONE.get(preset.prefix, "mid_bass")
        zm.preset_zones.setdefault(zone, []).append(
            (preset.name, preset.filename, f"galactia:preset/{preset.filename}")
        )
        zm.total_presets += 1

    _log.info("GALACTIA ZONE MAP: %d audio, %d presets — %s",
              zm.total_audio, zm.total_presets, zm.summary())
    return zm


# ═══════════════════════════════════════════════════════════════════════════
# ALS INTEGRATION — Project-wide GALATCIA → Ableton audio tracks
# ═══════════════════════════════════════════════════════════════════════════
# These functions convert GALATCIA samples into ALSTrack / ALSClipInfo
# objects that any make_*.py or forge.py script can use.
# Import from als_generator is deferred to avoid circular imports.
# ═══════════════════════════════════════════════════════════════════════════

# Default curated picks — scripts can override with their own mappings.
DEFAULT_DRUM_SAMPLES: dict[str, str] = {
    "kick":   "Drum One Shots/KICKS/BODP_Kick_3.wav",
    "snare":  "Drum One Shots/Snares/BODP_Snare_5.wav",
    "clap":   "Drum One Shots/Claps/BODP_Clap_2.wav",
    "hat_cl": "Drum One Shots/Hihats/Closed/BODP_Closed_7.wav",
    "hat_op": "Drum One Shots/Hihats/Open/BODP_Open_3.wav",
}

DEFAULT_FX_SAMPLES: dict[str, str] = {
    "impact":   "FX/Impacts/Booms/BODP_Impact_3.wav",
    "impact2":  "FX/Impacts/Booms/BODP_Impact_7.wav",
    "reverse":  "FX/Impacts/Reverses/BODP_Impact_Reverse_5.wav",
    "rising":   "FX/Noise/Rising/BODP_Rising_3.wav",
    "rising2":  "FX/Tonal/Rising/BODP_Rising_C_5.wav",
    "falling":  "FX/Noise/Falling/BODP_Falling_3.wav",
    "falling2": "FX/Tonal/Falling/BODP_Falling_C_7.wav",
    "shepard":  "FX/Shepard Tones/BODP_Shepard_F_1.wav",
}

DEFAULT_DRUM_LOOPS: dict[str, str] = {
    "beat1":   "Drum Loops/Beat Loops/BODP_Full_Beat_3.wav",
    "beat2":   "Drum Loops/Beat Loops/BODP_Full_Beat_7.wav",
    "build1":  "Drum Loops/Build Ups/BODP_Build_145_5.wav",
    "build2":  "Drum Loops/Build Ups/BODP_Build_145_12.wav",
    "fill1":   "Drum Loops/Fill & Perc Loops/BODP_Fill&Perc_4.wav",
    "hh_loop": "Drum Loops/Hihat Loops/BODP_HihatLoop_3.wav",
    "kns":     "Drum Loops/Kick And Snare Loops/BODP_KnS_5.wav",
}

DEFAULT_PRESET_MAP: dict[str, str] = {
    "BASS":       "BS Thicc.fxp",
    "GROWL":      "BS Disgusting.fxp",
    "WOBBLE":     "BS Flobble.fxp",
    "RIDDIM":     "BS Chopper.fxp",
    "FORMANT":    "BS Vocaloid.fxp",
    "LEAD":       "LD FM Fun.fxp",
    "COUNTER":    "PL Bellish.fxp",
    "VOCAL_CHOP": "PL Offbeat.fxp",
    "CHORDS":     "SYN Chord Stab.fxp",
    "PAD":        "PAD Eerie Digital.fxp",
    "ARP":        "PL Spaceage.fxp",
    "FX":         "SFX Laser.fxp",
    "RISER":      "SFX Ultra Tension.fxp",
}


@dataclass
class SectionInfo:
    """Describes an arrangement section for GALATCIA FX/loop placement.

    Parameters
    ----------
    name : str
        Section name (e.g. "DROP1", "PRE_CHORUS1").
    start_bar : int
        Starting bar number (0-indexed).
    n_bars : int
        Section length in bars.
    role : str
        One of: "intro", "verse", "build", "drop", "break",
        "bridge", "vip", "outro".  Determines which FX/loops to place.
    """
    name: str
    start_bar: int
    n_bars: int
    role: str = "verse"


def _wav_metadata(wav_path: Path) -> tuple[int, int, int]:
    """Return (sample_rate, n_frames, file_size) for a WAV file."""
    try:
        with wave.open(str(wav_path), "rb") as wf:
            return wf.getframerate(), wf.getnframes(), wav_path.stat().st_size
    except Exception:
        return 44100, 0, 0


def _resolve_sample(rel: str,
                    galatcia_root: Path | None = None) -> Path:
    """Resolve a relative GALATCIA sample path to absolute."""
    root = galatcia_root or DEFAULT_GALATCIA_ROOT
    return root / "Samples" / rel


def build_drum_audio_tracks(
    drum_notes: list[Any],
    pitch_map: dict[int, str] | None = None,
    drum_samples: dict[str, str] | None = None,
    galatcia_root: Path | None = None,
) -> list[Any]:
    """Convert drum MIDI notes into audio tracks with GALATCIA one-shots.

    Creates separate audio tracks for kicks, snares+claps, and hihats.

    Parameters
    ----------
    drum_notes : list[ALSMidiNote]
        MIDI notes from a drums track.  Each must have .pitch, .time,
        .duration, .velocity attributes.
    pitch_map : dict[int, str], optional
        Maps MIDI pitch → drum key (e.g. ``{36: "kick", 38: "snare"}``.
        Keys must match ``drum_samples`` keys.  If None, uses GM defaults:
        36=kick, 38=snare, 39=clap, 42=hat_cl, 46=hat_op.
    drum_samples : dict[str, str], optional
        Maps drum key → relative WAV path.  Defaults to
        ``DEFAULT_DRUM_SAMPLES``.
    galatcia_root : Path, optional
        Override GALATCIA root.

    Returns
    -------
    list[ALSTrack]
        Up to 3 audio tracks: KICK, SNARE, HATS.
    """
    from engine.als_generator import ALSClipInfo, ALSTrack

    if not drum_notes:
        return []

    samples = drum_samples or DEFAULT_DRUM_SAMPLES
    if pitch_map is None:
        pitch_map = {36: "kick", 38: "snare", 39: "clap",
                     42: "hat_cl", 46: "hat_op"}

    groups: dict[str, list[Any]] = {"kick": [], "snare": [], "hat": []}
    for n in drum_notes:
        key = pitch_map.get(n.pitch)
        if key == "kick":
            groups["kick"].append(n)
        elif key in ("snare", "clap"):
            groups["snare"].append(n)
        elif key in ("hat_cl", "hat_op"):
            groups["hat"].append(n)

    tracks: list[ALSTrack] = []

    # --- KICK ---
    kick_rel = samples.get("kick")
    if kick_rel and groups["kick"]:
        kick_path = _resolve_sample(kick_rel, galatcia_root)
        if kick_path.exists():
            sr, nf, fs = _wav_metadata(kick_path)
            clips = [
                ALSClipInfo(
                    path=str(kick_path), start_beat=n.time,
                    length_beats=max(n.duration, 1.0),
                    name=f"Kick@{n.time:.1f}",
                    sample_rate=sr, duration_frames=nf, file_size=fs,
                    gain=n.velocity / 127.0,
                ) for n in groups["kick"]
            ]
            tracks.append(ALSTrack(
                name="KICK [GALATCIA]", track_type="audio", color=69,
                volume_db=-1.0, pan=0.0, arrangement_clips=clips,
            ))

    # --- SNARE + CLAP ---
    snare_rel = samples.get("snare")
    clap_rel = samples.get("clap")
    clap_pitches = {p for p, k in pitch_map.items() if k == "clap"}
    if groups["snare"]:
        clips = []
        for n in groups["snare"]:
            rel = clap_rel if n.pitch in clap_pitches else snare_rel
            if not rel:
                continue
            path = _resolve_sample(rel, galatcia_root)
            if not path.exists():
                continue
            sr, nf, fs = _wav_metadata(path)
            is_clap = n.pitch in clap_pitches
            clips.append(ALSClipInfo(
                path=str(path), start_beat=n.time,
                length_beats=max(n.duration, 0.5),
                name=f"{'Clap' if is_clap else 'Snare'}@{n.time:.1f}",
                sample_rate=sr, duration_frames=nf, file_size=fs,
                gain=n.velocity / 127.0,
            ))
        if clips:
            tracks.append(ALSTrack(
                name="SNARE [GALATCIA]", track_type="audio", color=69,
                volume_db=-2.0, pan=0.0, arrangement_clips=clips,
            ))

    # --- HIHATS ---
    open_pitches = {p for p, k in pitch_map.items() if k == "hat_op"}
    hat_cl_rel = samples.get("hat_cl")
    hat_op_rel = samples.get("hat_op")
    if groups["hat"]:
        clips = []
        for n in groups["hat"]:
            rel = hat_op_rel if n.pitch in open_pitches else hat_cl_rel
            if not rel:
                continue
            path = _resolve_sample(rel, galatcia_root)
            if not path.exists():
                continue
            sr, nf, fs = _wav_metadata(path)
            is_open = n.pitch in open_pitches
            clips.append(ALSClipInfo(
                path=str(path), start_beat=n.time,
                length_beats=max(n.duration, 0.25),
                name=f"{'OH' if is_open else 'CH'}@{n.time:.1f}",
                sample_rate=sr, duration_frames=nf, file_size=fs,
                gain=n.velocity / 127.0 * 0.8,
            ))
        if clips:
            tracks.append(ALSTrack(
                name="HATS [GALATCIA]", track_type="audio", color=69,
                volume_db=-4.0, pan=0.0, arrangement_clips=clips,
            ))

    return tracks


def build_fx_audio_tracks(
    sections: list[SectionInfo],
    fx_samples: dict[str, str] | None = None,
    galatcia_root: Path | None = None,
) -> list[Any]:
    """Build IMPACTS and RISERS audio tracks from GALATCIA FX samples.

    Places FX at musically meaningful positions based on section roles:
    - Impacts at drop/vip entries
    - Reverse impacts 2 beats before drops
    - Risers during build sections
    - Fallers at break/bridge entries
    - Shepard tones in bridge sections

    Parameters
    ----------
    sections : list[SectionInfo]
        Arrangement sections with roles.
    fx_samples : dict[str, str], optional
        FX sample key → relative WAV path.  Defaults to
        ``DEFAULT_FX_SAMPLES``.
    galatcia_root : Path, optional
        Override GALATCIA root.

    Returns
    -------
    list[ALSTrack]
        Up to 2 audio tracks: IMPACTS, RISERS.
    """
    from engine.als_generator import ALSClipInfo, ALSTrack

    samples = fx_samples or DEFAULT_FX_SAMPLES
    fx_clips: list[ALSClipInfo] = []
    riser_clips: list[ALSClipInfo] = []

    def _make_clip(key: str, beat: float, length: float = 4.0,
                   gain: float = 0.8) -> ALSClipInfo | None:
        rel = samples.get(key)
        if not rel:
            return None
        path = _resolve_sample(rel, galatcia_root)
        if not path.exists():
            return None
        sr, nf, fs = _wav_metadata(path)
        return ALSClipInfo(
            path=str(path), start_beat=beat, length_beats=length,
            name=f"{key}@bar{beat / 4:.0f}",
            sample_rate=sr, duration_frames=nf, file_size=fs, gain=gain,
        )

    drop_idx = 0
    for sec in sections:
        beat = sec.start_bar * 4.0

        if sec.role in ("drop", "vip"):
            # Impact at drop entry
            key = "impact" if drop_idx % 2 == 0 else "impact2"
            clip = _make_clip(key, beat, length=4.0, gain=0.9)
            if clip:
                fx_clips.append(clip)
            # Reverse impact 2 beats before
            clip = _make_clip("reverse", beat - 2.0, length=2.0,
                              gain=0.7)
            if clip:
                fx_clips.append(clip)
            drop_idx += 1

        elif sec.role == "build":
            # Riser during build
            clip = _make_clip("rising", beat,
                              length=sec.n_bars * 4.0, gain=0.6)
            if clip:
                riser_clips.append(clip)

        elif sec.role == "bridge":
            # Second riser + shepard tone in bridge
            clip = _make_clip("rising2", beat,
                              length=sec.n_bars * 4.0, gain=0.6)
            if clip:
                riser_clips.append(clip)
            clip = _make_clip("shepard", beat,
                              length=sec.n_bars * 4.0, gain=0.35)
            if clip:
                riser_clips.append(clip)

        elif sec.role == "break":
            # Faller at break entry
            clip = _make_clip("falling", beat, length=8.0, gain=0.5)
            if clip:
                fx_clips.append(clip)

    tracks: list[ALSTrack] = []
    if fx_clips:
        tracks.append(ALSTrack(
            name="IMPACTS [GALATCIA]", track_type="audio", color=14,
            volume_db=-4.0, pan=0.0,
            arrangement_clips=sorted(fx_clips,
                                     key=lambda c: c.start_beat),
        ))
    if riser_clips:
        tracks.append(ALSTrack(
            name="RISERS [GALATCIA]", track_type="audio", color=15,
            volume_db=-6.0, pan=0.0,
            arrangement_clips=sorted(riser_clips,
                                     key=lambda c: c.start_beat),
        ))
    return tracks


def build_drum_loop_track(
    sections: list[SectionInfo],
    drum_loops: dict[str, str] | None = None,
    galatcia_root: Path | None = None,
) -> Any | None:
    """Layer GALATCIA drum loops during high-energy sections.

    - Beat loops in drop/vip sections
    - Build-up loops in build sections
    - K&S loops in bridge sections
    - Fill at the last bar before each drop

    Parameters
    ----------
    sections : list[SectionInfo]
        Arrangement sections with roles.
    drum_loops : dict[str, str], optional
        Loop key → relative WAV path.  Defaults to
        ``DEFAULT_DRUM_LOOPS``.
    galatcia_root : Path, optional
        Override GALATCIA root.

    Returns
    -------
    ALSTrack or None
        A single audio track with loop clips, or None if no loops found.
    """
    from engine.als_generator import ALSClipInfo, ALSTrack

    loops = drum_loops or DEFAULT_DRUM_LOOPS
    clips: list[ALSClipInfo] = []

    def _loop_clip(key: str, beat: float, length: float,
                   gain: float = 0.5) -> ALSClipInfo | None:
        rel = loops.get(key)
        if not rel:
            return None
        path = _resolve_sample(rel, galatcia_root)
        if not path.exists():
            return None
        sr, nf, fs = _wav_metadata(path)
        return ALSClipInfo(
            path=str(path), start_beat=beat, length_beats=length,
            name=f"Loop_{key}@bar{beat / 4:.0f}",
            sample_rate=sr, duration_frames=nf, file_size=fs,
            gain=gain, loop=True, loop_start=0.0, loop_end=length,
            warp_mode=4,
        )

    beat_idx = 0
    build_sections: list[SectionInfo] = []
    for sec in sections:
        beat = sec.start_bar * 4.0

        if sec.role in ("drop", "vip"):
            key = "beat1" if beat_idx % 2 == 0 else "beat2"
            clip = _loop_clip(key, beat, sec.n_bars * 4.0, gain=0.35)
            if clip:
                clips.append(clip)
            beat_idx += 1

        elif sec.role == "build":
            clip = _loop_clip("build1", beat, sec.n_bars * 4.0,
                              gain=0.4)
            if clip:
                clips.append(clip)
            build_sections.append(sec)

        elif sec.role == "bridge":
            clip = _loop_clip("kns", beat, sec.n_bars * 4.0, gain=0.3)
            if clip:
                clips.append(clip)

    # Fills at last bar before drops
    for sec in build_sections:
        fill_bar = sec.start_bar + sec.n_bars - 1
        clip = _loop_clip("fill1", fill_bar * 4.0, 4.0, gain=0.45)
        if clip:
            clips.append(clip)

    if not clips:
        return None

    return ALSTrack(
        name="LOOPS [GALATCIA]", track_type="audio", color=69,
        volume_db=-8.0, pan=0.0,
        arrangement_clips=sorted(clips, key=lambda c: c.start_beat),
    )


def install_wavetables(
    galatcia_root: Path | None = None,
    dest_folder: str = "DUBFORGE_GALATCIA",
) -> int:
    """Copy ERB NEURO WT wavetables into Serum 2's Tables folder.

    Parameters
    ----------
    galatcia_root : Path, optional
        Override GALATCIA root.
    dest_folder : str
        Subfolder name under Serum Presets/Tables/.

    Returns
    -------
    int
        Number of files copied.
    """
    root = galatcia_root or DEFAULT_GALATCIA_ROOT
    wt_dir = root / "ERB NEURO WT"
    serum_tables = (Path.home() / "Documents" / "Xfer"
                    / "Serum Presets" / "Tables" / dest_folder)
    if not wt_dir.is_dir():
        return 0
    wt_files = sorted(wt_dir.glob("*.wav"))
    if not wt_files:
        return 0
    serum_tables.mkdir(parents=True, exist_ok=True)
    copied = 0
    for wt in wt_files:
        dest = serum_tables / wt.name
        if not dest.exists():
            shutil.copy2(wt, dest)
            copied += 1
    _log.info("Installed %d/%d wavetables to %s",
              copied, len(wt_files), serum_tables)
    return copied


def copy_presets(
    preset_map: dict[str, str] | None = None,
    output_dir: str = "output",
    galatcia_root: Path | None = None,
) -> int:
    """Copy curated GALATCIA .fxp presets to output/presets/galatcia/.

    Parameters
    ----------
    preset_map : dict[str, str], optional
        Track name → FXP filename.  Defaults to ``DEFAULT_PRESET_MAP``.
    output_dir : str
        Output directory root.
    galatcia_root : Path, optional
        Override GALATCIA root.

    Returns
    -------
    int
        Number of presets copied.
    """
    root = galatcia_root or DEFAULT_GALATCIA_ROOT
    presets_dir = root / _REL_PRESETS
    out = Path(output_dir) / "presets" / "galatcia"
    out.mkdir(parents=True, exist_ok=True)
    if not presets_dir.is_dir():
        return 0
    pmap = preset_map or DEFAULT_PRESET_MAP
    copied = 0
    for track_name, fxp_name in pmap.items():
        src = presets_dir / fxp_name
        if src.exists():
            dest = out / f"{track_name}_{fxp_name}"
            shutil.copy2(src, dest)
            copied += 1
    _log.info("Copied %d/%d GALATCIA presets to %s",
              copied, len(pmap), out)
    return copied


def copy_racks(
    output_dir: str = "output",
    galatcia_root: Path | None = None,
) -> int:
    """Copy Ableton rack .adg files to output/racks/.

    Returns the number of racks copied.
    """
    root = galatcia_root or DEFAULT_GALATCIA_ROOT
    racks_dir = root / _REL_RACKS
    out = Path(output_dir) / "racks"
    out.mkdir(parents=True, exist_ok=True)
    if not racks_dir.is_dir():
        return 0
    copied = 0
    for adg in sorted(racks_dir.glob("*.adg")):
        dest = out / adg.name
        if not dest.exists():
            shutil.copy2(adg, dest)
            copied += 1
    _log.info("Copied %d GALATCIA racks to %s", copied, out)
    return copied


def integrate_galatcia_als(
    drum_notes: list[Any] | None = None,
    sections: list[SectionInfo] | None = None,
    pitch_map: dict[int, str] | None = None,
    drum_samples: dict[str, str] | None = None,
    fx_samples: dict[str, str] | None = None,
    drum_loops: dict[str, str] | None = None,
    preset_map: dict[str, str] | None = None,
    galatcia_root: Path | None = None,
) -> dict[str, Any]:
    """One-call GALATCIA ALS integration.

    Returns a dict with:
    - "audio_tracks": list[ALSTrack] to insert into an ALSProject
    - "preset_map": dict of track→FXP for ALS notes
    - "note_text": str for ALSProject.notes field

    Parameters
    ----------
    drum_notes : list, optional
        MIDI notes from drums track for audio conversion.
    sections : list[SectionInfo], optional
        Arrangement sections for FX/loop placement.
    pitch_map, drum_samples, fx_samples, drum_loops, preset_map :
        Override default mappings.
    galatcia_root : Path, optional
        Override GALATCIA root.
    """
    root = galatcia_root or DEFAULT_GALATCIA_ROOT
    samples_dir = root / "Samples" / "Samples"
    pmap = preset_map or DEFAULT_PRESET_MAP
    audio_tracks: list[Any] = []

    if samples_dir.is_dir():
        if drum_notes:
            audio_tracks.extend(build_drum_audio_tracks(
                drum_notes, pitch_map=pitch_map,
                drum_samples=drum_samples, galatcia_root=root,
            ))
        if sections:
            audio_tracks.extend(build_fx_audio_tracks(
                sections, fx_samples=fx_samples, galatcia_root=root,
            ))
            loop_track = build_drum_loop_track(
                sections, drum_loops=drum_loops, galatcia_root=root,
            )
            if loop_track:
                audio_tracks.append(loop_track)

    note_lines: list[str] = []
    if audio_tracks:
        note_lines.append(
            f"\nGALATCIA Integration: "
            f"{len(audio_tracks)} audio tracks loaded.")
        note_lines.append(
            "GALATCIA Serum 2 presets (in output/presets/galatcia/):")
        for tn, fxp in pmap.items():
            note_lines.append(f"  {tn} -> {fxp}")

    return {
        "audio_tracks": audio_tracks,
        "preset_map": pmap,
        "note_text": "\n".join(note_lines),
    }
