"""
DUBFORGE Engine — Producer Dojo / ill.Gates Methodology Engine

Comprehensive model of ill.Gates' (Dylan Lane) production philosophy,
Producer Dojo's belt system, The Approach workflow, and signature techniques
(128s, Mudpies, Infinite Drum Rack, clip launching) — all fused with
DUBFORGE phi/Fibonacci doctrine.

ill.Gates — Canadian electronic music producer, DJ, educator
  Born: Dylan Lane, October 8, 1982, Toronto, Ontario
  AKA: The Phat Conductor (pre-2006)
  Labels: Producer Dojo, Amorphos, Alpha Pup, Muti Music
  Genres: Dubstep, Drum & Bass, Drumstep, Glitch-Hop, IDM, Breakbeat
  Notable: First Ableton DJ Templates (2006), Serum 2 wavetables (2025)
  Collabs: Bassnectar, Gucci Mane, Alanis Morissette, Liquid Stranger,
           Mr. Bill, G Jones, KJ Sawka, Minnesota, Eprom, Apashe

Producer Dojo — Founded 2016, "Making Musical Heroes"
  Platform: Online education for music producers
  System: Martial arts-inspired belt progression (White → Black Belt)
  Star students: Apashe, G Jones, Illenium, Mr. Bill, Claude Von Stroke,
                 Eprom, Morgan Page, Dr. Fresch, Ravenscoon, Grammy Winner Seal,
                 10x Grammy Nominee Damian Taylor (Björk, Arcade Fire, Prodigy)

Reference:
    https://producerdojo.com/
    https://en.wikipedia.org/wiki/Ill.Gates
    https://illgates.com/

Outputs:
    output/dojo/dojo_methodology.json
    output/dojo/dojo_belt_system.json
    output/dojo/dojo_128_rack.json
    output/dojo/dojo_session_template.json
    output/dojo/dojo_approach_workflow.json
    output/dojo/dojo_phi_integration.json
"""

from __future__ import annotations
import json
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS — DUBFORGE DOCTRINE
# ═══════════════════════════════════════════════════════════════════════════

from engine.config_loader import PHI, FIBONACCI, A4_432, A4_440, get_config_value


# ═══════════════════════════════════════════════════════════════════════════
# BELT SYSTEM — Producer Dojo martial-arts ranking progression
# ═══════════════════════════════════════════════════════════════════════════

class BeltRank(Enum):
    """
    Producer Dojo belt system — martial arts-inspired progression.
    Each belt represents a milestone in production mastery.
    Promotion requires demonstrating skills through finished tracks + community review.
    """
    WHITE = "White Belt"
    YELLOW = "Yellow Belt"
    GREEN = "Green Belt"
    BLUE = "Blue Belt"
    PURPLE = "Purple Belt"
    BROWN = "Brown Belt"
    BLACK = "Black Belt"


@dataclass
class BeltLevel:
    """A single belt level with requirements, skills, and DUBFORGE integration."""
    rank: str
    color: str
    order: int
    description: str
    core_skills: list[str]
    completion_requirements: list[str]
    tracks_required: int
    dubforge_modules: list[str]           # which DUBFORGE modules are relevant
    phi_challenge: str                     # phi/Fibonacci-specific challenge


BELT_SYSTEM: list[dict] = [
    asdict(BeltLevel(
        rank=BeltRank.WHITE.value,
        color="#FFFFFF",
        order=0,
        description="Foundation — Learn the basics of your DAW and sound design. "
                    "Build your first complete track from start to finish.",
        core_skills=[
            "DAW navigation (Ableton Live Session + Arrangement View)",
            "Basic audio concepts (frequency, amplitude, waveforms)",
            "Simple sound design (subtractive synthesis basics)",
            "Beat making fundamentals (kick, snare, hi-hat patterns)",
            "Basic arrangement (intro, build, drop, breakdown, outro)",
            "File management and project organization",
            "Exporting and bouncing audio",
        ],
        completion_requirements=[
            "Complete 1 finished track (any genre)",
            "Demonstrate basic DAW proficiency",
            "Understand signal flow: source → processing → output",
            "Join Producer Dojo Discord community",
        ],
        tracks_required=1,
        dubforge_modules=["phi_core"],
        phi_challenge="Generate your first phi-harmonic wavetable and load it into a synth.",
    )),
    asdict(BeltLevel(
        rank=BeltRank.YELLOW.value,
        color="#FFD700",
        order=1,
        description="Structure — Learn arrangement principles, basic mixing, "
                    "and develop a repeatable workflow.",
        core_skills=[
            "Song structure and arrangement (8/16/32 bar sections)",
            "Basic mixing (levels, panning, EQ fundamentals)",
            "Clip launching and Session View workflow",
            "Introduction to sampling and resampling",
            "Basic effects (reverb, delay, compression)",
            "Reference track analysis",
            "The Approach: collect → sketch → finish",
        ],
        completion_requirements=[
            "Complete 3 finished tracks",
            "Apply The Approach workflow to at least 1 track",
            "Demonstrate basic mixing skills",
            "Submit track for peer review",
        ],
        tracks_required=3,
        dubforge_modules=["phi_core", "rco"],
        phi_challenge="Arrange a track using Fibonacci bar counts (8-bar intro, "
                      "13-bar build, 21-bar drop, 8-bar breakdown, 13-bar drop 2, "
                      "5-bar outro).",
    )),
    asdict(BeltLevel(
        rank=BeltRank.GREEN.value,
        color="#00AA00",
        order=2,
        description="Sound Design — Dive deep into synthesis, sampling, and "
                    "creating original sounds. Build your sonic identity.",
        core_skills=[
            "Wavetable synthesis (Serum 2 proficiency)",
            "FM synthesis fundamentals",
            "Resampling chains (record → process → resample)",
            "The 128 Rack technique (128 samples per Sampler)",
            "Mudpies (chaotic sound collage → extract gems)",
            "Advanced effects chains and parallel processing",
            "Sound design for bass music (sub, mid, high layers)",
            "Creating and editing wavetables",
        ],
        completion_requirements=[
            "Complete 5 finished tracks (demonstrate sonic variety)",
            "Build a personal 128 Rack with original sounds",
            "Create at least 3 original wavetables",
            "Demonstrate resampling workflow",
            "Submit track for community feedback",
        ],
        tracks_required=5,
        dubforge_modules=["phi_core", "rco", "psbs", "growl_resampler", "serum2"],
        phi_challenge="Create a wavetable using phi-spaced partials, load it "
                      "into Serum 2, and design a bass patch with phi FM ratio "
                      "and phi-envelope timing.",
    )),
    asdict(BeltLevel(
        rank=BeltRank.BLUE.value,
        color="#0066FF",
        order=3,
        description="Mixing & Production — Professional-quality mixing, "
                    "advanced arrangement, and developing a signature sound.",
        core_skills=[
            "Advanced mixing (gain staging, bus processing, parallel compression)",
            "Phase-separated bass processing (PSBS methodology)",
            "Stereo imaging and mid/side processing",
            "Automation for movement and energy",
            "Advanced arrangement (golden section climax, tension/release)",
            "Sub bass management (mono below 100 Hz)",
            "Sidechain compression and ducking",
            "The Infinite Drum Rack (organized macro sample library)",
            "A/B referencing against professional mixes",
        ],
        completion_requirements=[
            "Complete 8 finished tracks (Fibonacci 8)",
            "Demonstrate professional-level mixing on at least 2 tracks",
            "Apply PSBS bass methodology",
            "Show before/after mixing improvements",
            "Receive positive peer reviews",
        ],
        tracks_required=8,
        dubforge_modules=["phi_core", "rco", "psbs", "sb_analyzer",
                         "growl_resampler", "serum2", "ableton_live"],
        phi_challenge="Mix a track using phi-ratio crossover frequencies for "
                      "bass layer separation (55, 89, 144, 233, 377 Hz) and "
                      "place the climax at the golden section point.",
    )),
    asdict(BeltLevel(
        rank=BeltRank.PURPLE.value,
        color="#8800CC",
        order=4,
        description="Performance & Identity — Live performance skills, "
                    "DJ integration, artistic identity, and building an audience.",
        core_skills=[
            "Clip-based live performance (Session View)",
            "DJ + production hybrid sets",
            "Controller mapping (APC40, Push, Launchpad)",
            "Performance template design",
            "Transition design (risers, sweeps, drops)",
            "Crowd energy management (RCO methodology)",
            "Branding and visual identity",
            "Social media presence and content creation",
            "Networking in the bass music community",
        ],
        completion_requirements=[
            "Complete 13 finished tracks (Fibonacci 13)",
            "Build a live performance template",
            "Perform at least 1 live set (online or in-person)",
            "Establish online presence (SoundCloud/YouTube/social)",
            "Demonstrate crowd energy curve management",
        ],
        tracks_required=13,
        dubforge_modules=["phi_core", "rco", "psbs", "trance_arp",
                         "serum2", "ableton_live", "chord_progression"],
        phi_challenge="Design a live performance template with Fibonacci scene "
                      "counts and phi-timed transitions. Map macros to controller "
                      "using golden ratio response curves.",
    )),
    asdict(BeltLevel(
        rank=BeltRank.BROWN.value,
        color="#8B4513",
        order=5,
        description="Mastery & Teaching — Master-level production, mentoring "
                    "others, label-ready output, and industry connections.",
        core_skills=[
            "Mastering fundamentals (LUFS, limiting, true peak)",
            "Advanced sound design (spectral, granular, custom Max/M4L)",
            "Teaching and mentoring (explaining concepts clearly)",
            "Label submission preparation",
            "Collaboration workflow (stems, project exchange)",
            "Advanced music theory for electronic music",
            "Genre-fluid production (crossing bass music sub-genres)",
            "VIP system (revising and improving released tracks)",
            "Building a release catalog",
        ],
        completion_requirements=[
            "Complete 21 finished tracks (Fibonacci 21)",
            "Mentor at least 1 lower-belt student",
            "Submit tracks to labels",
            "Demonstrate mastering proficiency",
            "Build a cohesive EP or album concept",
        ],
        tracks_required=21,
        dubforge_modules=["phi_core", "rco", "psbs", "sb_analyzer",
                         "trance_arp", "growl_resampler", "serum2",
                         "ableton_live", "chord_progression"],
        phi_challenge="Produce a phi-structured EP: track count is a Fibonacci "
                      "number, track order follows golden spiral energy curve, "
                      "all bass patches use phi-ratio FM and PSBS crossovers.",
    )),
    asdict(BeltLevel(
        rank=BeltRank.BLACK.value,
        color="#000000",
        order=6,
        description="Professional — Released artist with professional workflow, "
                    "industry presence, and ability to create at the highest level. "
                    "Black Belt is not an endpoint — it's where mastery truly begins.",
        core_skills=[
            "Professional-quality output at every stage",
            "Rapid creation workflow (The Approach at full speed)",
            "Advanced live performance (improvisation, mashups)",
            "Industry navigation (labels, publishing, sync licensing)",
            "Complete artistic vision and sonic identity",
            "Community leadership and mentorship",
            "Hardware integration and hybrid workflows",
            "Cross-platform production (DAW-agnostic skills)",
            "Revenue generation from music",
        ],
        completion_requirements=[
            "Complete 34+ finished tracks (Fibonacci 34)",
            "Released on at least 1 recognized label",
            "Demonstrated professional quality consistently",
            "Active performer (live or DJ)",
            "Mentored multiple students",
            "Recognized contribution to the community",
        ],
        tracks_required=34,
        dubforge_modules=["ALL MODULES"],
        phi_challenge="Full DUBFORGE mastery — every module integrated into a "
                      "cohesive production workflow. Build a fractal arrangement "
                      "where micro (grain) mirrors macro (song structure).",
    )),
]


# ═══════════════════════════════════════════════════════════════════════════
# THE APPROACH — ill.Gates' production methodology
# ═══════════════════════════════════════════════════════════════════════════

class ApproachPhase(Enum):
    """
    The Approach — ill.Gates' methodology for rapid, effective music creation.
    Core philosophy: FINISH MUSIC. Completion > perfection.
    Work in focused passes rather than trying to do everything at once.
    """
    COLLECT = "Collect"
    SKETCH = "Sketch"
    ARRANGE = "Arrange"
    SOUND_DESIGN = "Sound Design"
    MIX = "Mix"
    MASTER = "Master"
    RELEASE = "Release"


@dataclass
class ApproachStep:
    """One phase of The Approach workflow."""
    phase: str
    order: int
    description: str
    duration_guideline: str
    key_actions: list[str]
    tools: list[str]
    dubforge_integration: str
    phi_principle: str


THE_APPROACH: list[dict] = [
    asdict(ApproachStep(
        phase=ApproachPhase.COLLECT.value,
        order=0,
        description="Gather raw material — samples, ideas, loops, recordings, "
                    "inspirations. Fill your palette before you paint. "
                    "ill.Gates: 'Get a bunch of flammable things in a pile.'",
        duration_guideline="Ongoing / 1-2 hours dedicated session",
        key_actions=[
            "Record sound design experiments (resampling sessions)",
            "Collect samples and organize into categories",
            "Build 128 Racks from collected material",
            "Capture melodic/harmonic ideas (MIDI or audio)",
            "Analyze reference tracks for inspiration",
            "Archive interesting textures, one-shots, loops",
            "Tag and color-code everything for fast retrieval",
        ],
        tools=["Ableton Sampler (128 Rack)", "Audio recorder", "Sample manager",
               "Reference library", "DUBFORGE SB Analyzer"],
        dubforge_integration="Use SB Analyzer to study reference tracks. "
                            "Build phi-harmonic wavetables during collect phase. "
                            "Capture Fibonacci-timed arp patterns with Trance Arp.",
        phi_principle="Fibonacci Collection: gather samples in Fibonacci quantities "
                      "(8 kicks, 13 snares, 21 textures, 34 one-shots). "
                      "Creates natural variety without overwhelm.",
    )),
    asdict(ApproachStep(
        phase=ApproachPhase.SKETCH.value,
        order=1,
        description="Rapidly create rough ideas — don't polish, just capture. "
                    "Speed > quality at this stage. Get the core idea down in "
                    "15-30 minutes. ill.Gates: 'Strike matches until one lights.'",
        duration_guideline="15-30 minutes per sketch (strict time limit)",
        key_actions=[
            "Launch Session View and start jamming",
            "Trigger 128 Rack elements against a beat",
            "Record clip improvisations",
            "Capture the core energy/vibe of the idea",
            "Don't EQ, don't mix, don't process — just capture",
            "Use Mudpie technique if stuck (chaos → extraction)",
            "Save and name the sketch immediately",
            "Rate sketches: fire (🔥), maybe (⭐), compost (♻️)",
        ],
        tools=["Ableton Session View", "128 Rack", "MIDI controller",
               "Mudpie technique", "Clip recorder"],
        dubforge_integration="Sketch over DUBFORGE chord progressions. "
                            "Use RCO energy curve as target shape. "
                            "Trigger phi-arp patterns as sketch foundations.",
        phi_principle="Phi Timer: sketch for exactly 1/phi of an hour "
                      "(≈37.1 min) then stop. Forces decisive action. "
                      "Golden ratio of creation:evaluation = 0.618:0.382.",
    )),
    asdict(ApproachStep(
        phase=ApproachPhase.ARRANGE.value,
        order=2,
        description="Structure the sketch into a full arrangement. "
                    "Move from Session View → Arrangement View. "
                    "Focus on the story arc and energy flow.",
        duration_guideline="1-2 hours",
        key_actions=[
            "Select best sketch and duplicate project as 'arrangement' version",
            "Define song sections (intro, build, drop, break, drop 2, outro)",
            "Set section lengths (use Fibonacci bar counts)",
            "Record Session View performance into Arrangement",
            "Add transitions (risers, sweeps, reverse crashes)",
            "Define the climax point (golden section)",
            "Create automation lanes for energy curve",
            "Add variation between sections (A/B/C patterns)",
        ],
        tools=["Ableton Arrangement View", "DUBFORGE RCO", "Automation",
               "Markers/Locators", "Scene recording"],
        dubforge_integration="Use RCO energy curve to map arrangement. "
                            "Set climax at golden section point (total_bars / phi). "
                            "Fibonacci bar counts for all sections. "
                            "Ableton Live engine templates for track layout.",
        phi_principle="Golden Section Arrangement: climax at bar = total / phi. "
                      "For a 128-bar track: climax at bar 79 (128/phi ≈ 79.1). "
                      "Section lengths: 8, 13, 21, 13, 21, 8 bars = 84 bars → drop at bar 42.",
    )),
    asdict(ApproachStep(
        phase=ApproachPhase.SOUND_DESIGN.value,
        order=3,
        description="Polish and refine sounds. Replace placeholder sounds with "
                    "custom-designed originals. This is a SEPARATE pass — not "
                    "done during sketching.",
        duration_guideline="2-4 hours (can be multiple sessions)",
        key_actions=[
            "Design custom bass patches (sub, mid, high layers)",
            "Create wavetables for Serum 2",
            "Resample and process for unique textures",
            "Design transition FX and impacts",
            "Build custom drum sounds or select from library",
            "Layer and process melodic elements",
            "Create sound variations for different sections",
            "Apply PSBS methodology for bass separation",
        ],
        tools=["Serum 2", "DUBFORGE PHI CORE", "Growl Resampler",
               "PSBS", "Effects chains", "Sampler instruments"],
        dubforge_integration="Generate phi-harmonic wavetables with PHI CORE. "
                            "Design bass with PSBS layers at phi crossovers. "
                            "Use Serum 2 engine presets as starting points. "
                            "Growl resampler for mid-bass character.",
        phi_principle="Phi layering: each bass layer's fundamental is the previous "
                      "layer's fundamental × phi. Sub=55Hz, Low=89Hz, Mid=144Hz, "
                      "High=233Hz, Click=377Hz. Self-similar at every frequency scale.",
    )),
    asdict(ApproachStep(
        phase=ApproachPhase.MIX.value,
        order=4,
        description="Mix as a SEPARATE pass. Don't mix while creating. "
                    "Focus on balance, clarity, and impact. "
                    "Reference against professional tracks.",
        duration_guideline="2-4 hours",
        key_actions=[
            "Gain staging (set all faders, then balance)",
            "EQ for clarity (carve space for each element)",
            "Compression for dynamics control",
            "Sidechain sub to kick",
            "Stereo imaging (mono below ~100 Hz, wide above)",
            "Bus processing (drum bus, bass bus, melodic bus)",
            "Automation refinement (volume rides, filter sweeps)",
            "A/B reference against target mixes",
            "Check on multiple systems (headphones, monitors, phone)",
        ],
        tools=["EQ Eight", "Compressor", "Utility (mid/side)",
               "Reference plugin", "Spectrum analyzer",
               "DUBFORGE PSBS (crossover guide)"],
        dubforge_integration="Use PSBS crossover frequencies for EQ band isolation. "
                            "Apply phi-ratio compression settings. "
                            "SB Analyzer reference data for target loudness/balance. "
                            "Phi-curve automation shapes.",
        phi_principle="Phi dynamics: compression ratio ≈ phi:1 (1.618:1) for natural "
                      "response. Attack/release in phi-ratio ms. "
                      "EQ bands at phi-spaced frequencies.",
    )),
    asdict(ApproachStep(
        phase=ApproachPhase.MASTER.value,
        order=5,
        description="Final polish. Subtle processing for loudness, translation, "
                    "and cohesion. If possible, have a professional master — "
                    "but learn the basics yourself.",
        duration_guideline="30-60 minutes (or send to mastering engineer)",
        key_actions=[
            "Apply gentle EQ (broad strokes only)",
            "Multi-band compression for tonal balance",
            "Stereo enhancement (subtle)",
            "Limiting for target loudness (-14 to -6 LUFS depending on genre)",
            "Dithering for bit-depth reduction",
            "Final A/B check against references",
            "Export multiple formats (WAV master, MP3 preview)",
            "Loudness metering (LUFS, true peak, dynamic range)",
        ],
        tools=["Limiter", "OTT / Multiband Comp", "EQ",
               "Metering plugin", "Dither"],
        dubforge_integration="Ableton Live engine master chain as starting point. "
                            "OTT at phi crossover frequencies. "
                            "Target: -8 LUFS for dubstep (loud but dynamic).",
        phi_principle="Phi limiting: set ceiling at -1/phi dBTP ≈ -0.618 dBTP. "
                      "Dynamic range target: phi × 5 ≈ 8.09 LU. "
                      "Mastering EQ boost at golden frequencies.",
    )),
    asdict(ApproachStep(
        phase=ApproachPhase.RELEASE.value,
        order=6,
        description="Get your music into the world. Release > perfection. "
                    "A finished track released is worth 100 unfinished ideas. "
                    "ill.Gates: 'Ship it.'",
        duration_guideline="1-2 hours (metadata, artwork, distribution)",
        key_actions=[
            "Prepare metadata (title, artist, genre, BPM, key)",
            "Create or commission artwork",
            "Write track description / story",
            "Upload to distribution platform",
            "Share on social media with context",
            "Submit to labels, playlist curators, blogs",
            "Archive project files (stems, session, presets)",
            "Retrospective: what worked, what to improve",
            "Start collecting for the NEXT track",
        ],
        tools=["Distribution platform", "Social media", "DAW export",
               "File archiver", "DUBFORGE .dubforge_memory"],
        dubforge_integration="Save session to .dubforge_memory with full metadata. "
                            "Track completion count toward belt progression. "
                            "Archive phi-parameters used for future reference.",
        phi_principle="Release cadence: Fibonacci schedule — release tracks at "
                      "Fibonacci week intervals (week 1, 1, 2, 3, 5, 8, 13...). "
                      "Golden ratio of creating:promoting = 0.618:0.382.",
    )),
]


# ═══════════════════════════════════════════════════════════════════════════
# SIGNATURE TECHNIQUES — ill.Gates innovations
# ═══════════════════════════════════════════════════════════════════════════

class TechniqueType(Enum):
    """Categories of ill.Gates production techniques."""
    SAMPLING = "Sampling"
    SOUND_DESIGN = "Sound Design"
    WORKFLOW = "Workflow"
    PERFORMANCE = "Performance"
    ARRANGEMENT = "Arrangement"
    MIXING = "Mixing"


@dataclass
class DojoTechnique:
    """A documented ill.Gates / Producer Dojo technique."""
    name: str
    year_introduced: int
    category: str
    description: str
    steps: list[str]
    tools_required: list[str]
    dubforge_integration: str
    phi_enhancement: str


DOJO_TECHNIQUES: list[dict] = [
    asdict(DojoTechnique(
        name="The 128 Rack",
        year_introduced=2010,
        category=TechniqueType.SAMPLING.value,
        description="Load 128 samples into a single Ableton Sampler instrument, "
                    "one sample per MIDI note (C-2 to G8 = 128 notes). "
                    "Creates an instant sound palette accessible from any MIDI "
                    "controller. Pioneered by ill.Gates as an evolution of "
                    "traditional drum rack workflows.",
        steps=[
            "1. Create a new Sampler instrument in Ableton Live",
            "2. Set the Zone tab to show the Key Zone editor",
            "3. Drag 128 samples into the sampler — each gets its own key zone",
            "4. Set each zone to a single MIDI note (C-2=0, C#-2=1, ... G8=127)",
            "5. Set all zones to one-shot mode (no loop, play full sample)",
            "6. Optionally set velocity layers for dynamic response",
            "7. Organize by category: kicks (C-2–B-1), snares (C-1–B0), "
               "hats (C1–B1), bass (C2–B2), FX (C3–B3), etc.",
            "8. Save as preset for instant recall in any project",
            "9. Trigger from MIDI controller (APC40, Push, Launchpad)",
            "10. Record triggering into Session View clips for performance",
        ],
        tools_required=["Ableton Sampler", "128 curated samples",
                       "MIDI controller (recommended)"],
        dubforge_integration="Build a DUBFORGE 128 Rack with phi-organized zones: "
                            "Fibonacci note ranges per category. "
                            "SUB samples: 8 zones (Fib), MID: 13, HIGH: 21, FX: 34, "
                            "Drums: 34, Melodic: 8, Atmos: 5, Utility: 5 = 128 total.",
        phi_enhancement="Zone count per category follows Fibonacci distribution. "
                        "Velocity curves shaped by phi response (vel^(1/phi)).",
    )),
    asdict(DojoTechnique(
        name="Mudpies",
        year_introduced=2008,
        category=TechniqueType.SOUND_DESIGN.value,
        description="Intentional sonic chaos as a creative technique. "
                    "Layer, mash, and collide sounds together WITHOUT concern "
                    "for quality or musicality. Record the chaos, then mine "
                    "the recording for golden moments — unexpected textures, "
                    "rhythms, and timbres that could never be designed intentionally. "
                    "Featured in Ableton's 'One Thing' series with ill.Gates.",
        steps=[
            "1. Gather 5-13 diverse sound sources (samples, synths, recordings)",
            "2. Stack them on separate tracks with NO mixing consideration",
            "3. Add random/extreme effects (heavy distortion, extreme reverb, etc.)",
            "4. Press play and start mangling — resample in real time",
            "5. Twist knobs randomly, automate chaotically",
            "6. Record the output as a single stereo audio file (5-15 minutes)",
            "7. Listen back and mark 'golden moments' (interesting textures)",
            "8. Chop the golden moments into individual samples",
            "9. Load best samples into a 128 Rack or Drum Rack",
            "10. Use these unique textures in your actual production",
        ],
        tools_required=["Ableton Live", "Multiple sound sources",
                       "Audio effects", "Audio recorder"],
        dubforge_integration="Generate phi-harmonic chaos: use multiple PHI CORE "
                            "wavetables at different speeds + growl resampler output "
                            "as Mudpie sources. The phi-ratio relationships create "
                            "structured chaos — fractal noise.",
        phi_enhancement="Golden Mudpie: layer phi-ratio sources (freq ratios of "
                        "1:phi:phi²:phi³). The resulting interference patterns "
                        "produce FRACTAL noise — self-similar at every time scale. "
                        "Mine for textures that embody natural chaos.",
    )),
    asdict(DojoTechnique(
        name="The Infinite Drum Rack",
        year_introduced=2014,
        category=TechniqueType.WORKFLOW.value,
        description="A scalable drum rack template that grows with your library. "
                    "Uses nested drum racks (racks within racks) to organize "
                    "unlimited samples into a hierarchical, instantly-searchable "
                    "structure. Each pad is a gateway to a category.",
        steps=[
            "1. Create a master Drum Rack with 16 pads visible",
            "2. Each pad holds a nested Drum Rack for a CATEGORY",
            "3. Categories: Kicks, Snares, Claps, Hi-hats, Cymbals, Percussion, "
               "Bass hits, FX, Risers, Downlifters, Impacts, Fills, "
               "Vox chops, Foley, Textures, Utility",
            "4. Within each category rack, add sample chains",
            "5. Use macro knobs to select between samples (Chain Selector)",
            "6. Map Chain Selector to a knob for live browsing",
            "7. Color-code categories for visual clarity",
            "8. Save as default template or master preset",
            "9. Add new samples to the appropriate category over time",
            "10. The rack GROWS with your career — never starts from scratch",
        ],
        tools_required=["Ableton Drum Rack", "Organized sample library"],
        dubforge_integration="Pre-populate with DUBFORGE-generated sounds: "
                            "phi wavetable one-shots, growl resampler hits, "
                            "Fibonacci-timed drum patterns as fills. "
                            "Category count = 16 (2^4, near Fibonacci 13).",
        phi_enhancement="Golden Chain Selection: map chain selector so that "
                        "phi-position (0.618 of range) selects the 'favorite' "
                        "sample. Organize chains by golden ratio quality ranking.",
    )),
    asdict(DojoTechnique(
        name="Clip Launching (Session View Performance)",
        year_introduced=2006,
        category=TechniqueType.PERFORMANCE.value,
        description="ill.Gates pioneered Ableton Live clip-launching performance "
                    "in 2006, creating the world's first Ableton DJ Templates. "
                    "Session View as a live instrument — triggers, layers, and "
                    "transitions all happen via clip launching on a grid controller.",
        steps=[
            "1. Design a Session View template with organized tracks",
            "2. Create clips for each section element (intro, verse, drop, etc.)",
            "3. Use Scenes for pre-programmed section changes",
            "4. Map clips to MIDI controller grid (APC40, Push, Launchpad)",
            "5. Set Follow Actions for automated clip progression",
            "6. Use Dummy Clips for FX automation (filter sweeps, etc.)",
            "7. Set launch quantization (1 bar for safety, 1/4 for flexibility)",
            "8. Create transition clips (risers, drops, silence)",
            "9. Practice performing — the template IS your instrument",
            "10. Record performance into Arrangement for studio capture",
        ],
        tools_required=[
            "Ableton Live Session View",
            "Grid MIDI controller (APC40, Push, Launchpad)",
            "Audio interface",
        ],
        dubforge_integration="Use Ableton Live engine session templates as "
                            "clip launch starting points. PSBS track layout "
                            "for bass layers. Fibonacci scene structure. "
                            "Phi-timed follow actions.",
        phi_enhancement="Golden Grid: organize clips so scene transitions "
                        "follow Fibonacci timing (1, 1, 2, 3, 5, 8 bar scenes). "
                        "Follow action chance at phi ratio (61.8% next, 38.2% random). "
                        "Launch quantization: 1 bar (golden ratio of predictability).",
    )),
    asdict(DojoTechnique(
        name="Resampling Chains",
        year_introduced=2010,
        category=TechniqueType.SOUND_DESIGN.value,
        description="Multi-stage resampling for deep sound design. "
                    "Create → record → process → record → process. "
                    "Each pass adds character, complexity, and uniqueness. "
                    "The first pass is raw material; by pass 3-5, you have "
                    "something completely original.",
        steps=[
            "1. Start with a raw sound (synth patch, sample, recording)",
            "2. Record the output as audio (freeze + flatten or resample)",
            "3. Process the recording (pitch shift, time stretch, effects)",
            "4. Record the processed version as NEW audio",
            "5. Repeat steps 3-4 for 3-5 passes",
            "6. Each pass: different processing (distortion → granular → reverb)",
            "7. Save each generation for comparison",
            "8. Use the final generation as your sound, or blend generations",
            "9. Create wavetable from resampled material",
            "10. Document processing chain for reproducibility",
        ],
        tools_required=["Ableton Live (freeze/flatten)", "Effects chains",
                       "Serum 2 (wavetable import)", "Audio editor"],
        dubforge_integration="Use Growl Resampler engine as starting point. "
                            "Import final resampled audio into Serum 2 wavetable. "
                            "PHI CORE wavetable as resample source for fractal "
                            "self-similarity through resampling generations.",
        phi_enhancement="Phi-pass resampling: each generation processed at "
                        "phi-ratio intensity (pass 1 at 0.382, pass 2 at 0.618, "
                        "pass 3 at 1.0, pass 4 at 0.618, pass 5 at 0.382). "
                        "Golden arch of processing intensity.",
    )),
    asdict(DojoTechnique(
        name="Color Coding System",
        year_introduced=2012,
        category=TechniqueType.WORKFLOW.value,
        description="Consistent color assignment for tracks, clips, and scenes. "
                    "Instant visual identification of element types. "
                    "Reduces cognitive load — your eyes know what's where "
                    "before your brain processes the name.",
        steps=[
            "1. Define your color code (consistent across ALL projects)",
            "2. Recommended: Drums=Gray, Bass=Red, Chords=Blue, "
               "Lead=Yellow, Pads=Purple, FX=Green, Vox=Orange",
            "3. Apply colors to tracks immediately when creating them",
            "4. Color clips to match their section (drop=red, intro=blue, etc.)",
            "5. Color scenes by energy level (cool→hot, blue→red)",
            "6. Use same colors in file management (folder colors)",
            "7. Train yourself to recognize colors = categories instantly",
        ],
        tools_required=["Ableton Live (color palette)", "Consistent discipline"],
        dubforge_integration="DUBFORGE track colors aligned with PSBS layers: "
                            "SUB=Dark Red, LOW=Red, MID=Orange, HIGH=Yellow, "
                            "CLICK=White. Matches frequency → color mapping.",
        phi_enhancement="Golden color progression: order track colors by "
                        "wavelength (frequency), mirroring how audio frequencies "
                        "map to visual spectrum. PHI ratio between hue values "
                        "for aesthetic harmony.",
    )),
    asdict(DojoTechnique(
        name="VIP System (Version Improvement Protocol)",
        year_introduced=2015,
        category=TechniqueType.WORKFLOW.value,
        description="Systematically improve released tracks by creating VIP "
                    "(Variation in Production) versions. Not remixes — evolutions. "
                    "Each VIP addresses weaknesses in the original while "
                    "preserving its identity. Subtronics' FRACTALS → Antifractals "
                    "is a masterclass in this technique.",
        steps=[
            "1. Release the original track (don't wait for perfection)",
            "2. After release, note listener feedback and your own observations",
            "3. Identify top 3 improvements (mix, arrangement, sound design)",
            "4. Duplicate the project as '[Track Name] VIP'",
            "5. Address ONE major improvement per VIP",
            "6. Preserve the core identity (same key, similar energy)",
            "7. Add new elements that evolved since the original (new sounds, skills)",
            "8. A/B the VIP against original — should be objectively better",
            "9. Release the VIP as a separate track",
            "10. Document what changed in .dubforge_memory for learning",
        ],
        tools_required=["Original project file", "A/B comparison",
                       "DUBFORGE VIP Delta analyzer"],
        dubforge_integration="Use SB Analyzer's VIP Delta system to quantify "
                            "changes between versions. Duration delta, structural "
                            "changes, timbral evolution. 24 Subtronics VIP pairs "
                            "already in the reference corpus.",
        phi_enhancement="Golden VIP rule: change exactly 1/phi (≈61.8%) of the "
                        "elements, keep 38.2% identical. This creates evolution "
                        "while preserving recognition — the phi ratio of "
                        "novelty to familiarity.",
    )),
    asdict(DojoTechnique(
        name="Performance Template Design",
        year_introduced=2006,
        category=TechniqueType.PERFORMANCE.value,
        description="Designing Ableton Live templates optimized for live "
                    "performance. ill.Gates' templates for APC40, MPD32, and "
                    "other controllers became legendary in the bass music scene "
                    "and helped establish clip-launching as a performance standard.",
        steps=[
            "1. Define your set structure (how many songs, transitions)",
            "2. Create track layout matching your controller grid",
            "3. Assign tracks to controller columns/channels",
            "4. Create consistent clip slot positions across tracks",
            "5. Design Scene launches for instant full-band changes",
            "6. Map effects to controller knobs (filter, delay, reverb)",
            "7. Set up dummy clips for automated FX",
            "8. Create recovery clips (safe clips that always work)",
            "9. Include transition elements on dedicated track",
            "10. Test extensively before performing live",
        ],
        tools_required=[
            "Ableton Live", "MIDI controller",
            "Performance practice time",
        ],
        dubforge_integration="Use Ableton Live engine session templates. "
                            "PSBS track layout maps perfectly to controller columns. "
                            "Fibonacci scene structure for set progression. "
                            "Max for Live control scripts for automation.",
        phi_enhancement="Golden set structure: total scenes = Fibonacci number. "
                        "Climax scene at position total/phi. "
                        "Controller macro response: phi curve for natural feel. "
                        "Transition lengths in Fibonacci beats.",
    )),
]


# ═══════════════════════════════════════════════════════════════════════════
# 128 RACK GENERATOR — Fibonacci-optimized zone distribution
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RackZone:
    """A single zone in the 128 Rack sampler."""
    note_start: int       # MIDI note number (0-127)
    note_end: int
    category: str
    sample_slot: int      # index within category
    velocity_low: int = 0
    velocity_high: int = 127
    label: str = ""


@dataclass
class RackCategory:
    """A category within the 128 Rack."""
    name: str
    zone_count: int       # Fibonacci-based allocation
    note_range_start: int
    note_range_end: int
    color: str
    description: str


def build_128_rack() -> dict:
    """
    Build a DUBFORGE-doctrine 128 Rack with Fibonacci zone distribution.
    Total zones = 128 (full MIDI range).
    Category sizes follow Fibonacci sequence where possible.
    """
    categories = [
        RackCategory("SUB BASS",       8,   0,   7, "#8B0000",
                     "Sub-bass hits and sustained notes (20-89 Hz)"),
        RackCategory("LOW BASS",       8,   8,  15, "#CC0000",
                     "Low bass hits and stabs (89-144 Hz)"),
        RackCategory("MID BASS",      13,  16,  28, "#FF4400",
                     "Mid-bass growls, yells, vowels (144-233 Hz)"),
        RackCategory("HIGH BASS",      8,  29,  36, "#FF8800",
                     "High bass fizz, harmonics, screech (233-610 Hz)"),
        RackCategory("KICKS",         13,  37,  49, "#444444",
                     "Kick drums — acoustic to electronic to layered"),
        RackCategory("SNARES/CLAPS",  13,  50,  62, "#666666",
                     "Snares, claps, rimshots — organic to synthetic"),
        RackCategory("HI-HATS",        8,  63,  70, "#888888",
                     "Closed hats, open hats, shakers, rides"),
        RackCategory("PERCUSSION",    13,  71,  83, "#AAAAAA",
                     "Toms, congas, bongos, timpani, misc percussion"),
        RackCategory("FX / RISERS",   13,  84,  96, "#00CC00",
                     "Risers, downlifters, sweeps, impacts, booms"),
        RackCategory("MELODIC",        8,  97, 104, "#0066FF",
                     "Melodic one-shots, stabs, chords, plucks"),
        RackCategory("ATMOSPHERE",     8, 105, 112, "#8800CC",
                     "Ambient textures, pads, drones, foley"),
        RackCategory("VOCAL",          5, 113, 117, "#FF6600",
                     "Vocal chops, spoken word, vox FX"),
        RackCategory("TRANSITIONS",    5, 118, 122, "#00AAAA",
                     "Fills, rolls, reverse crashes, tape stops"),
        RackCategory("UTILITY",        5, 123, 127, "#CCCCCC",
                     "Noise, silence, click, metronome, test tones"),
    ]

    # Verify total = 128
    total = sum(c.zone_count for c in categories)
    assert total == 128, f"Expected 128 zones, got {total}"

    # Build zone map
    zones = []
    for cat in categories:
        for i in range(cat.zone_count):
            note = cat.note_range_start + i
            zones.append(asdict(RackZone(
                note_start=note,
                note_end=note,
                category=cat.name,
                sample_slot=i,
                label=f"{cat.name} #{i+1}",
            )))

    # Fibonacci category sizes present
    fib_sizes = [n for n in [5, 8, 13] if any(c.zone_count == n for c in categories)]

    return {
        "name": "DUBFORGE 128 Rack",
        "inspired_by": "ill.Gates' 128 Rack technique (2010)",
        "total_zones": 128,
        "categories": [asdict(c) for c in categories],
        "zones": zones,
        "fibonacci_distribution": {
            "sizes_used": fib_sizes,
            "explanation": "Category sizes follow Fibonacci numbers (5, 8, 13) "
                          "for natural distribution — not equal, not random, "
                          "but proportioned by the golden ratio's sequence.",
        },
        "dubforge_preload": {
            "sub_bass": ["DUBFORGE_PHI_CORE (layered one-shots, pitched to sub range)"],
            "mid_bass": ["DUBFORGE_GROWL_SAW hits", "DUBFORGE_GROWL_FM hits"],
            "melodic": ["PHI CORE v2 WOOK pitched samples"],
            "fx": ["Phi-harmonic risers", "Fibonacci-timed sweeps"],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# DOJO SESSION TEMPLATE — Full Ableton Live session layout
# ═══════════════════════════════════════════════════════════════════════════

def build_dojo_session_template() -> dict:
    """
    Build a Dojo-style Ableton Session View template.
    Combines ill.Gates' clip launching methodology with DUBFORGE PSBS architecture.
    """
    tracks = [
        {
            "index": 0, "name": "128 RACK", "type": "midi",
            "color": "#00CC00", "width": 1,
            "instrument": "Sampler (128 Rack)",
            "description": "ill.Gates 128 Rack — full sample palette on one track",
            "clips": [
                {"slot": 0, "name": "COLLECT", "color": "#00CC00",
                 "description": "Recording slot for live sample capture"},
            ],
        },
        {
            "index": 1, "name": "SUB", "type": "midi",
            "color": "#8B0000", "width": 1,
            "instrument": "Serum 2 (DUBFORGE Fractal Sub)",
            "description": "Sub bass (20-89 Hz) — clean sine, mono, glued to kick",
            "clips": [
                {"slot": 0, "name": "SUB DROP A", "color": "#CC0000"},
                {"slot": 1, "name": "SUB DROP B", "color": "#CC0000"},
                {"slot": 2, "name": "SUB HOLD", "color": "#880000"},
            ],
        },
        {
            "index": 2, "name": "MID GROWL", "type": "midi",
            "color": "#FF4400", "width": 1,
            "instrument": "Serum 2 (DUBFORGE Phi Growl)",
            "description": "Mid-bass growl (144-233 Hz) — FM/wavetable, heavy processing",
            "clips": [
                {"slot": 0, "name": "GROWL A", "color": "#FF4400"},
                {"slot": 1, "name": "GROWL B", "color": "#FF6600"},
                {"slot": 2, "name": "GROWL TEAR", "color": "#FF2200"},
                {"slot": 3, "name": "GROWL FM", "color": "#FF8800"},
            ],
        },
        {
            "index": 3, "name": "SCREECH", "type": "midi",
            "color": "#FFAA00", "width": 1,
            "instrument": "Serum 2 (DUBFORGE Fibonacci FM Screech)",
            "description": "Screech/yell/high bass (233-610 Hz)",
            "clips": [
                {"slot": 0, "name": "SCREECH A", "color": "#FFAA00"},
                {"slot": 1, "name": "SCREECH B", "color": "#FFCC00"},
            ],
        },
        {
            "index": 4, "name": "REESE", "type": "midi",
            "color": "#CC4400", "width": 1,
            "instrument": "Serum 2 (DUBFORGE Golden Reese)",
            "description": "Reese bass — detuned unison, dark and heavy",
            "clips": [
                {"slot": 0, "name": "REESE DROP", "color": "#CC4400"},
                {"slot": 1, "name": "REESE SWELL", "color": "#AA3300"},
            ],
        },
        {
            "index": 5, "name": "CHORDS", "type": "midi",
            "color": "#0066FF", "width": 1,
            "instrument": "Serum 2 (DUBFORGE Phi Pad)",
            "description": "Chord stabs and pads — emotional content",
            "clips": [
                {"slot": 0, "name": "CHORD STAB", "color": "#0066FF"},
                {"slot": 1, "name": "PAD SWELL", "color": "#0044CC"},
                {"slot": 2, "name": "CHORD PROG", "color": "#2288FF"},
            ],
        },
        {
            "index": 6, "name": "LEAD", "type": "midi",
            "color": "#FFD700", "width": 1,
            "instrument": "Serum 2 (DUBFORGE Weapon)",
            "description": "Lead melody — cuts through the mix",
            "clips": [
                {"slot": 0, "name": "LEAD A", "color": "#FFD700"},
                {"slot": 1, "name": "LEAD B", "color": "#FFEE00"},
            ],
        },
        {
            "index": 7, "name": "ARP", "type": "midi",
            "color": "#00DDDD", "width": 1,
            "instrument": "Serum 2 + DUBFORGE Fibonacci Arp",
            "description": "Fibonacci-timed arp patterns",
            "clips": [
                {"slot": 0, "name": "ARP FIB", "color": "#00DDDD"},
                {"slot": 1, "name": "ARP PHI", "color": "#00BBBB"},
            ],
        },
        {
            "index": 8, "name": "DRUMS", "type": "midi",
            "color": "#666666", "width": 1,
            "instrument": "Drum Rack (Infinite Drum Rack)",
            "description": "Drum patterns — kick, snare, hats from Infinite Drum Rack",
            "clips": [
                {"slot": 0, "name": "BEAT DROP", "color": "#666666"},
                {"slot": 1, "name": "BEAT HALF", "color": "#888888"},
                {"slot": 2, "name": "BEAT FILL", "color": "#AAAAAA"},
                {"slot": 3, "name": "BEAT BREAK", "color": "#444444"},
            ],
        },
        {
            "index": 9, "name": "FX/TRANS", "type": "audio",
            "color": "#00CC00", "width": 1,
            "instrument": "Audio (FX samples)",
            "description": "Transition FX — risers, impacts, sweeps",
            "clips": [
                {"slot": 0, "name": "RISER 8BAR", "color": "#00FF00"},
                {"slot": 1, "name": "IMPACT", "color": "#00CC00"},
                {"slot": 2, "name": "SWEEP DN", "color": "#009900"},
                {"slot": 3, "name": "TAPE STOP", "color": "#006600"},
            ],
        },
        {
            "index": 10, "name": "MUDPIE", "type": "audio",
            "color": "#8B4513", "width": 1,
            "instrument": "Audio (Mudpie captures)",
            "description": "Mudpie technique — chaos captures and golden moments",
            "clips": [
                {"slot": 0, "name": "MUDPIE 1", "color": "#8B4513"},
                {"slot": 1, "name": "GOLDEN 1", "color": "#FFD700"},
                {"slot": 2, "name": "GOLDEN 2", "color": "#FFD700"},
            ],
        },
    ]

    scenes = [
        {"index": 0, "name": "INTRO (8 bars)", "bars": 8, "color": "#0066FF",
         "energy": 0.2, "description": "Gentle introduction — pads, atmosphere"},
        {"index": 1, "name": "BUILD (13 bars)", "bars": 13, "color": "#00AAFF",
         "energy": 0.5, "description": "Rising energy — add drums, arp, filter open"},
        {"index": 2, "name": "DROP A (21 bars)", "bars": 21, "color": "#FF0000",
         "energy": 1.0, "description": "Full energy — all bass layers, heavy drums"},
        {"index": 3, "name": "BREAK (8 bars)", "bars": 8, "color": "#8800CC",
         "energy": 0.3, "description": "Breakdown — chords, lead, atmosphere"},
        {"index": 4, "name": "BUILD 2 (8 bars)", "bars": 8, "color": "#00AAFF",
         "energy": 0.6, "description": "Second build — tension, anticipation"},
        {"index": 5, "name": "DROP B (21 bars)", "bars": 21, "color": "#FF0000",
         "energy": 1.0, "description": "Second drop — different bass sounds"},
        {"index": 6, "name": "OUTRO (5 bars)", "bars": 5, "color": "#333333",
         "energy": 0.1, "description": "Wind down — fade, filter close"},
    ]

    # Golden section calculation
    total_bars = sum(s["bars"] for s in scenes)
    golden_bar = round(total_bars / PHI, 1)

    return {
        "name": "DUBFORGE x DOJO Live Template",
        "inspired_by": [
            "ill.Gates clip launching system (2006)",
            "ill.Gates APC40 templates",
            "Producer Dojo performance methodology",
            "DUBFORGE PSBS bass architecture",
        ],
        "tracks": tracks,
        "track_count": len(tracks),
        "scenes": scenes,
        "scene_count": len(scenes),
        "total_bars": total_bars,
        "golden_section_bar": golden_bar,
        "bar_counts_fibonacci": [s["bars"] for s in scenes],
        "bpm": 150,
        "key": "Am",
        "tuning": A4_432,
        "launch_quantization": "1 Bar",
        "follow_actions": {
            "description": "Phi-weighted follow action probabilities",
            "next_scene": round(1.0 / PHI, 4),         # 0.618
            "random_scene": round(1.0 - 1.0 / PHI, 4), # 0.382
        },
        "controller_mapping": {
            "recommended": ["Akai APC40 mk2", "Ableton Push 3",
                           "Novation Launchpad X"],
            "column_assignment": "Each track → one controller column",
            "knob_assignment": {
                "knob_1": "Filter Cutoff (phi-curve response)",
                "knob_2": "Reverb Send (phi decay)",
                "knob_3": "Delay Send (Fibonacci timing)",
                "knob_4": "Macro 1: PHI MORPH",
                "knob_5": "Macro 2: FM DEPTH",
                "knob_6": "Macro 3: SUB WEIGHT",
                "knob_7": "Macro 4: GRIT",
                "knob_8": "Master Volume",
            },
        },
        "color_code": {
            "system": "ill.Gates color coding methodology",
            "mapping": {
                "Sub Bass": "#8B0000",
                "Mid Bass": "#FF4400",
                "High Bass": "#FFAA00",
                "Drums": "#666666",
                "Chords": "#0066FF",
                "Lead": "#FFD700",
                "FX": "#00CC00",
                "Atmosphere": "#8800CC",
                "Mudpie": "#8B4513",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# ILL.GATES ARTIST PROFILE
# ═══════════════════════════════════════════════════════════════════════════

ARTIST_PROFILE = {
    "name": "ill.Gates",
    "real_name": "Dylan Lane",
    "born": "October 8, 1982",
    "origin": "Toronto, Ontario, Canada",
    "aka": ["The Phat Conductor"],
    "genres": ["Dubstep", "Drum & Bass", "Drumstep", "Glitch-Hop",
               "IDM", "Breakbeat", "Electronica", "Downtempo"],
    "labels": ["Producer Dojo", "Amorphos", "Alpha Pup Records",
               "Muti Music", "Impossible Records", "False Profit Records"],
    "website": "https://illgates.com/",
    "discography": {
        "albums": [
            {"title": "Autopirate", "year": 2008},
            {"title": "The ill.Methodology series", "year": 2011},
            {"title": "Terminally Ill", "year": 2017},
            {"title": "Departures", "year": 2018},
            {"title": "The Arrival", "year": 2021},
            {"title": "Bent", "year": 2022},
        ],
        "eps": [
            {"title": "Irma Vep EP", "year": 2008},
            {"title": "Sweatshop EP", "year": 2008},
            {"title": "Church of Bass EP", "year": 2012},
            {"title": "Bounce EP", "year": 2016},
            {"title": "More Tea EP", "year": 2017},
            {"title": "Smoke EP", "year": 2022},
            {"title": "Racks EP", "year": 2022},
            {"title": "Boom EP", "year": 2023},
            {"title": "The Muse EP", "year": 2023},
            {"title": "Toxic EP", "year": 2023},
            {"title": "Wave EP", "year": 2023},
        ],
        "notable_collabs": [
            "Bassnectar — Expanded, Take You Down",
            "Gucci Mane — Polar Bear (Remix)",
            "Alanis Morissette — Emergency (Remix)",
            "Liquid Stranger — More Tea (Remix)",
            "Mr. Bill — Cabbatsu",
            "G Jones", "KJ Sawka — Unsung Heroes EP",
            "Minnesota — Thunderdome (Remix)",
            "Eprom", "Apashe", "Masia One",
        ],
        "special": [
            "Disney Star Wars Galaxy's Edge (2019) — as Sentient 7 and the Clankers (w/ Zain Effendi)",
        ],
    },
    "teaching_history": [
        "Ableton Education Summit",
        "Berklee College of Music",
        "N.Y.U.",
        "A.C.C.", "S.A.E.",
        "Ableton 'One Thing' (YouTube)",
        "Andrew Huang '4 Producers Flip The Same Sample'",
    ],
    "innovations": {
        "2006": "First Ableton Live DJ Templates (as The Phat Conductor)",
        "2008": "Mudpies technique — chaotic sound collage",
        "2010": "128 Rack — 128 samples in one Sampler instrument",
        "2012": "ill.Methodology Workshop",
        "2013": "APC40 Performance Template (via Splice)",
        "2014": "The Infinite Drum Rack",
        "2016": "Founded Producer Dojo",
        "2025": "128s-style wavetables shipped with Serum 2",
    },
    "stats": {
        "plays": "58 Million+",
        "songs": "275+",
        "shows": "1000+ on 5 continents",
        "tracks_2022": 56,
        "grammy_collabs": "Songs with winners of 9 Grammys",
    },
    "star_students": [
        "Apashe", "Beats Antique", "Chee", "Claude Von Stroke",
        "Dr. Fresch", "EOTO", "Eprom", "G Jones", "Illenium",
        "Minnesota", "Morgan Page", "Mr. Bill", "Phibes",
        "Rabbit In the Moon", "Ravenscoon",
        "Seal (Grammy Winner)",
        "Damian Taylor (10x Grammy Nominee — Björk, Arcade Fire, Killers, Prodigy)",
    ],
    "influences": [
        "Skinny Puppy", "Nine Inch Nails", "Aphex Twin",
        "Hip Hop", "Jamaican Dub", "Burning Man culture",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCER DOJO PLATFORM
# ═══════════════════════════════════════════════════════════════════════════

DOJO_PLATFORM = {
    "name": "Producer Dojo",
    "founded": 2016,
    "founder": "ill.Gates (Dylan Lane)",
    "tagline": "Making Musical Heroes Since 2016",
    "website": "https://producerdojo.com/",
    "community": "Discord-based",
    "label": "Producer Dojo Records",
    "philosophy": {
        "core_belief": "Anyone can make professional music with the right "
                       "training, community, and methodology.",
        "approach": "The Approach — Collect → Sketch → Arrange → Sound Design "
                   "→ Mix → Master → Release. Finish music. Ship it.",
        "belt_system": "Martial arts-inspired progression from White → Black Belt. "
                      "Promotion through finished tracks and community review.",
        "emphasis": [
            "Completion over perfection",
            "Community support and accountability",
            "Workflow optimization",
            "Sound design as identity",
            "Performance as part of production",
        ],
    },
    "curriculum_areas": [
        "Sound Design (Serum 2, synthesis, resampling)",
        "Mixing & Mastering (gain staging, loudness, translation)",
        "Music Theory for Electronic Music (scales, chords, harmony)",
        "Arrangement & Song Structure (energy curves, sections)",
        "Workflow & Creativity (The Approach, time management)",
        "Performance (DJing, clip launching, controller mapping)",
        "Business & Marketing (release strategy, social media, branding)",
    ],
    "signature_techniques": [t["name"] for t in DOJO_TECHNIQUES],
    "dubforge_alignment": {
        "shared_principles": [
            "Fractal self-similarity (ill.Gates' Mudpie chaos → DUBFORGE phi chaos)",
            "Fibonacci structure (Dojo belt track counts → DUBFORGE bar counts)",
            "Golden ratio aesthetics (both seek mathematical beauty in sound)",
            "Resampling as evolution (both use multi-pass resampling chains)",
            "VIP system (Subtronics VIP analysis in DUBFORGE SB Analyzer)",
            "Ableton Live expertise (both deeply integrated with Ableton)",
            "Serum 2 proficiency (ill.Gates ships wavetables with Serum 2)",
            "Bass music genre focus (dubstep, drum & bass, glitch-hop)",
        ],
        "philosophy_bridge": "ill.Gates' 'start a fire' metaphor aligns with "
                            "DUBFORGE's fractal doctrine: both seek organic, "
                            "self-organizing complexity from simple starting principles. "
                            "Phi IS the match — once the golden ratio ignites in "
                            "a wavetable, the fire of fractal harmonics burns on its own.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PHI x DOJO INTEGRATION — Doctrine-enhanced Dojo methodology
# ═══════════════════════════════════════════════════════════════════════════

def phi_belt_progression() -> dict:
    """
    Calculate phi-scaled belt progression metrics.
    Track requirements follow Fibonacci: 1, 3, 5, 8, 13, 21, 34.
    Hours to mastery follow phi scaling.
    """
    belt_tracks = [1, 3, 5, 8, 13, 21, 34]
    belt_names = [b.value for b in BeltRank]
    cumulative_tracks = []
    running = 0
    for t in belt_tracks:
        running += t
        cumulative_tracks.append(running)

    # Hours estimate: each belt takes phi × previous belt's hours
    base_hours = 50  # White Belt ~ 50 hours
    belt_hours = [base_hours]
    for i in range(1, len(belt_names)):
        belt_hours.append(round(belt_hours[-1] * PHI, 1))

    return {
        "belt_progression": [
            {
                "belt": name,
                "tracks_required": tracks,
                "tracks_cumulative": cum,
                "estimated_hours": hours,
                "phi_ratio_to_next": round(PHI, 4) if i < len(belt_names) - 1 else None,
            }
            for i, (name, tracks, cum, hours) in enumerate(
                zip(belt_names, belt_tracks, cumulative_tracks, belt_hours)
            )
        ],
        "total_tracks_to_black_belt": cumulative_tracks[-1],
        "total_estimated_hours": round(sum(belt_hours), 1),
        "fibonacci_track_counts": belt_tracks,
        "phi_hour_scaling": f"Each belt = previous × phi ({PHI:.4f})",
        "grand_total_tracks": f"85 tracks to mastery (sum of Fib: {sum(belt_tracks)})",
    }


def phi_approach_timing(total_hours: float = 8.0) -> dict:
    """
    Distribute The Approach phases using phi-ratio time allocation.
    Total session time divided by golden proportions.
    """
    phases = [p["phase"] for p in THE_APPROACH]
    # Allocate time by golden ratio segments
    # Collect:Sketch:Arrange:SoundDesign:Mix:Master:Release
    # Weight by inverse Fibonacci importance
    weights = [1, 2, 3, 5, 5, 2, 1]  # Fibonacci-ish weights
    total_weight = sum(weights)
    allocations = [round(total_hours * w / total_weight, 2) for w in weights]

    return {
        "total_session_hours": total_hours,
        "phase_allocation": {
            phase: f"{hours}h" for phase, hours in zip(phases, allocations)
        },
        "fibonacci_weights": weights,
        "golden_checkpoint": f"At {total_hours / PHI:.1f}h, you should be "
                            f"finishing Sound Design and entering Mix phase.",
        "rule": "If you hit the golden checkpoint and haven't started mixing, "
                "SIMPLIFY the sound design and move forward. Finish > perfect.",
    }


def phi_mudpie_recipe(num_sources: int = 8) -> dict:
    """
    Generate a phi-structured Mudpie recipe.
    Source selection and layering governed by golden ratio.
    """
    return {
        "technique": "Golden Mudpie",
        "source_count": num_sources,
        "sources": [
            {"index": i, "type": "DUBFORGE" if i % 2 == 0 else "EXTERNAL",
             "pitch_ratio": round(PHI ** (i - num_sources // 2), 4),
             "volume": round(1.0 / (PHI ** abs(i - num_sources // 2)), 4)}
            for i in range(num_sources)
        ],
        "fx_chain": [
            {"slot": 0, "effect": "Distortion (drive at 0.618)"},
            {"slot": 1, "effect": "Reverb (decay at phi seconds ≈ 1.618s)"},
            {"slot": 2, "effect": "Granular delay (grain size Fibonacci ms)"},
            {"slot": 3, "effect": "Frequency shifter (phi Hz offset)"},
            {"slot": 4, "effect": "Bitcrusher (at Fibonacci bit depths: 8, 5, 3)"},
        ],
        "recording_duration": f"{round(PHI * 5, 1)} minutes (golden duration)",
        "golden_moments_expected": f"~{round(num_sources / PHI)} per session",
        "instruction": "Layer ALL sources simultaneously with effects. "
                      "Randomize parameters for phi duration. Record output. "
                      "Mine for golden moments (1/phi ≈ 38% of recording is useful).",
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Generate all Dojo engine outputs
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all Producer Dojo / ill.Gates engine JSON outputs."""
    out = Path("output/dojo")
    out.mkdir(parents=True, exist_ok=True)

    # Load belt thresholds from memory config if available
    _belt_cfg = get_config_value(
        "memory_v1", "growth", "belt_progression", default=None)

    # 1) Full methodology reference
    method_path = out / "dojo_methodology.json"
    methodology = {
        "artist_profile": ARTIST_PROFILE,
        "platform": DOJO_PLATFORM,
        "techniques_count": len(DOJO_TECHNIQUES),
        "techniques": DOJO_TECHNIQUES,
    }
    with open(method_path, "w") as f:
        json.dump(methodology, f, indent=2)
    print(f"  ✓ Methodology reference  → {method_path}")

    # 2) Belt system
    belt_path = out / "dojo_belt_system.json"
    belt_data = {
        "belt_levels": BELT_SYSTEM,
        "progression_metrics": phi_belt_progression(),
    }
    with open(belt_path, "w") as f:
        json.dump(belt_data, f, indent=2)
    print(f"  ✓ Belt system            → {belt_path}")

    # 3) 128 Rack
    rack_path = out / "dojo_128_rack.json"
    rack_data = build_128_rack()
    with open(rack_path, "w") as f:
        json.dump(rack_data, f, indent=2)
    print(f"  ✓ 128 Rack ({rack_data['total_zones']} zones)   → {rack_path}")

    # 4) Session template
    session_path = out / "dojo_session_template.json"
    session_data = build_dojo_session_template()
    with open(session_path, "w") as f:
        json.dump(session_data, f, indent=2)
    print(f"  ✓ Session template       → {session_path}")

    # 5) The Approach workflow
    approach_path = out / "dojo_approach_workflow.json"
    approach_data = {
        "the_approach": THE_APPROACH,
        "phase_count": len(THE_APPROACH),
        "timing_8h_session": phi_approach_timing(8.0),
        "timing_4h_session": phi_approach_timing(4.0),
        "mudpie_recipe": phi_mudpie_recipe(8),
    }
    with open(approach_path, "w") as f:
        json.dump(approach_data, f, indent=2)
    print(f"  ✓ Approach workflow       → {approach_path}")

    # 6) Phi integration summary
    phi_path = out / "dojo_phi_integration.json"
    phi_data = {
        "phi_belt_progression": phi_belt_progression(),
        "phi_approach_timing": phi_approach_timing(),
        "phi_mudpie": phi_mudpie_recipe(),
        "phi_128_rack": {
            "fibonacci_zone_sizes": [5, 8, 13],
            "total_zones": 128,
            "category_count": 14,
        },
        "phi_session_template": {
            "fibonacci_bar_counts": [8, 13, 21, 8, 8, 21, 5],
            "total_bars": sum([8, 13, 21, 8, 8, 21, 5]),
            "golden_section_bar": round(sum([8, 13, 21, 8, 8, 21, 5]) / PHI, 1),
            "follow_action_probability": round(1.0 / PHI, 4),
        },
        "doctrine_bridge": DOJO_PLATFORM["dubforge_alignment"],
    }
    with open(phi_path, "w") as f:
        json.dump(phi_data, f, indent=2)
    print(f"  ✓ Phi integration        → {phi_path}")

    # Stats
    print()
    print(f"  Producer Dojo Engine Stats:")
    print(f"    Belt levels:          {len(BELT_SYSTEM)}")
    print(f"    Approach phases:      {len(THE_APPROACH)}")
    print(f"    Techniques:           {len(DOJO_TECHNIQUES)}")
    print(f"    128 Rack categories:  {len(rack_data['categories'])}")
    print(f"    Session tracks:       {session_data['track_count']}")
    print(f"    Session scenes:       {session_data['scene_count']}")
    print(f"    Tracks to Black Belt: {phi_belt_progression()['total_tracks_to_black_belt']}")
    print(f"    ill.Gates albums:     {len(ARTIST_PROFILE['discography']['albums'])}")
    print(f"    ill.Gates EPs:        {len(ARTIST_PROFILE['discography']['eps'])}")
    print(f"    Star students:        {len(ARTIST_PROFILE['star_students'])}")


if __name__ == "__main__":
    main()
