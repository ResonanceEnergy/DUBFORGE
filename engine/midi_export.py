"""
DUBFORGE Engine — MIDI Export

Converts chord progressions, arp patterns, and Ableton clips into
real .mid files you can drag straight into your DAW.

Uses mido for Standard MIDI File (SMF) generation.
All timing is phi/Fibonacci-aligned per DUBFORGE doctrine.

Outputs:
    output/midi/chord_*.mid        — One per chord progression preset
    output/midi/arp_*.mid          — One per arp pattern
    output/midi/clip_*.mid         — One per Ableton clip generator
    output/midi/DUBFORGE_FULL.mid  — Multi-track combined arrangement
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import mido

from engine.config_loader import get_config_value
from engine.log import get_logger

_log = get_logger("dubforge.midi_export")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

TICKS_PER_BEAT = 480       # Industry standard PPQN
DEFAULT_BPM = 150          # Dubstep standard
DEFAULT_VELOCITY = 100
DEFAULT_CHANNEL = 0        # MIDI channel 1 (0-indexed)
DRUM_CHANNEL = 9           # GM drums on channel 10

# General MIDI program numbers for dubstep-relevant sounds
GM_PROGRAMS = {
    "sub_bass": 38,        # Synth Bass 1
    "mid_bass": 39,        # Synth Bass 2
    "lead": 80,            # Square Lead
    "pad": 88,             # New Age Pad
    "arp": 80,             # Square Lead
    "chord": 4,            # Electric Piano
    "strings": 48,         # String Ensemble
}


# ═══════════════════════════════════════════════════════════════════════════
# CORE NOTE EVENT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NoteEvent:
    """Unified note event for MIDI export.

    All timing is in beats (quarter notes).
    """
    pitch: int              # MIDI note number 0-127
    start_beat: float       # Absolute position in beats
    duration_beats: float   # Length in beats
    velocity: int = 100     # 0-127
    channel: int = 0        # MIDI channel 0-15

    def start_ticks(self, tpb: int = TICKS_PER_BEAT) -> int:
        """Absolute start time in ticks."""
        return int(round(self.start_beat * tpb))

    def duration_ticks(self, tpb: int = TICKS_PER_BEAT) -> int:
        """Duration in ticks."""
        return max(1, int(round(self.duration_beats * tpb)))


# ═══════════════════════════════════════════════════════════════════════════
# CONVERTERS — Existing data → NoteEvent list
# ═══════════════════════════════════════════════════════════════════════════

def progression_to_events(prog, velocity: int = DEFAULT_VELOCITY) -> list[NoteEvent]:
    """Convert a ChordProgression (or its dict form) to NoteEvent list.

    Accepts either a ChordProgression dataclass or a dict with
    'chords' key containing chord dicts with 'midi_notes' and
    'duration_beats'.
    """
    chords = prog.chords if hasattr(prog, 'chords') else prog.get('chords', [])
    events = []
    beat_pos = 0.0

    for chord in chords:
        # Handle both dataclass and dict
        if hasattr(chord, 'midi_notes'):
            midi_notes = chord.midi_notes
            dur = chord.duration_beats
        else:
            midi_notes = chord.get('midi_notes', [])
            dur = chord.get('duration_beats', 4.0)

        for note in midi_notes:
            events.append(NoteEvent(
                pitch=max(0, min(127, note)),
                start_beat=beat_pos,
                duration_beats=dur,
                velocity=velocity,
            ))
        beat_pos += dur

    return events


def arp_pattern_to_events(
    pattern,
    root_note: int = 60,
    velocity: int = DEFAULT_VELOCITY,
) -> list[NoteEvent]:
    """Convert an ArpPattern to NoteEvent list.

    Works with both ArpPattern dataclass and dict form.
    """
    if hasattr(pattern, 'notes'):
        notes = pattern.notes
    else:
        notes = pattern.get('notes', [])

    events = []
    beat_pos = 0.0

    for note in notes:
        if hasattr(note, 'semitone_offset'):
            offset = note.semitone_offset
            vel = note.velocity
            dur = note.duration_beats * (note.gate_percent / 100.0)
            step_dur = note.duration_beats
        else:
            offset = note.get('semitone_offset', 0)
            vel = note.get('velocity', velocity)
            gate = note.get('gate_percent', 61.8)
            step_dur = note.get('duration_beats', 0.25)
            dur = step_dur * (gate / 100.0)

        midi_note = max(0, min(127, root_note + offset))
        events.append(NoteEvent(
            pitch=midi_note,
            start_beat=beat_pos,
            duration_beats=dur,
            velocity=vel,
        ))
        beat_pos += step_dur

    return events


def midi_clip_to_events(clip) -> list[NoteEvent]:
    """Convert an Ableton MIDIClip to NoteEvent list.

    Works with MIDIClip dataclass (from ableton_live.py).
    """
    notes = clip.notes if hasattr(clip, 'notes') else clip.get('notes', [])
    events = []

    for note in notes:
        if hasattr(note, 'pitch'):
            pitch = note.pitch
            start = note.start_time
            dur = note.duration
            vel = int(note.velocity)
        else:
            pitch = note.get('pitch', 60)
            start = note.get('start_time', 0)
            dur = note.get('duration', 1.0)
            vel = int(note.get('velocity', 100))

        events.append(NoteEvent(
            pitch=max(0, min(127, pitch)),
            start_beat=start,
            duration_beats=dur,
            velocity=max(0, min(127, vel)),
        ))

    return events


def raw_midi_events_to_events(
    midi_events: list[dict],
    source: str = "chord_progression",
) -> list[NoteEvent]:
    """Convert raw MIDI event dicts (from existing export functions) to NoteEvents.

    Handles both chord_progression format (tick/midi/velocity/duration_ticks)
    and trance_arp format (note/velocity/start_beat/duration_beat).
    """
    events = []
    for evt in midi_events:
        if 'tick' in evt:
            # chord_progression format
            events.append(NoteEvent(
                pitch=max(0, min(127, evt['midi'])),
                start_beat=evt['tick'] / TICKS_PER_BEAT,
                duration_beats=evt['duration_ticks'] / TICKS_PER_BEAT,
                velocity=evt.get('velocity', DEFAULT_VELOCITY),
            ))
        elif 'start_beat' in evt:
            # trance_arp format
            events.append(NoteEvent(
                pitch=max(0, min(127, evt['note'])),
                start_beat=evt['start_beat'],
                duration_beats=evt.get('duration_beat', 0.25),
                velocity=evt.get('velocity', DEFAULT_VELOCITY),
            ))
    return events


# ═══════════════════════════════════════════════════════════════════════════
# MIDI FILE WRITER — Core engine
# ═══════════════════════════════════════════════════════════════════════════

def events_to_track(
    events: list[NoteEvent],
    track_name: str = "DUBFORGE",
    channel: int = DEFAULT_CHANNEL,
    program: int | None = None,
    tpb: int = TICKS_PER_BEAT,
) -> mido.MidiTrack:
    """Convert NoteEvent list to a mido MidiTrack.

    Handles delta-time conversion from absolute positions.
    Sorts all MIDI messages by absolute time for correct playback.
    """
    track = mido.MidiTrack()

    # Track name
    track.append(mido.MetaMessage('track_name', name=track_name, time=0))

    # Program change (instrument)
    if program is not None:
        track.append(mido.Message(
            'program_change', program=program, channel=channel, time=0,
        ))

    # Build absolute-time message list
    abs_messages = []
    for evt in events:
        ch = evt.channel if evt.channel != DEFAULT_CHANNEL else channel
        start = evt.start_ticks(tpb)
        dur = evt.duration_ticks(tpb)

        abs_messages.append((start, mido.Message(
            'note_on',
            note=evt.pitch,
            velocity=evt.velocity,
            channel=ch,
            time=start,
        )))
        abs_messages.append((start + dur, mido.Message(
            'note_off',
            note=evt.pitch,
            velocity=0,
            channel=ch,
            time=start + dur,
        )))

    # Sort by absolute time, then note_off before note_on at same tick
    abs_messages.sort(key=lambda x: (x[0], 0 if x[1].type == 'note_off' else 1))

    # Convert to delta times
    last_tick = 0
    for abs_tick, msg in abs_messages:
        delta = abs_tick - last_tick
        msg.time = delta
        track.append(msg)
        last_tick = abs_tick

    # End of track
    track.append(mido.MetaMessage('end_of_track', time=0))

    return track


def write_midi_file(
    tracks: list[tuple[str, list[NoteEvent]]],
    path: str | Path,
    bpm: int = DEFAULT_BPM,
    time_sig_num: int = 4,
    time_sig_den: int = 4,
    programs: dict[str, int] | None = None,
    tpb: int = TICKS_PER_BEAT,
) -> Path:
    """Write a multi-track MIDI file.

    Args:
        tracks: List of (track_name, events) tuples.
        path: Output file path.
        bpm: Tempo in beats per minute.
        time_sig_num: Time signature numerator.
        time_sig_den: Time signature denominator.
        programs: Optional dict mapping track_name → GM program number.
        tpb: Ticks per beat (PPQN).

    Returns:
        Path to the written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mid = mido.MidiFile(type=1, ticks_per_beat=tpb)

    # Tempo track (track 0 in Type 1 MIDI)
    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage('track_name', name='DUBFORGE', time=0))
    tempo_track.append(mido.MetaMessage(
        'set_tempo', tempo=mido.bpm2tempo(bpm), time=0,
    ))
    # Denominator is encoded as power of 2 for mido
    tempo_track.append(mido.MetaMessage(
        'time_signature',
        numerator=time_sig_num,
        denominator=time_sig_den,
        clocks_per_click=24,
        notated_32nd_notes_per_beat=8,
        time=0,
    ))
    tempo_track.append(mido.MetaMessage('end_of_track', time=0))
    mid.tracks.append(tempo_track)

    # Add note tracks
    if programs is None:
        programs = {}

    for i, (name, events) in enumerate(tracks):
        channel = i % 16
        if channel == DRUM_CHANNEL:
            channel = (channel + 1) % 16  # Skip drum channel
        program = programs.get(name)
        track = events_to_track(
            events, track_name=name, channel=channel,
            program=program, tpb=tpb,
        )
        mid.tracks.append(track)

    mid.save(str(path))
    return path


def write_single_track_midi(
    events: list[NoteEvent],
    path: str | Path,
    track_name: str = "DUBFORGE",
    bpm: int = DEFAULT_BPM,
    program: int | None = None,
) -> Path:
    """Convenience: write a single-track MIDI file."""
    return write_midi_file(
        tracks=[(track_name, events)],
        path=path,
        bpm=bpm,
        programs={track_name: program} if program is not None else None,
    )


# ═══════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL EXPORTERS
# ═══════════════════════════════════════════════════════════════════════════

def export_progression_midi(prog, out_dir: str | Path = "output/midi") -> Path:
    """Export a ChordProgression as a .mid file.

    Args:
        prog: ChordProgression dataclass or equivalent dict.
        out_dir: Output directory.

    Returns:
        Path to the written .mid file.
    """
    out_dir = Path(out_dir)
    name = prog.name if hasattr(prog, 'name') else prog.get('name', 'unknown')
    bpm = prog.bpm if hasattr(prog, 'bpm') else prog.get('bpm', DEFAULT_BPM)

    events = progression_to_events(prog)
    path = out_dir / f"chord_{name}.mid"

    return write_single_track_midi(
        events, path,
        track_name=f"DUBFORGE_CHORD_{name}",
        bpm=bpm,
        program=GM_PROGRAMS["chord"],
    )


def export_arp_midi(
    pattern,
    out_dir: str | Path = "output/midi",
    root_note: int = 60,
    bpm: int = DEFAULT_BPM,
) -> Path:
    """Export an ArpPattern as a .mid file.

    Args:
        pattern: ArpPattern dataclass or equivalent dict.
        out_dir: Output directory.
        root_note: Root MIDI note for the arp.
        bpm: Tempo.

    Returns:
        Path to the written .mid file.
    """
    out_dir = Path(out_dir)
    name = pattern.name if hasattr(pattern, 'name') else pattern.get('name', 'arp')

    events = arp_pattern_to_events(pattern, root_note=root_note)
    path = out_dir / f"arp_{name.lower()}.mid"

    return write_single_track_midi(
        events, path,
        track_name=f"DUBFORGE_ARP_{name}",
        bpm=bpm,
        program=GM_PROGRAMS["arp"],
    )


def export_clip_midi(
    clip,
    out_dir: str | Path = "output/midi",
    bpm: int = DEFAULT_BPM,
    program: int | None = None,
) -> Path:
    """Export an Ableton MIDIClip as a .mid file.

    Args:
        clip: MIDIClip dataclass.
        out_dir: Output directory.
        bpm: Tempo.
        program: GM program number override.

    Returns:
        Path to the written .mid file.
    """
    out_dir = Path(out_dir)
    name = clip.name if hasattr(clip, 'name') else clip.get('name', 'clip')

    events = midi_clip_to_events(clip)
    path = out_dir / f"clip_{name}.mid"

    return write_single_track_midi(
        events, path,
        track_name=name,
        bpm=bpm,
        program=program,
    )


def export_full_arrangement(
    out_dir: str | Path = "output/midi",
    bpm: int = DEFAULT_BPM,
    key: str = "A",
    root_note: int = 57,
) -> Path:
    """Generate a full multi-track MIDI arrangement.

    Combines:
    - Sub bass pattern (sustained root notes)
    - Mid bass growl pattern (Fibonacci-timed triggers)
    - Arp pattern (Fibonacci arpeggio)
    - Chord stab pattern (Fibonacci-rhythmed chord stabs)
    - Chord progression (WEAPON_DARK preset)

    Returns path to the multi-track .mid file.
    """
    # Import here to avoid circular imports
    from engine.ableton_live import (
        generate_arp_clip,
        generate_chord_stab_clip,
        generate_mid_bass_clip,
        generate_sub_bass_clip,
    )
    from engine.chord_progression import ALL_PRESETS
    from engine.trance_arp import fibonacci_rise_pattern

    out_dir = Path(out_dir)

    # Sub bass — root note A1 (33)
    sub_clip = generate_sub_bass_clip(root_note=33, bars=16, bpm=bpm)
    sub_events = midi_clip_to_events(sub_clip)

    # Mid bass — root note A2 (45)
    mid_clip = generate_mid_bass_clip(root_note=45, bars=16, bpm=bpm)
    mid_events = midi_clip_to_events(mid_clip)

    # Arp — root note A3 (57)
    arp_clip = generate_arp_clip(root_note=root_note, scale="minor", bars=8)
    arp_events = midi_clip_to_events(arp_clip)

    # Chord progression — WEAPON_DARK
    weapon_prog = ALL_PRESETS["WEAPON_DARK"]()
    chord_events = progression_to_events(weapon_prog)

    # Fibonacci rise arp — root A3
    fib_arp = fibonacci_rise_pattern()
    fib_events = arp_pattern_to_events(fib_arp, root_note=root_note)

    # Chord stabs
    chord_clip = generate_chord_stab_clip(
        chord_notes=[root_note, root_note + 3, root_note + 7],  # Am triad
        bars=8,
    )
    stab_events = midi_clip_to_events(chord_clip)

    tracks = [
        ("SUB_BASS", sub_events),
        ("MID_BASS", mid_events),
        ("ARP", arp_events),
        ("CHORD_PROG", chord_events),
        ("FIB_ARP", fib_events),
        ("CHORD_STAB", stab_events),
    ]

    programs = {
        "SUB_BASS": GM_PROGRAMS["sub_bass"],
        "MID_BASS": GM_PROGRAMS["mid_bass"],
        "ARP": GM_PROGRAMS["arp"],
        "CHORD_PROG": GM_PROGRAMS["chord"],
        "FIB_ARP": GM_PROGRAMS["arp"],
        "CHORD_STAB": GM_PROGRAMS["strings"],
    }

    path = out_dir / "DUBFORGE_FULL.mid"
    return write_midi_file(
        tracks, path, bpm=bpm, programs=programs,
    )


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST — JSON sidecar for each MIDI file
# ═══════════════════════════════════════════════════════════════════════════

def write_manifest(midi_path: Path, metadata: dict) -> Path:
    """Write a JSON manifest alongside a MIDI file."""
    manifest_path = midi_path.with_suffix('.json')
    data = {
        "dubforge_module": "MIDI_EXPORT",
        "midi_file": midi_path.name,
        "ticks_per_beat": TICKS_PER_BEAT,
        **metadata,
    }
    with open(manifest_path, 'w') as f:
        json.dump(data, f, indent=2)
    return manifest_path


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Generate all MIDI files
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all MIDI files from all available data sources."""
    from engine.ableton_live import (
        generate_arp_clip,
        generate_chord_stab_clip,
        generate_mid_bass_clip,
        generate_sub_bass_clip,
    )
    from engine.chord_progression import ALL_PRESETS
    from engine.trance_arp import (
        fibonacci_rise_pattern,
        golden_gate_pattern,
        phi_spiral_pattern,
    )

    out_dir = Path("output/midi")
    out_dir.mkdir(parents=True, exist_ok=True)

    bpm = DEFAULT_BPM
    root = 57  # A3

    # Load BPM from config if available
    try:
        cfg_bpm = get_config_value(
            "fibonacci_blueprint_pack_v1", "FIBONACCI_WEAPON", "bpm",
            default=None,
        )
        if cfg_bpm is not None:
            bpm = int(cfg_bpm)
    except FileNotFoundError:
        pass

    print(f"  MIDI Export — BPM: {bpm}, Root: A3 (MIDI {root})")
    print(f"  Ticks/beat: {TICKS_PER_BEAT}")
    print()

    generated = []

    # ── 1. Chord Progressions ────────────────────────────────────────
    print("  [Chord Progressions]")
    for name, preset_fn in ALL_PRESETS.items():
        prog = preset_fn()
        path = export_progression_midi(prog, out_dir=out_dir)
        events = progression_to_events(prog)
        write_manifest(path, {
            "type": "chord_progression",
            "preset": name,
            "key": prog.key,
            "bpm": prog.bpm,
            "total_bars": prog.total_bars,
            "chord_count": len(prog.chords),
            "note_count": len(events),
            "chords": [c.get("symbol", "?") if isinstance(c, dict) else c.symbol
                       for c in prog.chords],
        })
        generated.append(path)
        print(f"    ✓ {path.name}")

    print()

    # ── 2. Arp Patterns ──────────────────────────────────────────────
    print("  [Arp Patterns]")
    arp_generators = [
        ("fibonacci_rise", fibonacci_rise_pattern),
        ("phi_spiral", phi_spiral_pattern),
        ("golden_gate", golden_gate_pattern),
    ]

    for arp_name, gen_fn in arp_generators:
        pattern = gen_fn()
        path = export_arp_midi(pattern, out_dir=out_dir, root_note=root, bpm=bpm)
        events = arp_pattern_to_events(pattern, root_note=root)
        write_manifest(path, {
            "type": "arp_pattern",
            "pattern": arp_name,
            "root_note": root,
            "bpm": bpm,
            "steps": pattern.steps if hasattr(pattern, 'steps') else len(events),
            "note_count": len(events),
        })
        generated.append(path)
        print(f"    ✓ {path.name}")

    print()

    # ── 3. Ableton Clips ─────────────────────────────────────────────
    print("  [Ableton Clips]")
    clip_generators = [
        ("sub_bass", generate_sub_bass_clip, {"root_note": 33}, GM_PROGRAMS["sub_bass"]),
        ("mid_bass", generate_mid_bass_clip, {"root_note": 45}, GM_PROGRAMS["mid_bass"]),
        ("arp", generate_arp_clip, {"root_note": root, "scale": "minor"}, GM_PROGRAMS["arp"]),
        ("chord_stab", generate_chord_stab_clip,
         {"chord_notes": [root, root + 3, root + 7]}, GM_PROGRAMS["strings"]),
    ]

    for clip_name, gen_fn, kwargs, program in clip_generators:
        clip = gen_fn(**kwargs)
        path = export_clip_midi(clip, out_dir=out_dir, bpm=bpm, program=program)
        events = midi_clip_to_events(clip)
        write_manifest(path, {
            "type": "ableton_clip",
            "clip_name": clip_name,
            "bpm": bpm,
            "length_beats": clip.length if hasattr(clip, 'length') else 0,
            "note_count": len(events),
            "gm_program": program,
        })
        generated.append(path)
        print(f"    ✓ {path.name}")

    print()

    # ── 4. Full Arrangement ──────────────────────────────────────────
    print("  [Full Arrangement]")
    path = export_full_arrangement(out_dir=out_dir, bpm=bpm, root_note=root)
    write_manifest(path, {
        "type": "full_arrangement",
        "bpm": bpm,
        "root_note": root,
        "tracks": ["SUB_BASS", "MID_BASS", "ARP", "CHORD_PROG", "FIB_ARP", "CHORD_STAB"],
    })
    generated.append(path)
    print(f"    ✓ {path.name}")

    print()
    print(f"  ✓ {len(generated)} MIDI files exported to {out_dir}/")
    print("    Drag any .mid file into Ableton / FL Studio / Logic / Reaper")


if __name__ == "__main__":
    main()
