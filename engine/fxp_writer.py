"""
DUBFORGE Engine — FXP / VST2 Preset Writer

Generates .fxp (single preset) and .fxb (preset bank) files
conforming to the VST2 preset format specification.

These files can be loaded in Serum 2, Vital, and other VST2-
compatible synthesizers.

Outputs:
    output/presets/*.fxp — Individual VST2 presets
    output/presets/preset_manifest.json — Metadata for all presets
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

from engine.config_loader import PHI
from engine.log import get_logger

_log = get_logger("dubforge.fxp_writer")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

# VST2 FXP/FXB magic numbers
FXP_MAGIC = b"CcnK"         # Main container chunk
FXP_REGULAR = b"FxCk"       # Regular preset (float params)
FXP_OPAQUE = b"FPCh"        # Opaque chunk preset (binary blob)
FXB_REGULAR = b"FxBk"       # Regular bank
FXB_OPAQUE = b"FBCh"        # Opaque chunk bank
VST2_VERSION = 1             # FXP format version


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VSTParam:
    """A single VST2 parameter."""
    index: int
    name: str
    value: float       # 0.0 - 1.0 normalized
    display: str = ""  # human-readable display value


@dataclass
class FXPPreset:
    """A VST2 preset (FXP format)."""
    name: str                                 # 28 chars max in FXP header
    plugin_id: str = "DubF"                   # 4-char VST2 plugin ID
    version: int = 1
    params: list[VSTParam] = field(default_factory=list)
    chunk_data: bytes = b""                   # opaque chunk (if any)

    @property
    def is_opaque(self) -> bool:
        return len(self.chunk_data) > 0


@dataclass
class FXPBank:
    """A VST2 preset bank (FXB format)."""
    name: str
    plugin_id: str = "DubF"
    version: int = 1
    presets: list[FXPPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# FXP BINARY WRITER
# ═══════════════════════════════════════════════════════════════════════════

def _encode_plugin_id(plugin_id: str) -> int:
    """Convert a 4-char plugin ID string to a 32-bit integer."""
    if len(plugin_id) != 4:
        raise ValueError(f"Plugin ID must be 4 chars, got: {plugin_id!r}")
    return struct.unpack(">I", plugin_id.encode("ascii"))[0]


def _pad_name(name: str, length: int = 28) -> bytes:
    """Pad preset name to fixed length, null-terminated."""
    encoded = name.encode("ascii", errors="replace")[:length]
    return encoded.ljust(length, b"\x00")


def write_fxp(preset: FXPPreset, path: str) -> str:
    """Write a VST2 .fxp preset file."""
    plugin_id_int = _encode_plugin_id(preset.plugin_id)
    name_bytes = _pad_name(preset.name)

    if preset.is_opaque:
        # Opaque chunk format
        chunk = preset.chunk_data
        # Header: chunkMagic(4) + byteSize(4) + fxMagic(4) +
        #          version(4) + fxID(4) + fxVersion(4) +
        #          numPrograms(4) + prgName(28) + chunkSize(4) + chunk(N)
        body = struct.pack(">I", VST2_VERSION)          # version
        body += struct.pack(">I", plugin_id_int)         # fxID
        body += struct.pack(">I", preset.version)        # fxVersion
        body += struct.pack(">I", 1)                     # numPrograms
        body += name_bytes                                # prgName
        body += struct.pack(">I", len(chunk))            # chunkSize
        body += chunk                                     # chunk data

        byte_size = len(body) + 8  # +8 for fxMagic + the remaining fields up
        header = FXP_MAGIC + struct.pack(">I", byte_size) + FXP_OPAQUE
        data = header + body
    else:
        # Regular params format
        n_params = len(preset.params)
        body = struct.pack(">I", VST2_VERSION)           # version
        body += struct.pack(">I", plugin_id_int)          # fxID
        body += struct.pack(">I", preset.version)         # fxVersion
        body += struct.pack(">I", n_params)               # numParams
        body += name_bytes                                 # prgName
        for param in sorted(preset.params, key=lambda p: p.index):
            body += struct.pack(">f", param.value)        # param value (float32 BE)

        byte_size = len(body) + 8
        header = FXP_MAGIC + struct.pack(">I", byte_size) + FXP_REGULAR
        data = header + body

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    _log.info("Wrote FXP: %s (%d params)", out_path.name, len(preset.params))
    return str(out_path)


def read_fxp(path: str) -> FXPPreset:
    """Read a VST2 .fxp preset file."""
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] != FXP_MAGIC:
        raise ValueError(f"Not a valid FXP file: {path}")

    struct.unpack(">I", data[4:8])[0]
    fx_magic = data[8:12]

    offset = 12
    struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    plugin_id_int = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    fx_version = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4

    plugin_id = struct.pack(">I", plugin_id_int).decode("ascii", errors="replace")

    if fx_magic == FXP_OPAQUE:
        struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        name = data[offset:offset + 28].rstrip(b"\x00").decode("ascii", errors="replace")
        offset += 28
        chunk_size = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        chunk = data[offset:offset + chunk_size]
        return FXPPreset(name=name, plugin_id=plugin_id, version=fx_version,
                         chunk_data=chunk)
    elif fx_magic == FXP_REGULAR:
        n_params = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        name = data[offset:offset + 28].rstrip(b"\x00").decode("ascii", errors="replace")
        offset += 28
        params = []
        for i in range(n_params):
            val = struct.unpack(">f", data[offset:offset + 4])[0]
            offset += 4
            params.append(VSTParam(index=i, name=f"param_{i}", value=val))
        return FXPPreset(name=name, plugin_id=plugin_id, version=fx_version,
                         params=params)
    else:
        raise ValueError(f"Unknown FXP format: {fx_magic!r}")


# ═══════════════════════════════════════════════════════════════════════════
# FXB BANK WRITER
# ═══════════════════════════════════════════════════════════════════════════

def write_fxb(bank: FXPBank, path: str) -> str:
    """Write a VST2 .fxb preset bank file."""
    plugin_id_int = _encode_plugin_id(bank.plugin_id)
    n_presets = len(bank.presets)

    if n_presets == 0:
        raise ValueError("Bank must contain at least one preset")

    # Assume all presets are regular (same param count)
    len(bank.presets[0].params)

    body = struct.pack(">I", VST2_VERSION)              # version
    body += struct.pack(">I", plugin_id_int)             # fxID
    body += struct.pack(">I", bank.version)              # fxVersion
    body += struct.pack(">I", n_presets)                  # numPrograms
    body += struct.pack(">I", 0)                          # currentProgram
    body += b"\x00" * 124                                 # future (reserved)

    for preset in bank.presets:
        name_bytes = _pad_name(preset.name)
        body += name_bytes
        for param in sorted(preset.params, key=lambda p: p.index):
            body += struct.pack(">f", param.value)

    byte_size = len(body) + 8
    header = FXP_MAGIC + struct.pack(">I", byte_size) + FXB_REGULAR
    data = header + body

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)

    _log.info("Wrote FXB bank: %s (%d presets)", out_path.name, n_presets)
    return str(out_path)


# ═══════════════════════════════════════════════════════════════════════════
# DUBFORGE SYNTH PRESETS — PHI-SEEDED PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

def _phi_param(base: float, index: int) -> float:
    """Generate a phi-scaled parameter value."""
    val = base * (1.0 / (PHI ** (index * 0.5)))
    return max(0.0, min(1.0, val))


def dubstep_sub_preset() -> FXPPreset:
    """Deep sub-bass preset with phi-tuned parameters."""
    params = [
        VSTParam(0, "Osc1_Shape", 0.0, "Sine"),
        VSTParam(1, "Osc1_Octave", 0.25, "-2 oct"),
        VSTParam(2, "Osc1_Level", 1.0, "0 dB"),
        VSTParam(3, "Osc2_Shape", _phi_param(0.3, 1), "Triangle-ish"),
        VSTParam(4, "Osc2_Octave", 0.25, "-2 oct"),
        VSTParam(5, "Osc2_Level", _phi_param(0.8, 1), "-3 dB"),
        VSTParam(6, "Filter_Cutoff", _phi_param(0.4, 0), "~200 Hz"),
        VSTParam(7, "Filter_Reso", 0.0, "No resonance"),
        VSTParam(8, "Filter_Type", 0.0, "LP 24"),
        VSTParam(9, "Amp_Attack", 0.01, "Fast"),
        VSTParam(10, "Amp_Decay", 0.3, "Medium"),
        VSTParam(11, "Amp_Sustain", 1.0, "Full"),
        VSTParam(12, "Amp_Release", _phi_param(0.5, 2), "Phi-release"),
        VSTParam(13, "Distortion", 0.0, "None"),
        VSTParam(14, "Unison_Voices", 0.0, "1 voice"),
        VSTParam(15, "Unison_Detune", 0.0, "No detune"),
    ]
    return FXPPreset(name="DUBFORGE_SUB", params=params)


def dubstep_growl_preset() -> FXPPreset:
    """Growl mid-bass preset with aggressive modulation."""
    params = [
        VSTParam(0, "Osc1_Shape", 0.5, "Saw"),
        VSTParam(1, "Osc1_Octave", 0.5, "0 oct"),
        VSTParam(2, "Osc1_Level", 0.9, "-1 dB"),
        VSTParam(3, "Osc2_Shape", 0.75, "Square"),
        VSTParam(4, "Osc2_Octave", 0.5, "0 oct"),
        VSTParam(5, "Osc2_Level", _phi_param(0.7, 1), "Phi-level"),
        VSTParam(6, "Filter_Cutoff", _phi_param(0.8, 0), "~3k Hz"),
        VSTParam(7, "Filter_Reso", _phi_param(0.6, 1), "Phi-reso"),
        VSTParam(8, "Filter_Type", 0.0, "LP 12"),
        VSTParam(9, "Amp_Attack", 0.002, "Instant"),
        VSTParam(10, "Amp_Decay", 0.1, "Short"),
        VSTParam(11, "Amp_Sustain", 0.8, "High sustain"),
        VSTParam(12, "Amp_Release", 0.15, "Fast"),
        VSTParam(13, "Distortion", _phi_param(0.7, 0), "Heavy"),
        VSTParam(14, "Unison_Voices", 0.5, "4 voices"),
        VSTParam(15, "Unison_Detune", _phi_param(0.4, 1), "Phi-detune"),
        VSTParam(16, "LFO1_Rate", _phi_param(0.6, 0), "Phi-rate"),
        VSTParam(17, "LFO1_Amount", 0.7, "Heavy mod"),
        VSTParam(18, "LFO1_Dest", 0.3, "→ Filter"),
        VSTParam(19, "FM_Amount", _phi_param(0.5, 1), "Phi-FM"),
    ]
    return FXPPreset(name="DUBFORGE_GROWL", params=params)


def dubstep_lead_preset() -> FXPPreset:
    """Cutting lead preset for melodic sections."""
    params = [
        VSTParam(0, "Osc1_Shape", 0.6, "Supersaw"),
        VSTParam(1, "Osc1_Octave", 0.75, "+1 oct"),
        VSTParam(2, "Osc1_Level", 0.85, "-1.5 dB"),
        VSTParam(3, "Osc2_Shape", 0.5, "Saw"),
        VSTParam(4, "Osc2_Octave", 0.5, "0 oct"),
        VSTParam(5, "Osc2_Level", 0.6, "-4 dB"),
        VSTParam(6, "Filter_Cutoff", _phi_param(0.9, 0), "~8k Hz"),
        VSTParam(7, "Filter_Reso", _phi_param(0.3, 1), "Subtle"),
        VSTParam(8, "Filter_Type", 0.0, "LP 12"),
        VSTParam(9, "Amp_Attack", 0.005, "Fast"),
        VSTParam(10, "Amp_Decay", 0.2, "Medium"),
        VSTParam(11, "Amp_Sustain", 0.7, "Med sustain"),
        VSTParam(12, "Amp_Release", 0.3, "Smooth"),
        VSTParam(13, "Distortion", 0.15, "Light"),
        VSTParam(14, "Unison_Voices", 0.75, "6 voices"),
        VSTParam(15, "Unison_Detune", _phi_param(0.3, 0), "Wide"),
    ]
    return FXPPreset(name="DUBFORGE_LEAD", params=params)


def dubstep_pad_preset() -> FXPPreset:
    """Ambient pad preset with long evolving textures."""
    params = [
        VSTParam(0, "Osc1_Shape", 0.3, "Triangle"),
        VSTParam(1, "Osc1_Octave", 0.5, "0 oct"),
        VSTParam(2, "Osc1_Level", 0.7, "-3 dB"),
        VSTParam(3, "Osc2_Shape", 0.5, "Saw"),
        VSTParam(4, "Osc2_Octave", 0.75, "+1 oct"),
        VSTParam(5, "Osc2_Level", _phi_param(0.5, 2), "Phi-level"),
        VSTParam(6, "Filter_Cutoff", _phi_param(0.5, 0), "~1k Hz"),
        VSTParam(7, "Filter_Reso", 0.2, "Low"),
        VSTParam(8, "Filter_Type", 0.0, "LP 12"),
        VSTParam(9, "Amp_Attack", 0.8, "Slow"),
        VSTParam(10, "Amp_Decay", 0.5, "Long"),
        VSTParam(11, "Amp_Sustain", 0.9, "High"),
        VSTParam(12, "Amp_Release", _phi_param(0.8, 0), "Phi-release"),
        VSTParam(13, "Distortion", 0.0, "None"),
        VSTParam(14, "Unison_Voices", 1.0, "8 voices"),
        VSTParam(15, "Unison_Detune", 0.15, "Subtle"),
    ]
    return FXPPreset(name="DUBFORGE_PAD", params=params)


ALL_PRESETS = {
    "sub":   dubstep_sub_preset,
    "growl": dubstep_growl_preset,
    "lead":  dubstep_lead_preset,
    "pad":   dubstep_pad_preset,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_preset_manifest(presets: dict[str, FXPPreset],
                          output_dir: str) -> str:
    """Write preset metadata to JSON."""
    data = {
        "generator": "DUBFORGE FXP Writer",
        "format": "VST2 FXP",
        "presets": {},
    }
    for name, preset in presets.items():
        data["presets"][name] = {
            "name": preset.name,
            "plugin_id": preset.plugin_id,
            "param_count": len(preset.params),
            "is_opaque": preset.is_opaque,
            "file": f"{preset.name}.fxp",
        }
    path = Path(output_dir) / "preset_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    out_dir = Path("output/presets")
    out_dir.mkdir(parents=True, exist_ok=True)

    presets = {}
    for name, gen_fn in ALL_PRESETS.items():
        preset = gen_fn()
        presets[name] = preset
        path = str(out_dir / f"{preset.name}.fxp")
        write_fxp(preset, path)
        print(f"  {preset.name}.fxp  ({len(preset.params)} params)")

    # Write bank
    bank = FXPBank(
        name="DUBFORGE_BANK",
        presets=list(presets.values()),
    )
    bank_path = str(out_dir / "DUBFORGE_BANK.fxb")
    write_fxb(bank, bank_path)
    print(f"  DUBFORGE_BANK.fxb  ({len(bank.presets)} presets)")

    # Manifest
    write_preset_manifest(presets, str(out_dir))
    print("  preset_manifest.json")

    print(f"FXP Writer complete — {len(presets)} presets + 1 bank.")


if __name__ == "__main__":
    main()
