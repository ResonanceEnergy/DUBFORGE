"""
DUBFORGE Engine — Rollercoaster Optimizer (RCO)

Analyzes and generates energy curves for drop arrangements.
Based on Subtronics structural analysis and phi-ratio timing.

The RCO models a track's energy as a time-series and optimizes
drop placement, build-up slopes, and tension/release using
Fibonacci bar counts and phi-ratio envelope shapes.

Outputs:
    output/analysis/rco_curve.json
    output/analysis/rco_curve.png  (if matplotlib available)
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from engine.config_loader import PHI, load_config

# --- Data Models ----------------------------------------------------------

@dataclass
class Section:
    """One section of a track arrangement."""
    name: str                    # e.g. "intro", "build_1", "drop_1", "break", "drop_2"
    bars: int                    # length in bars
    energy_start: float          # 0.0 – 1.0
    energy_end: float            # 0.0 – 1.0
    curve: str = "phi"           # "linear", "phi", "exponential", "fibonacci_step"
    bpm: float = 150.0


@dataclass
class RCOProfile:
    """Complete rollercoaster energy profile for a track."""
    name: str
    bpm: float
    sections: list = field(default_factory=list)
    total_bars: int = 0
    total_duration_s: float = 0.0

    def compute(self):
        self.total_bars = sum(s.bars for s in self.sections)
        self.total_duration_s = (self.total_bars * 4 * 60) / self.bpm  # 4 beats/bar


# --- Curve Functions ------------------------------------------------------

def phi_curve(start: float, end: float, n_points: int) -> list[float]:
    """Non-linear interpolation using phi exponent."""
    points = []
    for i in range(n_points):
        t = i / max(n_points - 1, 1)
        t_phi = t ** PHI
        val = start + (end - start) * t_phi
        points.append(round(val, 4))
    return points


def fibonacci_step_curve(start: float, end: float, n_points: int) -> list[float]:
    """Step-wise interpolation at Fibonacci intervals."""
    points = []
    fib_set = set()
    a, b = 1, 1
    while a <= n_points:
        fib_set.add(a - 1)
        a, b = b, a + b

    current = start
    step = (end - start) / max(len(fib_set), 1)
    for i in range(n_points):
        if i in fib_set:
            current += step
            current = min(max(current, 0.0), 1.0)
        points.append(round(current, 4))
    return points


def linear_curve(start: float, end: float, n_points: int) -> list[float]:
    points = []
    for i in range(n_points):
        t = i / max(n_points - 1, 1)
        points.append(round(start + (end - start) * t, 4))
    return points


def exponential_curve(start: float, end: float, n_points: int) -> list[float]:
    points = []
    for i in range(n_points):
        t = i / max(n_points - 1, 1)
        t_exp = t ** 2.0
        points.append(round(start + (end - start) * t_exp, 4))
    return points


CURVE_MAP = {
    "phi": phi_curve,
    "linear": linear_curve,
    "exponential": exponential_curve,
    "fibonacci_step": fibonacci_step_curve,
}


# --- RCO Engine -----------------------------------------------------------

def generate_energy_curve(profile: RCOProfile,
                          resolution_per_bar: int = 4) -> dict:
    """
    Generate a full energy curve for the arrangement.

    Returns dict with:
        time_s: list of timestamps
        energy: list of energy values [0..1]
        sections: section metadata
    """
    profile.compute()
    all_energy = []
    all_time = []
    bar_offset = 0
    seconds_per_bar = (4 * 60) / profile.bpm

    for section in profile.sections:
        n_points = section.bars * resolution_per_bar
        curve_fn = CURVE_MAP.get(section.curve, phi_curve)
        energy = curve_fn(section.energy_start, section.energy_end, n_points)

        for i, e in enumerate(energy):
            t = (bar_offset + i / resolution_per_bar) * seconds_per_bar
            all_time.append(round(t, 3))
            all_energy.append(e)

        bar_offset += section.bars

    return {
        "name": profile.name,
        "bpm": profile.bpm,
        "total_bars": profile.total_bars,
        "total_duration_s": round(profile.total_duration_s, 2),
        "time_s": all_time,
        "energy": all_energy,
        "sections": [asdict(s) for s in profile.sections],
    }


# --- Presets from Subtronics Analysis ------------------------------------

def subtronics_weapon_preset(bpm: float = 150.0) -> RCOProfile:
    """
    Weapon-style drop structure derived from Subtronics corpus analysis.
    16-bar drops, 8-bar builds, Fibonacci break lengths.
    """
    return RCOProfile(
        name="SUBTRONICS_WEAPON",
        bpm=bpm,
        sections=[
            Section("intro",    bars=8,  energy_start=0.0, energy_end=0.2, curve="linear"),
            Section("build_1",  bars=8,  energy_start=0.2, energy_end=0.85, curve="phi"),
            Section("drop_1",   bars=16, energy_start=1.0, energy_end=0.9, curve="fibonacci_step"),
            Section("break_1",  bars=8,  energy_start=0.3, energy_end=0.15, curve="phi"),
            Section("build_2",  bars=8,  energy_start=0.15, energy_end=0.95, curve="exponential"),
            Section("drop_2",   bars=16, energy_start=1.0, energy_end=0.85, curve="fibonacci_step"),
            Section("break_2",  bars=8,  energy_start=0.25, energy_end=0.1, curve="phi"),
            Section("build_3",  bars=8,  energy_start=0.1, energy_end=1.0, curve="phi"),
            Section("drop_3",   bars=16, energy_start=1.0, energy_end=0.8, curve="fibonacci_step"),
            Section("outro",    bars=8,  energy_start=0.3, energy_end=0.0, curve="linear"),
        ],
    )


def subtronics_emotive_preset(bpm: float = 150.0) -> RCOProfile:
    """
    Emotive/melodic drop structure — longer builds, gentler breaks.
    """
    return RCOProfile(
        name="SUBTRONICS_EMOTIVE",
        bpm=bpm,
        sections=[
            Section("intro",     bars=16, energy_start=0.0, energy_end=0.3, curve="phi"),
            Section("verse_1",   bars=16, energy_start=0.3, energy_end=0.4, curve="linear"),
            Section("build_1",   bars=8,  energy_start=0.4, energy_end=0.85, curve="phi"),
            Section("drop_1",    bars=16, energy_start=0.9, energy_end=0.75, curve="fibonacci_step"),
            Section("break_1",   bars=16, energy_start=0.35, energy_end=0.2, curve="phi"),
            Section("build_2",   bars=8,  energy_start=0.2, energy_end=0.95, curve="phi"),
            Section("drop_2",    bars=16, energy_start=1.0, energy_end=0.8, curve="fibonacci_step"),
            Section("outro",     bars=16, energy_start=0.3, energy_end=0.0, curve="phi"),
        ],
    )


def subtronics_hybrid_preset(bpm: float = 150.0) -> RCOProfile:
    """
    Hybrid: weapon aggression + emotive breaks.
    """
    return RCOProfile(
        name="SUBTRONICS_HYBRID",
        bpm=bpm,
        sections=[
            Section("intro",     bars=8,  energy_start=0.0, energy_end=0.25, curve="phi"),
            Section("build_1",   bars=8,  energy_start=0.25, energy_end=0.9, curve="exponential"),
            Section("drop_1",    bars=16, energy_start=1.0, energy_end=0.85, curve="fibonacci_step"),
            Section("melodic_break", bars=16, energy_start=0.4, energy_end=0.3, curve="phi"),
            Section("build_2",   bars=8,  energy_start=0.3, energy_end=1.0, curve="phi"),
            Section("drop_2",    bars=16, energy_start=1.0, energy_end=0.9, curve="fibonacci_step"),
            Section("break_2",   bars=8,  energy_start=0.3, energy_end=0.15, curve="phi"),
            Section("build_3",   bars=8,  energy_start=0.15, energy_end=1.0, curve="phi"),
            Section("drop_3",    bars=16, energy_start=1.0, energy_end=0.75, curve="fibonacci_step"),
            Section("outro",     bars=8,  energy_start=0.25, energy_end=0.0, curve="linear"),
        ],
    )


# --- YAML-driven profile loader -------------------------------------------

def load_rco_profiles_from_config() -> list[RCOProfile]:
    """
    Load RCO profiles from rco_psbs_vip_delta_v1.1.yaml.
    Falls back to hardcoded presets if YAML not available.
    """
    try:
        cfg = load_config("rco_psbs_vip_delta_v1.1")
    except FileNotFoundError:
        return []

    profiles_data = cfg.get("rco_profiles", {})
    if not isinstance(profiles_data, dict):
        return []

    profiles = []
    for name, pdata in profiles_data.items():
        if not isinstance(pdata, dict):
            continue
        bpm = float(pdata.get("bpm", 150))
        sections_raw = pdata.get("sections", [])
        sections = []
        for s in sections_raw:
            if not isinstance(s, dict):
                continue
            energy = s.get("energy", [0.0, 0.0])
            if isinstance(energy, list) and len(energy) >= 2:
                e_start, e_end = float(energy[0]), float(energy[1])
            else:
                e_start, e_end = 0.0, 0.0
            sections.append(Section(
                name=s.get("name", "section"),
                bars=int(s.get("bars", 8)),
                energy_start=e_start,
                energy_end=e_end,
                curve=str(s.get("curve", "phi")),
                bpm=bpm,
            ))
        profiles.append(RCOProfile(name=name, bpm=bpm, sections=sections))
    return profiles


# --- Plotting (optional) -------------------------------------------------

def plot_curve(curve_data: dict, out_path: Optional[str] = None):
    """Plot the energy curve. Requires matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — skipping plot.")
        return

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(curve_data["time_s"], curve_data["energy"],
            color="#ff5500", linewidth=1.5)
    ax.fill_between(curve_data["time_s"], curve_data["energy"],
                    alpha=0.3, color="#ff5500")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Energy")
    ax.set_title(f"RCO — {curve_data['name']}  |  {curve_data['bpm']} BPM  |  "
                 f"{curve_data['total_bars']} bars  |  "
                 f"{curve_data['total_duration_s']}s")
    ax.set_ylim(-0.05, 1.1)
    ax.grid(True, alpha=0.3)

    # Section markers
    bar_offset = 0
    spb = (4 * 60) / curve_data["bpm"]
    for sec in curve_data["sections"]:
        t = bar_offset * spb
        ax.axvline(x=t, color='white', alpha=0.4, linestyle='--', linewidth=0.7)
        ax.text(t + 0.5, 1.05, sec["name"], fontsize=6, rotation=45,
                color='white', alpha=0.7)
        bar_offset += sec["bars"]

    ax.set_facecolor('#1a1a2e')
    fig.patch.set_facecolor('#0f0f1a')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')

    plt.tight_layout()
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=150)
        print(f"  -> {out_path}")
    else:
        plt.show()
    plt.close()


# --- Main -----------------------------------------------------------------


def main() -> None:
    out_dir = Path('output/analysis')
    out_dir.mkdir(parents=True, exist_ok=True)

    # Try YAML-driven profiles first, fall back to hardcoded presets
    yaml_profiles = load_rco_profiles_from_config()
    if yaml_profiles:
        presets = yaml_profiles
    else:
        presets = [
            subtronics_weapon_preset(),
            subtronics_emotive_preset(),
            subtronics_hybrid_preset(),
        ]

    for profile in presets:
        curve = generate_energy_curve(profile)
        json_path = out_dir / f"rco_{profile.name.lower()}.json"
        with open(json_path, 'w') as f:
            json.dump(curve, f, indent=2)
        print(f"RCO curve: {json_path}")

        png_path = str(out_dir / f"rco_{profile.name.lower()}.png")
        plot_curve(curve, out_path=png_path)

    print("RCO engine complete.")


if __name__ == '__main__':
    main()
