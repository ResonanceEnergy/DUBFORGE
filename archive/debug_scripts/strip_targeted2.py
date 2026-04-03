"""Targeted strip: keep only track automation, strip clip envelopes, and vice versa."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import copy

src = Path("output/ableton/Wild_Ones_V12.als")
out_dir = Path("output/ableton/test_bisect")

with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

# Count ALL Envelopes containers and their children
print("=== ALL 'Envelopes' CONTAINERS IN V12 ===")
for envs in root.iter("Envelopes"):
    parent = None
    for elem in root.iter():
        for child in elem:
            if child is envs:
                parent = elem
                break
    parent_tag = parent.tag if parent is not None else "?"
    children = list(envs)
    child_tags = [c.tag for c in children]
    if children:
        print(f"  Under {parent_tag}: {len(children)} children: {child_tags[:5]}")

# Variant A: Strip ONLY AutomationEnvelope from track-level AutomationEnvelopes
# (keep clip envelopes intact)
print()
print("=== Variant A: Strip track auto, keep clip envelopes ===")
root_a = copy.deepcopy(root)
stripped_a = 0
for ae_elem in root_a.iter("AutomationEnvelopes"):
    envs = ae_elem.find("Envelopes")
    if envs is not None:
        # Only strip from elements that are children of AutomationEnvelopes
        for child in list(envs):
            envs.remove(child)
            stripped_a += 1
print(f"  Stripped {stripped_a} from AutomationEnvelopes")

xml = ET.tostring(root_a, encoding="unicode", xml_declaration=False)
xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
dst_a = out_dir / "v12_no_track_auto.als"
with gzip.open(dst_a, "wb") as f:
    f.write(xml.encode("utf-8"))
print(f"  Wrote: {dst_a}")

# Variant B: Strip clip envelopes but keep track automation
print()
print("=== Variant B: Keep track auto, strip clip envelopes ===")
root_b = copy.deepcopy(root)
stripped_b = 0
for clip in root_b.iter("MidiClip"):
    envs = clip.find("Envelopes")
    if envs is not None:
        for child in list(envs):
            envs.remove(child)
            stripped_b += 1
print(f"  Stripped {stripped_b} from MidiClip/Envelopes")

xml = ET.tostring(root_b, encoding="unicode", xml_declaration=False)
xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
dst_b = out_dir / "v12_no_clip_env.als"
with gzip.open(dst_b, "wb") as f:
    f.write(xml.encode("utf-8"))
print(f"  Wrote: {dst_b}")
