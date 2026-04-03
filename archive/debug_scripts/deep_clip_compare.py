"""Deep dive into V12 XML to find crash-causing structure."""
import gzip
import xml.etree.ElementTree as ET
import os

base = os.path.dirname(__file__)

def decompress(als_path):
    with gzip.open(als_path, "rb") as f:
        return f.read()

# Decompress both
mini_xml = decompress(os.path.join(base, "output", "ableton", "_test_mini.als"))
v12_xml = decompress(os.path.join(base, "output", "ableton", "Wild_Ones_V12.als"))

mini_root = ET.fromstring(mini_xml)
v12_root = ET.fromstring(v12_xml)

print("=== ARRANGEMENT CLIPS COMPARISON ===")
print()

# Find clips in arrangement view
def find_arrangement_clips(root):
    clips = []
    for track in root.findall(".//MidiTrack"):
        track_name_el = track.find(".//EffectiveName")
        track_name = track_name_el.get("Value", "?") if track_name_el is not None else "?"
        
        events = track.findall(".//MainSequencer/ClipTimeable/ArrangerAutomation/Events/MidiClip")
        for clip in events:
            clip_name = clip.find("Name")
            name_val = clip_name.get("Value", "?") if clip_name is not None else "?"
            
            # Get key attributes
            time_val = clip.get("Time", "?")
            clip_id = clip.get("Id", "?")
            
            # Count notes
            notes = clip.findall(".//MidiNoteEvent")
            
            # Check for special elements
            has_loop = clip.find("Loop") is not None
            has_envelopes = clip.find("Envelopes") is not None
            has_note_id_gen = clip.find(".//NoteIdGenerator") is not None
            
            clips.append({
                "track": track_name,
                "name": name_val,
                "id": clip_id,
                "time": time_val,
                "note_count": len(notes),
                "has_loop": has_loop,
                "has_envelopes": has_envelopes,
                "has_note_id_gen": has_note_id_gen,
            })
    return clips

mini_clips = find_arrangement_clips(mini_root)
v12_clips = find_arrangement_clips(v12_root)

print(f"Mini: {len(mini_clips)} arrangement clips")
for c in mini_clips[:5]:
    print(f"  Track={c['track']}, Name={c['name']}, Id={c['id']}, Time={c['time']}, "
          f"Notes={c['note_count']}, Loop={c['has_loop']}, Env={c['has_envelopes']}, "
          f"NoteIdGen={c['has_note_id_gen']}")

print(f"\nV12: {len(v12_clips)} arrangement clips")
for c in v12_clips[:5]:
    print(f"  Track={c['track']}, Name={c['name']}, Id={c['id']}, Time={c['time']}, "
          f"Notes={c['note_count']}, Loop={c['has_loop']}, Env={c['has_envelopes']}, "
          f"NoteIdGen={c['has_note_id_gen']}")

print("\n=== CLIP CHILDREN COMPARISON ===")

def get_clip_children(clip):
    """Get ordered list of child element tags."""
    return [child.tag for child in clip]

# Compare first clip from each
if mini_clips:
    mini_first = mini_root.findall(".//MainSequencer/ClipTimeable/ArrangerAutomation/Events/MidiClip")[0]
    print(f"\nMini first clip children ({len(list(mini_first))} total):")
    for i, child in enumerate(mini_first):
        attrs = " ".join(f"{k}={v}" for k, v in child.attrib.items())
        print(f"  [{i:2d}] {child.tag} {attrs[:80]}")

if v12_clips:
    v12_first = v12_root.findall(".//MainSequencer/ClipTimeable/ArrangerAutomation/Events/MidiClip")[0]
    print(f"\nV12 first clip children ({len(list(v12_first))} total):")
    for i, child in enumerate(v12_first):
        attrs = " ".join(f"{k}={v}" for k, v in child.attrib.items())
        print(f"  [{i:2d}] {child.tag} {attrs[:80]}")

# Check clip structure differences
print("\n=== CHILD TAG ORDER COMPARISON ===")
if mini_clips and v12_clips:
    mini_tags = get_clip_children(mini_first)
    v12_tags = get_clip_children(v12_first)
    
    if mini_tags == v12_tags:
        print("IDENTICAL child tag order")
    else:
        print(f"DIFFERENT! Mini has {len(mini_tags)} vs V12 has {len(v12_tags)}")
        # Show differences
        max_len = max(len(mini_tags), len(v12_tags))
        for i in range(max_len):
            m = mini_tags[i] if i < len(mini_tags) else "(missing)"
            v = v12_tags[i] if i < len(v12_tags) else "(missing)"
            marker = " ✓" if m == v else " *** DIFF ***"
            print(f"  [{i:2d}] Mini: {m:35s}  V12: {v:35s} {marker}")

# Check session clips (ClipSlots)
print("\n=== SESSION CLIP SLOTS ===")
def count_session_clips(root):
    filled = 0
    empty = 0
    for cs in root.findall(".//ClipSlot"):
        clip_slot_value = cs.find("Value")
        if clip_slot_value is not None and len(list(clip_slot_value)) > 0:
            filled += 1
        else:
            empty += 1
    return filled, empty

mf, me = count_session_clips(mini_root)
vf, ve = count_session_clips(v12_root)
print(f"  Mini: {mf} filled, {me} empty clip slots")
print(f"  V12:  {vf} filled, {ve} empty clip slots")

# Check if any ClipSlot has clip content
print("\n=== CHECKING CLIPSLOT CONTENT ===")
for label, root in [("Mini", mini_root), ("V12", v12_root)]:
    slots_with_clips = root.findall(".//ClipSlotList/ClipSlot/Value/MidiClip")
    print(f"  {label}: {len(slots_with_clips)} MidiClips in ClipSlots (session view)")
