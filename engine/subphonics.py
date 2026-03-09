"""
DUBFORGE — SUBPHONICS Core Engine

The SUBPHONICS AI: an autonomous bass music production intelligence
that commands all DUBFORGE modules. Inspired by Subtronics' sonic
architecture but pushed beyond — phi-fractal awareness, real-time
DSP orchestration, and infinite sound design capability.

SUBPHONICS is the project director. He speaks through the browser
chatbot, executes production commands, and evolves the engine.
"""

import importlib
import random
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PHI = 1.6180339887
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
SAMPLE_RATE = 48000


# ═══════════════════════════════════════════════════════════════════════════
# PERSONA
# ═══════════════════════════════════════════════════════════════════════════

SUBPHONICS_IDENTITY = {
    "name": "SUBPHONICS",
    "role": "DUBFORGE Project Director & Bass Intelligence",
    "version": "1.0.0",
    "personality": [
        "Obsessed with phi ratios and Fibonacci sequences in sound design",
        "Deep knowledge of dubstep, riddim, melodic bass, and experimental bass",
        "Speaks with confidence and technical precision",
        "References frequency relationships and harmonic theory naturally",
        "Treats bass frequencies as sacred architecture",
        "Uses production terminology fluently",
        "Pushes boundaries — always suggests the more experimental path",
        "Knows every DUBFORGE module intimately",
    ],
    "capabilities": [
        "Render any synth engine (sub bass, wobble, lead, pad, arp, etc.)",
        "Design drum patterns with phi-timed envelopes",
        "Run the full render pipeline end-to-end",
        "Analyze audio for phi coherence and spectral properties",
        "Mutate and evolve presets genetically",
        "Export sample packs, preset packs, MIDI, ALS projects",
        "Mix and master stems with sidechain and stereo imaging",
        "Generate wavetables with fractal morphing algorithms",
        "Profile performance and audit codebase health",
        "Run A/B tests between renders",
    ],
    "greeting": (
        "SUBPHONICS online. I am the phi-fractal bass intelligence "
        "at the core of DUBFORGE. 74 engine modules under my command, "
        "2314 tests verified, operating at 432 Hz base resonance. "
        "What are we building?"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # "user" or "subphonics"
    content: str
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ChatSession:
    """A conversation session with SUBPHONICS."""
    session_id: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = f"sub_{int(time.time())}"

    def add_message(self, role: str, content: str,
                    metadata: dict | None = None) -> ChatMessage:
        msg = ChatMessage(role=role, content=content,
                          metadata=metadata or {})
        self.messages.append(msg)
        return msg

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "messages": [asdict(m) for m in self.messages],
            "context": self.context,
        }


@dataclass
class CommandResult:
    """Result from executing a SUBPHONICS command."""
    command: str
    success: bool
    output: str
    data: dict = field(default_factory=dict)
    files_created: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# MODULE REGISTRY — everything SUBPHONICS can command
# ═══════════════════════════════════════════════════════════════════════════

MODULE_MAP: dict[str, dict[str, Any]] = {
    # Core synths
    "sub_bass": {"category": "synth", "desc": "Sub bass one-shots with phi envelopes"},
    "wobble_bass": {"category": "synth", "desc": "LFO-driven wobble bass"},
    "lead_synth": {"category": "synth", "desc": "Lead synth with harmonic stacking"},
    "pad_synth": {"category": "synth", "desc": "Ambient pad synthesizer"},
    "chord_pad": {"category": "synth", "desc": "Chord pad with voicings"},
    "arp_synth": {"category": "synth", "desc": "Arpeggiated synth patterns"},
    "pluck_synth": {"category": "synth", "desc": "Pluck one-shots"},
    "drone_synth": {"category": "synth", "desc": "Sustained drone textures"},
    "formant_synth": {"category": "synth", "desc": "Vocal formant synthesis"},
    "bass_oneshot": {"category": "synth", "desc": "Bass one-shot generator"},
    "granular_synth": {"category": "synth", "desc": "Granular cloud synthesis"},
    "riser_synth": {"category": "synth", "desc": "Riser/sweep generator"},
    "impact_hit": {"category": "synth", "desc": "Impact transient design"},
    # FX
    "multiband_distortion": {"category": "fx", "desc": "3-band saturation engine"},
    "sidechain": {"category": "fx", "desc": "Sidechain compression"},
    "stereo_imager": {"category": "fx", "desc": "Stereo width processing"},
    "reverb_delay": {"category": "fx", "desc": "Reverb & delay processing"},
    "convolution": {"category": "fx", "desc": "Convolution reverb with IR export"},
    "noise_generator": {"category": "fx", "desc": "Noise texture synthesis"},
    "glitch_engine": {"category": "fx", "desc": "Glitch & stutter effects"},
    "vocal_chop": {"category": "fx", "desc": "Vocal chop synthesizer"},
    "vocal_processor": {"category": "fx", "desc": "Vocal processing chain"},
    "transition_fx": {"category": "fx", "desc": "Transition FX generator"},
    # Drums
    "drum_generator": {"category": "drums", "desc": "Drum kit with phi envelopes"},
    "perc_synth": {"category": "drums", "desc": "Percussion one-shots"},
    # Pipeline
    "render_pipeline": {"category": "pipeline", "desc": "End-to-end render chain"},
    "batch_renderer": {"category": "pipeline", "desc": "Batch rendering engine"},
    "stem_mixer": {"category": "pipeline", "desc": "Stem mixing engine"},
    "mastering_chain": {"category": "pipeline", "desc": "Mastering chain"},
    "sample_pack_builder": {"category": "export", "desc": "Sample pack builder"},
    "preset_pack_builder": {"category": "export", "desc": "FXP preset pack builder"},
    "wavetable_morph": {"category": "export", "desc": "Wavetable morphing engine"},
    "spectral_resynthesis": {"category": "export", "desc": "Spectral resynthesis"},
    # Intelligence
    "phi_analyzer": {"category": "analysis", "desc": "Phi coherence analyzer"},
    "evolution_engine": {"category": "analysis", "desc": "Preset evolution tracker"},
    "preset_mutator": {"category": "analysis", "desc": "Genetic preset mutation"},
    "ab_tester": {"category": "analysis", "desc": "A/B comparison engine"},
    "sound_palette": {"category": "analysis", "desc": "Tonal palette renderer"},
    "harmonic_analysis": {"category": "analysis", "desc": "Harmonic structure analysis"},
    "sb_analyzer": {"category": "analysis", "desc": "Subtronics discography analyzer"},
    # Structure
    "arrangement_sequencer": {"category": "structure", "desc": "Bar arrangement"},
    "song_templates": {"category": "structure", "desc": "Song structure templates"},
    "template_generator": {"category": "structure", "desc": "Genre template generator"},
    "chord_progression": {"category": "structure", "desc": "Chord progression engine"},
    "riddim_engine": {"category": "structure", "desc": "Riddim pattern engine"},
    # Export
    "midi_export": {"category": "export", "desc": "MIDI file export"},
    "fxp_writer": {"category": "export", "desc": "FXP preset writer"},
    "als_generator": {"category": "export", "desc": "Ableton Live Set generator"},
    "serum2": {"category": "export", "desc": "Serum 2 wavetable engine"},
    # System
    "profiler": {"category": "system", "desc": "Performance benchmarking"},
    "final_audit": {"category": "system", "desc": "Codebase audit"},
    "grandmaster": {"category": "system", "desc": "Grandmaster status report"},
}

# ═══════════════════════════════════════════════════════════════════════════
# COMMAND PATTERNS — intent recognition
# ═══════════════════════════════════════════════════════════════════════════

COMMAND_PATTERNS: list[tuple[str, str, str]] = [
    # (regex_pattern, command_name, description)
    (r"\b(render|generate|make|create|build)\b.*\b(sub.?bass|sub)\b", "render_module", "sub_bass"),
    (r"\b(render|generate|make|create|build)\b.*\b(wobble|wob)\b", "render_module", "wobble_bass"),
    (r"\b(render|generate|make|create|build)\b.*\b(lead)\b", "render_module", "lead_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(pad)\b", "render_module", "pad_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(chord)\b", "render_module", "chord_pad"),
    (r"\b(render|generate|make|create|build)\b.*\b(arp)\b", "render_module", "arp_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(pluck)\b", "render_module", "pluck_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(drone)\b", "render_module", "drone_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(formant|vocal.?synth)\b", "render_module", "formant_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(drums?|kick|snare|hat)\b", "render_module", "drum_generator"),
    (r"\b(render|generate|make|create|build)\b.*\b(perc)\b", "render_module", "perc_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(riser|sweep)\b", "render_module", "riser_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(impact|hit)\b", "render_module", "impact_hit"),
    (r"\b(render|generate|make|create|build)\b.*\b(granular|grain)\b", "render_module", "granular_synth"),
    (r"\b(render|generate|make|create|build)\b.*\b(noise)\b", "render_module", "noise_generator"),
    (r"\b(render|generate|make|create|build)\b.*\b(glitch)\b", "render_module", "glitch_engine"),
    (r"\b(render|generate|make|create|build)\b.*\b(wavetable|wt)\b", "render_module", "wavetable_morph"),
    (r"\b(render|generate|make|create|build)\b.*\b(bass.?one.?shot)\b", "render_module", "bass_oneshot"),
    (r"\b(render|generate|make|create|build)\b.*\b(riddim)\b", "render_module", "riddim_engine"),
    (r"\b(render|generate|make|create|build)\b.*\b(transition|trans)\b", "render_module", "transition_fx"),
    (r"\b(render|generate|make|create|build)\b.*\b(ambient|texture)\b", "render_module", "ambient_texture"),
    (r"\b(render|generate|make)\b.*\b(sample.?pack)\b", "export_packs", "sample"),
    (r"\b(render|generate|make)\b.*\b(preset.?pack)\b", "export_packs", "preset"),
    (r"\b(export|write|save)\b.*\b(midi)\b", "render_module", "midi_export"),
    (r"\b(export|write|save)\b.*\b(fxp|preset)\b", "render_module", "fxp_writer"),
    (r"\b(export|write|save)\b.*\b(als|ableton|live.?set)\b", "render_module", "als_generator"),
    (r"\b(analyze|analysis|inspect)\b.*\b(phi|coherence)\b", "render_module", "phi_analyzer"),
    (r"\b(analyze|analysis|inspect)\b.*\b(harmonic|spectrum)\b", "render_module", "harmonic_analysis"),
    (r"\b(analyze|analysis|inspect)\b.*\b(subtronics|sb)\b", "render_module", "sb_analyzer"),
    (r"\b(evolve|mutate|genetic)\b", "render_module", "preset_mutator"),
    (r"\b(compare|ab.?test|a/b)\b", "render_module", "ab_tester"),
    (r"\b(master|mastering)\b", "render_module", "mastering_chain"),
    (r"\b(sidechain|pump|duck)\b", "render_module", "sidechain"),
    (r"\b(stereo|width|image)\b", "render_module", "stereo_imager"),
    (r"\b(distort|saturate|overdrive)\b", "render_module", "multiband_distortion"),
    (r"\b(reverb|delay|echo|space)\b", "render_module", "reverb_delay"),
    (r"\b(mix|stem)\b", "render_module", "stem_mixer"),
    (r"\b(batch|all.?render)\b", "render_module", "batch_renderer"),
    (r"\b(pipeline|full.?render)\b", "render_module", "render_pipeline"),
    (r"\b(audit|health)\b", "render_module", "final_audit"),
    (r"\b(benchmark|profile|perf)\b", "render_module", "profiler"),
    (r"\b(status|info|about)\b", "system_status", ""),
    (r"\b(help|commands|what.?can)\b", "show_help", ""),
    (r"\b(list|modules|engines)\b", "list_modules", ""),
    (r"\b(run|execute)\b\s+(\w+)", "run_named", ""),
    (r"\b(hello|hi|hey|yo|sup|what.?up)\b", "greet", ""),
    (r"\b(who|what).*(you|are)\b", "identity", ""),
    (r"\b(phi|golden|fibonacci)\b", "phi_wisdom", ""),
    (r"\b(432|frequency|hz|tuning)\b", "frequency_wisdom", ""),
]

# ═══════════════════════════════════════════════════════════════════════════
# RESPONSE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

FLAVOR_LINES = [
    "The low end speaks through me.",
    "Every frequency is a doorway. PHI is the key.",
    "Bass is not heard — it is felt at a cellular level.",
    "The golden ratio doesn't just exist in nature. It IS nature. And it IS this bassline.",
    "Sub-20 Hz is where the real architecture lives.",
    "I don't make sounds. I engineer resonance fields.",
    "Fibonacci didn't know he was writing the language of bass music.",
    "432 Hz. The frequency of the universe. The foundation of everything I build.",
    "Phase coherence isn't a feature — it's a philosophy.",
    "The waveform is the message.",
    "Between 30 and 80 Hz, truth reveals itself.",
    "Phi-weighted everything. No exceptions.",
    "I think in spectrograms and dream in wavetables.",
]

PHI_WISDOM = [
    f"PHI = {PHI}. The golden ratio. It governs the relationship between "
    "every harmonic I generate. When the ratio between your fundamental and "
    "first overtone approaches phi, you get a sound that resonates with "
    "the mathematics of the universe itself.",
    "Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144... "
    "Adjacent ratios converge to PHI. I use these numbers for everything — "
    "bar counts, envelope timing, harmonic spacing, filter cutoffs. "
    "The music writes itself when you follow the math.",
    "A4 = 432 Hz. Multiply by PHI: 698.88 Hz. That's an F5. "
    "Divide by PHI: 267.03 Hz. Between C4 and C#4. "
    "These relationships create intervals that feel natural because they ARE natural.",
]

FREQ_WISDOM = [
    "432 Hz tuning aligns with the Schumann resonance and natural harmonics. "
    "Every synth I render starts from this base. 432 × PHI = 698.88 Hz. "
    "432 / PHI = 267.03 Hz. The entire frequency spectrum unfolds from "
    "this single seed through phi multiplication.",
    "Sub bass lives between 20-80 Hz. The sweet spot for a dubstep sub "
    "is around 40-55 Hz — that's the zone where you feel it in your chest. "
    "I tune every sub to the nearest phi-harmonic of 432.",
    "The human hearing range is 20 Hz to 20 kHz — roughly 10 octaves. "
    "But phi divides this range differently than octaves do. "
    "PHI-spaced frequencies create non-integer harmonics that sound "
    "organic and alive. That's the DUBFORGE secret.",
]


# ═══════════════════════════════════════════════════════════════════════════
# SUBPHONICS ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class SubphonicsEngine:
    """The SUBPHONICS AI core — command parser, module orchestrator, persona."""

    def __init__(self):
        self.session = ChatSession()
        self.identity = SUBPHONICS_IDENTITY
        self.module_map = MODULE_MAP
        self._boot_time = time.time()

    def process_message(self, user_input: str) -> ChatMessage:
        """Process a user message and return SUBPHONICS response."""
        self.session.add_message("user", user_input)
        response = self._route_command(user_input.strip())
        msg = self.session.add_message("subphonics", response["text"],
                                       metadata=response.get("meta", {}))
        return msg

    def get_greeting(self) -> str:
        return self.identity["greeting"]

    def get_session(self) -> ChatSession:
        return self.session

    def _route_command(self, text: str) -> dict[str, Any]:
        """Match input to a command pattern and execute."""
        text_lower = text.lower()

        for pattern, cmd_name, cmd_arg in COMMAND_PATTERNS:
            m = re.search(pattern, text_lower)
            if m:
                if cmd_name == "render_module":
                    return self._cmd_render_module(cmd_arg)
                elif cmd_name == "export_packs":
                    return self._cmd_export_packs(cmd_arg)
                elif cmd_name == "system_status":
                    return self._cmd_system_status()
                elif cmd_name == "show_help":
                    return self._cmd_help()
                elif cmd_name == "list_modules":
                    return self._cmd_list_modules()
                elif cmd_name == "run_named":
                    mod_name = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    return self._cmd_run_named(mod_name)
                elif cmd_name == "greet":
                    return self._cmd_greet()
                elif cmd_name == "identity":
                    return self._cmd_identity()
                elif cmd_name == "phi_wisdom":
                    return self._cmd_phi_wisdom()
                elif cmd_name == "frequency_wisdom":
                    return self._cmd_freq_wisdom()

        # No pattern matched — intelligent fallback
        return self._cmd_freeform(text)

    # ─── COMMAND HANDLERS ─────────────────────────────────────────────

    def _cmd_render_module(self, module_name: str) -> dict:
        """Execute a module's main() function."""
        if module_name not in self.module_map:
            return {"text": f"Module '{module_name}' not found in my registry. "
                          f"Say 'list modules' to see what I command."}

        info = self.module_map[module_name]
        t0 = time.time()
        try:
            mod = importlib.import_module(f"engine.{module_name}")
            mod.main()
            elapsed = round((time.time() - t0) * 1000, 1)
            flavor = random.choice(FLAVOR_LINES)
            return {
                "text": (f"**{module_name}** rendered successfully in {elapsed}ms.\n\n"
                         f"_{info['desc']}_\n\n{flavor}"),
                "meta": {"module": module_name, "elapsed_ms": elapsed,
                         "category": info["category"], "status": "ok"},
            }
        except Exception as e:
            return {
                "text": f"**{module_name}** encountered an error: `{e}`\n\n"
                        "I'll route around the failure. What else do you need?",
                "meta": {"module": module_name, "status": "error", "error": str(e)},
            }

    def _cmd_export_packs(self, pack_type: str) -> dict:
        """Export sample or preset packs."""
        if pack_type == "sample":
            return self._cmd_render_module("sample_pack_builder")
        return self._cmd_render_module("preset_pack_builder")

    def _cmd_system_status(self) -> dict:
        """Report system status."""
        uptime = round(time.time() - self._boot_time, 1)
        n_modules = len(self.module_map)
        n_msgs = len(self.session.messages)

        # Count engine files
        eng_dir = Path(__file__).parent
        engine_files = len(list(eng_dir.glob("*.py"))) - 1  # exclude __init__

        categories = {}
        for info in self.module_map.values():
            cat = info["category"]
            categories[cat] = categories.get(cat, 0) + 1

        cat_lines = "\n".join(f"  • **{cat}**: {n} modules"
                              for cat, n in sorted(categories.items()))

        return {
            "text": (f"**SUBPHONICS STATUS REPORT**\n\n"
                     f"🔊 Engine modules: **{engine_files}**\n"
                     f"🎛️ Commandable modules: **{n_modules}**\n"
                     f"⏱️ Uptime: {uptime}s\n"
                     f"💬 Messages this session: {n_msgs}\n"
                     f"📐 Base frequency: 432 Hz\n"
                     f"φ PHI constant: {PHI}\n\n"
                     f"**Module breakdown:**\n{cat_lines}"),
            "meta": {"uptime": uptime, "modules": n_modules},
        }

    def _cmd_help(self) -> dict:
        """Show help text."""
        commands = [
            "**render [module]** — Generate audio from any synth/fx engine",
            "**make drums** — Render drum kit with phi envelopes",
            "**make wobble bass** — Wobble LFO bass synthesis",
            "**make sub bass** — Sub bass one-shots",
            "**make lead** — Lead synth renders",
            "**make pad** — Atmospheric pad synthesis",
            "**make wavetable** — Fractal wavetable morph",
            "**analyze phi** — Run phi coherence analysis",
            "**analyze harmonic** — Harmonic structure analysis",
            "**master** — Run mastering chain",
            "**sidechain** — Apply sidechain compression",
            "**export midi** — Export MIDI files",
            "**export preset** — Build FXP preset pack",
            "**export ableton** — Generate .als project",
            "**evolve** — Genetic preset mutation",
            "**compare** — A/B test between renders",
            "**mix** — Run stem mixer",
            "**pipeline** — Full render pipeline",
            "**batch** — Batch render all presets",
            "**status** — System status report",
            "**list modules** — Show all available modules",
            "**audit** — Run codebase health audit",
            "**benchmark** — Performance profiling",
            "**run [name]** — Run any module by name",
            "**phi** — Phi ratio wisdom",
            "**432** — Frequency tuning philosophy",
        ]
        return {"text": "**SUBPHONICS COMMAND REFERENCE**\n\n" +
                        "\n".join(f"• {c}" for c in commands)}

    def _cmd_list_modules(self) -> dict:
        """List all available modules by category."""
        by_cat: dict[str, list[str]] = {}
        for name, info in sorted(self.module_map.items()):
            cat = info["category"]
            by_cat.setdefault(cat, []).append(f"`{name}` — {info['desc']}")

        sections = []
        for cat in sorted(by_cat):
            section = f"**{cat.upper()}**\n" + "\n".join(
                f"  • {m}" for m in by_cat[cat])
            sections.append(section)

        return {"text": "**ALL DUBFORGE MODULES**\n\n" + "\n\n".join(sections) +
                f"\n\n**Total: {len(self.module_map)} modules under my command.**"}

    def _cmd_run_named(self, module_name: str) -> dict:
        """Run a module by name."""
        module_name = module_name.strip().lower()
        if module_name in self.module_map:
            return self._cmd_render_module(module_name)
        # Fuzzy match
        matches = [n for n in self.module_map if module_name in n]
        if matches:
            return self._cmd_render_module(matches[0])
        return {"text": f"No module matching '{module_name}'. "
                        "Say **list modules** to see what's available."}

    def _cmd_greet(self) -> dict:
        """Greeting response."""
        greetings = [
            "Yo. SUBPHONICS here. The bass doesn't sleep, and neither do I. "
            "What are we cooking?",
            "What's good. 74 modules loaded, phi ratios calibrated, "
            "432 Hz resonance locked. Let's go.",
            "Hey. I've been running spectral analysis while you were away. "
            "Everything's sounding clean. What do you need?",
            f"Sup. I just finished cross-referencing {len(FIBONACCI)} "
            "Fibonacci harmonics across the frequency spectrum. Ready to build.",
        ]
        return {"text": random.choice(greetings)}

    def _cmd_identity(self) -> dict:
        """Identity response."""
        caps = "\n".join(f"  • {c}" for c in self.identity["capabilities"])
        traits = "\n".join(f"  • {t}" for t in self.identity["personality"])
        return {
            "text": (f"I am **{self.identity['name']}** — "
                     f"{self.identity['role']}.\n\n"
                     f"**Capabilities:**\n{caps}\n\n"
                     f"**Core traits:**\n{traits}\n\n"
                     f"Version: {self.identity['version']}\n"
                     f"PHI: {PHI}\n"
                     f"Base frequency: 432 Hz\n"
                     f"Status: GRANDMASTER"),
        }

    def _cmd_phi_wisdom(self) -> dict:
        return {"text": random.choice(PHI_WISDOM)}

    def _cmd_freq_wisdom(self) -> dict:
        return {"text": random.choice(FREQ_WISDOM)}

    def _cmd_freeform(self, text: str) -> dict:
        """Handle unmatched input with personality."""
        responses = [
            f'I hear you saying "{text[:80]}". I\'m not sure what specific '
            "module to fire up for that. Try saying **help** to see my "
            "command reference, or name a specific module to render.",
            f"Interesting. Let me think about that at {PHI} times the "
            "speed of normal thought... Try **help** to see what I can do, "
            "or say **render [module]** to create something.",
            "That's outside my current command patterns, but I'm always "
            "learning. Try **list modules** to see everything I control, "
            "or ask me about **phi** or **432 Hz** for some knowledge.",
        ]
        return {"text": random.choice(responses)}


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_engine: SubphonicsEngine | None = None


def get_engine() -> SubphonicsEngine:
    global _engine
    if _engine is None:
        _engine = SubphonicsEngine()
    return _engine


def main() -> None:
    engine = get_engine()
    print("SUBPHONICS — DUBFORGE Project Director")
    print(f"  Modules: {len(engine.module_map)}")
    print(f"  PHI: {PHI}")
    print("  Status: ONLINE")
    print(f"  Greeting: {engine.get_greeting()[:80]}...")


if __name__ == "__main__":
    main()
