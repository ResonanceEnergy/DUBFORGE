"""
DUBFORGE Engine — Arrangement Sequencer

Combines individual modules (drums, bass, FX, pads) into full
song arrangements with section-level sequencing.

Templates:
    weapon      — aggressive weapon dubstep arrangement
    emotive     — melodic/emotive dubstep arrangement
    hybrid      — hybrid bass/dubstep arrangement
    fibonacci   — fibonacci-structured experimental arrangement

Each template defines sections (intro, build, drop, break, outro)
with bar counts and which elements are active per section.
"""

from dataclasses import dataclass, field

from engine.config_loader import PHI
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)

FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]


# --- Data Models ----------------------------------------------------------

@dataclass
class SectionDef:
    """Definition of a single arrangement section."""
    name: str              # intro, build, drop1, break, drop2, outro
    bars: int = 8          # length in bars
    elements: list[str] = field(default_factory=list)  # active element types
    intensity: float = 0.5  # 0-1 intensity level
    bpm: float = 150.0


@dataclass
class ArrangementTemplate:
    """Full arrangement template with sections."""
    name: str
    template_type: str  # weapon | emotive | hybrid | fibonacci
    bpm: float = 150.0
    sections: list[SectionDef] = field(default_factory=list)
    key: str = "Fm"
    time_signature: str = "4/4"


@dataclass
class ArrangementBank:
    """Collection of arrangement templates."""
    name: str
    templates: list[ArrangementTemplate] = field(default_factory=list)


# --- Section Builders ----------------------------------------------------

def build_weapon_sections(bpm: float = 150.0) -> list[SectionDef]:
    """Build aggressive weapon dubstep arrangement sections."""
    return [
        SectionDef("intro", 8, ["pad", "fx", "perc_light"], 0.2, bpm),
        SectionDef("build_1", 8, ["drums_light", "bass_sub", "pad", "riser"], 0.4, bpm),
        SectionDef("drop_1", 16, ["drums_full", "bass_heavy", "sidechain", "fx"], 1.0, bpm),
        SectionDef("break_1", 8, ["pad", "vocal", "fx_subtle"], 0.3, bpm),
        SectionDef("build_2", 8, ["drums_building", "bass_sub", "riser", "fx"], 0.6, bpm),
        SectionDef("drop_2", 16, ["drums_full", "bass_weapon", "riddim", "sidechain", "fx"], 1.0,
                   bpm),
        SectionDef("breakdown", 4, ["pad", "impact"], 0.15, bpm),
        SectionDef("drop_3", 8, ["drums_full", "bass_weapon", "riddim", "sidechain"], 1.0, bpm),
        SectionDef("outro", 8, ["drums_light", "pad", "fx_tail"], 0.2, bpm),
    ]


def build_emotive_sections(bpm: float = 150.0) -> list[SectionDef]:
    """Build emotive melodic dubstep arrangement sections."""
    return [
        SectionDef("intro", 8, ["pad", "ambient", "vocal"], 0.15, bpm),
        SectionDef("verse_1", 16, ["drums_light", "bass_sub", "lead", "pad"], 0.4, bpm),
        SectionDef("build_1", 8, ["drums_building", "bass_sub", "lead", "riser", "arp"], 0.6,
                   bpm),
        SectionDef("drop_1", 16, ["drums_full", "bass_melodic", "lead", "sidechain", "chord"],
                   0.9, bpm),
        SectionDef("break_1", 8, ["pad", "vocal", "ambient", "pluck"], 0.25, bpm),
        SectionDef("build_2", 8, ["drums_building", "bass_sub", "riser", "arp", "vocal"], 0.65,
                   bpm),
        SectionDef("drop_2", 16, ["drums_full", "bass_melodic", "lead", "sidechain", "chord",
                                  "fx"], 1.0, bpm),
        SectionDef("outro", 8, ["pad", "ambient", "vocal", "fx_tail"], 0.1, bpm),
    ]


def build_hybrid_sections(bpm: float = 150.0) -> list[SectionDef]:
    """Build hybrid bass arrangement sections."""
    return [
        SectionDef("intro", 4, ["drone", "fx", "noise"], 0.1, bpm),
        SectionDef("build_1", 8, ["drums_light", "bass_sub", "pad", "riser"], 0.4, bpm),
        SectionDef("drop_1", 16, ["drums_full", "bass_heavy", "sidechain", "glitch"], 0.95, bpm),
        SectionDef("interlude", 4, ["pad", "ambient", "vocal"], 0.2, bpm),
        SectionDef("build_2", 8, ["drums_building", "bass_sub", "riser", "arp"], 0.55, bpm),
        SectionDef("drop_2", 16, ["drums_full", "bass_weapon", "riddim", "sidechain", "fx",
                                  "glitch"], 1.0, bpm),
        SectionDef("break", 8, ["pad", "lead", "vocal"], 0.25, bpm),
        SectionDef("drop_3", 8, ["drums_full", "bass_heavy", "sidechain"], 0.9, bpm),
        SectionDef("outro", 4, ["pad", "fx_tail", "drone"], 0.1, bpm),
    ]


def build_fibonacci_sections(bpm: float = 150.0) -> list[SectionDef]:
    """Build fibonacci-structured arrangement — bar counts follow the sequence."""
    return [
        SectionDef("intro", 1, ["ambient"], 0.05, bpm),
        SectionDef("seed", 1, ["ambient", "noise"], 0.1, bpm),
        SectionDef("grow_1", 2, ["pad", "ambient"], 0.15, bpm),
        SectionDef("grow_2", 3, ["drums_light", "pad", "ambient"], 0.25, bpm),
        SectionDef("build", 5, ["drums_building", "bass_sub", "pad", "riser"], 0.5, bpm),
        SectionDef("drop_1", 8, ["drums_full", "bass_heavy", "sidechain", "fx"], 0.9, bpm),
        SectionDef("expand", 13, ["drums_full", "bass_weapon", "riddim", "sidechain", "fx",
                                  "glitch", "lead"], 1.0, bpm),
        SectionDef("transcend", 5, ["pad", "ambient", "lead", "drone"], 0.3, bpm),
        SectionDef("outro", 3, ["ambient", "fx_tail"], 0.1, bpm),
    ]


# --- Template Builders ---------------------------------------------------

def build_weapon_template(bpm: float = 150.0, key: str = "Fm") -> ArrangementTemplate:
    return ArrangementTemplate(
        name="WEAPON_ARRANGEMENT",
        template_type="weapon",
        bpm=bpm,
        sections=build_weapon_sections(bpm),
        key=key,
    )


def build_emotive_template(bpm: float = 150.0, key: str = "Em") -> ArrangementTemplate:
    return ArrangementTemplate(
        name="EMOTIVE_ARRANGEMENT",
        template_type="emotive",
        bpm=bpm,
        sections=build_emotive_sections(bpm),
        key=key,
    )


def build_hybrid_template(bpm: float = 150.0, key: str = "Dm") -> ArrangementTemplate:
    return ArrangementTemplate(
        name="HYBRID_ARRANGEMENT",
        template_type="hybrid",
        bpm=bpm,
        sections=build_hybrid_sections(bpm),
        key=key,
    )


def build_fibonacci_template(bpm: float = 150.0, key: str = "Gm") -> ArrangementTemplate:
    return ArrangementTemplate(
        name="FIBONACCI_ARRANGEMENT",
        template_type="fibonacci",
        bpm=bpm,
        sections=build_fibonacci_sections(bpm),
        key=key,
    )


# --- Analysis Functions ---------------------------------------------------

def arrangement_total_bars(template: ArrangementTemplate) -> int:
    """Total bars in arrangement."""
    return sum(s.bars for s in template.sections)


def arrangement_duration_s(template: ArrangementTemplate) -> float:
    """Total duration in seconds."""
    total_bars = arrangement_total_bars(template)
    beats_per_bar = 4  # 4/4 time
    return total_bars * beats_per_bar * 60.0 / template.bpm


def arrangement_energy_curve(template: ArrangementTemplate) -> list[dict]:
    """Generate energy curve from section intensities."""
    curve = []
    bar_pos = 0
    for section in template.sections:
        curve.append({
            "section": section.name,
            "start_bar": bar_pos,
            "end_bar": bar_pos + section.bars,
            "intensity": section.intensity,
            "elements": section.elements,
        })
        bar_pos += section.bars
    return curve


def arrangement_energy_compressed(template: ArrangementTemplate) -> CompressedAudioBuffer:
    """TQ-compress the energy/intensity vector of an arrangement."""
    intensities = [s.intensity for s in template.sections]
    if not intensities:
        intensities = [0.0]
    tq_cfg = TurboQuantConfig(bit_width=phi_optimal_bits(len(intensities)))
    return compress_audio_buffer(
        intensities, f"energy_{template.name}", tq_cfg,
        sample_rate=1, label=template.name,
    )


def golden_section_check(template: ArrangementTemplate) -> dict:
    """Check if the climax point aligns with the golden ratio."""
    total = arrangement_total_bars(template)
    golden_bar = int(total / PHI)

    # Find which section contains the golden bar
    bar_pos = 0
    golden_section = None
    for section in template.sections:
        if bar_pos <= golden_bar < bar_pos + section.bars:
            golden_section = section.name
            break
        bar_pos += section.bars

    # Find the highest intensity section
    peak_section = max(template.sections, key=lambda s: s.intensity)

    return {
        "total_bars": total,
        "golden_bar": golden_bar,
        "golden_section": golden_section,
        "peak_section": peak_section.name,
        "peak_intensity": peak_section.intensity,
        "aligned": golden_section == peak_section.name,
    }


# --- Router ---------------------------------------------------------------

def build_arrangement(template_type: str,
                      bpm: float = 150.0,
                      key: str = "Fm") -> ArrangementTemplate:
    """Build an arrangement template by type."""
    builders = {
        "weapon": build_weapon_template,
        "emotive": build_emotive_template,
        "hybrid": build_hybrid_template,
        "fibonacci": build_fibonacci_template,
    }
    builder = builders.get(template_type)
    if builder is None:
        raise ValueError(f"Unknown arrangement type: {template_type}")
    return builder(bpm, key)


# --- Banks ----------------------------------------------------------------

def weapon_arrangement_bank() -> ArrangementBank:
    return ArrangementBank(
        name="WEAPON_ARRANGEMENTS",
        templates=[
            build_weapon_template(150.0, "Fm"),
            build_weapon_template(148.0, "Em"),
            build_weapon_template(152.0, "Dm"),
            build_weapon_template(150.0, "Gm"),
        ],
    )


def emotive_arrangement_bank() -> ArrangementBank:
    return ArrangementBank(
        name="EMOTIVE_ARRANGEMENTS",
        templates=[
            build_emotive_template(150.0, "Em"),
            build_emotive_template(140.0, "Fm"),
            build_emotive_template(148.0, "Dm"),
            build_emotive_template(145.0, "Abm"),
        ],
    )


def hybrid_arrangement_bank() -> ArrangementBank:
    return ArrangementBank(
        name="HYBRID_ARRANGEMENTS",
        templates=[
            build_hybrid_template(150.0, "Dm"),
            build_hybrid_template(148.0, "Fm"),
            build_hybrid_template(152.0, "Em"),
            build_hybrid_template(150.0, "Gm"),
        ],
    )


def fibonacci_arrangement_bank() -> ArrangementBank:
    return ArrangementBank(
        name="FIBONACCI_ARRANGEMENTS",
        templates=[
            build_fibonacci_template(150.0, "Gm"),
            build_fibonacci_template(148.0, "Fm"),
            build_fibonacci_template(144.0, "Em"),
            build_fibonacci_template(150.0, "Dm"),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_ARRANGEMENT_BANKS: dict[str, callable] = {
    "weapon": weapon_arrangement_bank,
    "emotive": emotive_arrangement_bank,
    "hybrid": hybrid_arrangement_bank,
    "fibonacci": fibonacci_arrangement_bank,
}


# --- Manifest -------------------------------------------------------------

def write_arrangement_sequencer_manifest(output_dir: str = "output") -> dict:
    """Write arrangement sequencer manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_ARRANGEMENT_BANKS.items():
        bank = gen_fn()
        templates_data = []
        for t in bank.templates:
            templates_data.append({
                "name": t.name,
                "bpm": t.bpm,
                "key": t.key,
                "total_bars": arrangement_total_bars(t),
                "duration_s": round(arrangement_duration_s(t), 1),
                "sections": len(t.sections),
                "golden_check": golden_section_check(t),
            })
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "template_count": len(bank.templates),
            "templates": templates_data,
        }

    path = out / "arrangement_sequencer_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_arrangement_sequencer_manifest()
    total = sum(b["template_count"] for b in manifest["banks"].values())
    print(f"Arrangement Sequencer: {len(manifest['banks'])} banks, {total} templates")


if __name__ == "__main__":
    main()
