"""
DUBFORGE Engine — Sample Pack Builder

Package all rendered .wav files into organized sample pack folders.
Creates category-based directory structures (kicks/, snares/, basses/, etc.)
with manifest files and README.

Categories:
    drums       — kicks, snares, hats, claps, percussion
    bass        — sub-bass, mid-bass, wobble bass
    synths      — leads, pads, plucks, arps
    fx          — risers, impacts, transitions, textures
    stems       — mixed stems, pipeline renders

Banks: 5 categories × 4 presets = 20 presets
"""

import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

PHI = 1.6180339887


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PackPreset:
    """Configuration for a sample pack category."""
    name: str
    category: str  # drums, bass, synths, fx, stems
    num_samples: int = 8
    duration_s: float = 1.0
    base_freq: float = 100.0
    normalize: bool = True
    include_readme: bool = True


@dataclass
class PackBank:
    name: str
    presets: list[PackPreset]


# ═══════════════════════════════════════════════════════════════════════════
# SAMPLE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _generate_drum_sample(idx: int, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a drum one-shot."""
    rng = np.random.default_rng(idx * 42)
    dur = 0.3 + (idx % 3) * 0.1
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 60 + idx * 20
    env = np.exp(-t * (10 + idx * 3))
    tone = np.sin(2 * np.pi * freq * t * np.exp(-t * 5))
    noise = rng.normal(0, 1, n) * np.exp(-t * 30)
    return np.clip(env * (0.7 * tone + 0.3 * noise), -1, 1)


def _generate_bass_sample(idx: int, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a bass one-shot."""
    dur = 1.0
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 40 + idx * 10
    sig = np.sin(2 * np.pi * freq * t)
    sig += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.exp(-t * 2)
    return np.clip(sig * env * 0.8, -1, 1)


def _generate_synth_sample(idx: int, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a synth one-shot."""
    dur = 1.5
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 220 + idx * 55
    sig = np.zeros(n)
    for k in range(1, 6):
        sig += np.sin(2 * np.pi * freq * k * t) / k
    env = np.exp(-t * 1.5) * (1 - np.exp(-t * 50))
    return np.clip(sig * env * 0.5, -1, 1)


def _generate_fx_sample(idx: int, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate an FX sample (riser/impact)."""
    rng = np.random.default_rng(idx * 77)
    dur = 2.0
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    sweep = np.sin(2 * np.pi * (100 + 2000 * t / dur) * t)
    noise = rng.normal(0, 0.3, n)
    env = t / dur if idx % 2 == 0 else 1 - t / dur  # riser or impact
    return np.clip((sweep * 0.6 + noise * 0.4) * env, -1, 1)


def _generate_stem_sample(idx: int, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a mixed stem sample."""
    dur = 3.0
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 55.0 * (PHI ** (idx % 4))
    sig = np.sin(2 * np.pi * freq * t)
    sig += 0.618 * np.sin(2 * np.pi * freq * PHI * t)
    sig += 0.382 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.ones(n) * 0.7
    env[:int(sr * 0.01)] = np.linspace(0, 0.7, int(sr * 0.01))
    env[-int(sr * 0.1):] = np.linspace(0.7, 0, int(sr * 0.1))
    return np.clip(sig * env, -1, 1)


CATEGORY_GENERATORS = {
    "drums": _generate_drum_sample,
    "bass": _generate_bass_sample,
    "synths": _generate_synth_sample,
    "fx": _generate_fx_sample,
    "stems": _generate_stem_sample,
}


# ═══════════════════════════════════════════════════════════════════════════
# PACK BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_sample_pack(preset: PackPreset,
                      output_dir: str = "output") -> list[str]:
    """Build a sample pack folder with .wav files and manifest."""
    out = Path(output_dir) / "sample_packs" / preset.category / preset.name
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    gen_fn = CATEGORY_GENERATORS.get(preset.category, _generate_synth_sample)
    for i in range(preset.num_samples):
        audio = gen_fn(i)
        if preset.normalize:
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio / peak * 0.9
        fname = f"{preset.category}_{preset.name}_{i:03d}.wav"
        _write_wav(out / fname, audio)
        paths.append(str(out / fname))

    # Write pack manifest
    manifest = {
        "pack": preset.name,
        "category": preset.category,
        "num_samples": preset.num_samples,
        "files": [p.split("/")[-1] for p in paths],
    }
    with open(out / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    if preset.include_readme:
        readme = f"# {preset.name}\n\nCategory: {preset.category}\nSamples: {preset.num_samples}\nGenerated by DUBFORGE\n"
        (out / "README.md").write_text(readme)

    return paths


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def drums_pack_bank() -> PackBank:
    return PackBank("drums", [
        PackPreset("kicks", "drums", num_samples=8),
        PackPreset("snares", "drums", num_samples=8),
        PackPreset("hats", "drums", num_samples=6),
        PackPreset("percs", "drums", num_samples=6),
    ])


def bass_pack_bank() -> PackBank:
    return PackBank("bass", [
        PackPreset("sub_bass", "bass", num_samples=6, base_freq=40.0),
        PackPreset("mid_bass", "bass", num_samples=6, base_freq=80.0),
        PackPreset("wobble", "bass", num_samples=6, base_freq=55.0),
        PackPreset("reese", "bass", num_samples=6, base_freq=60.0),
    ])


def synths_pack_bank() -> PackBank:
    return PackBank("synths", [
        PackPreset("leads", "synths", num_samples=8),
        PackPreset("pads", "synths", num_samples=6, duration_s=3.0),
        PackPreset("plucks", "synths", num_samples=8, duration_s=0.5),
        PackPreset("arps", "synths", num_samples=6),
    ])


def fx_pack_bank() -> PackBank:
    return PackBank("fx", [
        PackPreset("risers", "fx", num_samples=6, duration_s=3.0),
        PackPreset("impacts", "fx", num_samples=6, duration_s=1.0),
        PackPreset("textures", "fx", num_samples=6, duration_s=4.0),
        PackPreset("transitions", "fx", num_samples=6, duration_s=2.0),
    ])


def stems_pack_bank() -> PackBank:
    return PackBank("stems", [
        PackPreset("full_stems", "stems", num_samples=4, duration_s=4.0),
        PackPreset("bass_stems", "stems", num_samples=4, duration_s=3.0),
        PackPreset("lead_stems", "stems", num_samples=4, duration_s=3.0),
        PackPreset("pad_stems", "stems", num_samples=4, duration_s=5.0),
    ])


ALL_PACK_BANKS: dict[str, callable] = {
    "drums": drums_pack_bank,
    "bass": bass_pack_bank,
    "synths": synths_pack_bank,
    "fx": fx_pack_bank,
    "stems": stems_pack_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_all_packs(output_dir: str = "output") -> list[str]:
    """Build all sample packs and return wav paths."""
    paths: list[str] = []
    for bank_name, bank_fn in ALL_PACK_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            paths.extend(build_sample_pack(preset, output_dir))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_pack_manifest(output_dir: str = "output") -> dict:
    """Write sample pack builder manifest JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_PACK_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }
    path = out / "sample_pack_builder_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_pack_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_all_packs()
    print(f"Sample Pack Builder: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
