"""
DUBFORGE Engine — Sample Pack Builder  (v2 — Real Engine)

Package rendered .wav files into organized sample packs using
REAL engine synthesisers (bass_oneshot, drum_generator, impact_hit,
riser_synth, noise_generator, transition_fx, vocal_chop).

Categories:
    drums       — kicks, snares, hats, claps, percussion  (drum_generator synth_*)
    bass        — sub, reese, fm, growl, wobble, neuro     (bass_oneshot)
    synths      — leads, pads, plucks, arps                (bass_oneshot + phi_core)
    fx          — risers, impacts, transitions, textures   (riser_synth, impact_hit, etc.)
    stems       — mixed stems, pipeline renders            (layered engine audio)

Banks: 5 categories × 4 presets = 20 preset groups
"""

import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.bass_oneshot import BassPreset, synthesize_bass
from engine.config_loader import PHI
from engine.drum_generator import (
    synth_clap,
    synth_crash,
    synth_hat_closed,
    synth_hat_open,
    synth_kick,
    synth_rim,
    synth_snare,
    synth_tom,
)
from engine.impact_hit import ImpactPreset, synthesize_impact
from engine.noise_generator import NoisePreset, synthesize_noise
from engine.phi_core import SAMPLE_RATE
from engine.riser_synth import RiserPreset, synthesize_riser
from engine.transition_fx import TransitionPreset, synthesize_transition
from engine.vocal_chop import VocalChop, synthesize_chop


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
# WAV WRITER
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


# ═══════════════════════════════════════════════════════════════════════════
# REAL ENGINE GENERATORS — Drums
# ═══════════════════════════════════════════════════════════════════════════

# Kick variations: vary freq/punch/decay across phi-stepped values
_KICK_PARAMS = [
    dict(freq=45.0, punch_freq=180.0, decay_ms=350, drive=0.2),
    dict(freq=50.0, punch_freq=200.0, decay_ms=300, drive=0.3),
    dict(freq=55.0, punch_freq=220.0, decay_ms=280, drive=0.4),
    dict(freq=40.0, punch_freq=160.0, decay_ms=400, drive=0.15),
    dict(freq=60.0, punch_freq=250.0, decay_ms=250, drive=0.5),
    dict(freq=48.0, punch_freq=190.0, decay_ms=320, drive=0.35),
    dict(freq=55.0, punch_freq=230.0, decay_ms=200, drive=0.6),
    dict(freq=42.0, punch_freq=170.0, decay_ms=380, drive=0.25),
]

_SNARE_PARAMS = [
    dict(tone_freq=180.0, noise_mix=0.5, decay_ms=200),
    dict(tone_freq=200.0, noise_mix=0.6, decay_ms=180),
    dict(tone_freq=160.0, noise_mix=0.7, decay_ms=220),
    dict(tone_freq=220.0, noise_mix=0.4, decay_ms=250),
    dict(tone_freq=190.0, noise_mix=0.65, decay_ms=160),
    dict(tone_freq=170.0, noise_mix=0.55, decay_ms=240),
    dict(tone_freq=210.0, noise_mix=0.75, decay_ms=150),
    dict(tone_freq=185.0, noise_mix=0.5, decay_ms=300),
]


def _generate_drum_kicks(num: int, sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate kick one-shots via drum_generator.synth_kick."""
    out = []
    for i in range(num):
        p = _KICK_PARAMS[i % len(_KICK_PARAMS)]
        out.append(synth_kick(sample_rate=sr, **p))
    return out


def _generate_drum_snares(num: int, sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate snare one-shots via drum_generator.synth_snare."""
    out = []
    for i in range(num):
        p = _SNARE_PARAMS[i % len(_SNARE_PARAMS)]
        out.append(synth_snare(sample_rate=sr, **p))
    return out


def _generate_drum_hats(num: int, sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate hi-hat one-shots: alternate closed/open."""
    out = []
    for i in range(num):
        if i % 2 == 0:
            out.append(synth_hat_closed(
                freq=7000.0 + i * 500, decay_ms=50 + i * 10, sample_rate=sr))
        else:
            out.append(synth_hat_open(
                freq=7500.0 + i * 300, decay_ms=200 + i * 50, sample_rate=sr))
    return out


def _generate_drum_percs(num: int, sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate percussion one-shots: claps, toms, rims, crashes."""
    synths = [
        lambda s: synth_clap(decay_ms=250, n_layers=3, sample_rate=s),
        lambda s: synth_tom(freq=100.0, decay_ms=250, sample_rate=s),
        lambda s: synth_rim(freq=500.0, decay_ms=50, sample_rate=s),
        lambda s: synth_tom(freq=150.0, decay_ms=200, sample_rate=s),
        lambda s: synth_crash(freq=6000.0, decay_ms=1500, sample_rate=s),
        lambda s: synth_clap(decay_ms=180, n_layers=5, sample_rate=s),
    ]
    return [synths[i % len(synths)](sr) for i in range(num)]


# ═══════════════════════════════════════════════════════════════════════════
# REAL ENGINE GENERATORS — Bass (bass_oneshot)
# ═══════════════════════════════════════════════════════════════════════════

_BASS_TYPES_BY_PRESET = {
    "sub_bass":  ["sub_sine", "sub_sine", "sub_sine", "sub_sine",
                   "sub_sine", "sub_sine"],
    "mid_bass":  ["growl", "neuro", "fm", "wobble", "acid", "donk"],
    "wobble":    ["wobble", "wobble", "wobble", "wobble", "wobble", "wobble"],
    "reese":     ["reese", "reese", "reese", "reese", "reese", "reese"],
}

_BASS_FREQS = [32.70, 36.71, 41.20, 46.25, 55.0, 65.41]  # C1-C2 range


def _generate_bass_samples(preset_name: str, num: int,
                           base_freq: float = 55.0,
                           sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate bass one-shots using bass_oneshot engine."""
    types = _BASS_TYPES_BY_PRESET.get(preset_name, ["fm"] * num)
    out = []
    for i in range(num):
        bp = BassPreset(
            name=f"{preset_name}_{i:03d}",
            bass_type=types[i % len(types)],
            frequency=_BASS_FREQS[i % len(_BASS_FREQS)] if base_freq < 50 else base_freq * (PHI ** (i * 0.1)),
            duration_s=0.8,
            fm_ratio=PHI if types[i % len(types)] == "fm" else 1.0,
            fm_depth=2.0 if types[i % len(types)] == "fm" else 0.0,
            distortion=0.3 * (i / max(num - 1, 1)),
        )
        out.append(synthesize_bass(bp, sr))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# REAL ENGINE GENERATORS — Synths (bass_oneshot as synth engine)
# ═══════════════════════════════════════════════════════════════════════════

_SYNTH_TYPES = {
    "leads":  ["saw", "sync", "dist_fm", "phase",
               "square", "pulse_width", "saw", "sync"],
    "pads":   ["reese", "sub_sine", "reese", "sub_sine",
               "reese", "sub_sine"],
    "plucks": ["fm", "formant", "fm", "phase",
               "fm", "formant", "fm", "phase"],
    "arps":   ["square", "saw", "pulse_width", "fm",
               "square", "saw"],
}

_SYNTH_FREQS = [220.0, 261.63, 293.66, 329.63, 349.23, 392.0, 440.0, 523.25]


def _generate_synth_samples(preset_name: str, num: int,
                            duration_s: float = 1.5,
                            sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate synth one-shots using bass_oneshot engine at higher registers."""
    types = _SYNTH_TYPES.get(preset_name, ["saw"] * num)
    out = []
    for i in range(num):
        bp = BassPreset(
            name=f"synth_{preset_name}_{i:03d}",
            bass_type=types[i % len(types)],
            frequency=_SYNTH_FREQS[i % len(_SYNTH_FREQS)],
            duration_s=duration_s,
            attack_s=0.01 if preset_name == "plucks" else 0.05,
            release_s=0.05 if preset_name == "plucks" else 0.3,
            fm_ratio=PHI,
            fm_depth=1.5 if "fm" in types[i % len(types)] else 0.0,
            filter_cutoff=0.7 + 0.3 * (i / max(num - 1, 1)),
        )
        out.append(synthesize_bass(bp, sr))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# REAL ENGINE GENERATORS — FX (riser_synth, impact_hit, transition_fx, noise)
# ═══════════════════════════════════════════════════════════════════════════

_RISER_TYPES = ["noise_sweep", "pitch_rise", "filter_sweep",
                "harmonic_build", "fm_riser", "doppler"]
_IMPACT_TYPES = ["sub_boom", "cinematic_hit", "distorted_impact",
                 "layered_hit", "glitch_impact", "metal_crash"]
_TRANSITION_TYPES = ["tape_stop", "reverse_crash", "gate_chop",
                     "pitch_dive", "glitch_stutter", "vinyl_fx"]
_NOISE_TYPES = ["white", "pink", "brown", "vinyl", "tape", "digital"]


def _generate_fx_risers(num: int, dur: float = 3.0,
                        sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    out = []
    for i in range(num):
        rp = RiserPreset(
            name=f"riser_{i:03d}",
            riser_type=_RISER_TYPES[i % len(_RISER_TYPES)],
            duration_s=dur,
            start_freq=100.0 + i * 50,
            end_freq=4000.0 + i * 500,
        )
        out.append(synthesize_riser(rp, sr))
    return out


def _generate_fx_impacts(num: int, dur: float = 1.0,
                         sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    out = []
    for i in range(num):
        ip = ImpactPreset(
            name=f"impact_{i:03d}",
            impact_type=_IMPACT_TYPES[i % len(_IMPACT_TYPES)],
            duration_s=dur,
            intensity=0.7 + 0.3 * (i / max(num - 1, 1)),
        )
        out.append(synthesize_impact(ip, sr))
    return out


def _generate_fx_textures(num: int, dur: float = 4.0,
                          sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    out = []
    for i in range(num):
        np_ = NoisePreset(
            name=f"texture_{i:03d}",
            noise_type=_NOISE_TYPES[i % len(_NOISE_TYPES)],
            duration_s=dur,
            brightness=0.3 + 0.1 * i,
            modulation=0.2 * i,
        )
        out.append(synthesize_noise(np_, sr))
    return out


def _generate_fx_transitions(num: int, dur: float = 2.0,
                             sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    out = []
    for i in range(num):
        tp = TransitionPreset(
            name=f"transition_{i:03d}",
            fx_type=_TRANSITION_TYPES[i % len(_TRANSITION_TYPES)],
            duration_s=dur,
        )
        out.append(synthesize_transition(tp, sr))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# REAL ENGINE GENERATORS — Stems (layered engine audio)
# ═══════════════════════════════════════════════════════════════════════════

def _generate_stem_full(idx: int, dur: float = 4.0,
                        sr: int = SAMPLE_RATE) -> np.ndarray:
    """Layer bass + drum + texture for a full stem."""
    n = int(sr * dur)
    bass = synthesize_bass(BassPreset(
        name=f"stem_bass_{idx}", bass_type="reese",
        frequency=55.0 * (PHI ** (idx * 0.15)), duration_s=dur,
    ), sr)
    kick = synth_kick(freq=50.0, decay_ms=300, sample_rate=sr)
    noise = synthesize_noise(NoisePreset(
        name=f"stem_tex_{idx}", noise_type="pink", duration_s=dur,
        gain=0.15,
    ), sr)
    # Pad/trim each to n samples
    layers = []
    for layer in [bass, kick, noise]:
        if len(layer) >= n:
            layers.append(layer[:n])
        else:
            padded = np.zeros(n)
            padded[:len(layer)] = layer
            layers.append(padded)
    mixed = 0.5 * layers[0] + 0.25 * layers[1] + 0.25 * layers[2]
    return np.clip(mixed, -1, 1)


def _generate_stem_bass(idx: int, dur: float = 3.0,
                        sr: int = SAMPLE_RATE) -> np.ndarray:
    types = ["growl", "fm", "neuro", "wobble"]
    return synthesize_bass(BassPreset(
        name=f"bass_stem_{idx}", bass_type=types[idx % len(types)],
        frequency=55.0 * (PHI ** (idx * 0.2)), duration_s=dur,
    ), sr)


def _generate_stem_lead(idx: int, dur: float = 3.0,
                        sr: int = SAMPLE_RATE) -> np.ndarray:
    types = ["saw", "sync", "dist_fm", "phase"]
    return synthesize_bass(BassPreset(
        name=f"lead_stem_{idx}", bass_type=types[idx % len(types)],
        frequency=261.63 * (PHI ** (idx * 0.1)), duration_s=dur,
    ), sr)


def _generate_stem_pad(idx: int, dur: float = 5.0,
                       sr: int = SAMPLE_RATE) -> np.ndarray:
    return synthesize_bass(BassPreset(
        name=f"pad_stem_{idx}", bass_type="reese",
        frequency=130.81 * (PHI ** (idx * 0.08)), duration_s=dur,
        attack_s=0.3, release_s=1.0,
    ), sr)


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════════════════

def _generate_for_preset(preset: PackPreset,
                         sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Route preset to the correct real-engine generator."""
    n = preset.num_samples

    # Drums
    if preset.category == "drums":
        if preset.name == "kicks":
            return _generate_drum_kicks(n, sr)
        elif preset.name == "snares":
            return _generate_drum_snares(n, sr)
        elif preset.name == "hats":
            return _generate_drum_hats(n, sr)
        elif preset.name == "percs":
            return _generate_drum_percs(n, sr)

    # Bass
    if preset.category == "bass":
        return _generate_bass_samples(preset.name, n, preset.base_freq, sr)

    # Synths
    if preset.category == "synths":
        return _generate_synth_samples(preset.name, n, preset.duration_s, sr)

    # FX
    if preset.category == "fx":
        if preset.name == "risers":
            return _generate_fx_risers(n, preset.duration_s, sr)
        elif preset.name == "impacts":
            return _generate_fx_impacts(n, preset.duration_s, sr)
        elif preset.name == "textures":
            return _generate_fx_textures(n, preset.duration_s, sr)
        elif preset.name == "transitions":
            return _generate_fx_transitions(n, preset.duration_s, sr)

    # Stems
    if preset.category == "stems":
        if preset.name == "full_stems":
            return [_generate_stem_full(i, preset.duration_s, sr) for i in range(n)]
        elif preset.name == "bass_stems":
            return [_generate_stem_bass(i, preset.duration_s, sr) for i in range(n)]
        elif preset.name == "lead_stems":
            return [_generate_stem_lead(i, preset.duration_s, sr) for i in range(n)]
        elif preset.name == "pad_stems":
            return [_generate_stem_pad(i, preset.duration_s, sr) for i in range(n)]

    # Fallback — sub_sine bass
    return [synthesize_bass(BassPreset(
        name=f"fallback_{i}", bass_type="sub_sine",
        frequency=preset.base_freq, duration_s=preset.duration_s,
    ), sr) for i in range(n)]


# ═══════════════════════════════════════════════════════════════════════════
# PACK BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_sample_pack(preset: PackPreset,
                      output_dir: str = "output") -> list[str]:
    """Build a sample pack folder with .wav files and manifest."""
    out = Path(output_dir) / "sample_packs" / preset.category / preset.name
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    samples = _generate_for_preset(preset)

    for i, audio in enumerate(samples):
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
        "engine": "DUBFORGE v4 — real synthesis",
        "files": [Path(p).name for p in paths],
    }
    with open(out / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    if preset.include_readme:
        readme = (
            f"# {preset.name}\n\n"
            f"Category: {preset.category}\n"
            f"Samples: {preset.num_samples}\n"
            f"Engine: DUBFORGE v4 real synthesis\n"
            f"Sample Rate: {SAMPLE_RATE} Hz\n"
            f"Tuning: A4 = 432 Hz | PHI = {PHI}\n"
        )
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
