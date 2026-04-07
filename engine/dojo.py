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
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS — DUBFORGE DOCTRINE
# ═══════════════════════════════════════════════════════════════════════════
from engine.config_loader import A4_432, PHI, get_config_value

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
        "plays": "60 Million+",
        "songs": "300+",
        "shows": "1000+ on 5 continents",
        "tracks_2022": 58,
        "grammy_collabs": "Songs with winners of 9 Grammys",
        "official_credits": ["Star Wars", "GTA5", "Microsoft"],
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
# CREATIVE PHILOSOPHY — ill.Gates' production wisdom (blog essays)
# ═══════════════════════════════════════════════════════════════════════════

CREATIVE_PHILOSOPHY: dict = {
    "the_14_minute_hit": {
        "title": "The 14-Minute Hit",
        "source": "producerdojo.com/blog/the-14-minute-hit (March 8 2026)",
        "core_thesis": "Sia wrote 'Diamonds' in 14 minutes. Speed is proof of "
                       "depth, not laziness. First instinct beats labored revision.",
        "principles": [
            {
                "name": "First Instinct Supremacy",
                "description": "Your first musical thought is usually the truest. "
                               "Revision often waters down the original spark. "
                               "Capture first instincts IMMEDIATELY.",
            },
            {
                "name": "Flow State Neuroscience",
                "description": "During flow states, the dorsolateral prefrontal cortex "
                               "(self-monitoring/judgment) DEACTIVATES while the medial "
                               "prefrontal cortex (self-expression) lights up. "
                               "Don't fight this — surrender to it.",
            },
            {
                "name": "Decision Fatigue Kills Creativity",
                "description": "Every preset auditioned, every knob twisted indecisively "
                               "burns creative fuel. Commit to sounds early. "
                               "Decision fatigue is the silent killer of great music.",
            },
            {
                "name": "Volume Is The Teacher",
                "description": "Write MORE. Not better. More. The producers who grow "
                               "fastest finish tracks constantly and relentlessly. "
                               "Volume is the teacher. Speed is how you let it teach.",
            },
            {
                "name": "Separate Creation From Revision",
                "description": "NEVER mix while creating. NEVER create while mixing. "
                               "These are different cognitive modes. Switching between "
                               "them destroys both.",
            },
            {
                "name": "Timer-Based Sessions",
                "description": "Use a hard timer: 60-90 minutes for creation. "
                               "When the timer ends, STOP. Commit or shelve. "
                               "The constraint IS the craft.",
            },
            {
                "name": "Finished > Perfect",
                "description": "A finished track with rough edges teaches you more "
                               "than an unfinished track with a pristine mix bus. "
                               "Ship it. Learn. Repeat.",
            },
        ],
        "sia_quote": "I'm pretty successful because I'm really productive, "
                     "not necessarily that I'm a great songwriter.",
        "phi_integration": {
            "phi_timer": f"1/phi of 90 min ≈ {round(90 / PHI, 1)} min creation, "
                        f"{round(90 - 90 / PHI, 1)} min evaluation",
            "fibonacci_session_blocks": "8 min warm-up, 13 min sketch, 21 min build, "
                                        "13 min polish, 8 min export = 63 min total",
            "golden_decision_rule": "After Fibonacci count of alternatives (3 presets, "
                                    "5 samples, 8 options max), STOP and commit.",
        },
    },
    "three_brain_model": {
        "title": "The Three-Brain Model of Creativity",
        "source": "ill.Gates / Producer Dojo methodology",
        "core_thesis": "The human creative psyche has three modes that must "
                       "NEVER be allowed to overlap during a session. The Child "
                       "creates, the Architect structures, the Critic polishes. "
                       "Letting the Critic into the room while the Child is "
                       "playing kills the flow state instantly.",
        "brains": [
            {
                "name": "The Child",
                "function": "Pure play, weird noises, no rules, experimentation",
                "when": "Phase 1 — Jamming / Sound Design / Sketching",
                "traits": ["Curiosity", "Fearlessness", "Spontaneity", "Joy"],
                "enemies": ["EQ tweaking", "A/B comparisons", "Self-doubt",
                            "Overthinking mix balance"],
            },
            {
                "name": "The Architect",
                "function": "Structure, arrangement, mathematical logic, song form",
                "when": "Phase 2 — Arranging the song, section planning",
                "traits": ["Logic", "Pattern recognition", "Energy mapping",
                           "Narrative arc"],
                "enemies": ["Sound design tangents", "Adding new elements",
                            "Rewriting instead of structuring"],
            },
            {
                "name": "The Critic",
                "function": "Mixing, EQ, cleanup, deletion, polish",
                "when": "Phase 3 — Mixing / Mastering / Final polish",
                "traits": ["Precision", "Objectivity", "Subtraction",
                           "Technical skill"],
                "enemies": ["Adding new ideas", "Rewriting melodies",
                            "Starting over instead of finishing"],
            },
        ],
        "golden_rule": "NEVER let the Critic into the room while the Child "
                       "is playing. If you start EQing a snare while writing "
                       "a melody, the Child gets bored and leaves — and your "
                       "flow state dies.",
        "phi_integration": {
            "session_split": f"Child: {round(1/PHI, 3)} of session (61.8%), "
                            f"Architect: {round(1/PHI**2, 3)} (23.6%), "
                            f"Critic: {round(1/PHI**3, 3)} (14.6%)",
            "golden_transition": "Transition between brains at phi checkpoints "
                                "of total session time — not abruptly.",
            "brain_warmup": "Each brain needs Fibonacci minutes to activate: "
                           "Child=3min, Architect=5min, Critic=8min warmup.",
        },
    },
    "dont_resist_whats_easy": {
        "title": "Don't Resist What's Easy",
        "source": "producerdojo.com/blog/don-t-resist-what-s-easy (February 10 2026)",
        "core_thesis": "The urge to reject the easy path is a trick of ego and "
                       "vanity. 9/10 times complexity does more harm than good. "
                       "Your audience cares about one thing: the FEELING.",
        "principles": [
            {
                "name": "Ego Trap Recognition",
                "description": "The desire to make everything 'special' or 'complex' "
                               "is often insecurity disguised as ambition. Recognize "
                               "when you're adding complexity for YOU, not the listener.",
            },
            {
                "name": "Direct Route First",
                "description": "Take the most direct route to the objective. "
                               "You can ALWAYS make the song more complex later. "
                               "It's really hard to unmake a mess.",
            },
            {
                "name": "Feeling Over Technique",
                "description": "Your audience primarily cares about one thing: FEELING. "
                               "Unnecessary complexity makes your track feel like it "
                               "comes from insecurity.",
            },
            {
                "name": "Style Is Confidence",
                "description": "Style is confidence in self-expression. "
                               "Don't let the imagined opinions of others hold you back.",
            },
        ],
        "rules": [
            "Not EVERY technique needs to be crazy.",
            "Not EVERY sound needs to be crazy.",
            "Not EVERY song needs to be crazy.",
            "Sometimes let the song write itself.",
        ],
        "phi_integration": "Golden simplicity ratio: for every phi complex element, "
                          "include phi² simple elements. Balance: 38.2% complex, "
                          "61.8% straightforward = natural, confident feel.",
    },
    "ninja_sounds": {
        "title": "Start Using Ninja Sounds",
        "source": "producerdojo.com/blog/start-using-ninja-sounds (January 21 2026)",
        "core_thesis": "Most sounds in a mix should AVOID listener attention. "
                       "Only the 'singer' should demand focus. Everything else "
                       "is the 'band' — supportive, invisible, essential.",
        "singer_band_metaphor": {
            "singer": "The ONE element that demands attention (lead, vocal, "
                      "main bass in the drop). Only 1 singer at a time.",
            "band": "Everything else — drums, pads, sub, FX, atmosphere. "
                    "Must be felt, not heard individually. Ninja sounds.",
        },
        "attention_thieves": [
            "Louder than the rest (competing for headroom)",
            "Brighter than the rest (stealing high-frequency attention)",
            "Dryer than the rest (standing out of the reverb space)",
            "Wider than the rest (dominating stereo field)",
            "Dominating the pain zone (2-4.5 kHz region)",
        ],
        "ninja_rules": [
            "If a mixing decision doesn't serve the focus direction, don't add it.",
            "High-pass the 'band' to make room for the 'singer'.",
            "Roll off 2-4.5 kHz on supporting elements — that's the 'singer' zone.",
            "Use reverb to push elements BACK in the mix (not everything dry).",
            "Mono your sub elements — they don't need width.",
            "Keep ninja sounds WARM (low-pass slightly) — warmth = invisible.",
        ],
        "pain_zone": {
            "range_hz": "2000-4500 Hz",
            "description": "The region of maximum ear sensitivity. Human hearing "
                          "evolved to be most sensitive here (speech intelligibility). "
                          "Any element dominating this zone STEALS attention.",
            "phi_frequency_center": f"{round(2000 * PHI, 1)} Hz "
                                    f"(≈{round(2000 * PHI)} Hz — the golden attention apex)",
        },
        "phi_integration": {
            "ninja_volume_rule": f"Ninja sounds at 1/phi (≈0.618) of singer volume.",
            "ninja_brightness_rule": f"Ninja high shelf cut at phi × 2kHz ≈ {round(2000 * PHI)} Hz.",
            "ninja_width_rule": "Ninja sounds at 0.382 stereo width (tight center), "
                               "singer at 0.618 width (naturally wider).",
        },
    },
    "stock_device_mastery": {
        "title": "Invest in Stock! ...Devices.",
        "source": "producerdojo.com/blog/invest-in-stock-devices (January 15 2026)",
        "core_thesis": "ill.Gates champions Ableton stock devices over third-party "
                       "plugins. Master the tools you already have before buying more. "
                       "The fundamentals are a bottomless well.",
        "devices": "See STOCK_DEVICE_MASTERY dict below for full catalog.",
    },
    "low_pass_mastery": {
        "title": "5 Killer Low Pass Tips",
        "source": "producerdojo.com/blog/5-ways-you-re-not-using-low-pass-filter-enough "
                  "(January 21 2026)",
        "core_thesis": "Low pass filter is far from the fanciest effect, but it's "
                       "one of the most powerful. The fundamentals are a bottomless "
                       "well — you can NEVER be too geeked out on them.",
        "techniques": "See LOW_PASS_TECHNIQUES list below for full breakdown.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# STOCK DEVICE MASTERY — ill.Gates' Ableton native device recommendations
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StockDevice:
    """An Ableton stock device recommended by ill.Gates."""
    name: str
    category: str          # INSTRUMENT / AUDIO_EFFECT / MIDI_EFFECT / M4L
    ill_gates_rank: int    # 1 = most essential
    description: str
    ill_gates_tip: str
    dubforge_use: str
    phi_enhancement: str


STOCK_DEVICE_MASTERY: list[dict] = [
    asdict(StockDevice(
        name="Sampler",
        category="INSTRUMENT",
        ill_gates_rank=1,
        description="ill.Gates' #1 instrument in Ableton. The engine behind "
                    "the 128 Rack and the Infinite Drum Rack. Multisampling, "
                    "zone editing, modulation matrix, round-robin — limitless.",
        ill_gates_tip="The 128 Rack technique puts an entire career of sounds "
                      "at your fingertips. One Sampler, 128 zones, infinite power.",
        dubforge_use="Build phi-organized 128 Racks with Fibonacci zone "
                     "distribution. Load DUBFORGE wavetable one-shots as zones.",
        phi_enhancement="Velocity curve: vel^(1/phi) for natural dynamic response. "
                       "Zone crossfade width: phi ratio between adjacent zones.",
    )),
    asdict(StockDevice(
        name="Operator",
        category="INSTRUMENT",
        ill_gates_rank=2,
        description="The timeless FM synth. Four operators, multiple algorithms. "
                    "Can produce everything from clean sine waves to screaming "
                    "digital chaos.",
        ill_gates_tip="Operator is timeless. People chase Serum but sleep on "
                      "Operator. It's been making hits for 20 years.",
        dubforge_use="FM ratio 1:phi between carriers and modulators. "
                     "Use as basis for resampling chains.",
        phi_enhancement="Carrier:Modulator ratio = 1:phi (1.618) for inharmonic "
                       "bass timbres. Operator feedback at 0.618.",
    )),
    asdict(StockDevice(
        name="Wavetable",
        category="INSTRUMENT",
        ill_gates_rank=3,
        description="Ableton's built-in wavetable synth. Great starting point "
                    "before reaching for Serum 2. Modern, capable, and FREE "
                    "with Ableton Suite.",
        ill_gates_tip="Between Wavetable, Meld, and Drift you have three "
                      "world-class synths that most people never even open.",
        dubforge_use="Import DUBFORGE PHI CORE wavetables directly. "
                     "Use as lightweight alternative to Serum 2.",
        phi_enhancement="Wavetable position modulated at Fibonacci LFO rates. "
                       "Sub oscillator at 1/phi of main oscillator level.",
    )),
    asdict(StockDevice(
        name="Meld",
        category="INSTRUMENT",
        ill_gates_rank=4,
        description="Hybrid poly synth combining multiple synthesis methods. "
                    "Modern, expressive, surprising — a sleeping giant.",
        ill_gates_tip="Meld is one of those synths people don't realize they "
                      "should be using. Open it. Be surprised.",
        dubforge_use="Layered pad generation for atmosphere tracks. "
                     "Alternative to Serum 2 Phi Pad preset.",
        phi_enhancement="Macro depth modulation at phi curve response. "
                       "Layer detune at phi cents intervals.",
    )),
    asdict(StockDevice(
        name="Drift",
        category="INSTRUMENT",
        ill_gates_rank=5,
        description="Analog-modeled subtractive synth with built-in character. "
                    "The 'imperfect' flavor that digital synths often lack.",
        ill_gates_tip="Drift has that warm, imperfect analog feel that just "
                      "sits in a mix perfectly without trying.",
        dubforge_use="Sub bass alternative with natural drift behavior. "
                     "Resampling source for organic textures.",
        phi_enhancement="Oscillator drift rate modulated at phi frequency. "
                       "Filter envelope: phi ratio attack:decay:release.",
    )),
    asdict(StockDevice(
        name="Saturator (Digital Clip mode)",
        category="AUDIO_EFFECT",
        ill_gates_rank=6,
        description="Ableton's Saturator in Digital Clip mode is a secret "
                    "weapon. Clean, hard clipping that adds harmonics without "
                    "muddiness.",
        ill_gates_tip="Digital Clip mode beats 9 out of 10 third-party "
                      "clipper plugins. It's right there in Saturator. Use it.",
        dubforge_use="Post-sub-bass harmonic enhancement. "
                     "Clipping stage in growl resampler chain.",
        phi_enhancement="Drive amount at phi-derived values: "
                       "0.618 (subtle), 1.0 (medium), 1.618 (aggressive).",
    )),
    asdict(StockDevice(
        name="OTT (Multiband Dynamics preset)",
        category="AUDIO_EFFECT",
        ill_gates_rank=7,
        description="The OTT preset in Multiband Dynamics. Legendary "
                    "upward+downward compression. Used on everything.",
        ill_gates_tip="OTT still slaps. It's been the secret weapon "
                      "for years and it's NOT going anywhere.",
        dubforge_use="Master chain compression. Bass group processing. "
                     "Crossovers at PSBS phi frequencies.",
        phi_enhancement="Crossover frequencies at phi ladder: "
                       f"{round(55 * PHI**0)} / {round(55 * PHI**1)} / "
                       f"{round(55 * PHI**2)} Hz.",
    )),
    asdict(StockDevice(
        name="Erosion",
        category="AUDIO_EFFECT",
        ill_gates_rank=8,
        description="Frequency-dependent distortion / noise modulation. "
                    "Adds fizz, grit, and texture to any signal.",
        ill_gates_tip="Erosion defined whole genres of bass music. "
                      "That fizzy, buzzy quality people chase with expensive "
                      "plugins? Erosion has been doing it for free.",
        dubforge_use="Mid-bass harmonic enhancement on PSBS MID layer. "
                     "Growl character in resampling chains.",
        phi_enhancement="Erosion frequency at phi multiples of fundamental. "
                       "Amount: 0.618 for subtle grit, phi for heavy.",
    )),
    asdict(StockDevice(
        name="Roar",
        category="AUDIO_EFFECT",
        ill_gates_rank=9,
        description="Multi-stage distortion with routing flexibility. "
                    "Serial, parallel, mid/side, and multiband modes.",
        ill_gates_tip="Roar is the new kid on the block but it's already "
                      "essential. The routing options are insane.",
        dubforge_use="Heavy distortion stage for mid-bass growl design. "
                     "Multiband mode with PSBS crossover frequencies.",
        phi_enhancement="Multiband crossovers at PSBS phi frequencies. "
                       "Drive stages at Fibonacci ratio intensities.",
    )),
    asdict(StockDevice(
        name="Glue Compressor",
        category="AUDIO_EFFECT",
        ill_gates_rank=10,
        description="SSL G-bus emulation. Nearly indistinguishable from "
                    "the hardware according to many A/B tests.",
        ill_gates_tip="Nearly indistinguishable from SSL hardware. "
                      "Stop buying compressor plugins.",
        dubforge_use="Drum bus glue. Master chain compression. "
                     "Sidechain compression for pump effect.",
        phi_enhancement="Ratio: phi:1 (≈1.618:1) for natural dynamics. "
                       "Attack/release in phi-ratio ms values.",
    )),
    asdict(StockDevice(
        name="Echo",
        category="AUDIO_EFFECT",
        ill_gates_rank=11,
        description="Dual delay with character controls, filter, reverb, "
                    "modulation, and ducking. Way more than a simple delay.",
        ill_gates_tip="Echo is a complete creative tool, not just a delay. "
                      "The modulation and ducking alone make it essential.",
        dubforge_use="Fibonacci-timed delays on return tracks. "
                     "Ducking echo for bass music clarity.",
        phi_enhancement="Delay times at Fibonacci ratios: 1/8, 1/5, 1/3, "
                       "1/2, phi/4 beats. Feedback at 0.618.",
    )),
    asdict(StockDevice(
        name="Max for Live (Free Devices)",
        category="M4L",
        ill_gates_rank=12,
        description="The free Max for Live device library is an untapped "
                    "goldmine. Convolution reverbs, spectral tools, LFOs, "
                    "and creative instruments — all free with Live Suite.",
        ill_gates_tip="Most people don't even open the free M4L devices. "
                      "There are convolution reverbs, spectral processors, "
                      "and creative tools in there that rival paid plugins.",
        dubforge_use="Generate custom M4L devices via DUBFORGE Ableton Live "
                     "engine M4L script generator.",
        phi_enhancement="Custom LFO shapes following phi curves. "
                       "Spectral processing at phi-harmonic frequencies.",
    )),
]


# ═══════════════════════════════════════════════════════════════════════════
# LOW PASS TECHNIQUES — ill.Gates' 5 killer uses of low pass filter
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LowPassTechnique:
    """A low pass filter technique from ill.Gates' production methodology."""
    name: str
    category: str
    description: str
    how_to: str
    dubforge_use: str
    phi_enhancement: str


LOW_PASS_TECHNIQUES: list[dict] = [
    asdict(LowPassTechnique(
        name="Narrative Filtering",
        category="ARRANGEMENT",
        description="Put low passes on groups, busses, or the master and SLOWLY "
                    "open them up over time. Adds narrative and variation to "
                    "simple, repetitive sections. Cliché for a reason: it WORKS.",
        how_to="1. Insert Auto Filter on a bus or master. "
               "2. Set to Low Pass, cutoff at ~200 Hz. "
               "3. Automate cutoff to open from 200 Hz → 20 kHz over 8-16 bars. "
               "4. Reset before drops for maximum impact.",
        dubforge_use="RCO energy curve automation maps directly to filter "
                     "cutoff. Low cutoff = low energy, full open = peak energy.",
        phi_enhancement=f"Open filter from phi × 100 Hz (≈{round(PHI * 100)} Hz) "
                       f"to phi × 12000 Hz (≈{round(PHI * 12000)} Hz). "
                       "Rate of opening follows golden spiral acceleration.",
    )),
    asdict(LowPassTechnique(
        name="High Frequency Boosting via Resonance",
        category="MIXING",
        description="Set low pass cutoff high (8 kHz+) and boost resonance. "
                    "Creates a smooth, creamy boost at the cutoff frequency "
                    "while gently rolling off the extreme highs. Lets vocals "
                    "own the 'air' frequencies above 10 kHz.",
        how_to="1. Set LP cutoff at 8-12 kHz. "
               "2. Increase resonance to 40-60%. "
               "3. The resonance peak accentuates frequencies around cutoff. "
               "4. Use on instrumental bus to let vocals sit on top.",
        dubforge_use="Apply to PSBS MID and HIGH layers to create space "
                     "for the lead 'singer' sound above.",
        phi_enhancement=f"Cutoff at phi × 5000 Hz ≈ {round(PHI * 5000)} Hz. "
                       "Resonance at 1/phi ≈ 0.618 for golden Q factor.",
    )),
    asdict(LowPassTechnique(
        name="Filter Pinging",
        category="SOUND_DESIGN",
        description="High resonance low pass filter fed with short transients "
                    "produces juicy percussive pinging sounds. The resonance "
                    "causes a ringing decay like an analog drum machine.",
        how_to="1. Use an analog-modeled LP filter (UAD Moog, Arturia, etc.). "
               "2. Set resonance to 80-95% (near self-oscillation). "
               "3. Feed short transient clicks, noise bursts, or impulses. "
               "4. Tune cutoff frequency to desired pitch. "
               "5. Result: resonant percussion with natural decay.",
        dubforge_use="Percussion synthesis in DUBFORGE drum generator. "
                     "Living, breathing analog-feel drum sounds.",
        phi_enhancement="Tune pings to phi-harmonic frequencies: "
                       "55, 89, 144, 233, 377 Hz. Decay time: phi × 100 ms.",
    )),
    asdict(LowPassTechnique(
        name="Low Pass Gate (LPG)",
        category="SOUND_DESIGN",
        description="Filter cutoff and VCA amplitude tied together. Opening "
                    "the VCA opens the filter. Emulates natural acoustic "
                    "behavior — loud = bright, quiet = dark. The famous "
                    "'Buchla Bongo' percussion sound comes from pinging an LPG.",
        how_to="1. Create a Macro controlling both filter cutoff AND amplitude. "
               "2. Set both to respond to the same envelope/modulator. "
               "3. When amplitude is high → filter opens → bright sound. "
               "4. When amplitude fades → filter closes → dark, warm tail. "
               "5. Many synths can route a single mod source to both targets.",
        dubforge_use="Apply LPG behavior to DUBFORGE bass layers — natural "
                     "dynamics where loud bass is bright, quiet bass is warm.",
        phi_enhancement="LPG tracking ratio: cutoff follows amplitude at "
                       "phi curve (amp^(1/phi)). Natural golden-ratio dynamics.",
    )),
    asdict(LowPassTechnique(
        name="Audio Rate Filter FM",
        category="SOUND_DESIGN",
        description="Route an oscillator to modulate the filter cutoff at audio "
                    "rate. With resonance, this produces gnarly FM tones that "
                    "feel much more alive than sterile DX7-style FM. "
                    "ill.Gates calls this his 'secret sound design weapon' for bass.",
        how_to="1. Route an oscillator's output to the filter cutoff input. "
               "2. Set the modulating oscillator to audio rate (20 Hz+). "
               "3. Increase filter resonance to 50-80%. "
               "4. For Reese bass: detune two oscillators, only ONE modulates "
               "   the filter cutoff → amazing alive quality. "
               "5. Experiment with mod oscillator waveform (sine=smooth, "
               "   saw=aggressive, square=digital).",
        dubforge_use="Core technique for DUBFORGE growl resampler mid-bass. "
                     "Filter FM produces the 'living' quality in dubstep bass.",
        phi_enhancement="FM oscillator frequency at phi ratio of carrier "
                       "fundamental. Mod depth at Fibonacci LFO rates. "
                       "Resonance at 1/phi for golden sweet spot.",
    )),
]


# ═══════════════════════════════════════════════════════════════════════════
# UNBEATABLE DRUMS — ill.Gates' hardware drum sample catalog
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DrumKit:
    """A hardware drum kit from the Unbeatable Drums collection."""
    name: str
    hardware_source: str
    year_sampled: int
    character: str
    combinatorial_count: int    # possible unique combinations
    categories: list[str]
    dubforge_use: str


UNBEATABLE_DRUMS: dict = {
    "name": "Unbeatable Drums — The Ultimate All-Genre Drum Library",
    "creator": "ill.Gates",
    "total_sounds": 3500,
    "price": "$39 (90% off from $290)",
    "combinations_per_kit": 180_000,
    "technique": "128s system — all power at your fingertips out of the box",
    "studio_processing": [
        "Neves", "SSLs", "1176s", "LA-2As", "Distressors",
        "Tubes", "Valves", "Vactrols",
    ],
    "kits": [
        asdict(DrumKit(
            name="SH-101 'Goldzilla'",
            hardware_source="1982 Black & Gold Roland SH-101",
            year_sampled=2023,
            character="Analog warmth, punchy, classic. Recorded through "
                      "UAD preamps + hardware distortion in megastudios.",
            combinatorial_count=180_000,
            categories=["Kicks", "Snares", "Hats", "Perc", "FX"],
            dubforge_use="Classic analog drum foundation. Sub-heavy kicks.",
        )),
        asdict(DrumKit(
            name="Erica Synths Perkons",
            hardware_source="Erica Synths Perkons HD-01 ($3000)",
            year_sampled=2023,
            character="Modern analog percussion. A whole new dimension. "
                      "Famously used by Eprom. You've gotta hear it.",
            combinatorial_count=180_000,
            categories=["Kicks", "Toms", "Snares", "Metallic", "Noise"],
            dubforge_use="Modern analog perc for bass music drops.",
        )),
        asdict(DrumKit(
            name="Modular Madness",
            hardware_source="Large format modular synthesizer",
            year_sampled=2023,
            character="Huge, unwieldy, massive sound without the hassle. "
                      "Same sound as owning a $50k modular setup.",
            combinatorial_count=180_000,
            categories=["Kicks", "Hits", "Noise", "Metallic", "Drones"],
            dubforge_use="Experimental percussion and textural hits.",
        )),
        asdict(DrumKit(
            name="Elektron Syntakt",
            hardware_source="Elektron Syntakt",
            year_sampled=2023,
            character="Subtractive + FM synthesis with analog filters and "
                      "overdrive. Shocking audio fidelity. Cuts like a knife.",
            combinatorial_count=180_000,
            categories=["Kicks", "Snares", "Hats", "Toms", "FX"],
            dubforge_use="Clean, precise electronic drums for modern drops.",
        )),
        asdict(DrumKit(
            name="Make Noise Shared System",
            hardware_source="Make Noise Shared System (Buchla-inspired)",
            year_sampled=2023,
            character="West Coast synthesis. Deep love of sound. Cutting edge "
                      "percussion from Buchla-inspired circuits.",
            combinatorial_count=180_000,
            categories=["Plucks", "Pings", "Bongos", "Clicks", "Textures"],
            dubforge_use="Buchla bongo percussion, LPG pings, organic textures.",
        )),
        asdict(DrumKit(
            name="Korg MS-20",
            hardware_source="Korg MS-20 (1978 semi-modular)",
            year_sampled=2023,
            character="So relevant that all Ableton filters emulate its sound. "
                      "Raw, aggressive, legendary. Used originals are expensive.",
            combinatorial_count=180_000,
            categories=["Kicks", "Snares", "Noise", "Zaps", "Sweeps"],
            dubforge_use="Raw analog aggression for heavy dubstep drops.",
        )),
        asdict(DrumKit(
            name="Erica Synths LXR-02",
            hardware_source="Erica Synths LXR-02",
            year_sampled=2023,
            character="Digital/analog hybrid drum machine. Clean and punchy.",
            combinatorial_count=180_000,
            categories=["Kicks", "Snares", "Hats", "Claps", "Perc"],
            dubforge_use="Hybrid electronic drums with clean digital punch.",
        )),
        asdict(DrumKit(
            name="All-Genre 128 Kit",
            hardware_source="Mixed multisampled sources",
            year_sampled=2023,
            character="Classic Infinite Drum Rack style. Contains a whole "
                      "career worth of combinations in a single kit.",
            combinatorial_count=180_000,
            categories=["Kicks", "Snares", "Hats", "Perc", "FX",
                        "Bass", "Melodic", "Vocal", "Foley"],
            dubforge_use="One-stop solution for any genre. Load and go.",
        )),
        asdict(DrumKit(
            name="Glitchy 128 Kit",
            hardware_source="Processed glitch sources",
            year_sampled=2023,
            character="Gooey, glitchy goodness. Designed to be reused "
                      "thousands of times without getting stale.",
            combinatorial_count=180_000,
            categories=["Glitch", "Stutter", "Artifact", "Digital", "Noise"],
            dubforge_use="Glitch fills, stutter edits, digital textures.",
        )),
        asdict(DrumKit(
            name="SH-101 Mudpie Kit",
            hardware_source="SH-101 processed through Mudpie technique",
            year_sampled=2023,
            character="Mudpie chaos captured from SH-101 experiments.",
            combinatorial_count=180_000,
            categories=["Chaos", "Texture", "Hits", "Noise", "Organic"],
            dubforge_use="Organic chaos textures from Mudpie sessions.",
        )),
        asdict(DrumKit(
            name="MS-20 Feedback Kit",
            hardware_source="MS-20 feedback patches",
            year_sampled=2023,
            character="Self-oscillating filter feedback from the MS-20. "
                      "Living, breathing, aggressive.",
            combinatorial_count=180_000,
            categories=["Feedback", "Resonant", "Tonal", "Aggressive"],
            dubforge_use="Feedback-driven percussion for aggressive drops.",
        )),
    ],
    "bonus_content": [
        "Drum Rack Workshop ($50 value)",
        "Acoustic Drum Breaks (recorded at Shelter Studios, 2023)",
        "Jungle Break Kit",
        "Electro/Techno Kit",
        "Fat n' Simple Kit",
        "Donk Kit",
    ],
    "phi_integration": {
        "kit_count": "11 kits (close to Fibonacci 13)",
        "sounds_total": f"3500 sounds (≈ Fibonacci 3 × 1000 + 500)",
        "combinations_per_kit": "180,000 (phi^12 ≈ 321.9 × 560 ≈ 180K)",
        "zone_distribution": "Fibonacci allocation across categories in 128 Rack",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# THE PRODUCER'S PATH — 12-week course structure
# ═══════════════════════════════════════════════════════════════════════════

PRODUCERS_PATH: dict = {
    "name": "The Producer's Path",
    "tagline": "90 Days to Music That Works",
    "guarantee": "You'll make music you're proud of by the end or your money back.",
    "duration_weeks": 12,
    "structure": {
        "weekly_classes": 12,
        "production_challenges": 12,
        "listening_levels": 12,
        "creativity_discussions": 12,
        "fundamental_technique_levels": 12,
        "digging_preparation_levels": 12,
    },
    "included_content": {
        "drums_bass_breaks_vocals": "Nearly 1 GB",
        "music_tools_templates": "All the tools + templates you'll ever need",
        "moog_sub_multisamples": "Damian Taylor's Grammy-nominated album sounds",
        "deep_reference_library": "Catch beginners up fast",
    },
    "methodology": {
        "scientific_goal_setting": "More than doubles finish rate",
        "prep_organization": "System adopted by household names",
        "psychological_tweaks": "Little tweaks that make it feel effortless",
        "enough_fun": "Fall in love with the fundamentals",
        "enough_depth": "Repeat any time you want to level up",
    },
    "annual_membership_includes": [
        "All four 12-week semester courses (live + at your own pace)",
        "ill.Gates private Discord live stream access",
        "Reference Library (best of 400+ Weekly Download Archive videos)",
        "Basics Library (fundamental production videos)",
        "Music Tool Vault (templates, instruments, racks, Unbeatable Drums, "
         "Infinite Drum Rack, top sound packs)",
        "Unlimited written track feedback",
        "WIP Wednesday + Feedback Friday live streams",
        "12 Sensei Sessions (optional add-on)",
    ],
    "phi_integration": {
        "course_weeks": f"12 weeks (near Fibonacci 13)",
        "fibonacci_challenge_schedule": "Challenges at Fibonacci week intervals: "
                                        "Week 1, 1, 2, 3, 5, 8 — intensifying pace",
        "golden_feedback_cycle": f"Submit track → wait phi days (≈{round(PHI, 1)} days) "
                                 "→ receive feedback → iterate. Natural learning cadence.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# EXTENDED DOJO TECHNIQUES — Ninja Sounds + Low Pass as formal techniques
# ═══════════════════════════════════════════════════════════════════════════

# Keep legacy DOJO_TECHNIQUES stable for compatibility and expose new material separately.
EXTENDED_DOJO_TECHNIQUES: list[dict] = []

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Ninja Sounds (Singer vs Band)",
    year_introduced=2024,
    category=TechniqueType.MIXING.value,
    description="The mix philosophy that most sounds should AVOID listener attention. "
                "Only the 'singer' element (lead/vocal/main bass) demands focus. "
                "Everything else is the 'band' — supportive, invisible, essential. "
                "Based on ill.Gates' 'Start Using Ninja Sounds' blog (Jan 2026).",
    steps=[
        "1. Identify the ONE 'singer' element for each section (usually lead or main bass)",
        "2. Everything else is 'band' — supportive ninja sounds",
        "3. Audit every mix decision: does this serve the focus direction?",
        "4. Pull back ninja sounds: slightly quieter, warmer, narrower, wetter",
        "5. Clear 2-4.5 kHz (pain zone) on band elements — that's the singer's zone",
        "6. Use reverb to push band elements BACK in the mix",
        "7. Mono sub elements — width steals attention",
        "8. A/B test: solo the singer, then add the band — band should enhance, not compete",
        "9. If a ninja sound grabs your attention, make it quieter/darker/narrower",
        "10. Result: a mix where the listener's ear goes EXACTLY where you want it",
    ],
    tools_required=["EQ Eight", "Utility (stereo width)", "Reverb (space placement)",
                   "Volume automation", "Mid/Side EQ"],
    dubforge_integration="PSBS layers map perfectly: SUB = ninja (felt, not heard), "
                        "MID = singer in drops, HIGH = ninja texture support. "
                        "During breakdowns: CHORDS = singer, everything else = ninja.",
    phi_enhancement="Ninja volume at 1/phi (0.618) of singer volume. "
                   "Ninja brightness cut at phi × 2kHz. "
                   "Singer:Band ratio = phi:1 in perceived loudness.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Low Pass Mastery (5 Killer Techniques)",
    year_introduced=2024,
    category=TechniqueType.SOUND_DESIGN.value,
    description="ill.Gates' 5 essential uses of low pass filter: Narrative filtering, "
                "high boosting via resonance, filter pinging, low pass gates (Buchla Bongo), "
                "and audio rate filter FM (his 'secret weapon' for bass). "
                "The fundamentals are a bottomless well.",
    steps=[
        "1. Narrative: automate LP on bus/master from 200 Hz → 20 kHz over 8-16 bars",
        "2. High boost: LP cutoff at 8 kHz+, boost resonance for creamy presence",
        "3. Pinging: high resonance LP + short transients = percussive tones",
        "4. LPG: macro controlling both amplitude AND filter simultaneously",
        "5. Audio rate FM: route oscillator to filter cutoff, boost resonance",
        "6. For Reese bass: one detuned osc modulates filter = ALIVE quality",
        "7. Use analog-modeled filters for pinging (digital filters sound terrible)",
        "8. Use Analog Heat physical LP circuit on instrumental, let vocal own air",
        "9. Combine techniques: LPG + filter FM = extreme organic character",
        "10. Never underestimate fundamentals — low pass is a bottomless well",
    ],
    tools_required=["Auto Filter", "Analog-modeled filter (UAD Moog, etc.)",
                   "Macro controls", "Analog Heat (optional hardware)"],
    dubforge_integration="All 5 techniques integrated into DUBFORGE signal processing: "
                        "narrative filtering in RCO energy curves, filter pinging in "
                        "drum generator, LPG behavior on bass layers, filter FM in "
                        "growl resampler mid-bass design.",
    phi_enhancement="LP narrative opens at golden spiral rate. "
                   "Resonance peak at phi Q factor. "
                   "Filter FM ratio: carrier:mod = 1:phi. "
                   "LPG tracking curve: amp^(1/phi).",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="The 14-Minute Hit (Rapid Creation)",
    year_introduced=2024,
    category=TechniqueType.WORKFLOW.value,
    description="Timer-based rapid creation methodology. Sia wrote 'Diamonds' in "
                "14 minutes. Speed is proof of depth. During flow states, the "
                "brain's self-monitoring center shuts down while self-expression "
                "center activates. Ride the wave — don't fight it.",
    steps=[
        "1. Set a hard timer: 14-37 minutes (14 = hit, 37 = 1/phi of 60)",
        "2. Pre-select sounds before starting (128 Rack ready, drums loaded)",
        "3. Start the timer and IMMEDIATELY begin creating",
        "4. Capture first instincts — do NOT second-guess",
        "5. No EQ, no mixing, no processing — just CAPTURE the idea",
        "6. When decision fatigue appears (audition paralysis), commit to current choice",
        "7. If it doesn't feel right in 3 attempts, move on (Fibonacci decision limit)",
        "8. When timer ends: STOP. Save. Rate: 🔥 / ⭐ / ♻️",
        "9. Do NOT revise in the same session — separate creation from revision",
        "10. Sessions with 🔥 ratings become full tracks. ⭐ become sound design fodder. "
            "♻️ gets composted — no shame, just volume.",
    ],
    tools_required=["Timer (phone/app)", "Pre-loaded 128 Rack",
                   "Pre-loaded drum kit", "Session View ready"],
    dubforge_integration="DUBFORGE fibonacci_feedback engine can auto-rate output "
                        "quality. 14-minute hit sessions feed the lessons_learned "
                        "engine for cross-track improvement.",
    phi_enhancement=f"Golden timer: 1/phi of 60 min = {round(60 / PHI, 1)} min. "
                   f"Decision limit: Fibonacci 3 (try 3 times then commit). "
                   f"Session rating ratio target: phi quality tracks per 5 sessions.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Stock Device Mastery",
    year_introduced=2024,
    category=TechniqueType.WORKFLOW.value,
    description="Master Ableton's stock devices before buying third-party plugins. "
                "The fundamentals are a bottomless well. Sampler (#1), Operator, "
                "Saturator Digital Clip ('beats 9/10 clippers'), OTT ('still slaps'), "
                "Erosion ('defined whole genres of bass'), Glue Compressor "
                "('nearly indistinguishable from SSL hardware'). "
                "From ill.Gates' 'Invest in Stock! ...Devices.' blog (Jan 2026).",
    steps=[
        "1. Learn Sampler deeply -- it IS the 128 Rack engine",
        "2. Master Operator for FM synthesis before reaching for Serum",
        "3. Discover Meld, Drift, and Wavetable -- three world-class synths you own",
        "4. Use Saturator Digital Clip mode for clean hard clipping",
        "5. Embrace OTT preset -- it's been the secret weapon for years",
        "6. Add Erosion for fizzy, buzzy bass character ('defined whole genres')",
        "7. Explore Roar's routing options (serial/parallel/M-S/multiband)",
        "8. Use Glue Compressor on every bus (SSL quality)",
        "9. Try Echo's ducking and modulation features",
        "10. Open the free Max for Live devices -- untapped goldmine",
    ],
    tools_required=["Ableton Live Suite", "Time and curiosity"],
    dubforge_integration="All DUBFORGE signal processing chains reference stock "
                        "devices as primary tools. Third-party plugins are optional "
                        "enhancements, not requirements.",
    phi_enhancement="Master each device for phi hours (1.618h) before moving to "
                   "the next. Fibonacci learning order: Sampler first, then 1 more, "
                   "then 2 more, then 3 more, etc.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Subtractive Arrangement (Fat Loop Method)",
    year_introduced=2015,
    category=TechniqueType.ARRANGEMENT.value,
    description="Build arrangements by SUBTRACTING from a full loop, not by "
                "building left-to-right. Create an 8-bar 'Fat Loop' where every "
                "element plays at once (the climax). Duplicate across the timeline. "
                "Then MUTE/DELETE parts to create sections. Much faster than "
                "additive arrangement and guarantees the drop sounds full.",
    steps=[
        "1. Create an 8-bar loop with ALL elements playing (the 'Fat Loop')",
        "2. This loop IS your drop -- every sound at full energy",
        "3. Duplicate the Fat Loop across the full arrangement (e.g. 4 minutes)",
        "4. Go to the intro: MUTE drums, bass, most elements -- leave only pads/atmos",
        "5. Go to the build: unmute drums (half-time), add elements progressively",
        "6. Leave the drop section intact (it's already full)",
        "7. Go to the breakdown: mute everything except chords/lead/atmosphere",
        "8. Second build: progressively unmute again",
        "9. Second drop: full loop again but swap some bass sounds (VIP mentality)",
        "10. Now you only need to design the 2-bar TRANSITIONS between sections",
    ],
    tools_required=["Ableton Live Arrangement View", "Clip duplication",
                   "Mute/Solo tools", "Transition FX library"],
    dubforge_integration="DUBFORGE RCO energy curve maps perfectly: start with "
                        "energy=1.0 everywhere, then carve the curve by muting. "
                        "Fibonacci bar counts for section lengths: 8+13+21+8+8+21+5.",
    phi_enhancement="Fat Loop length: 8 bars (Fibonacci). Transition gaps: "
                   "2 bars = Fibonacci. Muting pattern follows golden section: "
                   "first unmuted element at bar total/Phi. Subtraction ratio: "
                   "remove 1/phi of elements per energy level drop.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Song Mapping (Ghost Track Technique)",
    year_introduced=2012,
    category=TechniqueType.ARRANGEMENT.value,
    description="Reverse-engineer professional arrangements by dragging a "
                "reference track into your project and marking every structural "
                "event. Delete the reference audio but keep the markers. Build "
                "your own song using that exact structural 'map.' Removes "
                "'what comes next?' anxiety and lets you focus purely on sounds.",
    steps=[
        "1. Choose a professional track in a similar style to your target",
        "2. Drag it into your DAW project on a reference audio track",
        "3. Create Locator markers every time something changes:",
        "   -- 'Hi-hats enter' / 'Sub drops out' / 'New FX layer' / 'Drums half-time'",
        "4. Mark energy level at each marker (1-10 or low/med/high)",
        "5. Note bar counts between markers (will likely be powers of 2 or Fibonacci)",
        "6. Color-code markers by element type (drums, bass, melodic, FX)",
        "7. DELETE the reference audio -- keep ONLY the markers",
        "8. Build your own song using the marker skeleton as structure",
        "9. Focus on sounds and emotion -- structure is already decided",
        "10. After 5-10 maps, internalize the patterns and stop needing the reference",
    ],
    tools_required=["Professional reference track (WAV/MP3)",
                   "Ableton Live Locator Markers", "Color coding system"],
    dubforge_integration="DUBFORGE Reference Library + Reference Analyzer already "
                        "extract ArrangementDNA (section detection, drop/build/breakdown "
                        "labeling, tension curves). Use analyze results as automated "
                        "Ghost Track data -- no manual marker placement needed.",
    phi_enhancement="Golden Map: verify that the reference track's climax falls "
                   "near total_bars/phi. If it does, the track has natural golden "
                   "proportions. Use phi bar positions as marker anchors for your "
                   "own arrangement.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Frequency Slotting (Tetris Board Mix)",
    year_introduced=2016,
    category=TechniqueType.MIXING.value,
    description="Visualize the mix as a Tetris board where frequency = rows and "
                "time = columns. If two pieces overlap, the game ends (masking). "
                "Every sound gets a 'home' frequency range. Enforce with surgical "
                "EQ. High-pass EVERYTHING that isn't kick or sub up to 200-300 Hz "
                "to keep the 'basement' surgically clean.",
    steps=[
        "1. Assign dominant frequency ranges to each element:",
        "   -- Kick: 50-100 Hz, Sub: 30-60 Hz, Mid Bass: 144-233 Hz",
        "   -- Snare: 200-500 Hz fundamental, Lead: 400-2000 Hz, Vocals: 1-4 kHz",
        "2. High-pass EVERY non-kick non-sub element at 150-300 Hz",
        "3. For each pair of overlapping elements, decide who 'owns' the range",
        "4. Sidechain the subordinate element to the dominant one",
        "5. Use narrow EQ cuts on subordinate, boosts on dominant",
        "6. Check the Tetris board: no two dominant elements in same row at same time",
        "7. If drop has sub + kick competing below 80 Hz, sidechain sub to kick",
        "8. Use spectrum analyzer to visually verify slot separation",
        "9. A/B with reference tracks -- frequency distribution should match",
        "10. The cleaner the Tetris board, the louder the master can be pushed",
    ],
    tools_required=["EQ Eight", "Spectrum analyzer", "Sidechain Compressor",
                   "Auto Filter (high-pass)", "Reference plugin"],
    dubforge_integration="PSBS crossover frequencies (55/89/144/233/377 Hz) "
                        "ARE the Tetris row boundaries -- every bass layer has "
                        "a pre-assigned frequency slot. MixingDNA module measures "
                        "mud_ratio (200-500 Hz) and harshness_ratio (2-5 kHz) "
                        "to detect Tetris collisions.",
    phi_enhancement="Frequency slots at phi ladder: 55, 89, 144, 233, 377, 610 Hz. "
                   "Each slot width = previous_width * phi. "
                   "EQ cut depth = 1/phi (0.618) of overlap energy. "
                   "Sidechain ratio: phi:1 (1.618:1).",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Contrast is King",
    year_introduced=2018,
    category=TechniqueType.ARRANGEMENT.value,
    description="Every perceived quality is relative to what came before. "
                "You cannot have 'huge' without 'small' for reference. "
                "Wide drops need narrow breakdowns. Heavy drops need thin "
                "builds. Loud needs quiet. Every musical 'peak' is defined "
                "by the 'valley' that precedes it.",
    steps=[
        "1. For wide drops: make the preceding section MONO (narrow breakdowns)",
        "2. For huge drops: high-pass the breakdown heavily (thin before thick)",
        "3. For loud drops: pull volume down in the build (quiet before loud)",
        "4. For busy drops: strip the breakdown to 1-2 elements (sparse before dense)",
        "5. For bright drops: darken the build with low-pass filtering",
        "6. Create contrast checklist for every section transition:",
        "   -- Width: narrow → wide",
        "   -- Frequency: thin → full",
        "   -- Volume: quiet → loud",
        "   -- Density: sparse → dense",
        "   -- Brightness: dark → bright",
        "7. The greater the contrast, the greater the impact",
        "8. Use silence (even 1-2 beats) before drops for maximum effect",
        "9. Reverse the pattern for breakdowns: full → stripped",
        "10. A/B your transitions against reference tracks for contrast ratio",
    ],
    tools_required=["Automation (volume, filter, width)", "Utility (stereo)",
                   "Auto Filter", "Arrangement View"],
    dubforge_integration="DUBFORGE ArrangementDNA already measures breakdown_depth_db "
                        "and transition_sharpness. Higher contrast = higher quality "
                        "score. RCO energy curve enforces valley-peak-valley pattern.",
    phi_enhancement="Golden contrast ratio: drop energy = phi * breakdown energy. "
                   "Width contrast: breakdown at 1/phi (0.382) stereo width, "
                   "drop at 1.0. Volume contrast: breakdown at -phi*3 dB below drop. "
                   "The phi ratio IS the ideal contrast -- too much feels jarring, "
                   "too little feels flat. Phi hits the perceptual sweet spot.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Pink Noise Mixing",
    year_introduced=2014,
    category=TechniqueType.MIXING.value,
    description="A fast technique to get a balanced 'static mix' using pink noise "
                "as a reference signal. Play pink noise at a fixed level, then bring "
                "each track up until it is JUST audible over the noise. This creates "
                "a mathematically balanced frequency distribution across the mix "
                "because pink noise has equal energy per octave -- matching human "
                "perception of loudness across the frequency spectrum.",
    steps=[
        "1. Insert a pink noise generator on a dedicated 'Reference' track",
        "2. Set pink noise to a comfortable listening level (-18 to -12 dBFS)",
        "3. Solo the pink noise + ONE track at a time",
        "4. Bring the track fader up from -inf until it's JUST audible over the noise",
        "5. Mark the fader position and move to the next track",
        "6. Repeat for all tracks in the session",
        "7. Un-solo everything -- you now have a balanced 'static mix'",
        "8. Fine-tune from this baseline (much faster than starting from scratch)",
        "9. Use as a starting point ONLY -- creative mixing decisions come after",
        "10. Revisit pink noise check periodically to reset your ears",
    ],
    tools_required=["Pink noise generator (Test Tone in Ableton, or external)",
                   "Volume faders", "Solo/Mute controls", "Fresh ears"],
    dubforge_integration="DUBFORGE noise_generator module can produce pink noise "
                        "for this technique. MixingDNA frequency_balance_score "
                        "measures how close a mix is to pink noise distribution. "
                        "Auto-mixer module can implement this algorithmically.",
    phi_enhancement="Pink noise IS phi-friendly: equal energy per octave maps to "
                   "PSBS phi-ladder frequency bands. Set initial sub mix at "
                   "1/phi of pink noise level (the sub should be FELT, not heard "
                   "over noise). Use as calibration before phi-frequency mixing.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Low Volume Monitoring (Fletcher-Munson Discipline)",
    year_introduced=2016,
    category=TechniqueType.MIXING.value,
    description="Mix at conversational volume -- low enough to talk over without "
                "raising your voice. If the mix sounds powerful at low volume, it "
                "will sound DEADLY on a club system. Mixing loud causes ear fatigue "
                "(Fletcher-Munson effect) where perceived bass/treble boost at "
                "high SPL makes you compensate by cutting them, resulting in a "
                "thin, harsh mix when played at normal levels.",
    steps=[
        "1. Set monitoring to 'conversation level' (can talk without yelling)",
        "2. If you can't hear the sub at low volume, it's in the wrong frequency range",
        "3. If the snare disappears at low volume, it needs more mid-range body",
        "4. Check the mix briefly at high volume for sub accuracy (max 30 seconds)",
        "5. NEVER make EQ decisions at high volume -- Fletcher-Munson distorts perception",
        "6. Take 10-minute ear breaks every 45-60 minutes (Fibonacci: 45min on, 8min off)",
        "7. Check on headphones AND monitors -- different Fletcher-Munson curves",
        "8. Check on phone speaker (worst case scenario = most honest translation test)",
        "9. If it sounds good quiet, good on phones, and good loud -- it's done",
        "10. Ear fatigue is cumulative over a session -- your first hour is your most accurate",
    ],
    tools_required=["SPL meter (or phone app)", "Multiple monitoring systems",
                   "Timer for ear breaks", "Phone speaker for translation check"],
    dubforge_integration="DUBFORGE reference_analyzer measures loudness consistency "
                        "and streaming_loudness_penalty. Tracks mixed at low volume "
                        "naturally translate better to streaming (-14 LUFS target). "
                        "MasteringDNA limiting_transparency catches Fletcher-Munson "
                        "compensation artifacts.",
    phi_enhancement="Golden monitoring cycle: phi * 30 min = 48.5 min work, "
                   "then break. Fibonacci ear-break schedule: 3 min break after "
                   "first session, 5 min after second, 8 min after third. "
                   "Low volume level: phi * -20 dBFS ≈ -32 dBFS at monitor.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Organic Automation (Macro Performance Recording)",
    year_introduced=2014,
    category=TechniqueType.PERFORMANCE.value,
    description="Instead of drawing automation curves with a mouse, PERFORM them "
                "by recording knob movements in real time. Map 8 Macros to essential "
                "'vibe' controls (Filter, Distortion, Space, Movement, Width, Pitch, "
                "Decay, Drive) and record your physical performance. The tiny "
                "imperfections in human knob movements create organic, living "
                "automation that makes electronic music feel alive.",
    steps=[
        "1. Map 8 Macros to essential sound parameters:",
        "   -- Knob 1: Filter Cutoff (most expressive control)",
        "   -- Knob 2: Distortion / Saturation amount",
        "   -- Knob 3: Space (Reverb send / Dry-Wet)",
        "   -- Knob 4: Movement (LFO rate or Auto-pan)",
        "   -- Knob 5: Stereo Width",
        "   -- Knob 6: Pitch / Detune",
        "   -- Knob 7: Decay / Release",
        "   -- Knob 8: Drive / Grit intensity",
        "2. Arm automation recording in Arrangement View",
        "3. Play the arrangement and physically turn knobs in real time",
        "4. Don't aim for perfection -- the imperfections ARE the point",
        "5. Record multiple passes, overdubbing different parameters each time",
        "6. The result: organic, breathing automation with human micro-variations",
        "7. Quantize ONLY if absolutely necessary -- unquantized = more human",
        "8. Use controller sensitivity settings for musical response curves",
        "9. A/B against mouse-drawn automation -- performance feels more alive",
        "10. This turns mixing from editing into PLAYING -- the DAW becomes an instrument",
    ],
    tools_required=["MIDI controller with knobs (Push, APC40, generic)",
                   "Ableton automation recording mode",
                   "Macro rack mapping"],
    dubforge_integration="DUBFORGE automation_recorder module captures knob "
                        "movements as automation data. Phi-curve response "
                        "mapping on controller knobs for natural feel. "
                        "The 8-macro bank maps to PSBS layer controls.",
    phi_enhancement="Controller response curve: phi-exponential (value = input^phi) "
                   "for natural sensitivity. Macro range: center (0.5) maps to "
                   "phi sweet spot of each parameter. Recording quantization: "
                   "Fibonacci subdivision (off / 1/3 / 1/5 / 1/8 / 1/13 note).",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Nighttime/Daytime Rule (Energy-Matched Scheduling)",
    year_introduced=2018,
    category=TechniqueType.WORKFLOW.value,
    description="Match production tasks to your biological energy levels. "
                "'Nighttime' (low energy periods) = prep work: sound design, "
                "library organization, plugin updates, finger drumming practice. "
                "'Daytime' (peak energy) = writing: song structure, creativity, "
                "arrangement, the actual MUSIC. Treat writing like a job -- "
                "do it when your brain is fresh, not after hours of prep.",
    steps=[
        "1. Identify your peak creative hours (usually 1-3 hours after waking)",
        "2. PROTECT those hours -- no email, no social media, no prep work",
        "3. Use peak hours exclusively for songwriting and arrangement",
        "4. Schedule 'prep' work for low-energy periods:",
        "   -- Sound design experiments",
        "   -- Library organization and tagging",
        "   -- Building 128 Racks from collected samples",
        "   -- Plugin updates and template maintenance",
        "   -- Finger drumming and controller practice",
        "   -- Mixing revisions (separate from creation)",
        "5. End each prep session with a 'ready to write' state",
        "6. Morning routine: open DAW with template loaded, sounds ready",
        "7. Don't browse presets during writing -- use what's already loaded",
        "8. If energy drops mid-session, switch to prep mode -- don't force creativity",
        "9. Track your energy patterns for a week to find YOUR optimal schedule",
        "10. Standing desk during creation phase keeps energy high and body moving",
    ],
    tools_required=["Calendar/scheduler", "Pre-built templates",
                   "Organized sample library", "Standing desk (recommended)"],
    dubforge_integration="DUBFORGE 4-phase pipeline enforces this naturally: "
                        "Phase 1 (Generation) and Phase 2 (Arrangement) are 'daytime' "
                        "creative tasks. Phase 3 (Mixing) and Phase 4 (Mastering) are "
                        "'nighttime' technical tasks. Never mix phases.",
    phi_enhancement="Golden day split: phi hours of creation (peak hours), "
                   "remaining hours for prep. For an 8-hour production day: "
                   f"5 hours creation, 3 hours prep ({round(8/PHI, 1)} : "
                   f"{round(8 - 8/PHI, 1)}). Peak energy at the golden hour: "
                   "hour total/phi after waking.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Ear Stamina Discipline",
    year_introduced=2020,
    category=TechniqueType.MIXING.value,
    description="Technical mixing isn't just about knowledge -- it's about "
                "biological limitations. Your ears fatigue, your perception shifts "
                "with volume and duration, and your first hour of mixing is always "
                "your most accurate. Respect the biology or your decisions degrade.",
    steps=[
        "1. Your first hour of mixing is your MOST accurate -- prioritize critical decisions",
        "2. Ear fatigue is cumulative: 45 min on, 10 min off (minimum)",
        "3. NEVER exceed 85 dB SPL for extended periods (hearing damage threshold)",
        "4. Hearing sensitivity changes with volume (Fletcher-Munson curves):",
        "   -- Loud: perceived bass/treble boost → you cut too much → thin mix",
        "   -- Quiet: perceived bass/treble reduction → you boost too much → muddy mix",
        "5. Solution: mix at conversation level, check at loud for 30-second bursts ONLY",
        "6. Caffeine, alcohol, fatigue, and stress ALL alter frequency perception",
        "7. After 3 hours of mixing, STOP -- your ears are lying to you",
        "8. Sleep on it: next-day listening reveals issues invisible during the session",
        "9. Keep notes of what sounds 'wrong' on day 2 -- those are real problems",
        "10. Reference tracks RESET your ears -- A/B every 15-20 minutes to recalibrate",
    ],
    tools_required=["Timer (ear break forcing)", "SPL meter",
                   "Reference tracks", "Next-day revision habit"],
    dubforge_integration="DUBFORGE reference_library compare function serves as "
                        "an automated 'ear reset' -- objective frequency and loudness "
                        "comparison against the reference standard. No ear fatigue "
                        "in the algorithm. QualityScore is time-invariant.",
    phi_enhancement="Golden ear cycle: phi * 30 min ≈ 49 min work blocks. "
                   "Fibonacci break schedule: 3, 5, 8, 13 min breaks (escalating). "
                   "Reference check interval: every phi * 10 ≈ 16 min. "
                   "Maximum session: Fibonacci 3 hours then STOP.",
)))

EXTENDED_DOJO_TECHNIQUES.append(asdict(DojoTechnique(
    name="Commitment to Audio (Freeze + Flatten Discipline)",
    year_introduced=2016,
    category=TechniqueType.WORKFLOW.value,
    description="Once a synth line is 'good,' convert it to audio immediately. "
                "MIDI is fluid and invites endless tweaking. Audio is solid -- it "
                "forces you to COMMIT to your choices and move to the next creative "
                "decision. Freeze and Flatten is not just CPU management: it's "
                "psychological warfare against perfectionism.",
    steps=[
        "1. Design your sound in MIDI/synth mode (Phase 1: Child brain)",
        "2. When it sounds 'good enough' -- NOT perfect, just good -- STOP tweaking",
        "3. In Ableton: Freeze the track (commits the sound, saves CPU)",
        "4. Then: Flatten the track (converts frozen track to permanent audio)",
        "5. The synth is now GONE -- you cannot tweak the oscillator settings anymore",
        "6. This is INTENTIONAL -- the option to tweak was the enemy, not the sound",
        "7. If you genuinely need to change something later: duplicate BEFORE flatten",
        "8. Work with the audio: warp, chop, resample, arrange -- different toolset",
        "9. By end of arrangement: ALL synth tracks should be flattened to audio",
        "10. Mixing starts with audio stems ONLY -- no synths open, no temptation",
    ],
    tools_required=["Ableton Freeze + Flatten", "Self-discipline",
                   "Project backup before flatten"],
    dubforge_integration="DUBFORGE pipeline enforces this by design: Phase 1 outputs "
                        "sound palette (presets + wavetables), Phase 2 outputs STEMS "
                        "(audio). Each phase is a SEPARATE Ableton session. By Phase 3, "
                        "all sounds are committed audio -- no synths to tweak.",
    phi_enhancement="Golden commitment: decide in Fibonacci attempts (try 3 patches, "
                   "pick the best, flatten). 5 max if first 3 don't work. NEVER "
                   "audition more than 8 (Fibonacci limit). The first Fibonacci "
                   "number of options usually contains the winner.",
)))



# ═══════════════════════════════════════════════════════════════════════════
# ILL.GATES PRODUCTION RULES — Distilled wisdom for DUBFORGE integration
# ═══════════════════════════════════════════════════════════════════════════

ILL_GATES_RULES: list[str] = [
    "1.  FINISH MUSIC. Completion > perfection. Always.",
    "2.  Separate creation from revision — never mix while creating.",
    "3.  First instinct beats labored revision 90% of the time.",
    "4.  Volume is the teacher. Speed is how you let it teach.",
    "5.  Decision fatigue kills creativity — commit early, move forward.",
    f"6.  Use a timer: {round(60 / PHI, 1)} minutes creation, "
    f"    {round(60 - 60 / PHI, 1)} minutes evaluation (phi split).",
    "7.  Most sounds should be NINJAS — invisible, supportive, essential.",
    "8.  Only ONE element is the 'singer' at any given moment.",
    "9.  Clear the pain zone (2-4.5 kHz) on everything except the singer.",
    "10. The fundamentals are a bottomless well — master stock devices first.",
    "11. Saturator Digital Clip beats 9/10 third-party clippers.",
    "12. Erosion defined whole genres of bass music. Use it.",
    "13. OTT still slaps. Will always slap.",
    "14. Glue Compressor is nearly indistinguishable from SSL hardware.",
    "15. Not every technique, sound, or song needs to be crazy.",
    "16. Your audience cares about one thing: the FEELING.",
    "17. Style is confidence in self-expression.",
    "18. You can always add complexity later. You can't unmake a mess.",
    "19. Go the extra mile during PREP — but let the writing be effortless.",
    "20. Low pass filter is far from fancy but it's one of the most powerful tools.",
    "21. Audio rate filter FM is a secret weapon for bass sounds.",
    f"22. A finished track teaches more than {round(PHI)} unfinished tracks with pristine mix buses.",
    "23. Being nice is important. Not a dick. — Dylan aka ill.Gates",
    "24. Never let the Critic brain into the room while the Child is playing.",
    "25. Contrast is King — wide needs narrow, huge needs thin, loud needs quiet.",
    "26. Every mix is a Tetris board — overlapping frequencies = game over.",
    "27. High-pass EVERYTHING that isn't kick or sub (200-300 Hz minimum).",
    "28. Arrange by SUBTRACTING from a full loop, not building left to right.",
    "29. Mix at conversation volume. If it bangs quiet, it kills loud.",
    "30. Pink noise mixing for a fast balanced starting point — then refine.",
    "31. Your first hour of mixing is your most accurate. Respect ear fatigue.",
    "32. Freeze + Flatten is psychological warfare against perfectionism.",
    "33. Perform automation with knobs, don't draw it — imperfections are life.",
    "34. Do prep work (libraries, sound design) when energy is low. Write when fresh.",
]


# ═══════════════════════════════════════════════════════════════════════════
# MIXING MENTAL MODELS — Dojo-derived frameworks for DUBFORGE integration
# ═══════════════════════════════════════════════════════════════════════════

MIXING_MENTAL_MODELS: dict = {
    "frequency_slotting": {
        "name": "Frequency Slotting (Tetris Board)",
        "principle": "The mix is a Tetris board: frequency = rows, time = columns. "
                     "Two pieces in the same slot = masking = game over.",
        "default_slot_assignments": {
            "kick_fundamental": {"low_hz": 50, "high_hz": 100,
                                 "owner": "KICK", "priority": 1},
            "sub_bass":         {"low_hz": 20, "high_hz": 80,
                                 "owner": "SUB", "priority": 2},
            "bass_body":        {"low_hz": 80, "high_hz": 250,
                                 "owner": "BASS (MID)", "priority": 3},
            "snare_body":       {"low_hz": 200, "high_hz": 500,
                                 "owner": "SNARE", "priority": 4},
            "vocal_lead":       {"low_hz": 1000, "high_hz": 4500,
                                 "owner": "LEAD / VOCAL", "priority": 1},
            "hi_hats":          {"low_hz": 6000, "high_hz": 16000,
                                 "owner": "HATS / CYMBALS", "priority": 5},
            "air":              {"low_hz": 10000, "high_hz": 20000,
                                 "owner": "AIR / REVERB TAILS", "priority": 6},
        },
        "psbs_tetris_mapping": {
            "SUB (20-89)":    "Bottom 2 rows -- mono, no competition allowed",
            "LOW (89-144)":   "Bass foundation -- sidechain to kick",
            "MID (144-233)":  "Growl territory -- the singer in drops",
            "HIGH (233-377)": "Screech/harmonics -- ninja support in drops",
            "CLICK (377-610)":"Transient definition -- cuts through everything",
        },
        "high_pass_rule": "HP everything not kick/sub at 150-300 Hz. "
                          "This single rule fixes 80% of muddy mixes.",
    },
    "singer_band_model": {
        "name": "Singer vs Band (Attention Routing)",
        "principle": "Only ONE element is the 'singer' at any given moment. "
                     "Everything else is the 'band' -- invisible ninja sounds.",
        "singer_per_section": {
            "intro": "PAD / ATMOSPHERE (gentle vocalist)",
            "build": "RISER / ARP (building anticipation vocalist)",
            "drop": "MID BASS / GROWL (the screaming vocalist)",
            "breakdown": "LEAD / CHORDS (emotional vocalist)",
            "outro": "PAD fading (departing vocalist)",
        },
        "attention_theft_checklist": [
            "Louder than the singer? → Turn it down.",
            "Brighter than the singer? → Low-pass it.",
            "Dryer than the singer? → Add reverb to push it back.",
            "Wider than the singer? → Narrow it.",
            "Dominating 2-4.5 kHz? → EQ cut in that range.",
        ],
    },
    "contrast_framework": {
        "name": "Contrast is King",
        "principle": "Every peak is defined by the valley before it. "
                     "Maximize contrast at every section boundary.",
        "contrast_dimensions": {
            "width":      {"valley": "mono/narrow",  "peak": "wide stereo"},
            "frequency":  {"valley": "thin/HP'd",    "peak": "full spectrum"},
            "volume":     {"valley": "quiet",         "peak": "loud"},
            "density":    {"valley": "sparse (1-2)",  "peak": "dense (all in)"},
            "brightness": {"valley": "dark (LP'd)",   "peak": "bright/open"},
            "rhythm":     {"valley": "half-time/none", "peak": "full beat"},
        },
        "golden_contrast_ratio": f"Drop energy = phi ({PHI:.3f}) x breakdown energy. "
                                 f"Not 2x (too jarring), not 1.2x (too flat). "
                                 f"Phi is the perceptual sweet spot.",
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
# QUALITY METRICS — phi_analyzer integration (Session 128)
# ═══════════════════════════════════════════════════════════════════════════

def rate_output_quality(wav_path: str = "") -> dict:
    """Rate an output file using phi_analyzer and map to belt progression.

    If *wav_path* is empty, returns a template with zero scores.
    """
    try:
        from engine.phi_analyzer import analyze_wav_phi
    except ImportError:
        analyze_wav_phi = None

    score = 0.0
    phi_score_dict: dict = {}

    if wav_path and analyze_wav_phi is not None:
        from pathlib import Path as _P
        if _P(wav_path).exists():
            try:
                result = analyze_wav_phi(wav_path)
                score = result.composite
                phi_score_dict = result.as_dict()
            except Exception:
                pass

    # Map score to belt rank
    belt_thresholds = [
        (0.85, "Black Belt"),
        (0.70, "Brown Belt"),
        (0.55, "Purple Belt"),
        (0.40, "Blue Belt"),
        (0.25, "Green Belt"),
        (0.10, "Yellow Belt"),
        (0.0,  "White Belt"),
    ]
    assigned_belt = "White Belt"
    for threshold, belt in belt_thresholds:
        if score >= threshold:
            assigned_belt = belt
            break

    return {
        "phi_coherence_score": round(score, 4),
        "phi_details": phi_score_dict,
        "assigned_quality_belt": assigned_belt,
        "wav_path": wav_path,
    }


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION ROADMAP — Module-to-Dojo mapping for wiring priority
# Maps every unwired engine module to Approach phase, belt level, priority.
# Generated from comprehensive dojo-guided audit (2025-07-22).
# ═══════════════════════════════════════════════════════════════════════════

INTEGRATION_ROADMAP: dict = {
    "sprint_1_p0": {
        "theme": "Render quality — the song sounds better immediately",
        "dojo_rule": "#1 FINISH MUSIC — improve the existing render",
        "modules": [
            {"module": "tuning_system",         "phase": "SKETCH",       "belt": "GREEN",  "wire_point": "Phase 1 DNA — enforce 432Hz doctrine"},
            {"module": "sub_bass",              "phase": "SKETCH",       "belt": "GREEN",  "wire_point": "Phase 2 bass — 5 sub types vs 1 inline"},
            {"module": "chord_pad",             "phase": "SKETCH",       "belt": "GREEN",  "wire_point": "Phase 2 pads — proper chord voicings"},
            {"module": "dc_remover",            "phase": "MIX",          "belt": "GREEN",  "wire_point": "Phase 2-3 per-stem — DC offset cleanup"},
            {"module": "normalizer",            "phase": "MASTER",       "belt": "GREEN",  "wire_point": "Phase 4 pre-master — LUFS/PHI normalization"},
            {"module": "frequency_analyzer",    "phase": "MIX",          "belt": "PURPLE", "wire_point": "Phase 3 — Tetris Board frequency data"},
            {"module": "audio_analyzer",        "phase": "MIX",          "belt": "YELLOW", "wire_point": "Phase 3-4 QA — comprehensive mix stats"},
            {"module": "key_detector",          "phase": "COLLECT",      "belt": "YELLOW", "wire_point": "Phase 1 DNA — key consistency validation"},
            {"module": "phi_analyzer",          "phase": "MASTER",       "belt": "PURPLE", "wire_point": "Phase 4 final QA — phi coherence gate"},
            {"module": "reference_library",     "phase": "MIX",          "belt": "BLUE",   "wire_point": "Phase 4 comparison — Song Mapping"},
            {"module": "fibonacci_feedback",    "phase": "ALL",          "belt": "PURPLE", "wire_point": "Outer loop — 144-step self-correction"},
            {"module": "arrangement_sequencer", "phase": "ARRANGE",      "belt": "BLUE",   "wire_point": "Phase 1 structure — dojo-aligned templates"},
            {"module": "drum_pipeline",         "phase": "SKETCH",       "belt": "BLUE",   "wire_point": "Phase 2 drums — 6-stage pipeline"},
            {"module": "midbass_pipeline",      "phase": "SKETCH",       "belt": "BLUE",   "wire_point": "Phase 2 bass — 6-stage pipeline"},
        ],
    },
    "sprint_2_p1": {
        "theme": "Professional pipeline depth",
        "dojo_rule": "#2 Separate creation from revision",
        "modules": [
            {"module": "dither",                "phase": "MASTER",       "belt": "GREEN"},
            {"module": "crossfade",             "phase": "ARRANGE",      "belt": "GREEN"},
            {"module": "dynamics_processor",    "phase": "MIX",          "belt": "BLUE"},
            {"module": "bus_router",            "phase": "MIX",          "belt": "BLUE"},
            {"module": "signal_chain",          "phase": "MIX",          "belt": "BLUE"},
            {"module": "stem_mixer",            "phase": "MIX",          "belt": "BLUE"},
            {"module": "lead_pipeline",         "phase": "SKETCH",       "belt": "BLUE"},
            {"module": "fx_pipeline",           "phase": "SKETCH",       "belt": "BLUE"},
            {"module": "harmonic_gen",          "phase": "SOUND_DESIGN", "belt": "PURPLE"},
            {"module": "spectral_gate",         "phase": "MIX",          "belt": "PURPLE"},
            {"module": "ambient_texture",       "phase": "SKETCH",       "belt": "BLUE"},
            {"module": "trance_arp",            "phase": "SKETCH",       "belt": "BLUE"},
            {"module": "wave_folder",           "phase": "SOUND_DESIGN", "belt": "BLUE"},
            {"module": "ring_mod",              "phase": "SOUND_DESIGN", "belt": "BLUE"},
            {"module": "midi_export",           "phase": "RELEASE",      "belt": "GREEN"},
            {"module": "markov_melody",         "phase": "SKETCH",       "belt": "BLUE"},
            {"module": "memory",                "phase": "ALL",          "belt": "PURPLE"},
            {"module": "session_logger",        "phase": "ALL",          "belt": "PURPLE"},
            {"module": "lessons_learned",       "phase": "ALL",          "belt": "PURPLE"},
            {"module": "evolution_engine",      "phase": "ALL",          "belt": "PURPLE"},
            {"module": "audio_mmap",            "phase": "ALL",          "belt": "GREEN"},
            {"module": "metadata",              "phase": "RELEASE",      "belt": "GREEN"},
            {"module": "format_converter",      "phase": "RELEASE",      "belt": "GREEN"},
            {"module": "bounce",                "phase": "RELEASE",      "belt": "GREEN"},
        ],
    },
    "sprint_3_p2": {
        "theme": "Everything the Black Belt needs",
        "dojo_rule": "#4 Volume is the teacher",
        "module_groups": [
            "Serum 2 lifecycle (serum2 + serum2_preset + serum_blueprint + serum2_controller)",
            "VIP + tags (vip_pack + tag_system + preset_mutator + preset_vcs)",
            "Advanced analysis (pattern_recognizer + genre_detector + dubstep_taste_analyzer)",
            "Arrangement (audio_splitter + audio_stitcher + clip_manager)",
            "Evolution (genetic_evolver + preset_mutator + snapshot_manager)",
            "Release assets (artwork_generator + watermark + waveform_display)",
            "Templates (template_generator + ep_builder + macro_controller)",
        ],
    },
    "sprint_4_p3": {
        "theme": "Performance and ecosystem",
        "dojo_rule": "#33 Perform automation with knobs",
        "module_groups": [
            "Ableton Live (ableton_bridge + link_sync + live_fx + osc_controller)",
            "SUBPHONICS AI (subphonics + subphonics_server + chain_commands)",
            "Autonomous (autonomous + grandmaster + ascension)",
            "Live performance (scene_system + clip_launcher + looper + performance_recorder)",
            "External (soundcloud_pipeline + production_pipeline + collaboration)",
        ],
    },
    "workflow_chains": {
        "collect":  ["sample_library", "sample_slicer", "tempo_detector", "tag_system", "wav_pool"],
        "sketch":   ["tuning_system", "template_generator", "sub_bass", "chord_pad", "ambient_texture", "trance_arp"],
        "arrange":  ["arrangement_sequencer", "crossfade", "drum_pipeline", "midbass_pipeline", "lead_pipeline", "fx_pipeline"],
        "mix":      ["frequency_analyzer", "bus_router", "signal_chain", "dynamics_processor", "dc_remover", "stem_mixer", "normalizer"],
        "master":   ["audio_analyzer", "phi_analyzer", "reference_library", "normalizer", "dither"],
        "release":  ["metadata", "format_converter", "bounce", "midi_export", "watermark", "artwork_generator", "vip_pack", "sample_pack_builder"],
        "learning": ["session_logger", "memory", "lessons_learned", "evolution_engine", "fibonacci_feedback"],
    },
    "alignment_opportunities": [
        "Unified spectral analysis pass — frequency_analyzer + audio_analyzer + harmonic_analysis share one FFT",
        "Pipeline base class — drum/midbass/lead/fx all share 6-stage architecture",
        "Serum 2 lifecycle — model + generate + IO + control + distribute as one subsystem",
        "Unified asset management — sample_library + wav_pool + tag_system + galatcia + preset_browser",
        "Closed-loop learning — fibonacci_feedback + lessons_learned + memory + evolution_engine + session_logger",
        "Complete RELEASE pipeline — bounce + format_converter + metadata + watermark + artwork + midi + sample_pack",
    ],
    "redundancy_map": {
        "inline_sub_synthesis":      {"replacement": "sub_bass + sub_pipeline",     "lines_saved": 80},
        "inline_pad_chords":         {"replacement": "chord_pad",                   "lines_saved": 40},
        "inline_arp_gen":            {"replacement": "trance_arp",                  "lines_saved": 30},
        "inline_dc_removal":         {"replacement": "dc_remover",                  "lines_saved": 15},
        "inline_gain_norm":          {"replacement": "normalizer",                  "lines_saved": 20},
        "inline_drum_render":        {"replacement": "drum_pipeline",               "lines_saved": 200},
        "inline_bass_render":        {"replacement": "midbass_pipeline",            "lines_saved": 300},
        "inline_lead_render":        {"replacement": "lead_pipeline",               "lines_saved": 150},
        "inline_fx_render":          {"replacement": "fx_pipeline",                 "lines_saved": 100},
        "inline_stem_sum":           {"replacement": "stem_mixer",                  "lines_saved": 50},
        "raw_wav_io":                {"replacement": "audio_mmap",                  "lines_saved": 0, "note": "scattered, perf gain"},
    },
    "stats": {
        "total_unwired": 131,
        "functional": 104,
        "partial": 24,
        "stub": 2,
        "missing": 1,
        "sprint_1_count": 14,
        "sprint_2_count": 24,
        "estimated_forge_lines_replaced": 985,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Generate all Dojo engine outputs
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all Producer Dojo / ill.Gates engine JSON outputs."""
    out = Path("output/dojo")
    out.mkdir(parents=True, exist_ok=True)

    # Load belt thresholds from memory config if available
    belt_cfg = get_config_value(
        "memory_v1", "growth", "belt_progression", default=None)

    # 1) Full methodology reference
    method_path = out / "dojo_methodology.json"
    methodology = {
        "artist_profile": ARTIST_PROFILE,
        "platform": DOJO_PLATFORM,
        "techniques_count": len(DOJO_TECHNIQUES),
        "techniques": DOJO_TECHNIQUES,
        "belt_config_source": "memory_v1.yaml" if belt_cfg else "hardcoded",
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

    # 7) Creative philosophy (NEW — deep dive research)
    phil_path = out / "dojo_creative_philosophy.json"
    phil_data = {
        "creative_philosophy": CREATIVE_PHILOSOPHY,
        "ill_gates_rules": ILL_GATES_RULES,
        "rules_count": len(ILL_GATES_RULES),
    }
    with open(phil_path, "w") as f:
        json.dump(phil_data, f, indent=2)
    print(f"  ✓ Creative philosophy    → {phil_path}")

    # 8) Stock device mastery (NEW — deep dive research)
    stock_path = out / "dojo_stock_devices.json"
    stock_data = {
        "stock_device_mastery": STOCK_DEVICE_MASTERY,
        "device_count": len(STOCK_DEVICE_MASTERY),
        "source": "ill.Gates blog: 'Invest in Stock! ...Devices.' (Jan 2026)",
    }
    with open(stock_path, "w") as f:
        json.dump(stock_data, f, indent=2)
    print(f"  ✓ Stock device mastery   → {stock_path}")

    # 9) Low pass techniques (NEW — deep dive research)
    lp_path = out / "dojo_low_pass_techniques.json"
    lp_data = {
        "low_pass_techniques": LOW_PASS_TECHNIQUES,
        "technique_count": len(LOW_PASS_TECHNIQUES),
        "source": "ill.Gates blog: '5 Killer Low Pass Tips' (Jan 2026)",
    }
    with open(lp_path, "w") as f:
        json.dump(lp_data, f, indent=2)
    print(f"  ✓ Low pass techniques    → {lp_path}")

    # 10) Unbeatable Drums catalog (NEW — deep dive research)
    drums_path = out / "dojo_unbeatable_drums.json"
    with open(drums_path, "w") as f:
        json.dump(UNBEATABLE_DRUMS, f, indent=2)
    print(f"  ✓ Unbeatable Drums       → {drums_path}")

    # 11) Producer's Path course (NEW — deep dive research)
    pp_path = out / "dojo_producers_path.json"
    with open(pp_path, "w") as f:
        json.dump(PRODUCERS_PATH, f, indent=2)
    print(f"  ✓ Producer's Path        → {pp_path}")

    # 12) Integration Roadmap (dojo-guided module wiring plan)
    roadmap_path = out / "dojo_integration_roadmap.json"
    with open(roadmap_path, "w") as f:
        json.dump(INTEGRATION_ROADMAP, f, indent=2)
    print(f"  ✓ Integration Roadmap    → {roadmap_path}")

    # Stats
    print()
    print("  Producer Dojo Engine Stats (Enhanced):")
    print(f"    Belt levels:          {len(BELT_SYSTEM)}")
    print(f"    Approach phases:      {len(THE_APPROACH)}")
    print(f"    Techniques:           {len(DOJO_TECHNIQUES)}")
    print(f"    Stock devices:        {len(STOCK_DEVICE_MASTERY)}")
    print(f"    Low pass techniques:  {len(LOW_PASS_TECHNIQUES)}")
    print(f"    Unbeatable kits:      {len(UNBEATABLE_DRUMS['kits'])}")
    print(f"    ill.Gates rules:      {len(ILL_GATES_RULES)}")
    print(f"    128 Rack categories:  {len(rack_data['categories'])}")
    print(f"    Session tracks:       {session_data['track_count']}")
    print(f"    Session scenes:       {session_data['scene_count']}")
    print(f"    Tracks to Black Belt: {phi_belt_progression()['total_tracks_to_black_belt']}")
    print(f"    ill.Gates albums:     {len(ARTIST_PROFILE['discography']['albums'])}")
    print(f"    ill.Gates EPs:        {len(ARTIST_PROFILE['discography']['eps'])}")
    print(f"    Star students:        {len(ARTIST_PROFILE['star_students'])}")
    print(f"    Philosophy essays:    {len(CREATIVE_PHILOSOPHY)}")
    print(f"    Roadmap modules:      {INTEGRATION_ROADMAP['stats']['total_unwired']} ({INTEGRATION_ROADMAP['stats']['functional']} functional)")
    print(f"    JSON outputs:         12")


if __name__ == "__main__":
    main()
