"""Deep ALS crash diagnosis — compare generated V9 against factory template element by element."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import os

TEMPLATE = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"
GENERATED = "output/ableton/Wild_Ones_V9.als"

def load_als(path):
    with gzip.open(path, "rb") as f:
        return ET.fromstring(f.read())

tmpl = load_als(TEMPLATE)
gen = load_als(GENERATED)

print("=" * 60)
print("ROOT ATTRIBUTES")
print("=" * 60)
for key in sorted(set(list(tmpl.attrib.keys()) + list(gen.attrib.keys()))):
    tv = tmpl.get(key, "MISSING")
    gv = gen.get(key, "MISSING")
    flag = " *** MISMATCH" if tv != gv else ""
    print(f"  {key}: tmpl={tv!r} gen={gv!r}{flag}")

gen_ls = gen.find("LiveSet")
tmpl_ls = tmpl.find("LiveSet")

# Deep compare MainTrack structure
print()
print("=" * 60)
print("MAINTRACK COMPARISON")
print("=" * 60)

def compare_elem(tmpl_el, gen_el, path="", depth=0, max_depth=4):
    """Compare two elements recursively."""
    issues = []
    if tmpl_el is None and gen_el is None:
        return issues
    if tmpl_el is None:
        issues.append(f"  EXTRA in generated: {path}")
        return issues
    if gen_el is None:
        issues.append(f"  MISSING in generated: {path}")
        return issues
    
    # Compare attributes  
    for key in sorted(set(list(tmpl_el.attrib.keys()) + list(gen_el.attrib.keys()))):
        tv = tmpl_el.get(key)
        gv = gen_el.get(key)
        if tv != gv and key not in ("Value", "Id"):  # Skip value differences, just check structure
            issues.append(f"  ATTR DIFF {path}/@{key}: tmpl={tv!r} gen={gv!r}")
    
    if depth >= max_depth:
        return issues
    
    # Compare children by tag
    tmpl_tags = [c.tag for c in tmpl_el]
    gen_tags = [c.tag for c in gen_el]
    
    if tmpl_tags != gen_tags:
        tmpl_set = set(tmpl_tags)
        gen_set = set(gen_tags)
        missing = tmpl_set - gen_set
        extra = gen_set - tmpl_set
        if missing:
            issues.append(f"  MISSING children at {path}: {missing}")
        if extra:
            issues.append(f"  EXTRA children at {path}: {extra}")
        if len(tmpl_tags) != len(gen_tags):
            issues.append(f"  CHILD COUNT DIFF at {path}: tmpl={len(tmpl_tags)} gen={len(gen_tags)}")
    
    # Recurse into matching children
    tmpl_children = {c.tag: c for c in tmpl_el}
    gen_children = {c.tag: c for c in gen_el}
    
    for tag in tmpl_children:
        if tag in gen_children:
            sub_issues = compare_elem(tmpl_children[tag], gen_children[tag], 
                                       f"{path}/{tag}", depth + 1, max_depth)
            issues.extend(sub_issues)
    
    return issues

tmpl_mt = tmpl_ls.find("MainTrack")
gen_mt = gen_ls.find("MainTrack")
issues = compare_elem(tmpl_mt, gen_mt, "MainTrack", max_depth=5)
for iss in issues:
    print(iss)
if not issues:
    print("  MainTrack structure matches template!")

# Compare first AudioTrack
print()
print("=" * 60)
print("AUDIO TRACK COMPARISON (first track)")
print("=" * 60)
tmpl_tracks = tmpl_ls.find("Tracks")
gen_tracks = gen_ls.find("Tracks")

tmpl_audio = None
for t in tmpl_tracks:
    if t.tag == "AudioTrack":
        tmpl_audio = t
        break
gen_audio = None
for t in gen_tracks:
    if t.tag == "AudioTrack":
        gen_audio = t
        break

if tmpl_audio is not None and gen_audio is not None:
    issues = compare_elem(tmpl_audio, gen_audio, "AudioTrack", max_depth=5)
    for iss in issues:
        print(iss)
    if not issues:
        print("  AudioTrack structure matches template!")

# Compare ReturnTrack structure
print()
print("=" * 60)
print("RETURN TRACK COMPARISON")
print("=" * 60)
tmpl_return = None
for t in tmpl_tracks:
    if t.tag == "ReturnTrack":
        tmpl_return = t
        break
gen_return = None
for t in gen_tracks:
    if t.tag == "ReturnTrack":
        gen_return = t
        break

if tmpl_return is not None and gen_return is not None:
    issues = compare_elem(tmpl_return, gen_return, "ReturnTrack", max_depth=5)
    for iss in issues:
        print(iss)
    if not issues:
        print("  ReturnTrack structure matches template!")

# Compare MidiTrack structure
print()
print("=" * 60) 
print("MIDI TRACK COMPARISON")
print("=" * 60)
tmpl_midi = None
for t in tmpl_tracks:
    if t.tag == "MidiTrack":
        tmpl_midi = t
        break
gen_midi = None
for t in gen_tracks:
    if t.tag == "MidiTrack":
        gen_midi = t
        break

if tmpl_midi is not None and gen_midi is not None:
    issues = compare_elem(tmpl_midi, gen_midi, "MidiTrack", max_depth=5)
    for iss in issues:
        print(iss)
    if not issues:
        print("  MidiTrack structure matches template!")

# Check MainTrack Mixer children order
print()
print("=" * 60)
print("MAINTRACK MIXER CHILDREN ORDER")
print("=" * 60)
tmpl_mixer = tmpl_mt.find("DeviceChain/Mixer")
gen_mixer = gen_mt.find("DeviceChain/Mixer")
print("Template Mixer children:")
for c in tmpl_mixer:
    print(f"  {c.tag}")
print()
print("Generated Mixer children:")
for c in gen_mixer:
    print(f"  {c.tag}")

# Check MainTrack FreezeSequencer
print()
print("=" * 60)
print("MAINTRACK FREEZESEQUENCER COMPARISON")
print("=" * 60)
tmpl_fs = tmpl_mt.find("DeviceChain/FreezeSequencer")
gen_fs = gen_mt.find("DeviceChain/FreezeSequencer")
print(f"Template FreezeSequencer: {tmpl_fs is not None}")
if tmpl_fs is not None:
    print("  Template children:")
    for c in tmpl_fs:
        print(f"    {c.tag} (children={len(list(c))})")
print(f"Generated FreezeSequencer: {gen_fs is not None}")
if gen_fs is not None:
    print("  Generated children:")
    for c in gen_fs:
        print(f"    {c.tag} (children={len(list(c))})")

# Dump full XML size comparison
gen_xml = ET.tostring(gen, encoding="unicode")
tmpl_xml = ET.tostring(tmpl, encoding="unicode")
print(f"\nTemplate XML size: {len(tmpl_xml)} chars")
print(f"Generated XML size: {len(gen_xml)} chars")

# Check for any None or empty tags that shouldn't be
print()
print("=" * 60)
print("CHECKING FOR PROBLEMATIC PATTERNS")
print("=" * 60)

# Check for tags with no Value and no children (potentially empty required elements)
def find_empty_required(root, prefix=""):
    problems = []
    for el in root.iter():
        if el.tag in ("Devices", "SignalModulations", "LockedScripts",
                       "UserOnsets", "SavedWarpMarkersForStretched",
                       "SourceContext", "DetailClipKeyMidis",
                       "LinkedTrackGroups", "TuningSystems"):
            continue  # These are allowed to be empty
        if len(list(el)) == 0 and not el.attrib and el.text is None:
            problems.append(el.tag)
    return problems

probs = find_empty_required(gen)
if probs:
    from collections import Counter
    print(f"  Empty elements (no attrs, no children): {dict(Counter(probs))}")

# Check MainTrack DeviceChain children order vs template
print()
print("MainTrack DeviceChain children:")
tmpl_dc = tmpl_mt.find("DeviceChain")
gen_dc = gen_mt.find("DeviceChain")
if tmpl_dc is not None:
    tmpl_dc_children = [c.tag for c in tmpl_dc]
    gen_dc_children = [c.tag for c in gen_dc]
    print(f"  Template: {tmpl_dc_children}")
    print(f"  Generated: {gen_dc_children}")
    if tmpl_dc_children != gen_dc_children:
        print("  *** ORDER/CONTENT MISMATCH ***")
