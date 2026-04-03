"""Regenerate the Wild Ones V9 ALS file with the fixed generator."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, ALSClipInfo, ALSCuePoint, write_als
)
from pathlib import Path

BPM = 127
KEY = "Ab"
TOTAL_BARS = 144

# Stem names
STEMS = [
    "DRUMS", "BASS", "GROWL", "CHORDS", "HOOK", "PAD", "VOCAL", "ARP",
    "RISER", "FX", "TEXTURE", "DRONE", "WOBBLE", "SUB", "RIDDIM", "FORMANT"
]

# MIDI track names
MIDI_STEMS = ["Bass", "Hook", "Chords", "Vocal", "Growl", "Wobble"]

# Colors (Ableton color indices)
COLORS = {
    "DRUMS": 69, "BASS": 18, "GROWL": 27, "CHORDS": 20,
    "HOOK": 4, "PAD": 14, "VOCAL": 5, "ARP": 67,
    "RISER": 7, "FX": 8, "TEXTURE": 15, "DRONE": 16,
    "WOBBLE": 26, "SUB": 19, "RIDDIM": 28, "FORMANT": 9,
}

# Arrange sections (name, start_bar, length_bars)
SECTIONS = [
    ("INTRO", 0, 8), ("VERSE1", 8, 16), ("PRECHORUS1", 24, 8),
    ("DROP1", 32, 16), ("BREAKDOWN", 48, 16), ("BUILD", 64, 8),
    ("DROP2", 72, 16), ("BRIDGE", 88, 8), ("PRECHORUS2", 96, 8),
    ("DROP3", 104, 16), ("OUTRO", 120, 16), ("CODA", 136, 8),
]

total_beats = TOTAL_BARS * 4.0

# Build audio tracks
als_audio_tracks = []
stems_dir = Path("output/stems")
for stem in STEMS:
    wav_path = stems_dir / f"wild_ones_v9_{stem}.wav"
    if not wav_path.exists():
        print(f"WARNING: stem not found: {wav_path}")
        continue
    
    clip = ALSClipInfo(
        path=str(wav_path),
        start_beat=0.0,
        length_beats=total_beats,
        warp_mode=0,
        name=f"wild_ones_v9_{stem}",
    )
    
    track = ALSTrack(
        name=stem,
        track_type="audio",
        color=COLORS.get(stem, 0),
        volume_db=0.0,
        pan=0.0,
        arrangement_clips=[clip],
        send_levels=[0.3, 0.2],  # reverb, delay sends
    )
    als_audio_tracks.append(track)

# Build MIDI tracks (empty - just for reference)
als_midi_tracks = []
for midi_name in MIDI_STEMS:
    track = ALSTrack(
        name=f"{midi_name}_MIDI",
        track_type="midi",
        color=COLORS.get(midi_name.upper(), 0),
        send_levels=[0.0, 0.0],
    )
    als_midi_tracks.append(track)

# Return tracks
als_return_tracks = [
    ALSTrack(name="REVERB", track_type="return", color=10),
    ALSTrack(name="DELAY", track_type="return", color=11),
]

# Scenes
als_scenes = []
for sec_name, bar_start, bar_len in SECTIONS:
    als_scenes.append(ALSScene(
        name=sec_name,
        tempo=float(BPM),
    ))

# Cue points
als_cue_points = []
for sec_name, bar_start, bar_len in SECTIONS:
    als_cue_points.append(ALSCuePoint(
        name=sec_name,
        time=bar_start * 4.0,
    ))
golden_section_bar = int(TOTAL_BARS / 1.618)
als_cue_points.append(ALSCuePoint(
    name="GOLDEN_SECTION",
    time=golden_section_bar * 4.0,
))

# Build project
project = ALSProject(
    name="Wild_Ones_V9",
    bpm=float(BPM),
    tracks=als_audio_tracks + als_midi_tracks + als_return_tracks,
    scenes=als_scenes,
    notes="Wild Ones V9 (ULTIMATE Edition) | Ab major | 127 BPM | 144 bars",
    cue_points=als_cue_points,
)

als_path = "output/ableton/Wild_Ones_V9.als"
write_als(project, als_path)
print(f"ALS regenerated: {als_path}")
print(f"  Tracks: {len(project.tracks)}")
print(f"  BPM: {project.bpm}")
print(f"  Scenes: {len(project.scenes)}")
print(f"  Cues: {len(project.cue_points)}")
