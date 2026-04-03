"""Binary search for crash-causing element in V12.

Creates progressively larger subsets of V12 to find which element causes crash.
"""
import gzip
import xml.etree.ElementTree as ET
import os
import copy

base = os.path.dirname(__file__)
v12_path = os.path.join(base, "output", "ableton", "Wild_Ones_V12.als")
out_dir = os.path.join(base, "output", "ableton", "test_bisect")
os.makedirs(out_dir, exist_ok=True)

# Load V12
with gzip.open(v12_path, "rb") as f:
    raw = f.read()
root = ET.fromstring(raw)

liveset = root.find("LiveSet")
tracks_elem = liveset.find("Tracks")
midi_tracks = tracks_elem.findall("MidiTrack")
return_tracks = tracks_elem.findall("ReturnTrack")
scenes_elem = liveset.find("Scenes")
scenes = scenes_elem.findall("Scene")

print(f"V12 has {len(midi_tracks)} MIDI tracks, {len(return_tracks)} return tracks, {len(scenes)} scenes")

def get_track_name(track):
    el = track.find(".//EffectiveName")
    return el.get("Value", "?") if el is not None else "?"

for i, t in enumerate(midi_tracks):
    print(f"  Track {i}: {get_track_name(t)}")

def save_als(root_elem, filename):
    """Save XML to gzipped ALS.""" 
    xml_bytes = ET.tostring(root_elem, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    path = os.path.join(out_dir, filename)
    with gzip.open(path, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))
    print(f"  Saved: {filename} ({os.path.getsize(path)} bytes)")
    return path

# Test 1: Just 2 tracks (DRUMS + BASS), keep returns and scenes
print("\n--- Creating bisect variants ---")

for n_tracks in [2, 5, 8, 15]:
    r = copy.deepcopy(root)
    ls = r.find("LiveSet")
    te = ls.find("Tracks")
    
    # Remove excess MIDI tracks
    mt = te.findall("MidiTrack")
    for t in mt[n_tracks:]:
        te.remove(t)
    
    # Update SendsListPresets etc. — actually just save as-is
    fname = f"bisect_{n_tracks}tracks.als"
    save_als(r, fname)

# Test 2: Full 15 tracks but no clips (recreate bare skeleton from current V12)
r = copy.deepcopy(root)
for track in r.findall(".//MidiTrack"):
    events = track.find(".//MainSequencer/ClipTimeable/ArrangerAutomation/Events")
    if events is not None:
        for clip in list(events):
            events.remove(clip)
fname = "bisect_noClips.als"
save_als(r, fname)

# Test 3: Full 15 tracks, clips but with only 1 note each (simplify data)
r = copy.deepcopy(root)
for track in r.findall(".//MidiTrack"):
    events = track.find(".//MainSequencer/ClipTimeable/ArrangerAutomation/Events")
    if events is not None:
        for clip in events.findall("MidiClip"):
            # Simplify notes: keep only first KeyTrack with 1 note
            notes = clip.find("Notes")
            if notes is not None:
                key_tracks = notes.find("KeyTracks")
                if key_tracks is not None:
                    kts = key_tracks.findall("KeyTrack")
                    if len(kts) > 1:
                        for kt in kts[1:]:
                            key_tracks.remove(kt)
                    # In remaining KeyTrack, keep only first note
                    if kts:
                        notes_container = kts[0].find("Notes")
                        if notes_container is not None:
                            events_in = notes_container.findall("MidiNoteEvent")
                            for ev in events_in[1:]:
                                notes_container.remove(ev)
fname = "bisect_1note_each.als"
save_als(r, fname)

# Test 4: 15 tracks with clips but NO notes at all
r = copy.deepcopy(root)
for track in r.findall(".//MidiTrack"):
    for clip in track.findall(".//MidiClip"):
        notes = clip.find("Notes")
        if notes is not None:
            key_tracks = notes.find("KeyTracks")
            if key_tracks is not None:
                for kt in list(key_tracks):
                    key_tracks.remove(kt)
            # Reset NoteIdGenerator
            nig = notes.find("NoteIdGenerator")
            if nig is not None:
                nid = nig.find("NextId")
                if nid is not None:
                    nid.set("Value", "0")
fname = "bisect_clips_noNotes.als"
save_als(r, fname)

print("\n--- All bisect variants created ---")
print(f"Output: {out_dir}")
