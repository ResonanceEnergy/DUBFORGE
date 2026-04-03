"""Compare full Mixer XML between template MidiTrack and generated MidiTrack."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

def get_child_tags(elem, depth=0, max_depth=3):
    """Get a list of child tag names with depth."""
    result = []
    for child in elem:
        result.append(("  " * depth + child.tag, dict(child.attrib)))
        if depth < max_depth:
            result.extend(get_child_tags(child, depth + 1, max_depth))
    return result

# Template
template_path = Path(r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als")
with gzip.open(template_path, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()
tmpl_mt = root.find(".//Tracks/MidiTrack")
tmpl_dc = tmpl_mt.find("DeviceChain")
tmpl_mixer = tmpl_dc.find("Mixer")

print("=== TEMPLATE MidiTrack Mixer STRUCTURE ===")
for tag, attrs in get_child_tags(tmpl_mixer, max_depth=2):
    attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items()) if attrs else ""
    print(f"  {tag} {attr_str}".rstrip())

# Generated V12
v12_path = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(v12_path, "rb") as f:
    v12_tree = ET.parse(f)
v12_root = v12_tree.getroot()

# Use RISER track (Id=14) which had the crashing automation
for mt in v12_root.findall(".//Tracks/MidiTrack"):
    if mt.get("Id") == "14":
        v12_dc = mt.find("DeviceChain")
        v12_mixer = v12_dc.find("Mixer")
        print()
        print("=== GENERATED RISER (MidiTrack 14) Mixer STRUCTURE ===")
        for tag, attrs in get_child_tags(v12_mixer, max_depth=2):
            attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items()) if attrs else ""
            print(f"  {tag} {attr_str}".rstrip())
        break

# Also dump the full Volume element from each
print()
print("=== TEMPLATE Volume (full XML) ===")
tmpl_vol = tmpl_mixer.find("Volume")
print(ET.tostring(tmpl_vol, encoding="unicode"))

print()
print("=== GENERATED RISER Volume (full XML) ===")
v12_vol = v12_mixer.find("Volume")
print(ET.tostring(v12_vol, encoding="unicode"))
