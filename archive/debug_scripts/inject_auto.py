"""Inject specific V12 automation envelopes into the known-good no-auto base."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import copy

v12 = Path("output/ableton/Wild_Ones_V12.als")
base = Path("output/ableton/test_bisect/v12_no_auto.als")
out_dir = Path("output/ableton/test_bisect")

# Load both
with gzip.open(v12, "rb") as f:
    v12_tree = ET.parse(f)
v12_root = v12_tree.getroot()

with gzip.open(base, "rb") as f:
    base_tree = ET.parse(f)
base_root = base_tree.getroot()

# Extract AutomationEnvelopes from V12 MidiTracks
v12_envelopes = {}  # track_id -> list of AutomationEnvelope elements
for mt in v12_root.iter("MidiTrack"):
    tid = mt.get("Id")
    ae = mt.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            children = list(envs)
            if children:
                v12_envelopes[tid] = children
                name_el = mt.find(".//Name/EffectiveName")
                name = name_el.get("Value", "?") if name_el is not None else "?"
                print(f"V12 Track {tid} ({name}): {len(children)} envelope(s)")

def make_variant(track_ids_to_inject, label):
    """Inject V12 envelopes for given track IDs into clean base."""
    root = copy.deepcopy(base_root)
    for mt in root.iter("MidiTrack"):
        tid = mt.get("Id")
        if tid in track_ids_to_inject and tid in v12_envelopes:
            ae = mt.find("AutomationEnvelopes")
            envs = ae.find("Envelopes")
            for env in v12_envelopes[tid]:
                envs.append(copy.deepcopy(env))
            name_el = mt.find(".//Name/EffectiveName")
            name = name_el.get("Value", "?") if name_el is not None else "?"
            print(f"  Injected {len(v12_envelopes[tid])} envelope(s) into track {tid} ({name})")
    
    dst = out_dir / f"{label}.als"
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    with gzip.open(dst, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))
    print(f"  Wrote: {dst}")

# Variant 1: Only SUB (track 2) automation
print("\n--- inject_sub_only ---")
make_variant({"2"}, "inject_sub_only")

# Variant 2: Only RISER (track 14) automation
print("\n--- inject_riser_only ---")
make_variant({"14"}, "inject_riser_only")

# Variant 3: Both SUB + RISER
print("\n--- inject_sub_riser ---")
make_variant({"2", "14"}, "inject_sub_riser")

print("\nDone! Test with _quick_test.py")
