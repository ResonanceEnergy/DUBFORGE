"""Feature-by-feature crash isolation.
t17 loads fine. Now add V12 features one at a time:
  ta = volume_db + pan + color per track
  tb = ta + many notes (V12-scale per track)
  tc = ta + automation (Volume+Pan on every track)
  td = ta + tb + tc combined (V12-equivalent without device_names)
  te = td + device_names
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))

from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, ALSMidiNote, ALSMidiClip,
    ALSAutomation, ALSAutomationPoint, ALSCuePoint, write_als,
)
from pathlib import Path

OUT = Path("output/ableton/test_trackbuild")
OUT.mkdir(parents=True, exist_ok=True)

V12_TRACKS = [
    "DRUMS", "BASS", "SUB", "GROWL", "WOBBLE", "RIDDIM", "FORMANT",
    "LEAD", "COUNTER", "VOCAL_CHOP", "CHORDS", "PAD", "ARP",
    "FX", "RISER",
]
VOLUMES = {
    "DRUMS": 0.0, "BASS": -3.0, "SUB": -6.0, "GROWL": -4.0,
    "WOBBLE": -5.0, "RIDDIM": -5.0, "FORMANT": -5.0,
    "LEAD": -4.0, "COUNTER": -6.0, "VOCAL_CHOP": -5.0,
    "CHORDS": -6.0, "PAD": -9.0, "ARP": -8.0,
    "FX": -6.0, "RISER": -8.0,
}
PANS = {
    "DRUMS": 0.0, "BASS": 0.0, "SUB": 0.0, "GROWL": 0.0,
    "WOBBLE": 0.1, "RIDDIM": -0.1, "FORMANT": 0.15,
    "LEAD": 0.0, "COUNTER": -0.15, "VOCAL_CHOP": 0.2,
    "CHORDS": 0.0, "PAD": 0.2, "ARP": -0.3,
    "FX": 0.25, "RISER": -0.2,
}
COLORS = {
    "DRUMS": 69, "BASS": 69, "SUB": 69, "GROWL": 6,
    "WOBBLE": 6, "RIDDIM": 6, "FORMANT": 10,
    "LEAD": 25, "COUNTER": 25, "VOCAL_CHOP": 10,
    "CHORDS": 17, "PAD": 17, "ARP": 17,
    "FX": 45, "RISER": 45, "REVERB": 30, "DELAY": 30,
}
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

TOTAL_BEATS = 288 * 4.0  # ~V12 total length


def _simple_clip(name, idx):
    """4-note simple clip."""
    p = 36 + (idx * 5) % 48
    return ALSMidiClip(
        name=name, start_beat=0.0, length_beats=16.0,
        notes=[ALSMidiNote(pitch=p+k, time=float(k)*4, duration=2.0, velocity=90)
               for k in range(4)],
    )


def _heavy_clip(name, idx):
    """~300 notes across full arrangement length, like V12."""
    p = 36 + (idx * 5) % 48
    notes = []
    for j in range(300):
        t = float(j) * (TOTAL_BEATS / 300.0)
        notes.append(ALSMidiNote(
            pitch=p + (j % 24), time=t, duration=0.5,
            velocity=60 + (j % 60),
        ))
    return ALSMidiClip(
        name=name, start_beat=0.0, length_beats=TOTAL_BEATS, notes=notes,
    )


def _make_automation():
    """Volume + Pan automation with ~100 points each, like V12."""
    vol_pts = [ALSAutomationPoint(time=float(i)*10.0,
               value=0.3 + 0.5 * abs(math.sin(i * 0.3)))
               for i in range(120)]
    pan_pts = [ALSAutomationPoint(time=float(i)*10.0,
               value=-0.5 + math.sin(i * 0.2))
               for i in range(120)]
    return [
        ALSAutomation(parameter_name="Volume", points=vol_pts),
        ALSAutomation(parameter_name="Pan", points=pan_pts),
    ]


# ── ta: volume/pan/color ──
print("ta: volumes, pans, colors")
tracks_a = []
for i, name in enumerate(V12_TRACKS):
    tracks_a.append(ALSTrack(
        name=name, track_type="midi",
        color=COLORS.get(name, 0),
        volume_db=VOLUMES.get(name, 0.0),
        pan=PANS.get(name, 0.0),
        midi_clips=[_simple_clip(name, i)],
    ))
tracks_a.append(ALSTrack(name="REVERB", track_type="return",
                          color=COLORS["REVERB"], volume_db=-6.0))
tracks_a.append(ALSTrack(name="DELAY", track_type="return",
                          color=COLORS["DELAY"], volume_db=-9.0))
write_als(ALSProject(name="ta", bpm=127, tracks=tracks_a,
                     scenes=SCENES, cue_points=CUE_POINTS),
          str(OUT / "ta_vol_pan_color.als"))

# ── tb: many notes ──
print("tb: heavy notes (~4500 total)")
tracks_b = []
for i, name in enumerate(V12_TRACKS):
    tracks_b.append(ALSTrack(
        name=name, track_type="midi",
        midi_clips=[_heavy_clip(name, i)],
    ))
tracks_b.append(ALSTrack(name="REVERB", track_type="return"))
tracks_b.append(ALSTrack(name="DELAY", track_type="return"))
write_als(ALSProject(name="tb", bpm=127, tracks=tracks_b,
                     scenes=SCENES, cue_points=CUE_POINTS),
          str(OUT / "tb_heavy_notes.als"))

# ── tc: automation ──
print("tc: automation (Vol+Pan on all 15 tracks)")
tracks_c = []
for i, name in enumerate(V12_TRACKS):
    tracks_c.append(ALSTrack(
        name=name, track_type="midi",
        midi_clips=[_simple_clip(name, i)],
        automations=_make_automation(),
    ))
tracks_c.append(ALSTrack(name="REVERB", track_type="return"))
tracks_c.append(ALSTrack(name="DELAY", track_type="return"))
write_als(ALSProject(name="tc", bpm=127, tracks=tracks_c,
                     scenes=SCENES, cue_points=CUE_POINTS),
          str(OUT / "tc_automation.als"))

# ── td: everything except device_names ──
print("td: vol/pan/color + notes + automation (V12-like)")
tracks_d = []
for i, name in enumerate(V12_TRACKS):
    tracks_d.append(ALSTrack(
        name=name, track_type="midi",
        color=COLORS.get(name, 0),
        volume_db=VOLUMES.get(name, 0.0),
        pan=PANS.get(name, 0.0),
        midi_clips=[_heavy_clip(name, i)],
        automations=_make_automation(),
    ))
tracks_d.append(ALSTrack(name="REVERB", track_type="return",
                          color=COLORS["REVERB"], volume_db=-6.0))
tracks_d.append(ALSTrack(name="DELAY", track_type="return",
                          color=COLORS["DELAY"], volume_db=-9.0))
write_als(ALSProject(name="td", bpm=127, tracks=tracks_d,
                     scenes=SCENES, cue_points=CUE_POINTS,
                     master_volume_db=0.0),
          str(OUT / "td_full_no_devices.als"))

# ── te: everything + device_names ──
print("te: td + device_names=['Serum 2']")
tracks_e = []
for i, name in enumerate(V12_TRACKS):
    tracks_e.append(ALSTrack(
        name=name, track_type="midi",
        color=COLORS.get(name, 0),
        volume_db=VOLUMES.get(name, 0.0),
        pan=PANS.get(name, 0.0),
        device_names=["Serum 2"],
        midi_clips=[_heavy_clip(name, i)],
        automations=_make_automation(),
    ))
tracks_e.append(ALSTrack(name="REVERB", track_type="return",
                          color=COLORS["REVERB"], volume_db=-6.0))
tracks_e.append(ALSTrack(name="DELAY", track_type="return",
                          color=COLORS["DELAY"], volume_db=-9.0))
write_als(ALSProject(name="te", bpm=127, tracks=tracks_e,
                     scenes=SCENES, cue_points=CUE_POINTS,
                     master_volume_db=0.0,
                     notes="Test with device_names"),
          str(OUT / "te_full_with_devices.als"))

print("\nDone! Feature tests:")
for f in sorted(OUT.glob("t[a-e]*.als")):
    print(f"  {f.name}")
