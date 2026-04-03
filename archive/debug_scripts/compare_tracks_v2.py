"""Compare track structures between working tracks (0,1) and crashing tracks (2,3)."""
import gzip
import xml.etree.ElementTree as ET
import os

base = os.path.dirname(__file__)
v12_path = os.path.join(base, "output", "ableton", "Wild_Ones_V12.als")

with gzip.open(v12_path, "rb") as f:
    raw = f.read()
root = ET.fromstring(raw)

tracks = root.findall(".//Tracks/MidiTrack")

def get_track_name(t):
    el = t.find(".//EffectiveName")
    return el.get("Value", "?") if el is not None else "?"

def dump_track_structure(track, depth=0, max_depth=3):
    """Print track structure up to max_depth."""
    lines = []
    def recurse(elem, d):
        if d > max_depth:
            children = list(elem)
            if children:
                lines.append("  " * d + f"... ({len(children)} children)")
            return
        attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
        # Show Value if it exists
        val = elem.get("Value", "")
        tag_str = elem.tag
        if attrs:
            tag_str += f" [{attrs[:100]}]"
        lines.append("  " * d + tag_str)
        for child in elem:
            recurse(child, d + 1)
    recurse(track, depth)
    return lines

# Compare track 0 vs track 2 at high level
for idx in [0, 1, 2, 3]:
    t = tracks[idx]
    name = get_track_name(t)
    track_id = t.get("Id", "?")
    print(f"\n=== Track {idx}: {name} (Id={track_id}) ===")
    
    # First-level children
    for child in t:
        attrs = " ".join(f'{k}="{v[:30]}"' for k, v in child.attrib.items())
        n_children = len(list(child))
        print(f"  {child.tag} [{attrs}] ({n_children} children)")

# Compare specific elements
print("\n\n=== SENDS COMPARISON ===")
for idx in [0, 1, 2, 3]:
    t = tracks[idx]
    name = get_track_name(t)
    print(f"\nTrack {idx} ({name}):")
    
    sends = t.findall(".//TrackSendInfos/TrackSendInfo")
    print(f"  TrackSendInfo count: {len(sends)}")
    for si in sends:
        send_id = si.get("Id", "?")
        # Look for Send element inside
        send_elem = si.find("Send")
        if send_elem is not None:
            at = send_elem.find("AutomationTarget")
            if at is not None:
                pointee = at.get("Id", "?")
                print(f"    SendInfo[{send_id}] AutomationTarget.Id={pointee}")

# Compare AutomationEnvelopes
print("\n\n=== AUTOMATION ENVELOPES ===")
for idx in [0, 1, 2, 3]:
    t = tracks[idx]
    name = get_track_name(t)
    envs = t.findall(".//AutomationEnvelope")
    targets = t.findall(".//AutomationTarget")
    print(f"Track {idx} ({name}): {len(envs)} envelopes, {len(targets)} AutomationTargets")
    
    # Show all AutomationTarget IDs
    for at in targets:
        at_id = at.get("Id", "?")
        parent = "?"
        # Find parent element name
        for parent_elem in t.iter():
            for child in parent_elem:
                if child is at:
                    parent = parent_elem.tag
                    break
        print(f"    AT Id={at_id} parent={parent}")

# Check MidiTrack Id sequence
print("\n\n=== TRACK ID SEQUENCE ===")
for i, t in enumerate(tracks):
    print(f"  Track[{i}] Id={t.get('Id', '?')} name={get_track_name(t)}")

# Check return tracks
rts = root.findall(".//Tracks/ReturnTrack")
for i, rt in enumerate(rts):
    name_el = rt.find(".//EffectiveName")  
    name = name_el.get("Value", "?") if name_el is not None else "?"
    print(f"  ReturnTrack[{i}] Id={rt.get('Id', '?')} name={name}")
