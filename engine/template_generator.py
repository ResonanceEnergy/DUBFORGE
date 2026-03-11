"""
DUBFORGE — Template Generator  (Session 129 · v3.8.0)

Given a genre tag + energy profile, auto-generate a complete
Serum2Patch config + arrangement + FX chain.

5 generator types × 4 presets = 20 presets.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
PHI_INV = 1.0 / PHI


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TemplateConfig:
    """Generated template configuration."""
    name: str
    genre: str
    energy: float           # 0.0 (ambient) to 1.0 (peak)
    bpm: int = 150
    key: str = "F"
    scale: str = "minor"
    # Synth params
    osc_type: str = "saw"
    filter_cutoff: float = 0.7
    filter_resonance: float = 0.3
    distortion: float = 0.0
    reverb: float = 0.2
    delay: float = 0.1
    # Arrangement
    sections: list[str] = field(default_factory=lambda: ["intro", "drop", "break", "drop2", "outro"])
    bars_per_section: int = 16
    # FX chain
    fx_chain: list[str] = field(default_factory=lambda: ["eq", "compression", "stereo_width"])

    def to_dict(self) -> dict:
        return {
            "name": self.name, "genre": self.genre, "energy": self.energy,
            "bpm": self.bpm, "key": self.key, "scale": self.scale,
            "osc_type": self.osc_type, "filter_cutoff": round(self.filter_cutoff, 3),
            "filter_resonance": round(self.filter_resonance, 3),
            "distortion": round(self.distortion, 3),
            "reverb": round(self.reverb, 3), "delay": round(self.delay, 3),
            "sections": self.sections, "bars_per_section": self.bars_per_section,
            "fx_chain": self.fx_chain,
        }


@dataclass
class TemplatePreset:
    name: str
    generator_type: str  # dubstep | riddim | melodic | hybrid | ambient
    energy_profile: str = "standard"   # standard | escalating | phi_curve | flat | random
    bpm_range: tuple = (140, 160)
    complexity: float = 0.5   # 0-1


@dataclass
class TemplateBank:
    name: str
    presets: list[TemplatePreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# GENERATOR FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

GENRE_PROFILES = {
    "dubstep": {
        "osc_type": "saw", "filter_cutoff": 0.6, "distortion": 0.7,
        "reverb": 0.15, "delay": 0.1, "scale": "minor",
        "sections": ["intro", "buildup", "drop", "break", "drop2", "outro"],
        "fx_chain": ["eq", "multiband_distortion", "sidechain", "stereo_width", "limiter"],
    },
    "riddim": {
        "osc_type": "square", "filter_cutoff": 0.5, "distortion": 0.8,
        "reverb": 0.1, "delay": 0.05, "scale": "minor",
        "sections": ["intro", "drop", "break", "drop2", "outro"],
        "fx_chain": ["eq", "distortion", "sidechain", "compression"],
    },
    "melodic": {
        "osc_type": "saw", "filter_cutoff": 0.8, "distortion": 0.2,
        "reverb": 0.4, "delay": 0.3, "scale": "minor",
        "sections": ["intro", "verse", "buildup", "drop", "breakdown", "drop2", "outro"],
        "fx_chain": ["eq", "reverb", "delay", "stereo_width", "compression"],
    },
    "hybrid": {
        "osc_type": "wavetable", "filter_cutoff": 0.65, "distortion": 0.5,
        "reverb": 0.25, "delay": 0.15, "scale": "minor",
        "sections": ["intro", "buildup", "drop_a", "break", "drop_b", "outro"],
        "fx_chain": ["eq", "multiband_distortion", "reverb", "sidechain", "limiter"],
    },
    "ambient": {
        "osc_type": "sine", "filter_cutoff": 0.9, "distortion": 0.0,
        "reverb": 0.7, "delay": 0.5, "scale": "major",
        "sections": ["intro", "movement_a", "movement_b", "movement_c", "outro"],
        "fx_chain": ["eq", "reverb", "delay", "stereo_width", "chorus"],
    },
}

ENERGY_PROFILES = {
    "standard":    lambda n: [0.3, 0.6, 1.0, 0.4, 0.9, 0.3][:n],
    "escalating":  lambda n: [i / (n - 1) if n > 1 else 0.5 for i in range(n)],
    "phi_curve":   lambda n: [min(1.0, (PHI_INV ** (n - 1 - i))) for i in range(n)],
    "flat":        lambda n: [0.6] * n,
    "random":      lambda n: [float(np.random.uniform(0.2, 1.0)) for _ in range(n)],
}


def generate_template(preset: TemplatePreset) -> TemplateConfig:
    """Generate a complete template configuration."""
    profile = GENRE_PROFILES.get(preset.generator_type, GENRE_PROFILES["dubstep"])
    energy_fn = ENERGY_PROFILES.get(preset.energy_profile, ENERGY_PROFILES["standard"])

    sections = list(profile.get("sections", ["intro", "drop", "outro"]))
    energies = energy_fn(len(sections))
    avg_energy = float(np.mean(energies))

    bpm = int(np.random.uniform(*preset.bpm_range))

    # Scale parameters by complexity
    cutoff = profile["filter_cutoff"] * (0.5 + preset.complexity * 0.5)
    resonance = 0.2 + preset.complexity * 0.3
    dist = profile["distortion"] * preset.complexity
    fx = list(profile.get("fx_chain", []))
    if preset.complexity > 0.7:
        fx.append("multiband_compression")

    return TemplateConfig(
        name=f"{preset.generator_type}_{preset.name}",
        genre=preset.generator_type,
        energy=round(avg_energy, 3),
        bpm=bpm,
        key=np.random.choice(["C", "D", "E", "F", "G", "A", "B"]),
        scale=profile.get("scale", "minor"),
        osc_type=profile["osc_type"],
        filter_cutoff=round(cutoff, 3),
        filter_resonance=round(resonance, 3),
        distortion=round(dist, 3),
        reverb=round(profile["reverb"], 3),
        delay=round(profile["delay"], 3),
        sections=sections,
        bars_per_section=int(16 * (0.5 + preset.complexity)),
        fx_chain=fx,
    )


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def dubstep_bank() -> TemplateBank:
    return TemplateBank("dubstep", [
        TemplatePreset("dub_standard", "dubstep", "standard", (145, 155)),
        TemplatePreset("dub_escalating", "dubstep", "escalating", (140, 150)),
        TemplatePreset("dub_phi", "dubstep", "phi_curve", (148, 152)),
        TemplatePreset("dub_complex", "dubstep", "standard", (145, 155), complexity=0.9),
    ])


def riddim_bank() -> TemplateBank:
    return TemplateBank("riddim", [
        TemplatePreset("rid_standard", "riddim", "standard", (140, 150)),
        TemplatePreset("rid_flat", "riddim", "flat", (145, 150)),
        TemplatePreset("rid_phi", "riddim", "phi_curve", (140, 148)),
        TemplatePreset("rid_minimal", "riddim", "flat", (140, 150), complexity=0.3),
    ])


def melodic_bank() -> TemplateBank:
    return TemplateBank("melodic", [
        TemplatePreset("mel_standard", "melodic", "escalating", (135, 145)),
        TemplatePreset("mel_emotional", "melodic", "phi_curve", (130, 140)),
        TemplatePreset("mel_complex", "melodic", "standard", (135, 145), complexity=0.8),
        TemplatePreset("mel_simple", "melodic", "flat", (138, 142), complexity=0.2),
    ])


def hybrid_bank() -> TemplateBank:
    return TemplateBank("hybrid", [
        TemplatePreset("hyb_standard", "hybrid", "standard", (145, 155)),
        TemplatePreset("hyb_escalating", "hybrid", "escalating", (140, 150)),
        TemplatePreset("hyb_phi", "hybrid", "phi_curve", (148, 152)),
        TemplatePreset("hyb_dense", "hybrid", "random", (145, 155), complexity=0.9),
    ])


def ambient_bank() -> TemplateBank:
    return TemplateBank("ambient", [
        TemplatePreset("amb_slow", "ambient", "flat", (60, 80)),
        TemplatePreset("amb_phi", "ambient", "phi_curve", (70, 90)),
        TemplatePreset("amb_evolving", "ambient", "escalating", (80, 100)),
        TemplatePreset("amb_minimal", "ambient", "flat", (60, 70), complexity=0.1),
    ])


ALL_TEMPLATE_BANKS: dict[str, callable] = {
    "dubstep": dubstep_bank,
    "riddim": riddim_bank,
    "melodic": melodic_bank,
    "hybrid": hybrid_bank,
    "ambient": ambient_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def export_templates(output_dir: str = "output") -> list[str]:
    """Generate all templates and export as JSON configs."""
    out = Path(output_dir) / "templates"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for bank_name, gen_fn in ALL_TEMPLATE_BANKS.items():
        bank = gen_fn()
        for preset in bank.presets:
            template = generate_template(preset)
            fpath = out / f"template_{template.name}.json"
            with open(fpath, "w") as f:
                json.dump(template.to_dict(), f, indent=2)
            paths.append(str(fpath))

    return paths


def write_template_manifest(output_dir: str = "output") -> dict:
    out = Path(output_dir) / "templates"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"module": "template_generator", "banks": {}}
    for name, gen_fn in ALL_TEMPLATE_BANKS.items():
        bank = gen_fn()
        manifest["banks"][name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "template_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_template_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    templates = export_templates()
    print(f"Template Generator: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(templates)} templates")


if __name__ == "__main__":
    main()
