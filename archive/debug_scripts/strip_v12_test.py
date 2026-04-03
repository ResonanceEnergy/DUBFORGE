"""Strip features from V12.als to isolate crash cause.

Takes the actual crashing V12, strips one thing at a time,
re-compresses, and outputs test variants.
"""
import gzip
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path("output/ableton/Wild_Ones_V12.als")
OUT = Path("output/ableton/test_v12strip")
OUT.mkdir(parents=True, exist_ok=True)

# Parse original
with gzip.open(str(SRC), "rb") as f:
    raw = f.read()
print(f"Original V12: {len(raw):,} bytes")


def save(tree, name):
    xml_bytes = ET.tostring(tree.getroot(), encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    data = xml_bytes.encode("utf-8")
    out_path = OUT / f"{name}.als"
    with gzip.open(str(out_path), "wb") as f:
        f.write(data)
    print(f"  {name}.als: {len(data):,} bytes")
    return out_path


# --- s1: Strip bracket names (plain track names) ---
print("\ns1: Plain track names (no [Serum2: ...])")
tree = ET.ElementTree(ET.fromstring(raw))
for track in tree.findall(".//Tracks/MidiTrack"):
    for name_el in track.findall(".//Name/EffectiveName"):
        val = name_el.get("Value", "")
        if "[" in val:
            name_el.set("Value", val.split("[")[0].strip())
    for name_el in track.findall(".//Name/UserName"):
        val = name_el.get("Value", "")
        if "[" in val:
            name_el.set("Value", val.split("[")[0].strip())
save(tree, "s1_plain_names")


# --- s2: Strip ALL automation envelopes ---
print("\ns2: No automation envelopes")
tree = ET.ElementTree(ET.fromstring(raw))
for env_parent in tree.findall(".//AutomationEnvelopes"):
    envs = env_parent.find("Envelopes")
    if envs is not None:
        for child in list(envs):
            envs.remove(child)
save(tree, "s2_no_automation")


# --- s3: Strip Annotation (notes/description) ---
print("\ns3: Empty annotation")
tree = ET.ElementTree(ET.fromstring(raw))
for ann in tree.findall(".//Annotation"):
    val = ann.find("Value")
    if val is not None:
        val.text = ""
save(tree, "s3_no_annotation")


# --- s4: Keep only first 2 MIDI tracks + returns ---
print("\ns4: Only DRUMS + BASS + returns")
tree = ET.ElementTree(ET.fromstring(raw))
tracks_el = tree.find(".//Tracks")
midi_tracks = tracks_el.findall("MidiTrack")
return_tracks = tracks_el.findall("ReturnTrack")
# Remove tracks 2..14 (keep 0=DRUMS, 1=BASS)
for t in midi_tracks[2:]:
    tracks_el.remove(t)
# Fix scenes - remove extra ClipSlots to match track count
for scene in tree.findall(".//Scenes/Scene"):
    slots = scene.find("ClipSlots")
    if slots is not None:
        slot_list = list(slots)
        # Keep only first 2 slots (for 2 midi tracks)
        for s in slot_list[2:]:
            slots.remove(s)
save(tree, "s4_2tracks_only")


# --- s5: Only DRUMS track (1 midi + returns) ---
print("\ns5: Only DRUMS + returns")
tree = ET.ElementTree(ET.fromstring(raw))
tracks_el = tree.find(".//Tracks")
midi_tracks = tracks_el.findall("MidiTrack")
for t in midi_tracks[1:]:
    tracks_el.remove(t)
for scene in tree.findall(".//Scenes/Scene"):
    slots = scene.find("ClipSlots")
    if slots is not None:
        slot_list = list(slots)
        for s in slot_list[1:]:
            slots.remove(s)
save(tree, "s5_drums_only")


# --- s6: All tracks but ZERO notes (empty KeyTracks) ---
print("\ns6: All tracks, zero notes")
tree = ET.ElementTree(ET.fromstring(raw))
for kt in tree.findall(".//KeyTracks"):
    for child in list(kt):
        kt.remove(child)
save(tree, "s6_no_notes")


# --- s7: All tracks but simple 4-note clips (replace V12 note data) ---
print("\ns7: All tracks, 4-note simple clips")
tree = ET.ElementTree(ET.fromstring(raw))
note_id = [0]
for clip in tree.findall(".//MidiClip"):
    notes_el = clip.find("Notes")
    if notes_el is None:
        continue
    kt_el = notes_el.find("KeyTracks")
    if kt_el is None:
        continue
    # Clear existing KeyTracks
    for child in list(kt_el):
        kt_el.remove(child)
    # Add one simple KeyTrack with 4 notes at pitch 60
    kt = ET.SubElement(kt_el, "KeyTrack")
    kt_id = ET.SubElement(kt, "Id")
    kt_id.set("Value", "0")
    nn = ET.SubElement(kt, "Notes")
    for i in range(4):
        ne = ET.SubElement(nn, "MidiNoteEvent")
        ne.set("Time", str(float(i * 4)))
        ne.set("Duration", "2.0")
        ne.set("Velocity", "90")
        ne.set("VelocityDeviation", "0")
        ne.set("OffVelocity", "64")
        ne.set("Probability", "1")
        ne.set("IsEnabled", "true")
        ne.set("NoteId", str(note_id[0]))
        note_id[0] += 1
    mp = ET.SubElement(kt, "MidiKey")
    mp_val = ET.SubElement(mp, "Value")
    mp_val.set("Value", "60")
save(tree, "s7_simple_notes")


# --- s8: Strip device_names (remove PluginDesc elements) ---
print("\ns8: No plugin references")
tree = ET.ElementTree(ET.fromstring(raw))
for pd in tree.findall(".//PluginDesc"):
    parent = None
    # Find parent by searching
    for p in tree.iter():
        if pd in list(p):
            parent = p
            break
    if parent is not None:
        parent.remove(pd)
save(tree, "s8_no_plugins")


# --- s9: s1 + s6 combined (plain names + no notes) ---
print("\ns9: Plain names + zero notes + no automation")
tree = ET.ElementTree(ET.fromstring(raw))
# Strip names
for track in tree.findall(".//Tracks/MidiTrack"):
    for name_el in track.findall(".//Name/EffectiveName"):
        val = name_el.get("Value", "")
        if "[" in val:
            name_el.set("Value", val.split("[")[0].strip())
    for name_el in track.findall(".//Name/UserName"):
        val = name_el.get("Value", "")
        if "[" in val:
            name_el.set("Value", val.split("[")[0].strip())
# Strip notes
for kt in tree.findall(".//KeyTracks"):
    for child in list(kt):
        kt.remove(child)
# Strip automation
for env_parent in tree.findall(".//AutomationEnvelopes"):
    envs = env_parent.find("Envelopes")
    if envs is not None:
        for child in list(envs):
            envs.remove(child)
save(tree, "s9_bare_skeleton")


print(f"\nDone! {len(list(OUT.glob('s*.als')))} test variants in {OUT}")
print("\nTest plan:")
print("  s9 (bare skeleton)  → if crashes, structural/ID issue")
print("  s5 (drums only)     → if crashes, issue in DRUMS track")
print("  s6 (no notes)       → if loads, note data causes crash")
print("  s1 (plain names)    → if loads, bracket names cause crash")
print("  s2 (no automation)  → if loads, automation causes crash")
print("  s7 (simple notes)   → if loads, specific note values crash")
