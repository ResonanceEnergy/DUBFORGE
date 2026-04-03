"""Serum 2 native .SerumPreset reader / writer / modifier.

Reads XferJson-wrapped presets (header + JSON metadata + zstd-compressed CBOR),
modifies parameters, re-serializes, and writes valid .SerumPreset files that
Serum 2 loads natively.

Also provides ``get_processor_state()`` to produce raw bytes suitable for
embedding into an Ableton Live .als <ProcessorState> element (base64-encoded
by the caller).
"""
from __future__ import annotations

import hashlib
import json
import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cbor2
import zstandard

_log = logging.getLogger("dubforge.serum2_preset")

# ──────────────────────────────────────────────────────────────────────
# File format constants
# ──────────────────────────────────────────────────────────────────────
_MAGIC = b"XferJson\x00"              # 9-byte file header
_SERUM2_PRESET_DIR = Path(
    "/Library/Audio/Presets/Xfer Records/Serum 2 Presets"
)
_FACTORY_DIR = _SERUM2_PRESET_DIR / "Presets" / "Factory"
_USER_DIR = _SERUM2_PRESET_DIR / "Presets" / "User"
_DUBFORGE_DIR = _USER_DIR / "DUBFORGE"

ZSTD_LEVEL = 3  # compression level (1-22, 3 is default)


# ──────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────
@dataclass
class SerumPreset:
    """In-memory representation of a Serum 2 preset."""

    name: str
    author: str = "DUBFORGE"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    product: str = "Serum2"
    product_version: str = "2.0.11"
    vendor: str = "Xfer Records"
    url: str = "https://github.com/ResonanceEnergy/DUBFORGE"
    version: float = 4.0
    # The actual CBOR dict with all 175 module keys
    cbor_data: dict[str, Any] = field(default_factory=dict)

    # ── Convenience parameter access ──────────────────────────────────

    def set_param(self, module: str, param: str, value: Any) -> None:
        """Set a single parameter on a module's plainParams dict.

        If the module's plainParams is the string ``"default"``, it is
        promoted to a dict first.
        """
        mod = self.cbor_data.get(module)
        if mod is None:
            self.cbor_data[module] = {"plainParams": {param: value}}
            return
        if not isinstance(mod, dict):
            return
        pp = mod.get("plainParams", "default")
        if pp == "default":
            mod["plainParams"] = {param: value}
        elif isinstance(pp, dict):
            pp[param] = value
        else:
            mod["plainParams"] = {param: value}

    def set_params(self, module: str, params: dict[str, Any]) -> None:
        """Set multiple parameters on a module at once."""
        for k, v in params.items():
            self.set_param(module, k, v)

    def set_sub_param(self, module: str, sub: str, param: str, value: Any) -> None:
        """Set a parameter on a sub-module (e.g. Oscillator0.WTOsc0)."""
        mod = self.cbor_data.setdefault(module, {"plainParams": "default"})
        if not isinstance(mod, dict):
            return
        sub_mod = mod.setdefault(sub, {"plainParams": "default"})
        if not isinstance(sub_mod, dict):
            return
        pp = sub_mod.get("plainParams", "default")
        if pp == "default":
            sub_mod["plainParams"] = {param: value}
        elif isinstance(pp, dict):
            pp[param] = value

    def set_mod_slot(self, slot: int, *,
                     dest_module_id: int | None = None,
                     dest_param_id: int | None = None,
                     dest_param_name: str = "",
                     dest_type: str = "",
                     source: str = "",
                     amount: float = 50.0,
                     bipolar: bool = False) -> None:
        """Configure a modulation slot."""
        key = f"ModSlot{slot}"
        entry: dict[str, Any] = {}
        if dest_module_id is not None:
            entry["destModuleID"] = dest_module_id
        if dest_param_id is not None:
            entry["destModuleParamID"] = dest_param_id
        if dest_param_name:
            entry["destModuleParamName"] = dest_param_name
        if dest_type:
            entry["destModuleTypeString"] = dest_type
        if source:
            entry["source"] = source
        params: dict[str, Any] = {"kParamAmount": amount}
        if bipolar:
            params["kParamBipolar"] = 1.0
        entry["plainParams"] = params
        self.cbor_data[key] = entry

    def get_metadata(self) -> dict[str, Any]:
        """Return the JSON metadata dict for the file header."""
        raw = json.dumps({
            "fileType": "SerumPreset",
            "hash": hashlib.md5(self.name.encode()).hexdigest(),
            "presetAuthor": self.author,
            "presetDescription": self.description,
            "presetName": self.name,
            "product": self.product,
            "productVersion": self.product_version,
            "tags": self.tags,
            "url": self.url,
            "vendor": self.vendor,
            "version": self.version,
        }, separators=(",", ":"))
        return raw

    # ── Serialization ─────────────────────────────────────────────────

    def to_cbor_bytes(self) -> bytes:
        """Serialize the preset dict to raw CBOR."""
        return cbor2.dumps(self.cbor_data)

    def to_file_bytes(self) -> bytes:
        """Produce the complete .SerumPreset binary."""
        # 1. JSON metadata
        json_str = self.get_metadata()
        json_bytes = json_str.encode("utf-8")

        # 2. CBOR → zstd compress
        cbor_raw = self.to_cbor_bytes()
        cctx = zstandard.ZstdCompressor(level=ZSTD_LEVEL)
        compressed = cctx.compress(cbor_raw)

        # 3. Binary payload: uint32 LE decompressed_size + uint32 LE version + zstd
        payload = struct.pack("<II", len(cbor_raw), 2) + compressed

        # 4. File: magic(9) + uint32 LE json_len + 4 zero bytes + json + payload
        header = _MAGIC + struct.pack("<I", len(json_bytes)) + b"\x00\x00\x00\x00"
        return header + json_bytes + payload

    def get_processor_state(self) -> bytes:
        """Return bytes suitable for Ableton ALS <ProcessorState> embedding.

        This is the raw .SerumPreset binary that Serum 2's VST3
        ``IComponent::setState()`` can restore.
        """
        return self.to_file_bytes()

    def write(self, path: str | Path) -> Path:
        """Write the preset to a .SerumPreset file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.to_file_bytes())
        _log.info("Wrote Serum 2 preset: %s (%d bytes)", p.name, p.stat().st_size)
        return p

    def install(self, subfolder: str = "DUBFORGE") -> Path:
        """Install the preset into Serum 2's User presets directory."""
        dest = _USER_DIR / subfolder
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / f"{self.name}.SerumPreset"
        out.write_bytes(self.to_file_bytes())
        _log.info("Installed preset to Serum 2: %s", out)
        return out


# ──────────────────────────────────────────────────────────────────────
# Reader
# ──────────────────────────────────────────────────────────────────────
def read_preset(path: str | Path) -> SerumPreset:
    """Read a .SerumPreset file into a SerumPreset object."""
    data = Path(path).read_bytes()
    if not data.startswith(b"XferJson"):
        raise ValueError(f"Not a Serum 2 preset: {path}")

    json_len = struct.unpack_from("<I", data, 9)[0]
    json_start = 17
    json_bytes = data[json_start:json_start + json_len]
    meta = json.loads(json_bytes)

    binary_offset = json_start + json_len
    remaining = data[binary_offset:]
    zstd_data = remaining[8:]  # skip decompressed_size(4) + version(4)

    dctx = zstandard.ZstdDecompressor()
    decompressed = dctx.decompress(zstd_data)
    cbor_data = cbor2.loads(decompressed)

    return SerumPreset(
        name=meta.get("presetName", ""),
        author=meta.get("presetAuthor", ""),
        description=meta.get("presetDescription", ""),
        tags=meta.get("tags", []),
        product=meta.get("product", "Serum2"),
        product_version=meta.get("productVersion", "2.0.11"),
        vendor=meta.get("vendor", "Xfer Records"),
        url=meta.get("url", ""),
        version=meta.get("version", 4.0),
        cbor_data=cbor_data,
    )


def clone_factory(relative_path: str, new_name: str) -> SerumPreset:
    """Clone a factory preset by relative path under Presets/Factory/.

    Example: ``clone_factory("Bass/Sub/BA - Sub Sustain - Low.SerumPreset",
                             "DUBFORGE_Fractal_Sub")``
    """
    src = _FACTORY_DIR / relative_path
    if not src.exists():
        raise FileNotFoundError(f"Factory preset not found: {src}")
    preset = read_preset(src)
    preset.name = new_name
    preset.author = "DUBFORGE"
    preset.description = "Generated by DUBFORGE — Planck x phi fractal basscraft"
    preset.url = "https://github.com/ResonanceEnergy/DUBFORGE"
    # Update metadata inside CBOR too
    preset.cbor_data["presetName"] = new_name
    preset.cbor_data["presetAuthor"] = "DUBFORGE"
    preset.cbor_data["presetDescription"] = preset.description
    return preset


# ──────────────────────────────────────────────────────────────────────
# DUBFORGE preset factory — one preset per track role
# ──────────────────────────────────────────────────────────────────────
PHI = 1.6180339887

# Map each DUBFORGE preset to a factory base + parameter overrides
_PRESET_RECIPES: dict[str, dict[str, Any]] = {
    "DUBFORGE_Fractal_Sub": {
        "base": "Bass/Sub/BA - Sub Sustain - Low.SerumPreset",
        "tags": ["Bass", "Sub", "Mono"],
        "params": {
            "Global0": {
                "kParamMonoToggle": 1.0,
                "kParamLegato": 1.0,
                "kParamPortamentoTime": 0.1 * PHI,
            },
            "Oscillator0": {"kParamOctave": -2.0},
        },
    },
    "DUBFORGE_Deep_Sub": {
        "base": "Bass/Sub/BA - Bent Woofer.SerumPreset",
        "tags": ["Bass", "Sub", "Deep"],
        "params": {
            "Global0": {"kParamMonoToggle": 1.0, "kParamLegato": 1.0},
            "Oscillator0": {"kParamOctave": -2.0},
        },
    },
    "DUBFORGE_Phi_Growl": {
        "base": "Bass/Hard/BA - Basilisk.SerumPreset",
        "tags": ["Bass", "Growl", "Aggressive"],
        "params": {},
    },
    "DUBFORGE_Spectral_Tear": {
        "base": "Bass/Modulated/MDL - Slippery Snake.SerumPreset",
        "tags": ["Bass", "Wobble", "Modulated"],
        "params": {},
    },
    "DUBFORGE_Riddim_Minimal": {
        "base": "Bass/Hard/BA - RM Wub Generator.SerumPreset",
        "tags": ["Bass", "Riddim", "Minimal"],
        "params": {
            "Global0": {"kParamMonoToggle": 1.0},
        },
    },
    "DUBFORGE_Formant_Vowel": {
        "base": "Vox/VOX - I Talk.SerumPreset",
        "tags": ["Vox", "Formant", "Vowel"],
        "params": {},
    },
    "DUBFORGE_Fibonacci_FM_Screech": {
        "base": "Lead/LD - Das EDM.SerumPreset",
        "tags": ["Lead", "FM", "Screech"],
        "params": {},
    },
    "DUBFORGE_Counter_Pluck": {
        "base": "Pluck/PL - Resonant Pluck.SerumPreset",
        "tags": ["Pluck", "Counter", "Melodic"],
        "params": {},
    },
    "DUBFORGE_Vocal_Fracture": {
        "base": "Vox/VOX - Granular Voices.SerumPreset",
        "tags": ["Vox", "Vocal", "Granular"],
        "params": {},
    },
    "DUBFORGE_Golden_Reese": {
        "base": "Bass/Reese/BA - Gnarly Reese.SerumPreset",
        "tags": ["Bass", "Reese", "Chord"],
        "params": {},
    },
    "DUBFORGE_Granular_Atmosphere": {
        "base": "Pad/PD - Ether.SerumPreset",
        "tags": ["Pad", "Atmosphere", "Granular"],
        "params": {},
    },
    "DUBFORGE_Phi_Arp": {
        "base": "Arp/ARP - Daftronic.SerumPreset",
        "tags": ["Arp", "Synth", "Rhythmic"],
        "params": {},
    },
    "DUBFORGE_Weapon": {
        "base": "SFX/FX - Demon Woosh.SerumPreset",
        "tags": ["SFX", "Impact", "Weapon"],
        "params": {},
    },
    "DUBFORGE_Riser_Sweep": {
        "base": "SFX/FX - Wasp Whistle Sweep.SerumPreset",
        "tags": ["SFX", "Riser", "Sweep"],
        "params": {},
    },
}


def build_preset(name: str) -> SerumPreset:
    """Build a DUBFORGE preset by name using the recipe registry."""
    recipe = _PRESET_RECIPES.get(name)
    if recipe is None:
        raise KeyError(f"No recipe for preset: {name}")
    preset = clone_factory(recipe["base"], name)
    preset.tags = recipe.get("tags", [])
    # Apply parameter overrides
    for module, params in recipe.get("params", {}).items():
        preset.set_params(module, params)
    return preset


def build_all_presets() -> dict[str, SerumPreset]:
    """Build all DUBFORGE presets. Returns {name: SerumPreset}."""
    result = {}
    for name in _PRESET_RECIPES:
        try:
            result[name] = build_preset(name)
        except FileNotFoundError as exc:
            _log.warning("Skipping %s: %s", name, exc)
    return result


def install_all_presets() -> list[Path]:
    """Build and install all DUBFORGE presets to Serum 2's User folder."""
    paths = []
    for name, preset in build_all_presets().items():
        try:
            paths.append(preset.install())
        except OSError as exc:
            _log.warning("Failed to install %s: %s", name, exc)
    return paths


def get_preset_state_map() -> dict[str, bytes]:
    """Return {preset_name: state_bytes} for all DUBFORGE presets.

    The bytes are the raw .SerumPreset file content, ready for
    base64-encoding into ALS <ProcessorState>.
    """
    result = {}
    for name, preset in build_all_presets().items():
        result[name] = preset.get_processor_state()
    return result


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "install":
        paths = install_all_presets()
        print(f"Installed {len(paths)} presets to {_DUBFORGE_DIR}")
        for p in paths:
            print(f"  {p.name}")
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        for name in sorted(_PRESET_RECIPES):
            print(f"  {name} <- {_PRESET_RECIPES[name]['base']}")
    else:
        print("Usage: python -m engine.serum2_preset [install|list]")
        print(f"  install — Build & install {len(_PRESET_RECIPES)} DUBFORGE presets to Serum 2")
        print(f"  list    — Show preset recipes")
