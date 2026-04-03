"""Add automation to DRUMS (track 0) in v12_no_auto to test on a different track."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

src = Path("output/ableton/test_bisect/v12_no_auto.als")
dst = Path("output/ableton/test_bisect/v12_drums_auto.als")

with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

# Track 0 (DRUMS)
tracks = root.find(".//Tracks")
drums = None
for mt in tracks.findall("MidiTrack"):
    if mt.get("Id") == "0":
        drums = mt
        break

dc = drums.find("DeviceChain")
mixer = dc.find("Mixer")
vol = mixer.find("Volume")
at = vol.find("AutomationTarget")
target_id = at.get("Id")
print(f"DRUMS Volume AutomationTarget Id = {target_id}")

# Add the envelope
ae = drums.find("AutomationEnvelopes")
envs = ae.find("Envelopes")

env = ET.SubElement(envs, "AutomationEnvelope", Id="0")
et_elem = ET.SubElement(env, "EnvelopeTarget")
ptid = ET.SubElement(et_elem, "PointeeId")
ptid.set("Value", target_id)
auto = ET.SubElement(env, "Automation")
events = ET.SubElement(auto, "Events")
e1 = ET.SubElement(events, "FloatEvent", Id="0")
e1.set("Time", "0.0")
e1.set("Value", "0.5")
e2 = ET.SubElement(events, "FloatEvent", Id="1")
e2.set("Time", "16.0")
e2.set("Value", "1.0")
atvs = ET.SubElement(auto, "AutomationTransformViewState")
itp = ET.SubElement(atvs, "IsTransformPending")
itp.set("Value", "false")
ET.SubElement(atvs, "TimeAndValueTransforms")

xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with gzip.open(dst, "wb") as f:
    f.write(xml_bytes.encode("utf-8"))
print(f"Wrote: {dst}")
