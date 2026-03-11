"""
DUBFORGE Engine — Song Templates

Subtronics-style song structure templates derived from analysis
of the 74-track corpus. Provides standardized song structures
for different dubstep sub-genres.

Templates:
    weapon_standard — Standard weapon dubstep (76 bars)
    weapon_extended — Extended weapon format (96 bars)
    emotive_standard — Melodic/emotive format (88 bars)
    emotive_cinematic — Cinematic emotive (96 bars)
    hybrid_compact — Compact hybrid bass (68 bars)
    riddim_loop — Riddim-focused loop format (64 bars)
    vip_remix — VIP remix structure (80 bars)
    festival_weapon — Festival main-stage weapon (104 bars)

Banks: 4 categories × 5 templates each = 20 templates
"""

from dataclasses import dataclass, field

from engine.config_loader import PHI
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]


# --- Data Models ----------------------------------------------------------

@dataclass
class SongSection:
    """A single section in a song template."""
    name: str
    bars: int
    description: str = ""
    energy: float = 0.5  # 0-1

    @property
    def beats(self) -> int:
        return self.bars * 4


@dataclass
class SongTemplate:
    """Complete song structure template."""
    name: str
    category: str           # weapon | emotive | hybrid | experimental
    bpm: float = 150.0
    key: str = "Fm"
    sections: list[SongSection] = field(default_factory=list)
    description: str = ""
    source_tracks: list[str] = field(default_factory=list)  # corpus tracks this is based on

    @property
    def total_bars(self) -> int:
        return sum(s.bars for s in self.sections)

    @property
    def duration_s(self) -> float:
        return self.total_bars * 4 * 60.0 / self.bpm

    @property
    def golden_bar(self) -> int:
        return int(self.total_bars / PHI)


@dataclass
class SongTemplateBank:
    """Collection of song templates."""
    name: str
    templates: list[SongTemplate] = field(default_factory=list)


# --- Weapon Templates ----------------------------------------------------

def weapon_standard_template() -> SongTemplate:
    """Standard weapon dubstep — 76 bars, fast build to double drop."""
    return SongTemplate(
        name="WEAPON_STANDARD",
        category="weapon",
        bpm=150.0,
        key="Fm",
        sections=[
            SongSection("intro", 8, "FX + ambient buildup", 0.1),
            SongSection("build_1", 8, "Drums + bass teaser + riser", 0.45),
            SongSection("drop_1", 16, "Full weapon bass + drums", 1.0),
            SongSection("break", 8, "Melodic break / vocal", 0.25),
            SongSection("build_2", 4, "Quick rebuild with riser", 0.6),
            SongSection("drop_2", 16, "Heavier weapon bass variant", 1.0),
            SongSection("breakdown", 4, "Impact + silence", 0.1),
            SongSection("drop_3", 8, "Final weapon blast", 0.95),
            SongSection("outro", 4, "Fade out / tail FX", 0.05),
        ],
        source_tracks=["Scream Saver", "Griztronics", "Hollow Point"],
    )


def weapon_extended_template() -> SongTemplate:
    """Extended weapon — 96 bars with longer builds."""
    return SongTemplate(
        name="WEAPON_EXTENDED",
        category="weapon",
        bpm=150.0,
        key="Dm",
        sections=[
            SongSection("intro", 8, "Atmospheric onset", 0.1),
            SongSection("verse", 8, "Light drums + melody hint", 0.3),
            SongSection("build_1", 8, "Rising energy, snare rolls", 0.55),
            SongSection("drop_1", 16, "Weapon bass drop", 1.0),
            SongSection("break_1", 8, "Vocal / melodic break", 0.2),
            SongSection("build_2", 8, "Extended rebuild", 0.6),
            SongSection("drop_2", 16, "Heavier drop variant", 1.0),
            SongSection("break_2", 4, "Short ambient break", 0.15),
            SongSection("drop_3", 12, "Final extended weapon section", 0.95),
            SongSection("outro", 8, "Gradual wind-down", 0.05),
        ],
        source_tracks=["Pineapple", "Legion", "Gassed Up"],
    )


def weapon_blitz_template() -> SongTemplate:
    """Short weapon blitz — 56 bars, relentless energy."""
    return SongTemplate(
        name="WEAPON_BLITZ",
        category="weapon",
        bpm=152.0,
        key="Em",
        sections=[
            SongSection("intro", 4, "Quick FX intro", 0.15),
            SongSection("build", 4, "Rapid build", 0.5),
            SongSection("drop_1", 16, "Weapon assault", 1.0),
            SongSection("break", 4, "Minimal break", 0.2),
            SongSection("drop_2", 16, "Second wave weapon", 1.0),
            SongSection("drop_3", 8, "Final blast", 0.95),
            SongSection("outro", 4, "Hard stop + tail", 0.05),
        ],
        source_tracks=["Scream Saver VIP", "Clockwork"],
    )


def weapon_festival_template() -> SongTemplate:
    """Festival main-stage weapon — 104 bars, extended for live sets."""
    return SongTemplate(
        name="WEAPON_FESTIVAL",
        category="weapon",
        bpm=150.0,
        key="Gm",
        sections=[
            SongSection("intro", 16, "Long atmospheric intro", 0.1),
            SongSection("build_1", 8, "Tension build", 0.4),
            SongSection("drop_1", 16, "Festival weapon drop", 1.0),
            SongSection("break_1", 8, "Crowd moment / vocal", 0.2),
            SongSection("build_2", 8, "Big rebuild", 0.55),
            SongSection("drop_2", 16, "Massive second drop", 1.0),
            SongSection("interlude", 8, "Extended melodic interlude", 0.3),
            SongSection("build_3", 4, "Final build", 0.65),
            SongSection("drop_3", 12, "Final festival weapon", 0.95),
            SongSection("outro", 8, "Wind-down for mix transition", 0.1),
        ],
        source_tracks=["On My Mind", "Open Your Eyes"],
    )


def weapon_vip_template() -> SongTemplate:
    """VIP remix weapon structure — 80 bars, reimagined drops."""
    return SongTemplate(
        name="WEAPON_VIP",
        category="weapon",
        bpm=150.0,
        key="Fm",
        sections=[
            SongSection("intro", 8, "Recognizable intro elements", 0.15),
            SongSection("build_1", 8, "Original build reimagined", 0.5),
            SongSection("drop_1", 16, "VIP drop — new bass design", 1.0),
            SongSection("break", 8, "Reworked melodic section", 0.25),
            SongSection("build_2", 4, "Quick transition build", 0.6),
            SongSection("drop_2", 16, "VIP drop variant 2", 1.0),
            SongSection("drop_3", 12, "Extended VIP finale", 0.95),
            SongSection("outro", 8, "VIP outro with callback", 0.1),
        ],
        source_tracks=["Nevermore VIP", "Other Side VIP"],
    )


# --- Emotive Templates ---------------------------------------------------

def emotive_standard_template() -> SongTemplate:
    """Standard emotive dubstep — 88 bars, melodic focus."""
    return SongTemplate(
        name="EMOTIVE_STANDARD",
        category="emotive",
        bpm=148.0,
        key="Em",
        sections=[
            SongSection("intro", 8, "Piano/pad intro", 0.1),
            SongSection("verse", 16, "Vocals + light drums", 0.35),
            SongSection("build_1", 8, "Emotional build with arp", 0.55),
            SongSection("drop_1", 16, "Melodic bass drop", 0.9),
            SongSection("break", 8, "Vocal break / piano", 0.2),
            SongSection("build_2", 8, "Second emotional build", 0.6),
            SongSection("drop_2", 16, "Full emotional drop", 1.0),
            SongSection("outro", 8, "Gentle fade / resolution", 0.1),
        ],
        source_tracks=["Nevermore", "Spacetime", "Amnesia"],
    )


def emotive_cinematic_template() -> SongTemplate:
    """Cinematic emotive — 96 bars, orchestral elements."""
    return SongTemplate(
        name="EMOTIVE_CINEMATIC",
        category="emotive",
        bpm=145.0,
        key="Em",
        sections=[
            SongSection("intro", 8, "Cinematic pad + strings feel", 0.1),
            SongSection("theme", 8, "Main melodic theme", 0.3),
            SongSection("verse", 16, "Full verse with drums", 0.4),
            SongSection("build_1", 8, "Epic build + riser", 0.6),
            SongSection("drop_1", 16, "Cinematic bass drop", 0.9),
            SongSection("interlude", 8, "Orchestral interlude", 0.25),
            SongSection("build_2", 8, "Final emotional build", 0.65),
            SongSection("drop_2", 16, "Climactic drop", 1.0),
            SongSection("outro", 8, "Resolution + fade", 0.1),
        ],
        source_tracks=["Spacetime", "Amnesia"],
    )


def emotive_journey_template() -> SongTemplate:
    """Emotive journey — 100 bars, extended narrative arc."""
    return SongTemplate(
        name="EMOTIVE_JOURNEY",
        category="emotive",
        bpm=146.0,
        key="Fm",
        sections=[
            SongSection("dawn", 8, "Ambient sunrise", 0.05),
            SongSection("awakening", 8, "Melody emerges", 0.2),
            SongSection("verse", 16, "Full vocal verse", 0.4),
            SongSection("ascent", 8, "Rising emotional build", 0.55),
            SongSection("peak_1", 16, "First emotional peak", 0.85),
            SongSection("reflection", 8, "Contemplative break", 0.2),
            SongSection("surge", 8, "Intensifying rebuild", 0.65),
            SongSection("peak_2", 16, "Ultimate emotional climax", 1.0),
            SongSection("descent", 4, "Gentle wind-down", 0.3),
            SongSection("dusk", 8, "Ambient sunset fade", 0.05),
        ],
        source_tracks=["Spacetime", "Open Your Eyes", "Amnesia"],
    )


def emotive_minimal_template() -> SongTemplate:
    """Minimal emotive — 72 bars, stripped back."""
    return SongTemplate(
        name="EMOTIVE_MINIMAL",
        category="emotive",
        bpm=148.0,
        key="Dm",
        sections=[
            SongSection("intro", 8, "Sparse intro", 0.1),
            SongSection("build", 8, "Subtle build", 0.4),
            SongSection("drop_1", 16, "Understated melodic drop", 0.8),
            SongSection("break", 8, "Minimal break", 0.2),
            SongSection("drop_2", 16, "Fuller melodic drop", 1.0),
            SongSection("fade", 16, "Extended gentle fade", 0.3),
        ],
        source_tracks=["Nevermore"],
    )


def emotive_vocal_template() -> SongTemplate:
    """Vocal-focused emotive — 88 bars, prominent vocals."""
    return SongTemplate(
        name="EMOTIVE_VOCAL",
        category="emotive",
        bpm=150.0,
        key="Em",
        sections=[
            SongSection("intro", 8, "Vocal sample intro", 0.15),
            SongSection("verse_1", 16, "Full vocal verse", 0.4),
            SongSection("pre_drop", 8, "Vocal build + riser", 0.55),
            SongSection("drop_1", 16, "Chopped vocal bass drop", 0.9),
            SongSection("verse_2", 8, "Second vocal section", 0.35),
            SongSection("build", 4, "Quick vocal build", 0.6),
            SongSection("drop_2", 16, "Final vocal drop", 1.0),
            SongSection("outro", 12, "Vocal outro", 0.15),
        ],
        source_tracks=["On My Mind", "Amnesia"],
    )


# --- Hybrid Templates ----------------------------------------------------

def hybrid_standard_template() -> SongTemplate:
    """Standard hybrid bass — 76 bars, genre-blending."""
    return SongTemplate(
        name="HYBRID_STANDARD",
        category="hybrid",
        bpm=150.0,
        key="Dm",
        sections=[
            SongSection("intro", 4, "Dark ambient intro", 0.1),
            SongSection("build_1", 8, "Glitchy build", 0.45),
            SongSection("drop_1", 16, "Hybrid bass drop", 0.95),
            SongSection("transition", 4, "Genre shift transition", 0.3),
            SongSection("drop_1b", 8, "Riddim variant drop", 0.9),
            SongSection("break", 8, "Atmospheric break", 0.2),
            SongSection("build_2", 8, "Final build", 0.6),
            SongSection("drop_2", 16, "Full hybrid assault", 1.0),
            SongSection("outro", 4, "Hard stop outro", 0.05),
        ],
        source_tracks=["Gassed Up", "Pineapple", "Clockwork"],
    )


def hybrid_glitch_template() -> SongTemplate:
    """Glitch-heavy hybrid — 80 bars."""
    return SongTemplate(
        name="HYBRID_GLITCH",
        category="hybrid",
        bpm=150.0,
        key="Gm",
        sections=[
            SongSection("intro", 8, "Glitch intro textures", 0.15),
            SongSection("build_1", 8, "Stuttered build", 0.5),
            SongSection("drop_1", 16, "Glitch bass drop", 1.0),
            SongSection("glitch_break", 4, "Glitch interlude", 0.35),
            SongSection("drop_1b", 8, "Drop continuation with glitch", 0.9),
            SongSection("break", 8, "Melodic break", 0.2),
            SongSection("build_2", 4, "Quick rebuild", 0.55),
            SongSection("drop_2", 16, "Final glitch weapon", 1.0),
            SongSection("outro", 8, "Glitch fade", 0.1),
        ],
        source_tracks=["Clockwork", "Scream Saver"],
    )


def hybrid_collab_template() -> SongTemplate:
    """Collab-style hybrid — 84 bars, back-to-back distinct styles."""
    return SongTemplate(
        name="HYBRID_COLLAB",
        category="hybrid",
        bpm=150.0,
        key="Fm",
        sections=[
            SongSection("intro", 8, "Joint intro", 0.1),
            SongSection("build_1", 8, "Artist A style build", 0.45),
            SongSection("drop_1", 16, "Artist A style drop", 0.95),
            SongSection("transition", 4, "Style transition", 0.3),
            SongSection("build_2", 4, "Artist B style build", 0.5),
            SongSection("drop_2", 16, "Artist B style drop", 1.0),
            SongSection("break", 4, "Shared melodic moment", 0.2),
            SongSection("drop_3", 16, "Combined style finale", 1.0),
            SongSection("outro", 8, "Joint outro", 0.1),
        ],
        source_tracks=["Griztronics", "On My Mind"],
    )


def hybrid_dnb_cross_template() -> SongTemplate:
    """DnB crossover hybrid — 80 bars, tempo flexibility."""
    return SongTemplate(
        name="HYBRID_DNB_CROSS",
        category="hybrid",
        bpm=150.0,
        key="Em",
        sections=[
            SongSection("intro", 8, "140-style intro", 0.1),
            SongSection("build_1", 8, "Tempo-ambiguous build", 0.4),
            SongSection("drop_1_halftime", 16, "Halftime dubstep drop", 1.0),
            SongSection("break", 8, "Break for transition", 0.2),
            SongSection("build_2", 8, "DnB-influenced build", 0.5),
            SongSection("drop_2_doubletime", 16, "Doubletime section", 0.95),
            SongSection("drop_3_halftime", 8, "Return to halftime", 0.9),
            SongSection("outro", 8, "Dual-tempo fade", 0.1),
        ],
        source_tracks=["Other Side", "Legion"],
    )


def hybrid_experimental_template() -> SongTemplate:
    """Experimental hybrid — 72 bars, unconventional structure."""
    return SongTemplate(
        name="HYBRID_EXPERIMENTAL",
        category="hybrid",
        bpm=150.0,
        key="Abm",
        sections=[
            SongSection("void", 4, "Silence + noise burst", 0.05),
            SongSection("emergence", 8, "Sound design showcase", 0.3),
            SongSection("drop_1", 12, "Unconventional drop", 0.9),
            SongSection("chaos", 4, "Controlled chaos section", 0.8),
            SongSection("drop_2", 16, "Full experimental drop", 1.0),
            SongSection("dissolution", 8, "Deconstruction", 0.4),
            SongSection("rebuild", 4, "Quick abstract rebuild", 0.5),
            SongSection("drop_3", 8, "Final experimental blast", 0.95),
            SongSection("void_return", 8, "Return to silence", 0.05),
        ],
        source_tracks=["Hollow Point"],
    )


# --- Experimental Templates ----------------------------------------------

def fibonacci_song_template() -> SongTemplate:
    """Fibonacci-structured song — bar counts follow the sequence."""
    return SongTemplate(
        name="FIBONACCI_SONG",
        category="experimental",
        bpm=150.0,
        key="Gm",
        sections=[
            SongSection("seed_1", 1, "Single bar seed", 0.05),
            SongSection("seed_2", 1, "Echo of seed", 0.1),
            SongSection("sprout", 2, "First growth", 0.2),
            SongSection("grow", 3, "Expanding idea", 0.35),
            SongSection("build", 5, "Fibonacci build", 0.55),
            SongSection("bloom", 8, "Full bloom drop", 0.9),
            SongSection("spiral", 13, "Extended spiral climax", 1.0),
            SongSection("descent", 8, "Reverse bloom", 0.4),
            SongSection("echo", 5, "Fibonacci echo", 0.2),
            SongSection("fade", 3, "Fade to origin", 0.1),
        ],
        source_tracks=[],
        description="Bar counts: 1,1,2,3,5,8,13,8,5,3 — Fibonacci palindrome",
    )


def golden_ratio_template() -> SongTemplate:
    """Golden ratio proportions — climax at phi point."""
    total = 80
    golden_bar = int(total / PHI)  # ~49
    return SongTemplate(
        name="GOLDEN_RATIO_SONG",
        category="experimental",
        bpm=150.0,
        key="Fm",
        sections=[
            SongSection("intro", 8, "Atmospheric intro", 0.1),
            SongSection("verse", 16, "Main verse section", 0.4),
            SongSection("build", 8, "Build to golden point", 0.6),
            SongSection("golden_drop", 17, "Biggest drop at phi", 1.0),
            SongSection("break", 7, "Post-climax break", 0.2),
            SongSection("drop_2", 16, "Second drop", 0.85),
            SongSection("outro", 8, "Resolution", 0.1),
        ],
        source_tracks=[],
        description=f"Climax at bar {golden_bar} (~phi point of {total} bars)",
    )


def tesseract_template() -> SongTemplate:
    """Tesseract structure — 4D-inspired symmetry."""
    return SongTemplate(
        name="TESSERACT_SONG",
        category="experimental",
        bpm=150.0,
        key="Dm",
        sections=[
            SongSection("dimension_1", 8, "First dimensional plane", 0.3),
            SongSection("fold_1", 4, "First fold", 0.5),
            SongSection("dimension_2", 8, "Second plane — rotated", 0.6),
            SongSection("fold_2", 4, "Second fold — energy surge", 0.7),
            SongSection("dimension_3", 8, "Third plane — peak", 1.0),
            SongSection("fold_3", 4, "Third fold — collapse", 0.8),
            SongSection("dimension_4", 8, "Fourth plane — transcendent", 0.95),
            SongSection("unfold", 4, "Unfold back", 0.4),
            SongSection("origin", 8, "Return to origin", 0.1),
        ],
        source_tracks=[],
        description="4D-symmetric bar structure",
    )


def sacred_geometry_template() -> SongTemplate:
    """Sacred geometry — proportions from golden angle."""
    return SongTemplate(
        name="SACRED_GEOMETRY_SONG",
        category="experimental",
        bpm=150.0,
        key="Em",
        sections=[
            SongSection("point", 2, "Single point — seed", 0.1),
            SongSection("line", 4, "Two points — line", 0.2),
            SongSection("triangle", 6, "Three points — triangle", 0.35),
            SongSection("square", 8, "Four points — stability", 0.5),
            SongSection("pentagon", 10, "Five points — golden", 0.7),
            SongSection("hexagon", 12, "Six points — harmony", 1.0),
            SongSection("circle", 8, "Return to wholeness", 0.4),
            SongSection("void", 4, "Dissolution", 0.1),
        ],
        source_tracks=[],
        description="Bar counts: 2,4,6,8,10,12,8,4 — sacred polygon series",
    )


def fractal_template() -> SongTemplate:
    """Fractal structure — self-similar at different scales."""
    return SongTemplate(
        name="FRACTAL_SONG",
        category="experimental",
        bpm=150.0,
        key="Gm",
        sections=[
            SongSection("macro_a", 16, "Large-scale A section", 0.6),
            SongSection("macro_b", 8, "Large-scale B section", 0.9),
            SongSection("micro_a", 4, "Small A — fractal echo", 0.7),
            SongSection("micro_b", 2, "Small B — compressed", 1.0),
            SongSection("nano_a", 2, "Nano A — fast echo", 0.8),
            SongSection("nano_b", 1, "Nano B — instant", 0.95),
            SongSection("expansion", 8, "Reverse expand", 0.5),
            SongSection("macro_return", 16, "Return to large scale", 0.4),
            SongSection("coda", 3, "Fractal coda", 0.1),
        ],
        source_tracks=[],
        description="A-B pattern at decreasing scales, then expansion",
    )


# --- Banks ----------------------------------------------------------------

def weapon_template_bank() -> SongTemplateBank:
    return SongTemplateBank(
        name="WEAPON_TEMPLATES",
        templates=[
            weapon_standard_template(),
            weapon_extended_template(),
            weapon_blitz_template(),
            weapon_festival_template(),
            weapon_vip_template(),
        ],
    )


def emotive_template_bank() -> SongTemplateBank:
    return SongTemplateBank(
        name="EMOTIVE_TEMPLATES",
        templates=[
            emotive_standard_template(),
            emotive_cinematic_template(),
            emotive_journey_template(),
            emotive_minimal_template(),
            emotive_vocal_template(),
        ],
    )


def hybrid_template_bank() -> SongTemplateBank:
    return SongTemplateBank(
        name="HYBRID_TEMPLATES",
        templates=[
            hybrid_standard_template(),
            hybrid_glitch_template(),
            hybrid_collab_template(),
            hybrid_dnb_cross_template(),
            hybrid_experimental_template(),
        ],
    )


def experimental_template_bank() -> SongTemplateBank:
    return SongTemplateBank(
        name="EXPERIMENTAL_TEMPLATES",
        templates=[
            fibonacci_song_template(),
            golden_ratio_template(),
            tesseract_template(),
            sacred_geometry_template(),
            fractal_template(),
        ],
    )


# --- Registry -------------------------------------------------------------

ALL_SONG_TEMPLATE_BANKS: dict[str, callable] = {
    "weapon": weapon_template_bank,
    "emotive": emotive_template_bank,
    "hybrid": hybrid_template_bank,
    "experimental": experimental_template_bank,
}


# --- Manifest -------------------------------------------------------------

def write_song_templates_manifest(output_dir: str = "output") -> dict:
    """Write song templates manifest JSON."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_SONG_TEMPLATE_BANKS.items():
        bank = gen_fn()
        templates_data = []
        for t in bank.templates:
            templates_data.append({
                "name": t.name,
                "category": t.category,
                "bpm": t.bpm,
                "key": t.key,
                "total_bars": t.total_bars,
                "duration_s": round(t.duration_s, 1),
                "golden_bar": t.golden_bar,
                "sections": len(t.sections),
                "section_names": [s.name for s in t.sections],
                "source_tracks": t.source_tracks,
            })
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "template_count": len(bank.templates),
            "templates": templates_data,
        }

    path = out / "song_templates_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_song_templates_manifest()
    total = sum(b["template_count"] for b in manifest["banks"].values())
    print(f"Song Templates: {len(manifest['banks'])} banks, {total} templates")


if __name__ == "__main__":
    main()
