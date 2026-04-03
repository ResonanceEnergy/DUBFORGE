"""Add automation to the RAW Ableton template's own MidiTrack."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

template_path = Path(r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als")
dst = Path("output/ableton/test_bisect/template_with_auto.als")
dst.parent.mkdir(parents=True, exist_ok=True)

with gzip.open(template_path, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()
ls = root.find("LiveSet")
tracks = ls.find("Tracks")

# Find the first MidiTrack in the template
midi_track = tracks.find("MidiTrack")
if midi_track is None:
    print("No MidiTrack in template!")
    exit(1)

print(f"Template MidiTrack Id={midi_track.get('Id')}")

# Find its Volume AutomationTarget Id
dc = midi_track.find("DeviceChain")
mixer = dc.find("Mixer")
vol = mixer.find("Volume")
at = vol.find("AutomationTarget")
target_id = at.get("Id")
print(f"Volume AutomationTarget Id = {target_id}")

# Find AutomationEnvelopes container
ae = midi_track.find("AutomationEnvelopes")
envs = ae.find("Envelopes")

# Add a simple automation envelope
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

# Save
xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with gzip.open(dst, "wb") as f:
    f.write(xml_bytes.encode("utf-8"))
print(f"Wrote: {dst}")
print(f"Added Volume automation (PointeeId={target_id}) to template's own MidiTrack")
