"""Find non-unique list IDs in the ALS XML."""
import gzip
import xml.etree.ElementTree as ET
from collections import Counter

with gzip.open('output/ableton/Wild_Ones_V6.als', 'rb') as f:
    xml_str = f.read().decode('utf-8')

root = ET.fromstring(xml_str)

# For every parent element, check if any children share the same tag+Id combo
duplicates = []

def check_children(parent, path=""):
    """Check for duplicate Id attributes among sibling elements."""
    children_with_ids = []
    for child in parent:
        child_id = child.get("Id")
        if child_id is not None:
            children_with_ids.append((child.tag, child_id))
    
    # Check for duplicates within same tag
    tag_id_counts = Counter(children_with_ids)
    for (tag, cid), count in tag_id_counts.items():
        if count > 1:
            duplicates.append((path, tag, cid, count))
    
    # Also check: all Ids within same parent regardless of tag
    id_only = [cid for (_, cid) in children_with_ids]
    id_counts = Counter(id_only)
    for cid, count in id_counts.items():
        if count > 1:
            tags = [tag for (tag, tid) in children_with_ids if tid == cid]
            duplicates.append((path + " [cross-tag]", str(tags), cid, count))
    
    for child in parent:
        child_path = f"{path}/{child.tag}"
        if child.get("Id"):
            child_path += f"[@Id={child.get('Id')}]"
        check_children(child, child_path)

check_children(root, "Ableton")

if duplicates:
    print(f"FOUND {len(duplicates)} DUPLICATE ID ISSUES:")
    seen = set()
    for path, tag, cid, count in duplicates:
        key = (path, tag, cid)
        if key not in seen:
            seen.add(key)
            print(f"  Path: {path}")
            print(f"    Tag={tag} Id={cid} appears {count}x")
            print()
else:
    print("No duplicate IDs found among siblings.")

# Also check: track-level Id uniqueness
print("\n--- Track IDs ---")
tracks = root.find('.//Tracks')
if tracks is not None:
    track_ids = []
    for t in tracks:
        tid = t.get("Id")
        track_ids.append((t.tag, tid))
        print(f"  {t.tag} Id={tid} name={t.find('.//Name/EffectiveName').get('Value')}")
    
    id_counts = Counter([tid for (_, tid) in track_ids])
    for tid, count in id_counts.items():
        if count > 1:
            print(f"  ** DUPLICATE track Id={tid} appears {count}x")

# Check scene IDs
print("\n--- Scene IDs ---")
scenes = root.findall('.//Scenes/Scene')
scene_ids = [s.get("Id") for s in scenes]
scene_counts = Counter(scene_ids)
for sid, count in scene_counts.items():
    if count > 1:
        print(f"  ** DUPLICATE scene Id={sid} appears {count}x")
    else:
        print(f"  Scene Id={sid} OK")

# Check ClipSlot IDs per sequencer
print("\n--- ClipSlot ID check (first track) ---")
first_track = tracks[0] if tracks is not None else None
if first_track is not None:
    for seq_tag in ["MainSequencer", "FreezeSequencer"]:
        seq = first_track.find(f'.//{seq_tag}')
        if seq is not None:
            slots = seq.findall('.//ClipSlotList/ClipSlot')
            slot_ids = [s.get("Id") for s in slots]
            print(f"  {seq_tag}: {len(slots)} clip slots, IDs: {slot_ids}")
            slot_counts = Counter(slot_ids)
            for sid, count in slot_counts.items():
                if count > 1:
                    print(f"    ** DUPLICATE ClipSlot Id={sid} appears {count}x")

# Check Locator IDs
print("\n--- Locator IDs ---")
locs = root.findall('.//Locators/Locators/Locator')
loc_ids = [l.get("Id") for l in locs]
loc_counts = Counter(loc_ids)
for lid, count in loc_counts.items():
    if count > 1:
        print(f"  ** DUPLICATE Locator Id={lid} appears {count}x")
print(f"  Total: {len(locs)} locators, IDs: {loc_ids}")

# Check AutomationTarget IDs globally (must be unique across entire file)
print("\n--- AutomationTarget ID uniqueness (global) ---")
all_at = root.iter()
at_ids = []
for elem in root.iter():
    if elem.tag in ("AutomationTarget", "ModulationTarget"):
        at_id = elem.get("Id")
        if at_id is not None:
            at_ids.append(at_id)

at_counts = Counter(at_ids)
dups = {k: v for k, v in at_counts.items() if v > 1}
if dups:
    print(f"  ** {len(dups)} DUPLICATE AutomationTarget/ModulationTarget IDs:")
    for k, v in sorted(dups.items(), key=lambda x: int(x[0])):
        print(f"    Id={k} appears {v}x")
else:
    print(f"  All {len(at_ids)} AutomationTarget/ModulationTarget IDs are unique.")

# Check Pointee IDs globally
print("\n--- Pointee ID uniqueness (global) ---")
pointee_ids = []
for elem in root.iter():
    if elem.tag == "Pointee":
        pid = elem.get("Id")
        if pid is not None:
            pointee_ids.append(pid)

p_counts = Counter(pointee_ids)
p_dups = {k: v for k, v in p_counts.items() if v > 1}
if p_dups:
    print(f"  ** {len(p_dups)} DUPLICATE Pointee IDs:")
    for k, v in sorted(p_dups.items(), key=lambda x: int(x[0])):
        print(f"    Id={k} appears {v}x")
else:
    print(f"  All {len(pointee_ids)} Pointee IDs are unique.")

# Check TrackSendHolder IDs per track
print("\n--- TrackSendHolder IDs ---")
for t in (tracks or []):
    name = t.find('.//Name/EffectiveName').get('Value')
    holders = t.findall('.//TrackSendHolder')
    hids = [h.get("Id") for h in holders]
    h_counts = Counter(hids)
    for hid, count in h_counts.items():
        if count > 1:
            print(f"  ** {name}: DUPLICATE TrackSendHolder Id={hid} appears {count}x")

# Check AutomationLane IDs
print("\n--- AutomationLane IDs per DeviceChain ---")
for t in (tracks or []):
    name = t.find('.//Name/EffectiveName').get('Value')
    lanes = t.findall('.//AutomationLane')
    lids = [l.get("Id") for l in lanes]
    l_counts = Counter(lids)
    for lid, count in l_counts.items():
        if count > 1:
            print(f"  ** {name}: DUPLICATE AutomationLane Id={lid} appears {count}x")

# Check FloatEvent IDs
print("\n--- FloatEvent ID uniqueness per Automation ---")
dup_event_count = 0
for env in root.iter("AutomationEnvelope"):
    events = env.findall('.//FloatEvent')
    eids = [e.get("Id") for e in events]
    e_counts = Counter(eids)
    for eid, count in e_counts.items():
        if count > 1:
            dup_event_count += 1
            param = env.find("ParameterName")
            pname = param.get("Value") if param is not None else "?"
            print(f"  ** param={pname}: DUPLICATE FloatEvent Id={eid} appears {count}x")

if dup_event_count == 0:
    total_events = len(list(root.iter("FloatEvent")))
    print(f"  All FloatEvent IDs unique within their envelopes. (Total: {total_events})")

print("\nDONE")
