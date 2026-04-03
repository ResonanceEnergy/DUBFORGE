"""Check factory template ReturnTrack structure."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

# Factory template
tmpl_path = Path(r"C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences\Crash\2026_03_28__01_12_39_BaseFiles\DefaultLiveSet.als")
if not tmpl_path.exists():
    # Try to find any DefaultLiveSet.als
    for p in Path(r"C:\Users\gripa\AppData\Roaming\Ableton").rglob("DefaultLiveSet.als"):
        tmpl_path = p
        break

print(f"Template: {tmpl_path}")
with gzip.open(str(tmpl_path), "rb") as f:
    root = ET.fromstring(f.read())

ls = root.find(".//LiveSet")
if ls is None:
    ls = root

tracks = ls.find("Tracks")
print(f"\nTracks: {[c.tag for c in tracks]}")

# Find ReturnTracks
for rt in tracks.findall("ReturnTrack"):
    rt_id = rt.get("Id")
    name_el = rt.find(".//Name/EffectiveName")
    name = name_el.get("Value", "?") if name_el is not None else "?"
    print(f"\n=== ReturnTrack Id={rt_id} Name={name} ===")
    
    dc = rt.find("DeviceChain")
    if dc is None:
        print("  NO DeviceChain!")
        continue
    
    print(f"  DeviceChain children: {[c.tag for c in dc]}")
    
    ms = dc.find("MainSequencer")
    if ms is not None:
        print(f"  MainSequencer children: {[c.tag for c in ms]}")
        csl = ms.find("ClipSlotList")
        if csl is not None:
            print(f"  MainSequencer ClipSlots: {len(list(csl))}")
    else:
        print("  NO MainSequencer!")
    
    fs = dc.find("FreezeSequencer")
    if fs is not None:
        print(f"  FreezeSequencer children: {[c.tag for c in fs]}")
        csl = fs.find("ClipSlotList")
        if csl is not None:
            print(f"  FreezeSequencer ClipSlots: {len(list(csl))}")
    else:
        print("  NO FreezeSequencer!")

# Also check scenes count for reference
scenes = ls.find("Scenes")
print(f"\nScenes count: {len(list(scenes)) if scenes is not None else 0}")
