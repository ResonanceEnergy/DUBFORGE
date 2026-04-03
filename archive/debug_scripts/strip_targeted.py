"""Create targeted envelope strip variants for testing."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil

src = Path("output/ableton/Wild_Ones_V12.als")
out_dir = Path("output/ableton/test_bisect")
out_dir.mkdir(parents=True, exist_ok=True)

with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

def save(root_elem, name):
    xml_bytes = ET.tostring(root_elem, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    dst = out_dir / name
    with gzip.open(dst, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))
    print(f"Wrote: {dst}")

# Variant 1: Strip ONLY MidiTrack automation envelopes (keep MainTrack)
import copy
root1 = copy.deepcopy(root)
ls = root1.find(".//LiveSet")
tracks = ls.find("Tracks")
stripped = 0
for midi_track in tracks.findall("MidiTrack"):
    ae = midi_track.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            for child in list(envs):
                envs.remove(child)
                stripped += 1
print(f"Variant 1 (no MidiTrack auto): stripped {stripped} envelopes from MidiTracks")
save(root1, "v12_no_midi_auto.als")

# Variant 2: Strip ONLY MainTrack automation (keep MidiTrack)
root2 = copy.deepcopy(root)
ls2 = root2.find(".//LiveSet")
main = ls2.find(".//MainTrack")
if main is not None:
    ae = main.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            s2 = 0
            for child in list(envs):
                envs.remove(child)
                s2 += 1
            print(f"Variant 2 (no MainTrack auto): stripped {s2} MainTrack envelopes")
save(root2, "v12_no_main_auto.als")

# Variant 3: Only SUB (track 2) has automation — strip RISER (track 14) too
root3 = copy.deepcopy(root)
ls3 = root3.find(".//LiveSet")
tracks3 = ls3.find("Tracks")
for midi_track in tracks3.findall("MidiTrack"):
    tid = midi_track.get("Id")
    if tid == "14":  # RISER
        ae = midi_track.find("AutomationEnvelopes")
        if ae is not None:
            envs = ae.find("Envelopes")
            if envs is not None:
                for child in list(envs):
                    envs.remove(child)
print("Variant 3 (only SUB auto): kept SUB, stripped RISER")
save(root3, "v12_only_sub_auto.als")

# Variant 4: Only RISER (track 14) has automation — strip SUB (track 2)
root4 = copy.deepcopy(root)
ls4 = root4.find(".//LiveSet")
tracks4 = ls4.find("Tracks")
for midi_track in tracks4.findall("MidiTrack"):
    tid = midi_track.get("Id")
    if tid == "2":  # SUB
        ae = midi_track.find("AutomationEnvelopes")
        if ae is not None:
            envs = ae.find("Envelopes")
            if envs is not None:
                for child in list(envs):
                    envs.remove(child)
print("Variant 4 (only RISER auto): stripped SUB, kept RISER")
save(root4, "v12_only_riser_auto.als")
