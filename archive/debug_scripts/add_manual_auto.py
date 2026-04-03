"""Add a minimal automation envelope to the working v12_no_auto file and test."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

src = Path("output/ableton/test_bisect/v12_no_auto.als")
dst = Path("output/ableton/test_bisect/v12_manual_auto.als")

with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

# Find RISER track (MidiTrack Id=14)
tracks = root.find(".//Tracks")
riser = None
for mt in tracks.findall("MidiTrack"):
    if mt.get("Id") == "14":
        riser = mt
        break

# Find RISER's Volume AutomationTarget Id
dc = riser.find("DeviceChain")
mixer = dc.find("Mixer")
vol = mixer.find("Volume")
at = vol.find("AutomationTarget")
target_id = at.get("Id")
print(f"RISER Volume AutomationTarget Id = {target_id}")

# Find the AutomationEnvelopes/Envelopes container
ae = riser.find("AutomationEnvelopes")
envs = ae.find("Envelopes")

# Add a minimal envelope (same structure as working MainTrack ones)
env = ET.SubElement(envs, "AutomationEnvelope", Id="0")
et_elem = ET.SubElement(env, "EnvelopeTarget")
ptid = ET.SubElement(et_elem, "PointeeId")
ptid.set("Value", target_id)
auto = ET.SubElement(env, "Automation")
events = ET.SubElement(auto, "Events")
# Just 2 events like a simple ramp
e1 = ET.SubElement(events, "FloatEvent", Id="0")
e1.set("Time", "64.0")
e1.set("Value", "0.2")
e2 = ET.SubElement(events, "FloatEvent", Id="1")
e2.set("Time", "96.0")
e2.set("Value", "1.0")
atvs = ET.SubElement(auto, "AutomationTransformViewState")
itp = ET.SubElement(atvs, "IsTransformPending")
itp.set("Value", "false")
ET.SubElement(atvs, "TimeAndValueTransforms")

# Save
xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with gzip.open(dst, "wb") as f:
    f.write(xml_bytes.encode("utf-8"))
print(f"Wrote: {dst}")
print("Added 1 envelope with 2 events to RISER")
