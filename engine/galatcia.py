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

DEFAULT_GALATCIA_ROOT = Path(r"C:\dev\DUBFORGE GALATCIA")

# Relative paths inside GALATCIA root
_REL_PRESETS = Path("Black Octopus - Brutal Dubstep and Riddim") / \
    "Black Octopus - Brutal Dubstep and Riddim"
_REL_WAVETABLES = Path("ERB NEURO WT") / "ERB NEURO WT"
_REL_SAMPLES = Path("Samples") / "Samples"
_REL_RACKS = Path("Ableton Racks") / "Ableton Racks"
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
    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

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
