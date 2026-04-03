"""Minimal test: manually build RISER's exact 4 events to see if data or injection method matters."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import copy

base = Path("output/ableton/test_bisect/v12_no_auto.als")
out_dir = Path("output/ableton/test_bisect")

with gzip.open(base, "rb") as f:
    base_tree = ET.parse(f)

# Test 1: Manually build RISER automation with exact same data as V12
root1 = copy.deepcopy(base_tree.getroot())
for mt in root1.iter("MidiTrack"):
    if mt.get("Id") == "14":
        dc = mt.find("DeviceChain")
        mixer = dc.find("Mixer")
        vol = mixer.find("Volume")
        at = vol.find("AutomationTarget")
        target_id = at.get("Id")
        print(f"RISER Volume AutomationTarget Id = {target_id}")

        ae = mt.find("AutomationEnvelopes")
        envs = ae.find("Envelopes")
        env = ET.SubElement(envs, "AutomationEnvelope", Id="0")
        et_elem = ET.SubElement(env, "EnvelopeTarget")
        ptid = ET.SubElement(et_elem, "PointeeId")
        ptid.set("Value", target_id)
        auto = ET.SubElement(env, "Automation")
        events = ET.SubElement(auto, "Events")
        # Exact same data as V12 RISER
        for i, (t, v) in enumerate([(64.0, 0.2), (96.0, 1.0), (192.0, 0.2), (224.0, 1.0)]):
            e = ET.SubElement(events, "FloatEvent", Id=str(i))
            e.set("Time", str(t))
            e.set("Value", str(v))
        atvs = ET.SubElement(auto, "AutomationTransformViewState")
        itp = ET.SubElement(atvs, "IsTransformPending")
        itp.set("Value", "false")
        ET.SubElement(atvs, "TimeAndValueTransforms")
        break

dst1 = out_dir / "manual_riser_4pt.als"
xml_bytes = ET.tostring(root1, encoding="unicode", xml_declaration=False)
xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with gzip.open(dst1, "wb") as f:
    f.write(xml_bytes.encode("utf-8"))
print(f"Wrote: {dst1}")

# Test 2: Same data but with Time starting at 0.0 (in case time range matters)
root2 = copy.deepcopy(base_tree.getroot())
for mt in root2.iter("MidiTrack"):
    if mt.get("Id") == "14":
        ae = mt.find("AutomationEnvelopes")
        envs = ae.find("Envelopes")
        dc = mt.find("DeviceChain")
        mixer = dc.find("Mixer")
        vol = mixer.find("Volume")
        at = vol.find("AutomationTarget")
        target_id = at.get("Id")

        env = ET.SubElement(envs, "AutomationEnvelope", Id="0")
        et_elem = ET.SubElement(env, "EnvelopeTarget")
        ptid = ET.SubElement(et_elem, "PointeeId")
        ptid.set("Value", target_id)
        auto = ET.SubElement(env, "Automation")
        events = ET.SubElement(auto, "Events")
        for i, (t, v) in enumerate([(0.0, 0.2), (32.0, 1.0), (128.0, 0.2), (160.0, 1.0)]):
            e = ET.SubElement(events, "FloatEvent", Id=str(i))
            e.set("Time", str(t))
            e.set("Value", str(v))
        atvs = ET.SubElement(auto, "AutomationTransformViewState")
        itp = ET.SubElement(atvs, "IsTransformPending")
        itp.set("Value", "false")
        ET.SubElement(atvs, "TimeAndValueTransforms")
        break

dst2 = out_dir / "manual_riser_4pt_from0.als"
xml_bytes = ET.tostring(root2, encoding="unicode", xml_declaration=False)
xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with gzip.open(dst2, "wb") as f:
    f.write(xml_bytes.encode("utf-8"))
print(f"Wrote: {dst2}")

# Test 3: Diff the injected envelope XML vs manual one
v12 = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(v12, "rb") as f:
    v12_tree = ET.parse(f)
v12_root = v12_tree.getroot()

# Get V12's RISER envelope
for mt in v12_root.iter("MidiTrack"):
    if mt.get("Id") == "14":
        ae = mt.find("AutomationEnvelopes")
        envs = ae.find("Envelopes")
        v12_env = list(envs)[0]
        v12_xml = ET.tostring(v12_env, encoding="unicode")
        print(f"\nV12 RISER envelope XML ({len(v12_xml)} chars):")
        print(v12_xml)
        break

# Get our manual one
for mt in root1.iter("MidiTrack"):
    if mt.get("Id") == "14":
        ae = mt.find("AutomationEnvelopes")
        envs = ae.find("Envelopes")
        man_env = list(envs)[0]
        man_xml = ET.tostring(man_env, encoding="unicode")
        print(f"\nManual RISER envelope XML ({len(man_xml)} chars):")
        print(man_xml)
        break

# Check if they're identical
print(f"\nXML identical: {v12_xml == man_xml}")
if v12_xml != man_xml:
    for i, (a, b) in enumerate(zip(v12_xml, man_xml)):
        if a != b:
            print(f"  First diff at char {i}: V12='{v12_xml[max(0,i-20):i+20]}' vs Manual='{man_xml[max(0,i-20):i+20]}'")
            break
