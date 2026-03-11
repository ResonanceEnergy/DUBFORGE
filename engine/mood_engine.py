"""
DUBFORGE — Mood Engine  (Session 155)

Mood-driven patch selection and sound design.
Maps emotional descriptors to synthesis parameters and module choices.
"""

from dataclasses import dataclass, field

from engine.config_loader import PHI
A4_432 = 432.0


@dataclass
class MoodProfile:
    """Mapping from mood descriptor to sound parameters."""
    name: str
    energy: float  # 0=calm, 1=intense
    darkness: float  # 0=bright, 1=dark
    complexity: float  # 0=simple, 1=complex
    tempo_mult: float = 1.0  # BPM multiplier
    freq_offset: float = 0.0  # Hz offset from base
    reverb_amount: float = 0.5
    distortion: float = 0.0
    suggested_modules: list[str] = field(default_factory=list)
    suggested_key: str = ""
    suggested_scale: str = ""
    tags: list[str] = field(default_factory=list)


# Mood database
MOODS: dict[str, MoodProfile] = {
    "aggressive": MoodProfile(
        "aggressive", 0.95, 0.8, 0.7, 1.0, 0, 0.2, 0.9,
        ["wobble_bass", "riddim_engine", "drum_generator", "impact_hit",
         "growl_resampler", "multiband_distortion"],
        "F", "minor", ["heavy", "intense", "drop"]),
    "dark": MoodProfile(
        "dark", 0.6, 0.95, 0.6, 0.9, -12, 0.6, 0.4,
        ["drone_synth", "sub_bass", "pad_synth", "noise_generator",
         "reverb_delay"],
        "D", "minor", ["moody", "sinister", "deep"]),
    "euphoric": MoodProfile(
        "euphoric", 0.85, 0.2, 0.8, 1.1, 24, 0.7, 0.2,
        ["lead_synth", "arp_synth", "chord_pad", "riser_synth",
         "trance_arp"],
        "A", "major", ["uplifting", "bright", "emotional"]),
    "melancholy": MoodProfile(
        "melancholy", 0.3, 0.6, 0.5, 0.8, -7, 0.8, 0.1,
        ["pad_synth", "pluck_synth", "ambient_texture", "reverb_delay"],
        "E", "minor", ["sad", "emotional", "reflective"]),
    "hypnotic": MoodProfile(
        "hypnotic", 0.5, 0.5, 0.9, 1.0, 0, 0.6, 0.3,
        ["arp_synth", "wavetable_morph", "granular_synth", "lfo_matrix",
         "drone_synth"],
        "G", "dorian", ["trance", "repetitive", "mesmerizing"]),
    "chaotic": MoodProfile(
        "chaotic", 1.0, 0.5, 1.0, 1.2, 0, 0.3, 0.7,
        ["glitch_engine", "granular_synth", "noise_generator",
         "multiband_distortion", "sample_slicer"],
        "C", "chromatic", ["random", "unpredictable", "experimental"]),
    "dreamy": MoodProfile(
        "dreamy", 0.2, 0.3, 0.6, 0.7, 12, 0.9, 0.05,
        ["ambient_texture", "pad_synth", "granular_synth", "reverb_delay",
         "stereo_imager"],
        "C", "major", ["ambient", "floating", "ethereal"]),
    "heavy": MoodProfile(
        "heavy", 0.9, 0.9, 0.5, 0.95, -24, 0.3, 0.8,
        ["sub_bass", "wobble_bass", "drum_generator", "sidechain",
         "multiband_distortion"],
        "E", "minor", ["bass", "weight", "pressure"]),
    "minimal": MoodProfile(
        "minimal", 0.4, 0.4, 0.2, 0.9, 0, 0.4, 0.1,
        ["drum_generator", "sub_bass", "pluck_synth", "perc_synth"],
        "A", "minor", ["clean", "sparse", "tight"]),
    "epic": MoodProfile(
        "epic", 0.8, 0.4, 0.9, 1.0, 0, 0.7, 0.3,
        ["lead_synth", "chord_pad", "riser_synth", "impact_hit",
         "drum_generator", "arp_synth"],
        "D", "minor", ["cinematic", "powerful", "heroic"]),
    "chill": MoodProfile(
        "chill", 0.2, 0.3, 0.4, 0.75, 7, 0.7, 0.0,
        ["pad_synth", "pluck_synth", "ambient_texture", "chord_pad"],
        "G", "major", ["relaxed", "lofi", "smooth"]),
    "alien": MoodProfile(
        "alien", 0.6, 0.6, 0.95, 1.0, 33, 0.5, 0.5,
        ["formant_synth", "granular_synth", "spectral_resynthesis",
         "wavetable_morph", "vocal_processor"],
        "B", "whole_tone", ["weird", "otherworldly", "experimental"]),
    "tribal": MoodProfile(
        "tribal", 0.7, 0.5, 0.6, 1.0, -5, 0.4, 0.2,
        ["perc_synth", "drum_generator", "bass_oneshot",
         "impact_hit", "vocal_chop"],
        "A", "pentatonic", ["rhythmic", "primal", "organic"]),
    "filthy": MoodProfile(
        "filthy", 0.9, 0.85, 0.8, 1.0, -10, 0.2, 0.95,
        ["riddim_engine", "growl_resampler", "multiband_distortion",
         "wobble_bass", "glitch_engine"],
        "F", "minor", ["dirty", "gnarly", "disgusting"]),
}

# Mood aliases
MOOD_ALIASES: dict[str, str] = {
    "angry": "aggressive", "rage": "aggressive", "hard": "aggressive",
    "sad": "melancholy", "emotional": "melancholy", "crying": "melancholy",
    "happy": "euphoric", "bright": "euphoric", "uplifting": "euphoric",
    "spooky": "dark", "creepy": "dark", "sinister": "dark",
    "trippy": "hypnotic", "psychedelic": "hypnotic",
    "crazy": "chaotic", "insane": "chaotic", "wild": "chaotic",
    "ambient": "dreamy", "ethereal": "dreamy", "floating": "dreamy",
    "bass": "heavy", "low": "heavy", "deep": "heavy",
    "clean": "minimal", "sparse": "minimal",
    "big": "epic", "cinematic": "epic", "massive": "epic",
    "relaxed": "chill", "lofi": "chill", "calm": "chill",
    "weird": "alien", "strange": "alien", "cosmic": "alien",
    "percussion": "tribal", "primal": "tribal",
    "dirty": "filthy", "gnarly": "filthy", "nasty": "filthy",
    "grimy": "filthy", "disgusting": "filthy",
}


@dataclass
class MoodSuggestion:
    """Suggested configuration based on mood."""
    mood: str
    modules: list[str]
    key: str
    scale: str
    bpm: float
    base_freq: float
    reverb: float
    distortion: float
    energy: float
    darkness: float
    tags: list[str]

    def to_dict(self) -> dict:
        return {
            "mood": self.mood,
            "modules": self.modules,
            "key": self.key,
            "scale": self.scale,
            "bpm": self.bpm,
            "base_freq": round(self.base_freq, 2),
            "reverb": self.reverb,
            "distortion": self.distortion,
            "energy": self.energy,
            "darkness": self.darkness,
            "tags": self.tags,
        }


def resolve_mood(text: str) -> str:
    """Resolve mood text to a known mood name."""
    t = text.lower().strip()
    if t in MOODS:
        return t
    if t in MOOD_ALIASES:
        return MOOD_ALIASES[t]
    # Fuzzy match
    for name in MOODS:
        if name in t or t in name:
            return name
    for alias, mood in MOOD_ALIASES.items():
        if alias in t or t in alias:
            return mood
    return "aggressive"  # Default to dubstep energy


def get_mood_suggestion(mood_text: str,
                         bpm: float = 140.0) -> MoodSuggestion:
    """Get sound design suggestion for a mood."""
    mood_name = resolve_mood(mood_text)
    profile = MOODS[mood_name]

    adjusted_bpm = round(bpm * profile.tempo_mult)
    base_freq = A4_432 + profile.freq_offset

    return MoodSuggestion(
        mood=mood_name,
        modules=profile.suggested_modules,
        key=profile.suggested_key,
        scale=profile.suggested_scale,
        bpm=adjusted_bpm,
        base_freq=base_freq,
        reverb=profile.reverb_amount,
        distortion=profile.distortion,
        energy=profile.energy,
        darkness=profile.darkness,
        tags=profile.tags,
    )


def blend_moods(mood_a: str, mood_b: str,
                 blend: float = 0.5) -> MoodSuggestion:
    """Blend two moods together."""
    a_name = resolve_mood(mood_a)
    b_name = resolve_mood(mood_b)
    a = MOODS[a_name]
    b = MOODS[b_name]

    inv = 1.0 - blend
    energy = a.energy * inv + b.energy * blend
    darkness = a.darkness * inv + b.darkness * blend
    reverb = a.reverb_amount * inv + b.reverb_amount * blend
    distortion = a.distortion * inv + b.distortion * blend
    tempo = a.tempo_mult * inv + b.tempo_mult * blend
    freq_off = a.freq_offset * inv + b.freq_offset * blend

    # Merge modules (interleave)
    modules: list[str] = []
    for i in range(max(len(a.suggested_modules),
                       len(b.suggested_modules))):
        if i < len(a.suggested_modules) and \
                a.suggested_modules[i] not in modules:
            modules.append(a.suggested_modules[i])
        if i < len(b.suggested_modules) and \
                b.suggested_modules[i] not in modules:
            modules.append(b.suggested_modules[i])

    blend_name = f"{a_name}+{b_name}"
    tags = list(set(a.tags + b.tags))

    return MoodSuggestion(
        mood=blend_name,
        modules=modules,
        key=a.suggested_key if blend < 0.5 else b.suggested_key,
        scale=a.suggested_scale if blend < 0.5 else b.suggested_scale,
        bpm=round(140.0 * tempo),
        base_freq=round(A4_432 + freq_off, 2),
        reverb=round(reverb, 2),
        distortion=round(distortion, 2),
        energy=round(energy, 2),
        darkness=round(darkness, 2),
        tags=tags,
    )


def mood_suggestion_text(suggestion: MoodSuggestion) -> str:
    """Format mood suggestion as readable text."""
    lines = [
        f"**Mood: {suggestion.mood.upper()}**",
        f"Energy: {'█' * int(suggestion.energy * 10)}{'░' * (10 - int(suggestion.energy * 10))} "
        f"({suggestion.energy:.0%})",
        f"Darkness: {'█' * int(suggestion.darkness * 10)}{'░' * (10 - int(suggestion.darkness * 10))} "
        f"({suggestion.darkness:.0%})",
        "",
        f"**Key:** {suggestion.key} {suggestion.scale} | "
        f"**BPM:** {suggestion.bpm} | "
        f"**Base Freq:** {suggestion.base_freq}Hz",
        f"**Reverb:** {suggestion.reverb:.0%} | "
        f"**Distortion:** {suggestion.distortion:.0%}",
        "",
        "**Suggested Modules:**",
    ]
    for m in suggestion.modules:
        lines.append(f"  → {m}")
    if suggestion.tags:
        lines.append(f"\n**Tags:** {', '.join(suggestion.tags)}")
    return "\n".join(lines)


def list_moods() -> list[str]:
    """List all available moods."""
    return sorted(MOODS.keys())


def main() -> None:
    print("Mood Engine")
    for mood in list_moods():
        s = get_mood_suggestion(mood)
        print(f"  {mood}: {s.key} {s.scale}, {s.bpm}bpm, "
              f"energy={s.energy:.0%}, dark={s.darkness:.0%}")
    print()
    blend = blend_moods("aggressive", "dreamy", 0.4)
    print(mood_suggestion_text(blend))
    print("Done.")


if __name__ == "__main__":
    main()
