"""Deep compare automation envelope structure: working (MainTrack) vs crashing (MidiTrack)."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

src = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

def dump_tree(elem, indent=0, max_depth=6):
    """Print element tree structure with attributes."""
    if indent > max_depth * 2:
        return
    attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
    text = (elem.text or "").strip()
    tag = f"{elem.tag}"
    if attrs:
        tag += f" [{attrs}]"
    if text and len(text) < 100:
        tag += f" = {text}"
    print(" " * indent + tag)
    for child in elem:
        dump_tree(child, indent + 2, max_depth)

# MainTrack automation (WORKS)
print("=== MAINTRACK AUTOMATION (from template, WORKS) ===")
main = root.find(".//MainTrack")
main_ae = main.find("AutomationEnvelopes")
dump_tree(main_ae, max_depth=8)

print()

# RISER (MidiTrack 14) automation (CRASHES with just 4 events)
print("=== RISER (MidiTrack Id=14) AUTOMATION (generated, CRASHES) ===")
tracks = root.find(".//Tracks")
for mt in tracks.findall("MidiTrack"):
    if mt.get("Id") == "14":
        ae = mt.find("AutomationEnvelopes")
        dump_tree(ae, max_depth=8)
        break

# Also show RISER's Mixer/Volume/AutomationTarget
print()
print("=== RISER MIXER VOLUME STRUCTURE ===")
for mt in tracks.findall("MidiTrack"):
    if mt.get("Id") == "14":
        dc = mt.find("DeviceChain")
        mixer = dc.find("Mixer") if dc is not None else None
        if mixer is not None:
            vol = mixer.find("Volume")
            if vol is not None:
                dump_tree(vol, max_depth=5)
        break

# Show what PointeeId 24421 actually points to
print()
print("=== SEARCH FOR AutomationTarget Id=24421 ===")
for at in root.iter("AutomationTarget"):
    if at.get("Id") == "24421":
        # Get parent chain
        parent = None
        for elem in root.iter():
            for child in elem:
                if child is at:
                    parent = elem
                    break
        print(f"  Found: AutomationTarget Id=24421 under parent={parent.tag if parent else '?'}")
        break

# Show what PointeeId 10 actually points to (MainTrack working one)
print()
print("=== SEARCH FOR AutomationTarget Id=10 ===")
for at in root.iter("AutomationTarget"):
    if at.get("Id") == "10":
        parent = None
        for elem in root.iter():
            for child in elem:
                if child is at:
                    parent = elem
                    break
        print(f"  Found: AutomationTarget Id=10 under parent={parent.tag if parent else '?'}")
        break
