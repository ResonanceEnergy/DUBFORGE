"""
DUBFORGE — Parameter Control Engine  (Session 149)

Parse module parameters from natural language:
"render sub bass at 40hz with 2s decay and 0.8 drive"
"""

import re
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class ParsedParams:
    """Parameters parsed from user input."""
    module: str = ""
    frequency_hz: float | None = None
    duration_s: float | None = None
    decay_s: float | None = None
    drive: float | None = None
    rate_hz: float | None = None
    depth: float | None = None
    mix: float | None = None
    bpm: float | None = None
    key: str | None = None
    scale: str | None = None
    octave: int | None = None
    cutoff_hz: float | None = None
    resonance: float | None = None
    attack_s: float | None = None
    release_s: float | None = None
    output_path: str | None = None
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if v is not None and k != "extras":
                d[k] = v
        if self.extras:
            d["extras"] = self.extras
        return d


# Parameter extraction patterns
_PATTERNS: list[tuple[str, str, type]] = [
    (r'(\d+(?:\.\d+)?)\s*(?:hz|hertz)', "frequency_hz", float),
    (r'(?:freq|frequency)\s*[=:]\s*(\d+(?:\.\d+)?)', "frequency_hz", float),
    (r'(\d+(?:\.\d+)?)\s*(?:sec|seconds?|s)\b', "duration_s", float),
    (r'(?:duration|dur|length)\s*[=:]\s*(\d+(?:\.\d+)?)', "duration_s", float),
    (r'(?:decay)\s*[=:of]?\s*(\d+(?:\.\d+)?)\s*s?', "decay_s", float),
    (r'(?:drive|dist(?:ortion)?)\s*[=:of]?\s*(\d+(?:\.\d+)?)', "drive", float),
    (r'(?:rate)\s*[=:of]?\s*(\d+(?:\.\d+)?)\s*(?:hz)?', "rate_hz", float),
    (r'(?:depth)\s*[=:of]?\s*(\d+(?:\.\d+)?)', "depth", float),
    (r'(?:mix|wet)\s*[=:of]?\s*(\d+(?:\.\d+)?)\s*%?', "mix", float),
    (r'(\d+(?:\.\d+)?)\s*(?:bpm|tempo)', "bpm", float),
    (r'(?:bpm|tempo)\s*[=:of]?\s*(\d+(?:\.\d+)?)', "bpm", float),
    (r'(?:key|root)\s*[=:of]?\s*([A-Ga-g][#b♯♭]?)', "key", str),
    (r'\b([A-G][#b]?)\s+(?:minor|major|min|maj)', "key", str),
    (r'(?:scale)\s*[=:of]?\s*(\w+)', "scale", str),
    (r'\b(minor|major|dorian|phrygian|lydian|mixolydian|aeolian|locrian)\b',
     "scale", str),
    (r'(?:octave|oct)\s*[=:of]?\s*(\d+)', "octave", int),
    (r'(?:cutoff|lpf|hpf)\s*[=:of]?\s*(\d+(?:\.\d+)?)\s*(?:hz)?',
     "cutoff_hz", float),
    (r'(?:res(?:onance)?|q)\s*[=:of]?\s*(\d+(?:\.\d+)?)',
     "resonance", float),
    (r'(?:attack|att)\s*[=:of]?\s*(\d+(?:\.\d+)?)\s*(?:s|ms)?',
     "attack_s", float),
    (r'(?:release|rel)\s*[=:of]?\s*(\d+(?:\.\d+)?)\s*(?:s|ms)?',
     "release_s", float),
]

# Module name aliases
_MODULE_ALIASES: dict[str, str] = {
    "sub": "sub_bass", "sub bass": "sub_bass", "subbass": "sub_bass",
    "wobble": "wobble_bass", "wobble bass": "wobble_bass",
    "lead": "lead_synth", "lead synth": "lead_synth",
    "pad": "pad_synth", "pad synth": "pad_synth",
    "drums": "drum_generator", "drum": "drum_generator",
    "kick": "drum_generator", "snare": "drum_generator",
    "hihat": "drum_generator", "hat": "drum_generator",
    "bass": "sub_bass", "bassline": "sub_bass",
    "arp": "arp_synth", "arpegg": "arp_synth",
    "chord": "chord_pad", "chords": "chord_pad",
    "riser": "riser_synth", "rise": "riser_synth",
    "impact": "impact_hit", "hit": "impact_hit",
    "noise": "noise_generator", "white noise": "noise_generator",
    "pluck": "pluck_synth", "plucks": "pluck_synth",
    "drone": "drone_synth", "ambient": "ambient_texture",
    "formant": "formant_synth", "vocal": "vocal_chop",
    "glitch": "glitch_engine", "riddim": "riddim_engine",
    "fx": "fx_generator", "effects": "fx_generator",
    "reverb": "reverb_delay", "delay": "reverb_delay",
    "sidechain": "sidechain",
    "master": "mastering_chain", "mastering": "mastering_chain",
    "wavetable": "wavetable_morph", "granular": "granular_synth",
    "trance": "trance_arp", "transition": "transition_fx",
}


def resolve_module(text: str) -> str:
    """Resolve user text to a module name."""
    t = text.lower().strip()
    # Direct alias match
    if t in _MODULE_ALIASES:
        return _MODULE_ALIASES[t]
    # Partial match
    for alias, module in _MODULE_ALIASES.items():
        if alias in t or t in alias:
            return module
    return t.replace(" ", "_")


def parse_params(text: str) -> ParsedParams:
    """Extract parameters from natural language text."""
    params = ParsedParams()

    # Try to extract module name from beginning
    lower = text.lower()
    # Match "render/make/create/generate MODULE ..."
    m = re.match(
        r'(?:render|make|create|generate|build|play|preview)\s+'
        r'(?:a\s+|an\s+|the\s+)?'
        r'(.+?)(?:\s+(?:at|with|using|@)\b|\s*$)',
        lower,
    )
    if m:
        params.module = resolve_module(m.group(1))

    # Extract all numeric parameters
    for pattern, attr, typ in _PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and getattr(params, attr) is None:
            val = match.group(1)
            try:
                setattr(params, attr, typ(val))
            except (ValueError, TypeError):
                pass

    # Normalise mix from percentage
    if params.mix is not None and params.mix > 1.0:
        params.mix = params.mix / 100.0

    return params


def apply_params_to_kwargs(params: ParsedParams) -> dict:
    """Convert parsed params to keyword arguments for module functions."""
    kwargs: dict = {}
    if params.frequency_hz:
        kwargs["freq"] = params.frequency_hz
        kwargs["frequency"] = params.frequency_hz
    if params.duration_s:
        kwargs["duration"] = params.duration_s
        kwargs["duration_s"] = params.duration_s
    if params.decay_s:
        kwargs["decay"] = params.decay_s
    if params.drive:
        kwargs["drive"] = params.drive
    if params.rate_hz:
        kwargs["rate"] = params.rate_hz
        kwargs["rate_hz"] = params.rate_hz
    if params.depth:
        kwargs["depth"] = params.depth
    if params.mix:
        kwargs["mix"] = params.mix
    if params.bpm:
        kwargs["bpm"] = params.bpm
    if params.key:
        kwargs["key"] = params.key
        kwargs["root_note"] = params.key
    if params.scale:
        kwargs["scale"] = params.scale
    if params.octave:
        kwargs["octave"] = params.octave
    if params.cutoff_hz:
        kwargs["cutoff"] = params.cutoff_hz
    if params.resonance:
        kwargs["resonance"] = params.resonance
    if params.attack_s:
        kwargs["attack"] = params.attack_s
    if params.release_s:
        kwargs["release"] = params.release_s
    return kwargs


def describe_params(params: ParsedParams) -> str:
    """Human-readable description of parsed params."""
    parts = []
    if params.module:
        parts.append(f"Module: **{params.module}**")
    if params.frequency_hz:
        parts.append(f"Freq: {params.frequency_hz}Hz")
    if params.duration_s:
        parts.append(f"Duration: {params.duration_s}s")
    if params.bpm:
        parts.append(f"BPM: {params.bpm}")
    if params.key:
        parts.append(f"Key: {params.key}")
    if params.scale:
        parts.append(f"Scale: {params.scale}")
    if params.drive:
        parts.append(f"Drive: {params.drive}")
    if params.cutoff_hz:
        parts.append(f"Cutoff: {params.cutoff_hz}Hz")
    return " | ".join(parts) if parts else "No parameters detected"


def main() -> None:
    print("Parameter Control Engine")
    tests = [
        "render sub bass at 40hz with 2s decay",
        "make wobble bass 150 bpm rate=8hz depth=0.7",
        "generate lead synth in C# minor 3 octave cutoff 2000hz",
        "play drums at 140 bpm",
    ]
    for t in tests:
        p = parse_params(t)
        print(f"  '{t}'")
        print(f"    → {describe_params(p)}")
    print("Done.")


if __name__ == "__main__":
    main()
