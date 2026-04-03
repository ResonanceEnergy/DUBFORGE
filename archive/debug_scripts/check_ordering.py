"""Check element ordering in Ableton template vs generated tracks."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

# Load the factory template
template_path = Path(r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als")
with gzip.open(template_path, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()
ls = root.find("LiveSet")

# MainTrack element order
print("=== TEMPLATE MainTrack CHILD ELEMENT ORDER ===")
main = ls.find("MainTrack")
for i, child in enumerate(main):
    print(f"  {i:3d}: {child.tag}")

# Check if template has any audio/midi tracks
print()
tracks = ls.find("Tracks")
for child in tracks:
    print(f"=== TEMPLATE {child.tag} CHILD ELEMENT ORDER ===")
    for i, sub in enumerate(child):
        print(f"  {i:3d}: {sub.tag}")
    break  # just show the first one

# Now check OUR generated V12
print()
v12_path = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(v12_path, "rb") as f:
    v12_tree = ET.parse(f)
v12_root = v12_tree.getroot()
v12_ls = v12_root.find("LiveSet")

# Generated MidiTrack element order (first track)
tracks = v12_ls.find("Tracks")
for mt in tracks.findall("MidiTrack"):
    print(f"=== GENERATED MidiTrack Id={mt.get('Id')} CHILD ELEMENT ORDER ===")
    for i, child in enumerate(mt):
        print(f"  {i:3d}: {child.tag}")
    break  # just show the first one

# Generated MainTrack element order (from template)
print()
main = v12_ls.find("MainTrack")
print("=== V12 MainTrack CHILD ELEMENT ORDER ===")
for i, child in enumerate(main):
    print(f"  {i:3d}: {child.tag}")
