"""Quick XML structure diff: test0 (raw template) vs test1 (1 empty MIDI)."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path


def load(p):
    with gzip.open(str(p), "rb") as f:
        return ET.fromstring(f.read())


def tag_tree(el, depth=0, max_depth=4):
    """Return sorted list of (path, attrib_keys) up to max_depth."""
    items = []
    path = el.tag
    items.append((depth, path, sorted(el.attrib.keys()), el.text and el.text.strip()))
    if depth < max_depth:
        for ch in el:
            for item in tag_tree(ch, depth + 1, max_depth):
                items.append(item)
    return items


base = Path("output/ableton/test_minimal")

print("=== Loading test0 (raw template) ===")
t0 = load(base / "test0_raw_template.als")
print("=== Loading test1 (1 empty MIDI) ===")
t1 = load(base / "test1_empty_midi.als")

# Compare LiveSet children
ls0 = t0.find(".//LiveSet")
ls1 = t1.find(".//LiveSet")

print("\n--- LiveSet children ---")
ch0 = [c.tag for c in ls0]
ch1 = [c.tag for c in ls1]
print(f"Template: {len(ch0)} children")
print(f"Test1:    {len(ch1)} children")

# Find differences
missing = [t for t in ch0 if t not in ch1]
extra = [t for t in ch1 if t not in ch0]
if missing:
    print(f"\nMISSING in test1: {missing}")
if extra:
    print(f"\nEXTRA in test1: {extra}")
if not missing and not extra:
    print("Same child tags!")

# Compare child tag ORDER
if ch0 != ch1:
    print("\nORDER DIFFERS:")
    for i, (a, b) in enumerate(zip(ch0, ch1)):
        if a != b:
            print(f"  [{i}] template={a}, test1={b}")

# Dig into Tracks element
tracks0 = ls0.find("Tracks")
tracks1 = ls1.find("Tracks")
if tracks0 is not None and tracks1 is not None:
    tt0 = [c.tag for c in tracks0]
    tt1 = [c.tag for c in tracks1]
    print(f"\n--- Tracks ---")
    print(f"Template tracks: {tt0}")
    print(f"Test1 tracks:    {tt1}")

# Check first MidiTrack structure (depth 3)
midi1 = tracks1.find("MidiTrack") if tracks1 is not None else None
if midi1 is not None:
    print(f"\n--- Test1 MidiTrack children ---")
    for ch in midi1:
        attrs = " ".join(f'{k}="{v}"' for k, v in ch.attrib.items())
        sub_count = len(list(ch))
        print(f"  <{ch.tag} {attrs}> ({sub_count} children)")

# Check Scenes
scenes0 = ls0.find("Scenes")
scenes1 = ls1.find("Scenes")
if scenes0 is not None:
    print(f"\n--- Template Scenes children ({len(list(scenes0))}) ---")
    for sc in scenes0:
        kids = [c.tag for c in sc]
        print(f"  <{sc.tag} {sc.attrib}>: {kids}")
if scenes1 is not None:
    print(f"\n--- Test1 Scenes children ({len(list(scenes1))}) ---")
    for sc in scenes1:
        kids = [c.tag for c in sc]
        print(f"  <{sc.tag} {sc.attrib}>: {kids}")

# Check MasterTrack
mt0 = ls0.find("MasterTrack")
mt1 = ls1.find("MasterTrack")
if mt0 is not None and mt1 is not None:
    mc0 = [c.tag for c in mt0]
    mc1 = [c.tag for c in mt1]
    if mc0 != mc1:
        print(f"\n--- MasterTrack DIFFERS ---")
        print(f"  Template: {mc0}")
        print(f"  Test1:    {mc1}")
    else:
        print(f"\n--- MasterTrack: MATCH ({len(mc0)} children) ---")

# Check PreHearTrack
ph0 = ls0.find("PreHearTrack")
ph1 = ls1.find("PreHearTrack")
if ph0 is not None and ph1 is not None:
    pc0 = [c.tag for c in ph0]
    pc1 = [c.tag for c in ph1]
    if pc0 != pc1:
        print(f"\n--- PreHearTrack DIFFERS ---")
        print(f"  Template: {pc0}")
        print(f"  Test1:    {pc1}")
    else:
        print(f"\n--- PreHearTrack: MATCH ({len(pc0)} children) ---")
