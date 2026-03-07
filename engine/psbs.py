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

def render_psbs_cycle(preset: PSBSPreset, n_samples: int = 2048) -> np.ndarray:
    """
    Render one single-cycle of the full PSBS stack (preview).
    Each layer generates its waveform within its frequency band.
    """
    t = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    output = np.zeros(n_samples, dtype=np.float64)

    for layer in preset.layers:
        center_hz = (layer.freq_low + layer.freq_high) / 2
        ratio = center_hz / preset.root_hz
        phase = math.radians(layer.phase_offset_deg)
        gain = 10 ** (layer.gain_db / 20.0)

        if layer.waveform == "sine":
            wave = np.sin(ratio * t + phase)
        elif layer.waveform == "saw":
            wave = 2.0 * (((ratio * t + phase) / (2 * np.pi)) % 1.0) - 1.0
        elif layer.waveform == "square":
            wave = np.sign(np.sin(ratio * t + phase))
        elif layer.waveform == "noise":
            base = np.sin(ratio * t + phase)
            noise = np.random.uniform(-1, 1, n_samples)
            wave = base * 0.5 + noise * 0.5
        elif layer.waveform in ("fm", "wavetable"):
            mod = np.sin(ratio * PHI * t)
            wave = np.sin(ratio * t + phase + layer.distortion * 5 * mod)
        else:
            wave = np.sin(ratio * t + phase)

        # Apply distortion (tanh saturation)
        if layer.distortion > 0:
            drive = 1.0 + layer.distortion * 5.0
            wave = np.tanh(wave * drive)

        output += wave * gain

    # Normalize
    peak = np.max(np.abs(output))
    if peak > 0:
        output /= peak

    return output


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


# --- Main -----------------------------------------------------------------

def export_wavetable(preset: PSBSPreset, out_dir: str = "output/wavetables",
                     n_samples: int = 2048) -> str:
    """Render a PSBS preset to a single-cycle WAV wavetable file."""
    from engine.phi_core import write_wav

    cycle = render_psbs_cycle(preset, n_samples=n_samples)
    # Stack as single frame (Serum-compatible single-cycle)
    frames = cycle.reshape(1, -1)

    wt_dir = Path(out_dir)
    wt_dir.mkdir(parents=True, exist_ok=True)
    wav_name = f"PSBS_{preset.name.upper()}.wav"
    wav_path = str(wt_dir / wav_name)
    write_wav(wav_path, frames)
    print(f"  PSBS wavetable: {wav_name}")
    return wav_path


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
        export_preset(preset)
        export_wavetable(preset)

    print("PSBS engine complete.")


if __name__ == '__main__':
    main()
