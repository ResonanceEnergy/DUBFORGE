"""Compare full DeviceChain structure between template and generated MidiTrack."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

def dump_structure(elem, indent=0, max_depth=4):
    """Print full element tree structure."""
    prefix = "  " * indent
    attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
    tag = elem.tag
    if attrs:
        tag += f" [{attrs}]"
    print(f"{prefix}{tag}")
    if indent < max_depth:
        for child in elem:
            dump_structure(child, indent + 1, max_depth)

# Template
tp = Path(r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als")
with gzip.open(tp, "rb") as f:
    root = ET.parse(f).getroot()
tmpl_mt = root.find(".//Tracks/MidiTrack")
tmpl_dc = tmpl_mt.find("DeviceChain")

print("=== TEMPLATE DeviceChain (depth 2) ===")
dump_structure(tmpl_dc, max_depth=2)

# Generated V12 - track 14 (RISER)
v12 = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(v12, "rb") as f:
    v12root = ET.parse(f).getroot()
for mt in v12root.findall(".//Tracks/MidiTrack"):
    if mt.get("Id") == "14":
        v12_dc = mt.find("DeviceChain")
        print()
        print("=== GENERATED RISER DeviceChain (depth 2) ===")
        dump_structure(v12_dc, max_depth=2)
        break

# Also track 0 (DRUMS) for comparison
for mt in v12root.findall(".//Tracks/MidiTrack"):
    if mt.get("Id") == "0":
        v12_dc0 = mt.find("DeviceChain")
        print()
        print("=== GENERATED DRUMS DeviceChain (depth 2) ===")
        dump_structure(v12_dc0, max_depth=2)
        break
