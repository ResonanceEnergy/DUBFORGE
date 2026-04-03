"""Check ClipSlot count per track vs Scene count in V12.
ACCESS_VIOLATION if track has fewer ClipSlots than scenes."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

als_path = Path("output/ableton/Wild_Ones_V12.als")
if not als_path.exists():
    # Try other possible locations
    for p in Path("output").rglob("Wild_Ones_V12.als"):
        als_path = p
        break

print(f"Loading: {als_path}")
with gzip.open(str(als_path), "rb") as f:
    root = ET.fromstring(f.read())

ls = root.find(".//LiveSet")
if ls is None:
    ls = root  # maybe root IS LiveSet

# Count scenes
scenes = ls.find("Scenes")
scene_count = len(list(scenes)) if scenes is not None else 0
print(f"\nScenes: {scene_count}")
if scenes is not None:
    for sc in scenes:
        print(f"  Scene Id={sc.get('Id')}: {sc.find('Name').get('Value', '?') if sc.find('Name') is not None else '?'}")

# Check each track's ClipSlotList
tracks = ls.find("Tracks")
if tracks is None:
    print("ERROR: No Tracks element!")
    exit(1)

print(f"\n{'Track Type':<15} {'Id':<5} {'Name':<25} {'ClipSlots':<10} {'Match?'}")
print("-" * 70)

problems = []
for tr in tracks:
    tr_type = tr.tag
    tr_id = tr.get("Id", "?")
    name_el = tr.find(".//Name/EffectiveName")
    name = name_el.get("Value", "?") if name_el is not None else "?"

    # Check MainSequencer ClipSlotList
    dc = tr.find("DeviceChain")
    if dc is None:
        print(f"{tr_type:<15} {tr_id:<5} {name:<25} NO DEVICECHAIN")
        problems.append(f"{name}: no DeviceChain")
        continue

    ms = dc.find("MainSequencer")
    if ms is None:
        print(f"{tr_type:<15} {tr_id:<5} {name:<25} NO MAIN_SEQ")
        problems.append(f"{name}: no MainSequencer")
        continue

    csl = ms.find("ClipSlotList")
    cs_count = len(list(csl)) if csl is not None else 0
    match = "OK" if cs_count == scene_count else f"MISMATCH!"
    if cs_count != scene_count:
        problems.append(f"{name}: has {cs_count} ClipSlots, expected {scene_count}")

    print(f"{tr_type:<15} {tr_id:<5} {name:<25} {cs_count:<10} {match}")

    # Also check FreezeSequencer
    fs = dc.find("FreezeSequencer")
    if fs is not None:
        fs_csl = fs.find("ClipSlotList")
        fs_count = len(list(fs_csl)) if fs_csl is not None else 0
        if fs_count != scene_count:
            problems.append(f"{name} FreezeSeq: has {fs_count} ClipSlots, expected {scene_count}")
            print(f"  ^^ FreezeSeq ClipSlots: {fs_count} MISMATCH!")

# Check MasterTrack
mt = ls.find("MasterTrack")
if mt is not None:
    mt_dc = mt.find("DeviceChain")
    if mt_dc is not None:
        mt_ms = mt_dc.find("MainSequencer")
        if mt_ms is not None:
            mt_csl = mt_ms.find("ClipSlotList")
            mt_count = len(list(mt_csl)) if mt_csl is not None else 0
            match = "OK" if mt_count == scene_count else "MISMATCH!"
            if mt_count != scene_count:
                problems.append(f"MasterTrack: has {mt_count} ClipSlots, expected {scene_count}")
            print(f"{'MasterTrack':<15} {'M':<5} {'Master':<25} {mt_count:<10} {match}")

# Check ReturnTrack sends vs return count
return_count = sum(1 for tr in tracks if tr.tag == "ReturnTrack")
print(f"\nReturn tracks: {return_count}")

# Check sends on each track
print(f"\n{'Track':<25} {'Sends':<10} {'Expected':<10} {'Match?'}")
print("-" * 55)
for tr in tracks:
    if tr.tag == "ReturnTrack":
        continue  # returns don't send to themselves usually
    name_el = tr.find(".//Name/EffectiveName")
    name = name_el.get("Value", "?") if name_el is not None else "?"
    dc = tr.find("DeviceChain")
    if dc is None:
        continue
    mixer = dc.find("Mixer")
    if mixer is None:
        continue
    sends = mixer.find("Sends")
    send_count = len(list(sends)) if sends is not None else 0
    match = "OK" if send_count == return_count else "MISMATCH!"
    if send_count != return_count:
        problems.append(f"{name}: {send_count} sends, expected {return_count}")
    print(f"{name:<25} {send_count:<10} {return_count:<10} {match}")

# Also check master track sends
if mt is not None:
    mt_mixer = mt.find(".//Mixer")
    if mt_mixer is not None:
        mt_sends = mt_mixer.find("Sends")
        mt_send_count = len(list(mt_sends)) if mt_sends is not None else 0
        match = "OK" if mt_send_count == return_count else "MISMATCH!"
        if mt_send_count != return_count:
            problems.append(f"MasterTrack: {mt_send_count} sends, expected {return_count}")
        print(f"{'Master':<25} {mt_send_count:<10} {return_count:<10} {match}")

if problems:
    print(f"\n{'='*60}")
    print(f"PROBLEMS FOUND: {len(problems)}")
    for p in problems:
        print(f"  - {p}")
else:
    print("\nAll counts match!")
