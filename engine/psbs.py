"""
DUBFORGE Engine — Phase-Separated Bass System (PSBS)

Multi-layer bass architecture with phase-aligned separation.
Each frequency band is independently controllable while maintaining
phase coherence via phi-ratio alignment.

Layers:
    SUB      — Pure sine / triangle, sub-bass fundamental
    LOW      — Saw/square, main bass body
    MID      — FM / wavetable, growl zone
    HIGH     — Noise + harmonics, presence / grit
    CLICK    — Transient layer for attack definition

All crossover frequencies derived from phi-ratio ladder.

v2.8.0 — real audio output: multi-frame wavetables, per-layer stems,
         phi-ladder root sweeps. Every preset → Serum-ready 256-frame .wav.
"""

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI, load_config

# --- Layer Definitions ----------------------------------------------------

@dataclass
class BassLayer:
    """A single frequency layer in the PSBS stack."""
    name: str
    freq_low: float              # Hz — lower crossover
    freq_high: float             # Hz — upper crossover
    waveform: str                # "sine", "saw", "square", "wavetable", "noise", "fm"
    gain_db: float = 0.0
    phase_offset_deg: float = 0.0
    distortion: float = 0.0     # 0.0 – 1.0
    stereo_width: float = 0.0   # 0.0 = mono, 1.0 = full stereo
    note: str = ""


@dataclass
class PSBSPreset:
    """Complete PSBS layer stack."""
    name: str
    root_hz: float = 55.0       # Root note frequency
    tuning_a4: float = 432.0    # 432 Hz coherence tuning
    layers: list = field(default_factory=list)
    crossover_mode: str = "phi"  # "phi" | "linear" | "custom"


# --- Phi Crossover Calculator ---------------------------------------------

def phi_crossovers(root_hz: float, n_bands: int = 5) -> list[float]:
    """
    Calculate crossover frequencies using phi-ratio spacing.
    Each crossover = root * phi^n
    """
    return [round(root_hz * (PHI ** n), 2) for n in range(n_bands + 1)]


# --- Preset Builders ------------------------------------------------------

def default_psbs(root_hz: float = 55.0, tuning: float = 432.0) -> PSBSPreset:
    """
    Standard 5-layer PSBS with phi crossovers.
    """
    xo = phi_crossovers(root_hz, 5)
    # xo example for root=55:
    #   [55.0, 89.0, 143.9, 232.9, 376.8, 609.7]

    return PSBSPreset(
        name="PSBS_DEFAULT",
        root_hz=root_hz,
        tuning_a4=tuning,
        layers=[
            BassLayer(
                name="SUB",
                freq_low=20.0,
                freq_high=xo[1],
                waveform="sine",
                gain_db=0.0,
                phase_offset_deg=0.0,
                distortion=0.0,
                stereo_width=0.0,
                note="Pure sub. Mono. No processing.",
            ),
            BassLayer(
                name="LOW",
                freq_low=xo[1],
                freq_high=xo[2],
                waveform="saw",
                gain_db=-3.0,
                phase_offset_deg=0.0,
                distortion=0.15,
                stereo_width=0.0,
                note="Main bass body. Light saturation. Mono.",
            ),
            BassLayer(
                name="MID",
                freq_low=xo[2],
                freq_high=xo[3],
                waveform="wavetable",
                gain_db=-2.0,
                phase_offset_deg=90.0,
                distortion=0.4,
                stereo_width=0.3,
                note="Growl zone. Wavetable morph. Slight stereo.",
            ),
            BassLayer(
                name="HIGH",
                freq_low=xo[3],
                freq_high=xo[4],
                waveform="noise",
                gain_db=-6.0,
                phase_offset_deg=180.0,
                distortion=0.6,
                stereo_width=0.7,
                note="Presence and grit. Wide stereo.",
            ),
            BassLayer(
                name="CLICK",
                freq_low=xo[4],
                freq_high=xo[5],
                waveform="fm",
                gain_db=-8.0,
                phase_offset_deg=0.0,
                distortion=0.3,
                stereo_width=0.5,
                note="Transient click. Short envelope. FM synthesis.",
            ),
        ],
    )


def weapon_psbs(root_hz: float = 55.0) -> PSBSPreset:
    """
    Weapon-mode PSBS: heavier distortion, wider stereo on mid/high,
    tighter sub, more aggressive FM click.
    """
    preset = default_psbs(root_hz)
    preset.name = "PSBS_WEAPON"

    for layer in preset.layers:
        if layer.name == "SUB":
            layer.distortion = 0.05
            layer.note = "Sub with minimal drive for weight."
        elif layer.name == "LOW":
            layer.distortion = 0.35
            layer.gain_db = -1.5
            layer.note = "Heavy low body. More saturation."
        elif layer.name == "MID":
            layer.distortion = 0.65
            layer.stereo_width = 0.5
            layer.note = "Aggressive growl. PHI CORE v2 wavetable."
        elif layer.name == "HIGH":
            layer.distortion = 0.8
            layer.stereo_width = 0.9
            layer.note = "Maximum grit. Near-full stereo."
        elif layer.name == "CLICK":
            layer.distortion = 0.5
            layer.gain_db = -5.0
            layer.note = "Harder transient. More FM depth."

    return preset


def wook_psbs(root_hz: float = 55.0) -> PSBSPreset:
    """
    Wook-mode PSBS: sub-heavy, more sub-harmonic folding,
    dirtier mid-range, deeper growl.
    """
    preset = default_psbs(root_hz)
    preset.name = "PSBS_WOOK"

    # Add extra sub-harmonic layer
    preset.layers.insert(0, BassLayer(
        name="SUB_FOLD",
        freq_low=20.0,
        freq_high=40.0,
        waveform="sine",
        gain_db=2.0,
        phase_offset_deg=0.0,
        distortion=0.0,
        stereo_width=0.0,
        note="Sub-harmonic fold. Octave below root. Maximum chest pressure.",
    ))

    for layer in preset.layers:
        if layer.name == "MID":
            layer.distortion = 0.7
            layer.waveform = "wavetable"
            layer.note = "Wook growl. PHI CORE v2 WOOK wavetable. Filthy."
        elif layer.name == "HIGH":
            layer.distortion = 0.75
            layer.note = "Crunchy top end. Not too bright — wook dark."

    return preset


# --- Phase Alignment Calculator -------------------------------------------

def calculate_phase_coherence(layers: list[BassLayer],
                              root_hz: float) -> dict:
    """
    Verify phase alignment across layers.
    Returns coherence report.
    """
    report = {"root_hz": root_hz, "layers": []}

    for layer in layers:
        center_freq = (layer.freq_low + layer.freq_high) / 2
        # Phase offset in radians
        phase_rad = math.radians(layer.phase_offset_deg)
        # Wavelength at center freq
        wavelength_ms = 1000.0 / center_freq if center_freq > 0 else 0
        # Time offset due to phase
        time_offset_ms = (phase_rad / (2 * math.pi)) * wavelength_ms

        report["layers"].append({
            "name": layer.name,
            "center_hz": round(center_freq, 2),
            "phase_deg": layer.phase_offset_deg,
            "time_offset_ms": round(time_offset_ms, 4),
            "wavelength_ms": round(wavelength_ms, 4),
        })

    return report


# --- Audio Render (single cycle preview) ----------------------------------

# --- Audio Render ---------------------------------------------------------

def _render_layer(layer: BassLayer, root_hz: float, n_samples: int,
                  morph: float = 0.0) -> np.ndarray:
    """
    Render a single layer as one cycle.

    Args:
        layer: BassLayer config
        root_hz: preset root frequency
        n_samples: samples per frame
        morph: 0.0–1.0 morphing parameter (affects distortion & FM depth)
    """
    t = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    center_hz = (layer.freq_low + layer.freq_high) / 2
    ratio = center_hz / root_hz
    phase = math.radians(layer.phase_offset_deg)
    gain = 10 ** (layer.gain_db / 20.0)

    # Morph drives distortion and FM depth across frames
    dist = layer.distortion * (1.0 + morph * PHI)

    if layer.waveform == "sine":
        wave = np.sin(ratio * t + phase)
    elif layer.waveform == "saw":
        wave = 2.0 * (((ratio * t + phase) / (2 * np.pi)) % 1.0) - 1.0
    elif layer.waveform == "square":
        wave = np.sign(np.sin(ratio * t + phase))
    elif layer.waveform == "triangle":
        wave = (2.0 * np.abs(
            2.0 * (((ratio * t + phase) / (2 * np.pi)) % 1.0) - 1.0
        ) - 1.0)
    elif layer.waveform == "noise":
        base = np.sin(ratio * t + phase)
        rng = np.random.RandomState(int(abs(ratio * 1000 + morph * 100)))
        noise = rng.uniform(-1, 1, n_samples)
        mix = 0.5 + morph * 0.3  # more noise as morph increases
        wave = base * (1.0 - mix) + noise * mix
    elif layer.waveform in ("fm", "wavetable"):
        mod_depth = dist * 5
        mod = np.sin(ratio * PHI * t)
        wave = np.sin(ratio * t + phase + mod_depth * mod)
    else:
        wave = np.sin(ratio * t + phase)

    # Apply distortion (tanh saturation) — morphed
    if dist > 0:
        drive = 1.0 + dist * 5.0
        wave = np.tanh(wave * drive)

    return wave * gain


def render_psbs_cycle(preset: PSBSPreset, n_samples: int = 2048,
                      morph: float = 0.0) -> np.ndarray:
    """
    Render one single-cycle of the full PSBS stack.

    Args:
        preset: PSBS preset to render
        n_samples: samples per frame (default 2048 = Serum standard)
        morph: 0.0–1.0 morphing parameter for evolving sound
    """
    output = np.zeros(n_samples, dtype=np.float64)

    for layer in preset.layers:
        output += _render_layer(layer, preset.root_hz, n_samples, morph)

    # Normalize
    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak

    return output


def render_psbs_multiframe(preset: PSBSPreset, n_frames: int = 256,
                           n_samples: int = 2048) -> list[np.ndarray]:
    """
    Render a full multi-frame wavetable from a PSBS preset.
    Each frame morphs the sound via phi-curve interpolation.

    Frame 0 = clean/minimal distortion.
    Frame 255 = full morph (maximum distortion/FM depth).
    Morph curve follows x^(1/phi) for natural evolution.

    Returns list of n_frames numpy arrays, each n_samples long.
    """
    frames = []
    for i in range(n_frames):
        linear = i / max(n_frames - 1, 1)
        # Phi-curve morph: gentler buildup, aggressive tail
        morph = linear ** (1.0 / PHI)
        frame = render_psbs_cycle(preset, n_samples=n_samples, morph=morph)
        frames.append(frame)
    return frames


def render_psbs_layer_stem(preset: PSBSPreset, layer_name: str,
                           n_frames: int = 256,
                           n_samples: int = 2048) -> list[np.ndarray]:
    """
    Render a single layer from the PSBS stack as a multi-frame wavetable.
    Useful for per-layer stems that can be loaded into separate Serum oscillators.
    """
    target_layer = None
    for layer in preset.layers:
        if layer.name == layer_name:
            target_layer = layer
            break

    if target_layer is None:
        raise ValueError(f"Layer '{layer_name}' not found in preset '{preset.name}'")

    frames = []
    for i in range(n_frames):
        linear = i / max(n_frames - 1, 1)
        morph = linear ** (1.0 / PHI)
        raw = _render_layer(target_layer, preset.root_hz, n_samples, morph)
        peak = np.max(np.abs(raw))
        if peak > 0:
            raw /= peak
        frames.append(raw)
    return frames


# --- YAML-driven preset loader --------------------------------------------

def load_psbs_presets_from_config() -> list[PSBSPreset]:
    """
    Load PSBS presets from rco_psbs_vip_delta_v1.1.yaml.
    Falls back to hardcoded presets if YAML not available.
    """
    try:
        cfg = load_config("rco_psbs_vip_delta_v1.1")
    except FileNotFoundError:
        return []

    presets_data = cfg.get("psbs_presets", {})
    if not isinstance(presets_data, dict):
        return []

    presets = []
    for name, pdata in presets_data.items():
        if not isinstance(pdata, dict):
            continue
        root_hz = float(pdata.get("root_hz", 55.0))
        tuning = float(pdata.get("tuning_a4", 432.0))
        xo_mode = str(pdata.get("crossover_mode", "phi"))
        layers_raw = pdata.get("layers", {})
        layers = []
        if isinstance(layers_raw, dict):
            for lname, ldata in layers_raw.items():
                if not isinstance(ldata, dict):
                    continue
                freq_range = ldata.get("freq_range", [20, 200])
                if isinstance(freq_range, list) and len(freq_range) >= 2:
                    fl, fh = float(freq_range[0]), float(freq_range[1])
                else:
                    fl, fh = 20.0, 200.0
                layers.append(BassLayer(
                    name=lname,
                    freq_low=fl,
                    freq_high=fh,
                    waveform=str(ldata.get("waveform", "sine")),
                    gain_db=float(ldata.get("gain_db", 0.0)),
                    phase_offset_deg=float(ldata.get("phase_deg", 0.0)),
                    distortion=float(ldata.get("distortion", 0.0)),
                    stereo_width=float(ldata.get("stereo_width", 0.0)),
                    note=str(ldata.get("note", "")),
                ))
        presets.append(PSBSPreset(
            name=f"PSBS_{name}",
            root_hz=root_hz,
            tuning_a4=tuning,
            layers=layers,
            crossover_mode=xo_mode,
        ))
    return presets


# --- Export ----------------------------------------------------------------

def export_preset(preset: PSBSPreset, out_dir: str = "output/analysis"):
    """Export a PSBS preset to JSON."""
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    data = asdict(preset)
    data["phase_coherence"] = calculate_phase_coherence(
        preset.layers, preset.root_hz
    )

    json_path = path / f"psbs_{preset.name.lower()}.json"
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"PSBS preset: {json_path}")
    return json_path


def export_wavetable(preset: PSBSPreset, out_dir: str = "output/wavetables",
                     n_samples: int = 2048, n_frames: int = 256) -> str:
    """
    Render a PSBS preset to a multi-frame WAV wavetable file (Serum-ready).

    256 frames × 2048 samples. Phi-curve morph from clean → full saturation.
    """
    from engine.phi_core import write_wav

    frames = render_psbs_multiframe(preset, n_frames=n_frames,
                                    n_samples=n_samples)

    wt_dir = Path(out_dir)
    wt_dir.mkdir(parents=True, exist_ok=True)
    hz_tag = f"_{int(preset.root_hz)}hz" if preset.root_hz != 55.0 else ""
    wav_name = f"PSBS_{preset.name.upper()}{hz_tag}.wav"
    wav_path = str(wt_dir / wav_name)
    write_wav(wav_path, frames)
    print(f"  PSBS wavetable ({n_frames} frames): {wav_name}")
    return wav_path


def export_layer_stems(preset: PSBSPreset, out_dir: str = "output/wavetables",
                       n_samples: int = 2048,
                       n_frames: int = 256) -> list[str]:
    """
    Export each layer of a PSBS preset as a separate multi-frame wavetable.
    Load SUB into Osc A, MID into Osc B, HIGH into Osc C, etc.
    """
    from engine.phi_core import write_wav

    wt_dir = Path(out_dir)
    wt_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for layer in preset.layers:
        frames = render_psbs_layer_stem(
            preset, layer.name, n_frames=n_frames, n_samples=n_samples
        )
        wav_name = f"PSBS_{preset.name.upper()}_{layer.name}.wav"
        wav_path = str(wt_dir / wav_name)
        write_wav(wav_path, frames)
        print(f"  PSBS stem ({layer.name}, {n_frames} frames): {wav_name}")
        paths.append(wav_path)

    return paths


def export_phi_ladder(preset_fn, out_dir: str = "output/wavetables",
                      n_frames: int = 256) -> list[str]:
    """
    Render a PSBS preset at multiple root frequencies on the phi ladder.
    Frequencies: root * phi^(n/12) for n in 0..7.

    Produces wavetables at different bass fundamentals for variety.
    """
    roots = [55.0 * (PHI ** (n / 12.0)) for n in range(8)]
    paths = []
    for root in roots:
        preset = preset_fn(root_hz=round(root, 2))
        path = export_wavetable(preset, out_dir=out_dir, n_frames=n_frames)
        paths.append(path)
    return paths


# --- Main -----------------------------------------------------------------

def main() -> None:
    # Try YAML-driven presets first, fall back to hardcoded
    yaml_presets = load_psbs_presets_from_config()
    if yaml_presets:
        presets = yaml_presets
    else:
        presets = [
            default_psbs(),
            weapon_psbs(),
            wook_psbs(),
        ]

    for preset in presets:
        # JSON analysis
        export_preset(preset)
        # Multi-frame wavetable (256 frames)
        export_wavetable(preset)
        # Per-layer stems
        export_layer_stems(preset)

    # Phi-ladder renders for the default preset
    print("\n  Phi-ladder wavetables:")
    export_phi_ladder(default_psbs)

    print("PSBS engine complete.")


if __name__ == '__main__':
    main()
