"""Dump the exact XML structure of all automation envelopes in V12."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

src = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

for ae in root.iter("AutomationEnvelopes"):
    parent = None
    # Find parent tag
    for elem in root.iter():
        for child in elem:
            if child is ae:
                parent = elem
                break
    parent_tag = parent.tag if parent else "?"
    parent_id = parent.get("Id", "?") if parent else "?"
    
    envs = ae.find("Envelopes")
    if envs is None or len(envs) == 0:
        continue
    
    print(f"=== {parent_tag} Id={parent_id} ({len(envs)} envelopes) ===")
    for env in envs:
        # Print first 500 chars of XML
        xml = ET.tostring(env, encoding="unicode")
        if len(xml) > 1000:
            print(f"  Envelope Id={env.get('Id')}:")
            # Print just structure, not all events
            target = env.find("EnvelopeTarget")
            ptid = target.find("PointeeId") if target is not None else None
            print(f"    PointeeId: {ptid.get('Value') if ptid is not None else '?'}")
            auto = env.find("Automation")
            if auto is not None:
                events = auto.find("Events")
                print(f"    Events: {len(events) if events is not None else 0}")
                if events is not None and len(events) > 0:
                    # First and last event
                    first = events[0]
                    last = events[-1]
                    print(f"    First: {dict(first.attrib)}")
                    print(f"    Last:  {dict(last.attrib)}")
                atvs = auto.find("AutomationTransformViewState")
                if atvs is not None:
                    print(f"    ATVS: {ET.tostring(atvs, encoding='unicode')}")
        else:
            print(f"  {xml}")
        print()
