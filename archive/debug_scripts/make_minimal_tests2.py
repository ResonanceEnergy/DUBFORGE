"""Progressive tests to find what causes V12 to crash.
Tests 6-10: closer to V12 without full complexity."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, ALSMidiNote, ALSMidiClip,
    ALSAutomation, ALSAutomationPoint, write_als,
)
from pathlib import Path

OUT = Path("output/ableton/test_minimal")
OUT.mkdir(parents=True, exist_ok=True)

# Test 6: 15 MIDI tracks (like V12) + 2 returns, 1 scene, NO clips/automation
print("Test 6: 15 MIDI + 2 returns, 1 scene, empty")
tracks6 = [ALSTrack(name=f"MIDI{i+1}", track_type="midi") for i in range(15)]
tracks6.append(ALSTrack(name="REVERB", track_type="return"))
tracks6.append(ALSTrack(name="DELAY", track_type="return"))
p6 = ALSProject(
    name="test6", bpm=127,
    tracks=tracks6,
    scenes=[ALSScene(name="Scene1")],
)
write_als(p6, str(OUT / "test6_15midi_2ret_empty.als"))

# Test 7: 15 MIDI + 2 returns, 13 scenes (V12 scene count), NO clips
print("Test 7: 15 MIDI + 2 returns, 13 scenes, empty")
tracks7 = [ALSTrack(name=f"MIDI{i+1}", track_type="midi") for i in range(15)]
tracks7.append(ALSTrack(name="REVERB", track_type="return"))
tracks7.append(ALSTrack(name="DELAY", track_type="return"))
scenes7 = [ALSScene(name=f"Scene{i+1}") for i in range(13)]
p7 = ALSProject(
    name="test7", bpm=127,
    tracks=tracks7,
    scenes=scenes7,
)
write_als(p7, str(OUT / "test7_15midi_2ret_13scenes.als"))

# Test 8: 15 MIDI + 2 returns, 13 scenes, each track has 1 clip with 1 note
print("Test 8: 15 MIDI + 2 returns, 13 scenes, 1 clip each")
tracks8 = []
for i in range(15):
    t = ALSTrack(
        name=f"MIDI{i+1}", track_type="midi",
        midi_clips=[ALSMidiClip(
            name=f"Clip{i}",
            start_beat=0.0,
            length_beats=16.0,
            notes=[ALSMidiNote(pitch=60+i, time=0.0, duration=4.0, velocity=100)]
        )]
    )
    tracks8.append(t)
tracks8.append(ALSTrack(name="REVERB", track_type="return"))
tracks8.append(ALSTrack(name="DELAY", track_type="return"))
p8 = ALSProject(
    name="test8", bpm=127,
    tracks=tracks8,
    scenes=[ALSScene(name=f"Scene{i+1}") for i in range(13)],
)
write_als(p8, str(OUT / "test8_clips_one_note.als"))

# Test 9: 15 MIDI + 2 returns, 13 scenes, clips with many notes (V12-like)
print("Test 9: 15 MIDI + 2 returns, many notes per clip")
tracks9 = []
for i in range(15):
    notes = [ALSMidiNote(pitch=36+(j%24), time=float(j), duration=0.5, velocity=80+(j%40))
             for j in range(200)]
    t = ALSTrack(
        name=f"MIDI{i+1}", track_type="midi",
        midi_clips=[ALSMidiClip(
            name=f"Clip{i}",
            start_beat=0.0,
            length_beats=400.0,
            notes=notes,
        )]
    )
    tracks9.append(t)
tracks9.append(ALSTrack(name="REVERB", track_type="return"))
tracks9.append(ALSTrack(name="DELAY", track_type="return"))
p9 = ALSProject(
    name="test9", bpm=127,
    tracks=tracks9,
    scenes=[ALSScene(name=f"Scene{i+1}") for i in range(13)],
)
write_als(p9, str(OUT / "test9_many_notes.als"))

# Test 10: Same as test8 but WITH automation (Volume + Pan on each track)
print("Test 10: 15 MIDI + 2 returns + automation")
tracks10 = []
for i in range(15):
    auto = [
        ALSAutomation(
            parameter_name="Volume",
            points=[ALSAutomationPoint(time=0.0, value=0.5),
                    ALSAutomationPoint(time=100.0, value=1.0)],
        ),
        ALSAutomation(
            parameter_name="Pan",
            points=[ALSAutomationPoint(time=0.0, value=-0.5),
                    ALSAutomationPoint(time=100.0, value=0.5)],
        ),
    ]
    t = ALSTrack(
        name=f"MIDI{i+1}", track_type="midi",
        midi_clips=[ALSMidiClip(
            name=f"Clip{i}",
            start_beat=0.0,
            length_beats=16.0,
            notes=[ALSMidiNote(pitch=60+i, time=0.0, duration=4.0, velocity=100)]
        )],
        automations=auto,
    )
    tracks10.append(t)
tracks10.append(ALSTrack(name="REVERB", track_type="return"))
tracks10.append(ALSTrack(name="DELAY", track_type="return"))
p10 = ALSProject(
    name="test10", bpm=127,
    tracks=tracks10,
    scenes=[ALSScene(name=f"Scene{i+1}") for i in range(13)],
)
write_als(p10, str(OUT / "test10_with_automation.als"))

print("\nDone! Test files:")
for f in sorted(OUT.glob("test[6-9]*.als")) + sorted(OUT.glob("test10*.als")):
    print(f"  {f}")
