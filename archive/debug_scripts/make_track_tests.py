"""Track-by-track binary search for Ableton crash.
Generates files t01..t17, each adding one more track from V12's order.
t01 = DRUMS only, t02 = DRUMS+BASS, ... t15 = all 15 MIDI, t16 = +REVERB, t17 = +DELAY.
Each track gets 1 clip with a few notes (enough to be non-empty).
All use 13 scenes (V12's count) and 14 cue points."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, ALSMidiNote, ALSMidiClip,
    ALSCuePoint, write_als,
)
from pathlib import Path

OUT = Path("output/ableton/test_trackbuild")
OUT.mkdir(parents=True, exist_ok=True)

V12_TRACKS = [
    "DRUMS", "BASS", "SUB", "GROWL", "WOBBLE", "RIDDIM", "FORMANT",
    "LEAD", "COUNTER", "VOCAL_CHOP", "CHORDS", "PAD", "ARP",
    "FX", "RISER",
]

SECTIONS = [
    ("INTRO", 0), ("VERSE1", 32), ("PRE_CHORUS1", 64),
    ("DROP1", 80), ("BREAK", 112), ("VERSE2", 128),
    ("PRE_CHORUS2", 160), ("DROP2", 176), ("BRIDGE_GOLDEN", 208),
    ("VIP_DROP", 224), ("VIP2_DOUBLE", 248), ("FINAL_CHORUS", 264),
    ("OUTRO", 280),
]

SCENES = [ALSScene(name=s[0], tempo=127) for s in SECTIONS]

CUE_POINTS = [ALSCuePoint(name=s[0], time=float(s[1]) * 4.0) for s in SECTIONS]
CUE_POINTS.append(ALSCuePoint(name="GOLDEN_SECTION", time=89.0 * 4.0))


def _make_clip(track_name: str, idx: int) -> ALSMidiClip:
    """Simple 16-beat clip with 4 notes."""
    base_pitch = 36 + (idx * 5) % 48
    notes = [
        ALSMidiNote(pitch=base_pitch, time=0.0, duration=2.0, velocity=100),
        ALSMidiNote(pitch=base_pitch+7, time=4.0, duration=2.0, velocity=90),
        ALSMidiNote(pitch=base_pitch+12, time=8.0, duration=2.0, velocity=80),
        ALSMidiNote(pitch=base_pitch+5, time=12.0, duration=2.0, velocity=85),
    ]
    return ALSMidiClip(
        name=track_name, start_beat=0.0, length_beats=16.0, notes=notes
    )


for count in range(1, 18):  # t01..t17
    tracks = []
    # MIDI tracks
    midi_count = min(count, 15)
    for i in range(midi_count):
        tracks.append(ALSTrack(
            name=V12_TRACKS[i],
            track_type="midi",
            midi_clips=[_make_clip(V12_TRACKS[i], i)],
        ))
    # Return tracks
    if count >= 16:
        tracks.append(ALSTrack(name="REVERB", track_type="return"))
    if count >= 17:
        tracks.append(ALSTrack(name="DELAY", track_type="return"))

    fname = f"t{count:02d}_{midi_count}midi"
    if count >= 16:
        fname += f"_{count-15}ret"
    fname += ".als"

    p = ALSProject(
        name=f"test_t{count:02d}",
        bpm=127,
        tracks=tracks,
        scenes=SCENES,
        cue_points=CUE_POINTS,
    )
    write_als(p, str(OUT / fname))
    print(f"  {fname}")

print(f"\nDone! {len(list(OUT.glob('t*.als')))} files in {OUT}")
