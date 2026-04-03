"""Create minimal ALS files to isolate crash via binary search.

Test 0: Raw factory template (zero modifications)
Test 1: 1 empty MIDI track, 1 scene
Test 2: 1 MIDI track with 1 clip (4 notes)
Test 3: 1 MIDI track with automation
Test 4: 2 MIDI + 1 return track, 2 scenes
Test 5: Heavy single track (200 notes, 200 automation points)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, ALSMidiNote, ALSMidiClip,
    ALSAutomation, ALSAutomationPoint,
    write_als, _load_default_template,
)
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path("output/ableton/test_minimal")
OUT.mkdir(parents=True, exist_ok=True)


def write_raw(root, name):
    path = OUT / name
    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=True)
    with gzip.open(str(path), "wb") as f:
        f.write(xml_str.encode("utf-8"))
    print(f"  Wrote: {path}")


# Test 0: Raw template, zero modifications
print("Test 0: Raw factory template (no changes)")
tmpl = _load_default_template()
if tmpl is not None:
    write_raw(tmpl, "test0_raw_template.als")
else:
    print("  ERROR: No template found!")

# Test 1: Minimal project — 1 empty MIDI track, 1 scene, no clips
print("Test 1: 1 empty MIDI track, 1 scene")
p1 = ALSProject(
    name="test1",
    bpm=120,
    tracks=[ALSTrack(name="MIDI1", track_type="midi")],
    scenes=[ALSScene(name="Scene1")],
)
write_als(p1, str(OUT / "test1_empty_midi.als"))

# Test 2: 1 MIDI track with 1 simple clip (4 notes)
print("Test 2: 1 MIDI track, 1 clip, 4 notes")
t2 = ALSTrack(
    name="MIDI1",
    track_type="midi",
    midi_clips=[ALSMidiClip(
        name="Clip1",
        start_beat=0.0,
        length_beats=16.0,
        notes=[
            ALSMidiNote(pitch=60, time=0.0, duration=1.0, velocity=100),
            ALSMidiNote(pitch=62, time=4.0, duration=1.0, velocity=100),
            ALSMidiNote(pitch=64, time=8.0, duration=1.0, velocity=100),
            ALSMidiNote(pitch=65, time=12.0, duration=1.0, velocity=100),
        ],
    )],
)
p2 = ALSProject(
    name="test2",
    bpm=120,
    tracks=[t2],
    scenes=[ALSScene(name="Scene1")],
)
write_als(p2, str(OUT / "test2_midi_with_notes.als"))

# Test 3: 1 MIDI track with automation only
print("Test 3: 1 MIDI track, automation only")
t3 = ALSTrack(
    name="MIDI1",
    track_type="midi",
    automations=[
        ALSAutomation(
            parameter_name="Volume",
            points=[
                ALSAutomationPoint(time=0.0, value=0.5),
                ALSAutomationPoint(time=16.0, value=1.0),
            ],
        ),
    ],
)
p3 = ALSProject(
    name="test3",
    bpm=120,
    tracks=[t3],
    scenes=[ALSScene(name="Scene1")],
)
write_als(p3, str(OUT / "test3_midi_automation.als"))

# Test 4: 2 MIDI tracks + 1 return
print("Test 4: 2 MIDI + 1 return track")
t4a = ALSTrack(name="MIDI1", track_type="midi")
t4b = ALSTrack(name="MIDI2", track_type="midi")
t4r = ALSTrack(name="Return1", track_type="return")
p4 = ALSProject(
    name="test4",
    bpm=120,
    tracks=[t4a, t4b, t4r],
    scenes=[ALSScene(name="Scene1"), ALSScene(name="Scene2")],
)
write_als(p4, str(OUT / "test4_multi_track.als"))

# Test 5: Full V12-like complexity but only 1 track
print("Test 5: 1 MIDI track, many notes + automation (V12-like)")
notes5 = [
    ALSMidiNote(
        pitch=36 + (i % 12),
        time=float(i * 2),
        duration=0.5,
        velocity=80 + (i % 40),
    )
    for i in range(200)
]
auto5 = [
    ALSAutomation(
        parameter_name="Volume",
        points=[ALSAutomationPoint(time=float(i * 4), value=0.3 + 0.5 * (i % 2))
                for i in range(100)],
    ),
    ALSAutomation(
        parameter_name="Pan",
        points=[ALSAutomationPoint(time=float(i * 4), value=-0.5 + (i % 3) * 0.5)
                for i in range(100)],
    ),
]
t5 = ALSTrack(
    name="DRUMS",
    track_type="midi",
    midi_clips=[ALSMidiClip(
        name="HeavyClip",
        start_beat=0.0,
        length_beats=400.0,
        notes=notes5,
    )],
    automations=auto5,
)
p5 = ALSProject(
    name="test5",
    bpm=127,
    tracks=[t5],
    scenes=[ALSScene(name="Scene1", tempo=127.0)],
)
write_als(p5, str(OUT / "test5_heavy_single.als"))

print("\nDone! Open each file in Ableton to find which one crashes:")
for f in sorted(OUT.glob("*.als")):
    print(f"  {f}")
