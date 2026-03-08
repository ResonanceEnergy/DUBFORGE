"""
DUBFORGE Engine — Preset Pack Builder

Batch-export Serum 2 .fxp presets from all patches.
Organized into category folders with metadata manifests.

Categories:
    bass        — sub/mid/wobble bass patches
    lead        — lead synth patches
    pad         — pad/atmosphere patches
    pluck       — pluck/stab patches
    fx          — FX/riser/impact patches

Banks: 5 categories × 4 presets = 20 presets
"""

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

PHI = 1.6180339887

# FXP constants
FXP_MAGIC = b'CcnK'
FXP_VERSION = 1
FXP_OPAQUE_ID = b'DubF'
FXP_CHUNK_MAGIC = b'FPCh'


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PresetPackEntry:
    """A single preset entry in a pack."""
    name: str
    category: str
    osc_type: str = "saw"
    num_voices: int = 1
    detune: float = 0.0
    filter_cutoff: float = 1.0
    filter_resonance: float = 0.0
    env_attack: float = 0.01
    env_decay: float = 0.3
    env_sustain: float = 0.7
    env_release: float = 0.5
    lfo_rate: float = 1.0
    lfo_depth: float = 0.0
    fx_drive: float = 0.0
    fx_reverb: float = 0.0


@dataclass
class PresetPackPreset:
    """Configuration for building a preset pack."""
    name: str
    pack_type: str  # bass, lead, pad, pluck, fx
    entries: list[PresetPackEntry] = field(default_factory=list)
    format: str = "fxp"


@dataclass
class PresetPackBank:
    name: str
    presets: list[PresetPackPreset]


# ═══════════════════════════════════════════════════════════════════════════
# FXP WRITER
# ═══════════════════════════════════════════════════════════════════════════

def _entry_to_bytes(entry: PresetPackEntry) -> bytes:
    """Serialize a preset entry to binary chunk data."""
    data = json.dumps({
        "name": entry.name,
        "category": entry.category,
        "osc_type": entry.osc_type,
        "num_voices": entry.num_voices,
        "detune": entry.detune,
        "filter_cutoff": entry.filter_cutoff,
        "filter_resonance": entry.filter_resonance,
        "env_attack": entry.env_attack,
        "env_decay": entry.env_decay,
        "env_sustain": entry.env_sustain,
        "env_release": entry.env_release,
        "lfo_rate": entry.lfo_rate,
        "lfo_depth": entry.lfo_depth,
        "fx_drive": entry.fx_drive,
        "fx_reverb": entry.fx_reverb,
    }).encode("utf-8")
    return data


def write_fxp(entry: PresetPackEntry, path: Path) -> str:
    """Write a single .fxp preset file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk_data = _entry_to_bytes(entry)
    # FXP header: magic(4) + size(4) + fxMagic(4) + version(4) + fxID(4) +
    #             fxVersion(4) + numPrograms(4) + prgName(28) + chunkSize(4) + chunk
    prgname = entry.name.encode("utf-8")[:28].ljust(28, b'\x00')
    header_size = 4 + 4 + 4 + 4 + 4 + 28 + 4 + len(chunk_data)
    data = b''
    data += FXP_MAGIC
    data += struct.pack('>I', header_size)
    data += FXP_CHUNK_MAGIC
    data += struct.pack('>I', FXP_VERSION)
    data += FXP_OPAQUE_ID
    data += struct.pack('>I', 1)  # fxVersion
    data += struct.pack('>I', 1)  # numPrograms
    data += prgname
    data += struct.pack('>I', len(chunk_data))
    data += chunk_data

    with open(path, "wb") as f:
        f.write(data)
    return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# PACK BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _generate_bass_entries() -> list[PresetPackEntry]:
    return [
        PresetPackEntry("Bass Sub Pure", "bass", "sine", 1, 0.0, 0.3, 0.0, 0.01, 0.5, 0.8, 0.3),
        PresetPackEntry("Bass Mid Growl", "bass", "saw", 3, 0.15, 0.5, 0.3, 0.01, 0.3, 0.7, 0.2,
                        fx_drive=0.4),
        PresetPackEntry("Bass Wobble Phi", "bass", "square", 2, 0.1, 0.6, 0.2, 0.01, 0.4, 0.6, 0.3,
                        lfo_rate=PHI, lfo_depth=0.5),
        PresetPackEntry("Bass Reese", "bass", "saw", 4, 0.25, 0.4, 0.1, 0.01, 0.6, 0.5, 0.4),
    ]


def _generate_lead_entries() -> list[PresetPackEntry]:
    return [
        PresetPackEntry("Lead Bright", "lead", "saw", 5, 0.2, 0.9, 0.1, 0.01, 0.2, 0.5, 0.3),
        PresetPackEntry("Lead Soft", "lead", "sine", 1, 0.0, 0.7, 0.0, 0.05, 0.3, 0.8, 0.5),
        PresetPackEntry("Lead Scream", "lead", "saw", 7, 0.3, 1.0, 0.4, 0.001, 0.1, 0.4, 0.2,
                        fx_drive=0.6),
        PresetPackEntry("Lead Phi", "lead", "saw", 3, 1.0 / PHI * 0.3, 0.8, 0.15, 0.01, 0.2, 0.6, 0.3),
    ]


def _generate_pad_entries() -> list[PresetPackEntry]:
    return [
        PresetPackEntry("Pad Warm", "pad", "saw", 4, 0.1, 0.4, 0.0, 0.5, 1.0, 0.9, 2.0,
                        fx_reverb=0.6),
        PresetPackEntry("Pad Airy", "pad", "sine", 2, 0.05, 0.6, 0.0, 0.8, 1.5, 0.8, 3.0,
                        fx_reverb=0.8),
        PresetPackEntry("Pad Dark", "pad", "square", 3, 0.15, 0.2, 0.1, 0.3, 0.8, 0.9, 1.5,
                        fx_reverb=0.5),
        PresetPackEntry("Pad Phi Evolve", "pad", "saw", 5, 1.0 / PHI * 0.2, 0.5, 0.05, 1.0, 2.0, 0.7, 4.0,
                        lfo_rate=1.0 / PHI, lfo_depth=0.3, fx_reverb=0.7),
    ]


def _generate_pluck_entries() -> list[PresetPackEntry]:
    return [
        PresetPackEntry("Pluck Sharp", "pluck", "saw", 1, 0.0, 0.8, 0.2, 0.001, 0.1, 0.0, 0.2),
        PresetPackEntry("Pluck Soft", "pluck", "sine", 2, 0.05, 0.5, 0.0, 0.005, 0.2, 0.1, 0.4),
        PresetPackEntry("Pluck Metallic", "pluck", "square", 3, 0.1, 1.0, 0.5, 0.001, 0.05, 0.0, 0.15),
        PresetPackEntry("Pluck Phi", "pluck", "saw", 2, 1.0 / PHI * 0.1, 0.7, 0.1, 0.002, 0.15, 0.05, 0.25),
    ]


def _generate_fx_entries() -> list[PresetPackEntry]:
    return [
        PresetPackEntry("FX Riser", "fx", "saw", 5, 0.3, 0.1, 0.0, 2.0, 0.5, 0.3, 1.0,
                        lfo_rate=0.25, lfo_depth=0.8, fx_reverb=0.5),
        PresetPackEntry("FX Impact", "fx", "sine", 1, 0.0, 0.9, 0.0, 0.001, 0.8, 0.0, 0.05,
                        fx_drive=0.3),
        PresetPackEntry("FX Texture", "fx", "saw", 7, 0.4, 0.3, 0.1, 0.5, 2.0, 0.5, 3.0,
                        lfo_rate=PHI, lfo_depth=0.4, fx_reverb=0.9),
        PresetPackEntry("FX Phi Sweep", "fx", "square", 3, 0.2, 0.5, 0.2, 1.0, 1.5, 0.2, 2.0,
                        lfo_rate=1.0 / PHI, lfo_depth=0.6),
    ]


ENTRY_GENERATORS = {
    "bass": _generate_bass_entries,
    "lead": _generate_lead_entries,
    "pad": _generate_pad_entries,
    "pluck": _generate_pluck_entries,
    "fx": _generate_fx_entries,
}


def build_preset_pack(preset: PresetPackPreset,
                      output_dir: str = "output") -> list[str]:
    """Build an .fxp preset pack."""
    out = Path(output_dir) / "presets" / preset.pack_type / preset.name
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    entries = preset.entries
    if not entries:
        gen = ENTRY_GENERATORS.get(preset.pack_type, _generate_bass_entries)
        entries = gen()

    for entry in entries:
        fname = f"{entry.name.replace(' ', '_').lower()}.fxp"
        p = write_fxp(entry, out / fname)
        paths.append(p)

    # Write pack manifest
    manifest = {
        "pack": preset.name,
        "type": preset.pack_type,
        "num_presets": len(entries),
        "files": [p.split("/")[-1] for p in paths],
    }
    with open(out / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return paths


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def bass_preset_bank() -> PresetPackBank:
    return PresetPackBank("bass", [
        PresetPackPreset("bass_essentials", "bass"),
        PresetPackPreset("bass_heavy", "bass"),
        PresetPackPreset("bass_phi", "bass"),
        PresetPackPreset("bass_wobble", "bass"),
    ])


def lead_preset_bank() -> PresetPackBank:
    return PresetPackBank("lead", [
        PresetPackPreset("lead_essentials", "lead"),
        PresetPackPreset("lead_bright", "lead"),
        PresetPackPreset("lead_phi", "lead"),
        PresetPackPreset("lead_scream", "lead"),
    ])


def pad_preset_bank() -> PresetPackBank:
    return PresetPackBank("pad", [
        PresetPackPreset("pad_essentials", "pad"),
        PresetPackPreset("pad_ambient", "pad"),
        PresetPackPreset("pad_phi", "pad"),
        PresetPackPreset("pad_dark", "pad"),
    ])


def pluck_preset_bank() -> PresetPackBank:
    return PresetPackBank("pluck", [
        PresetPackPreset("pluck_essentials", "pluck"),
        PresetPackPreset("pluck_metallic", "pluck"),
        PresetPackPreset("pluck_phi", "pluck"),
        PresetPackPreset("pluck_soft", "pluck"),
    ])


def fx_preset_bank() -> PresetPackBank:
    return PresetPackBank("fx", [
        PresetPackPreset("fx_essentials", "fx"),
        PresetPackPreset("fx_risers", "fx"),
        PresetPackPreset("fx_phi", "fx"),
        PresetPackPreset("fx_textures", "fx"),
    ])


ALL_PRESET_PACK_BANKS: dict[str, callable] = {
    "bass": bass_preset_bank,
    "lead": lead_preset_bank,
    "pad": pad_preset_bank,
    "pluck": pluck_preset_bank,
    "fx": fx_preset_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_all_preset_packs(output_dir: str = "output") -> list[str]:
    """Build all preset packs and return .fxp paths."""
    paths: list[str] = []
    for bank_name, bank_fn in ALL_PRESET_PACK_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            paths.extend(build_preset_pack(preset, output_dir))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_preset_pack_manifest(output_dir: str = "output") -> dict:
    """Write preset pack builder manifest JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_PRESET_PACK_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }
    path = out / "preset_pack_builder_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_preset_pack_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    fxps = export_all_preset_packs()
    print(f"Preset Pack Builder: {len(manifest['banks'])} banks, {total} presets, {len(fxps)} .fxp")


if __name__ == "__main__":
    main()
