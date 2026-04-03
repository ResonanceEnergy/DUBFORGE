"""Compare the AutomationEnvelope XML from generator vs working manual test."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

# Load the V12 (with automation that crashes)
v12 = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(v12, "rb") as f:
    v12_tree = ET.parse(f)
v12_root = v12_tree.getroot()

# Load a working individual track test (any of them)
# Let's just check the auto_track_2.als (SUB track)
working = Path("output/ableton/test_bisect/auto_track_2.als")
if working.exists():
    with gzip.open(working, "rb") as f:
        w_tree = ET.parse(f)
    w_root = w_tree.getroot()
else:
    w_root = None
    print("No working test file found")

# Dump ALL AutomationEnvelopes from V12
print("=== V12 AutomationEnvelopes ===")
for mt in v12_root.iter("MidiTrack"):
    tid = mt.get("Id")
    name_el = mt.find(".//Name/EffectiveName")
    name = name_el.get("Value", "?") if name_el is not None else "?"
    ae = mt.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            children = list(envs)
            if children:
                for env in children:
                    env_id = env.get("Id")
                    target = env.find("EnvelopeTarget")
                    ptid = target.find("PointeeId").get("Value") if target is not None else "?"
                    auto = env.find("Automation")
                    events = auto.find("Events") if auto is not None else None
                    n_events = len(list(events)) if events is not None else 0
                    print(f"\n  Track {tid} ({name}): EnvId={env_id}, PointeeId={ptid}, Events={n_events}")
                    
                    # Print full XML of this envelope (first 2000 chars)
                    xml_str = ET.tostring(env, encoding="unicode")
                    if n_events <= 10:
                        print(f"    Full XML:\n{xml_str[:3000]}")
                    else:
                        # Just show first and last few events
                        print(f"    Envelope tag: {env.tag} attribs={env.attrib}")
                        print(f"    Children: {[c.tag for c in env]}")
                        if auto is not None:
                            print(f"    Automation children: {[c.tag for c in auto]}")
                            if events is not None:
                                evlist = list(events)
                                print(f"    First 3 events:")
                                for e in evlist[:3]:
                                    print(f"      {ET.tostring(e, encoding='unicode').strip()}")
                                print(f"    Last 3 events:")
                                for e in evlist[-3:]:
                                    print(f"      {ET.tostring(e, encoding='unicode').strip()}")

# Also check MainTrack
print("\n=== V12 MainTrack AutomationEnvelopes ===")
for mt in v12_root.iter("MainTrack"):
    ae = mt.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            for env in envs:
                env_id = env.get("Id")
                target = env.find("EnvelopeTarget")
                ptid = target.find("PointeeId").get("Value") if target is not None else "?"
                auto = env.find("Automation")
                events = auto.find("Events") if auto is not None else None
                n_events = len(list(events)) if events is not None else 0
                xml_str = ET.tostring(env, encoding="unicode")
                print(f"  MainTrack EnvId={env_id}, PointeeId={ptid}, Events={n_events}")
                print(f"    XML:\n{xml_str[:2000]}")

# Now compare with working file
if w_root is not None:
    print("\n=== WORKING auto_track_2.als AutomationEnvelopes ===")
    for mt in w_root.iter("MidiTrack"):
        tid = mt.get("Id")
        name_el = mt.find(".//Name/EffectiveName")
        name = name_el.get("Value", "?") if name_el is not None else "?"
        ae = mt.find("AutomationEnvelopes")
        if ae is not None:
            envs = ae.find("Envelopes")
            if envs is not None:
                children = list(envs)
                if children:
                    for env in children:
                        env_id = env.get("Id")
                        target = env.find("EnvelopeTarget")
                        ptid = target.find("PointeeId").get("Value") if target is not None else "?"
                        auto = env.find("Automation")
                        events = auto.find("Events") if auto is not None else None
                        n_events = len(list(events)) if events is not None else 0
                        xml_str = ET.tostring(env, encoding="unicode")
                        print(f"\n  Track {tid} ({name}): EnvId={env_id}, PointeeId={ptid}, Events={n_events}")
                        print(f"    XML:\n{xml_str[:2000]}")
