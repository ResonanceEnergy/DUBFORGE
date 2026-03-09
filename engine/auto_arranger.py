"""
DUBFORGE — Auto-Arranger Engine  (Session 181)

Generates full dubstep arrangements from sections,
with structure templates, transitions, and PHI proportions.
"""

from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class Section:
    """A section of an arrangement."""
    name: str
    duration_bars: int
    energy: float = 0.5  # 0=calm, 1=maximum
    modules: list[str] = field(default_factory=list)
    bpm: float = 140.0

    @property
    def duration_beats(self) -> int:
        return self.duration_bars * 4

    @property
    def duration_s(self) -> float:
        return self.duration_beats * 60.0 / self.bpm

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bars": self.duration_bars,
            "energy": round(self.energy, 2),
            "duration_s": round(self.duration_s, 1),
            "modules": self.modules,
        }


@dataclass
class Transition:
    """Transition between sections."""
    type: str  # "riser", "drop", "fade", "cut", "sweep"
    duration_bars: int = 2
    intensity: float = 0.8

    def to_dict(self) -> dict:
        return {"type": self.type, "bars": self.duration_bars,
                "intensity": round(self.intensity, 2)}


@dataclass
class Arrangement:
    """A full song arrangement."""
    sections: list[Section] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    bpm: float = 140.0
    key: str = "F"
    name: str = "Untitled"

    @property
    def total_bars(self) -> int:
        s = sum(sec.duration_bars for sec in self.sections)
        s += sum(t.duration_bars for t in self.transitions)
        return s

    @property
    def total_duration_s(self) -> float:
        return self.total_bars * 4 * 60.0 / self.bpm

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bpm": self.bpm,
            "key": self.key,
            "total_bars": self.total_bars,
            "duration_s": round(self.total_duration_s, 1),
            "sections": [s.to_dict() for s in self.sections],
            "transitions": [t.to_dict() for t in self.transitions],
        }


# Standard dubstep arrangement templates
ARRANGEMENT_TEMPLATES: dict[str, list[dict]] = {
    "standard": [
        {"name": "Intro", "bars": 16, "energy": 0.2, "modules": ["pad", "reverb"]},
        {"name": "Buildup", "bars": 8, "energy": 0.5,
         "modules": ["riser", "drums", "noise"]},
        {"name": "Drop 1", "bars": 16, "energy": 1.0,
         "modules": ["sub_bass", "wobble", "drums", "sidechain"]},
        {"name": "Breakdown", "bars": 8, "energy": 0.3,
         "modules": ["pad", "vocal", "reverb"]},
        {"name": "Buildup 2", "bars": 8, "energy": 0.6,
         "modules": ["riser", "drums", "noise", "sidechain"]},
        {"name": "Drop 2", "bars": 16, "energy": 1.0,
         "modules": ["sub_bass", "wobble", "drums", "sidechain", "distortion"]},
        {"name": "Outro", "bars": 8, "energy": 0.15,
         "modules": ["pad", "reverb", "delay"]},
    ],
    "tearout": [
        {"name": "Intro", "bars": 8, "energy": 0.3, "modules": ["noise", "reverb"]},
        {"name": "Drop", "bars": 32, "energy": 1.0,
         "modules": ["sub_bass", "growl", "drums", "sidechain", "distortion"]},
        {"name": "Break", "bars": 4, "energy": 0.2, "modules": ["silence"]},
        {"name": "Drop 2", "bars": 32, "energy": 1.0,
         "modules": ["sub_bass", "growl", "drums", "sidechain", "glitch"]},
        {"name": "Outro", "bars": 4, "energy": 0.1, "modules": ["reverb"]},
    ],
    "melodic": [
        {"name": "Intro", "bars": 16, "energy": 0.2,
         "modules": ["pad", "arp", "reverb"]},
        {"name": "Verse", "bars": 16, "energy": 0.4,
         "modules": ["lead", "pad", "drums_light"]},
        {"name": "Buildup", "bars": 8, "energy": 0.6,
         "modules": ["riser", "arp", "drums"]},
        {"name": "Drop", "bars": 16, "energy": 0.9,
         "modules": ["lead", "sub_bass", "drums", "sidechain"]},
        {"name": "Breakdown", "bars": 16, "energy": 0.3,
         "modules": ["pad", "vocal", "arp"]},
        {"name": "Drop 2", "bars": 16, "energy": 1.0,
         "modules": ["lead", "sub_bass", "drums", "sidechain", "supersaw"]},
        {"name": "Outro", "bars": 16, "energy": 0.15,
         "modules": ["pad", "arp", "reverb"]},
    ],
    "riddim": [
        {"name": "Intro", "bars": 8, "energy": 0.3, "modules": ["sub_bass"]},
        {"name": "Drop", "bars": 16, "energy": 1.0,
         "modules": ["sub_bass", "wobble", "drums", "sidechain"]},
        {"name": "Pattern Switch", "bars": 16, "energy": 0.9,
         "modules": ["sub_bass", "wobble", "drums", "sidechain"]},
        {"name": "Break", "bars": 4, "energy": 0.1, "modules": ["reverb"]},
        {"name": "Drop 2", "bars": 16, "energy": 1.0,
         "modules": ["sub_bass", "wobble", "drums", "sidechain", "distortion"]},
        {"name": "Outro", "bars": 4, "energy": 0.2, "modules": ["sub_bass"]},
    ],
}


def generate_arrangement(template: str = "standard",
                          bpm: float = 140.0,
                          key: str = "F") -> Arrangement:
    """Generate an arrangement from a template."""
    tmpl = ARRANGEMENT_TEMPLATES.get(template, ARRANGEMENT_TEMPLATES["standard"])

    sections: list[Section] = []
    transitions: list[Transition] = []

    for i, t in enumerate(tmpl):
        sections.append(Section(
            name=t["name"],
            duration_bars=t["bars"],
            energy=t["energy"],
            modules=t.get("modules", []),
            bpm=bpm,
        ))

        # Auto-insert transitions between sections
        if i < len(tmpl) - 1:
            curr_energy = t["energy"]
            next_energy = tmpl[i + 1]["energy"]
            delta = next_energy - curr_energy

            if delta > 0.3:
                trans_type = "riser"
            elif delta < -0.3:
                trans_type = "drop"
            elif abs(delta) < 0.1:
                trans_type = "fade"
            else:
                trans_type = "sweep"

            transitions.append(Transition(
                type=trans_type,
                duration_bars=2 if abs(delta) > 0.5 else 1,
                intensity=abs(delta),
            ))

    return Arrangement(
        sections=sections,
        transitions=transitions,
        bpm=bpm,
        key=key,
        name=f"DUBFORGE — {template.title()}",
    )


def phi_arrangement(bpm: float = 140.0, key: str = "F") -> Arrangement:
    """Generate arrangement with PHI-ratio section proportions."""
    total_bars = 80
    phi_bars = [
        int(total_bars / (PHI ** i))
        for i in range(6)
    ]
    # [80, 49, 30, 19, 12, 7]

    section_defs = [
        ("Drop", 1.0, ["sub_bass", "wobble", "drums", "sidechain"]),
        ("Breakdown", 0.3, ["pad", "reverb"]),
        ("Buildup", 0.6, ["riser", "drums", "noise"]),
        ("Drop 2", 1.0, ["sub_bass", "wobble", "drums", "distortion"]),
        ("Intro", 0.2, ["pad", "ambient"]),
        ("Outro", 0.15, ["reverb", "delay"]),
    ]

    sections: list[Section] = []
    for i, (name, energy, modules) in enumerate(section_defs):
        bars = phi_bars[i] if i < len(phi_bars) else 4
        sections.append(Section(name, bars, energy, modules, bpm))

    # Reorder: Intro, Buildup, Drop, Breakdown, Drop2, Outro
    ordered = [sections[4], sections[2], sections[0],
               sections[1], sections[3], sections[5]]

    return Arrangement(
        sections=ordered,
        bpm=bpm,
        key=key,
        name="DUBFORGE — PHI Arrangement",
    )


def arrangement_text(arr: Arrangement) -> str:
    """Format arrangement as text timeline."""
    lines = [f"Arrangement: {arr.name}"]
    lines.append(f"BPM: {arr.bpm} | Key: {arr.key} | "
                 f"Duration: {arr.total_duration_s:.0f}s "
                 f"({arr.total_bars} bars)")
    lines.append("")

    bar_pos = 0
    for i, section in enumerate(arr.sections):
        end_bar = bar_pos + section.duration_bars
        energy_bar = "█" * int(section.energy * 10)
        lines.append(
            f"  [{bar_pos:3d}-{end_bar:3d}] {section.name:<15} "
            f"{section.duration_bars:2d} bars  {energy_bar}"
        )
        bar_pos = end_bar

        if i < len(arr.transitions):
            t = arr.transitions[i]
            bar_pos += t.duration_bars
            lines.append(f"         ↳ {t.type} ({t.duration_bars} bars)")

    return "\n".join(lines)


def main() -> None:
    print("Auto-Arranger Engine")

    for tmpl in ["standard", "tearout", "melodic", "riddim"]:
        arr = generate_arrangement(tmpl, 140.0, "F")
        print(f"\n{arrangement_text(arr)}")

    print("\n" + "=" * 50)
    phi_arr = phi_arrangement(140.0, "F")
    print(f"\n{arrangement_text(phi_arr)}")
    print("Done.")


if __name__ == "__main__":
    main()
