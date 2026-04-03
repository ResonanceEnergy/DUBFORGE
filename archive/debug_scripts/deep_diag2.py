"""Comprehensive V12 ALS diagnostic: check automation references, 
LiveSet structure, and compare against factory template at every level."""
import gzip
import xml.etree.ElementTree as ET
from collections import Counter

with gzip.open('output/ableton/Wild_Ones_V12.als', 'rb') as f:
    v12 = ET.fromstring(f.read())
with gzip.open(
    r'C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences'
    r'\Crash\2026_03_28__01_12_39_BaseFiles\DefaultLiveSet.als', 'rb'
) as f:
    tmpl = ET.fromstring(f.read())

print("=" * 70)
print("1. LIVESET TOP-LEVEL CHILDREN COMPARISON")
print("=" * 70)
ls = v12.find('LiveSet')
ls_t = tmpl.find('LiveSet')

v12_children = [c.tag for c in ls]
tmpl_children = [c.tag for c in ls_t]
print(f"V12: {v12_children}")
print(f"TMPL: {tmpl_children}")
print(f"Missing from V12: {set(tmpl_children) - set(v12_children)}")
print(f"Extra in V12: {set(v12_children) - set(tmpl_children)}")

# Check order matters
print(f"\nV12 order: {v12_children}")
print(f"TMPL order: {tmpl_children}")

print("\n" + "=" * 70)
print("2. AUTOMATION TARGET IDs vs ENVELOPE POINTEE IDs")
print("=" * 70)

# Collect all AutomationTarget Ids
all_at_ids = set()
for at in v12.iter("AutomationTarget"):
    aid = at.get("Id")
    if aid:
        all_at_ids.add(aid)
for mt in v12.iter("ModulationTarget"):
    aid = mt.get("Id")
    if aid:
        all_at_ids.add(aid)

# Collect all EnvelopeTarget PointeeIds
all_pointee_ids = set()
orphan_pointees = []
for et_elem in v12.iter("EnvelopeTarget"):
    pid_elem = et_elem.find("PointeeId")
    if pid_elem is not None:
        pid = pid_elem.get("Value")
        all_pointee_ids.add(pid)
        if pid not in all_at_ids:
            orphan_pointees.append(pid)

print(f"Total AutomationTarget IDs: {len(all_at_ids)}")
print(f"Total EnvelopeTarget PointeeIds: {len(all_pointee_ids)}")
print(f"Orphan PointeeIds (no matching target): {len(orphan_pointees)}")
if orphan_pointees:
    print(f"  ORPHANS: {orphan_pointees[:20]}")

# Check for duplicate AutomationTarget Ids (should be unique!)
at_id_counts = Counter()
for at in v12.iter("AutomationTarget"):
    at_id_counts[at.get("Id")] += 1
for mt in v12.iter("ModulationTarget"):
    at_id_counts[mt.get("Id")] += 1
dups = {k: v for k, v in at_id_counts.items() if v > 1}
if dups:
    print(f"\nDUPLICATE AutomationTarget/ModulationTarget IDs: {dups}")
else:
    print(f"\nNo duplicate AutomationTarget/ModulationTarget IDs (good)")

print("\n" + "=" * 70)
print("3. FLOAT EVENT STRUCTURE")  
print("=" * 70)
fe_count = 0
fe_attrs = Counter()
for fe in v12.iter("FloatEvent"):
    fe_count += 1
    for attr in fe.attrib:
        fe_attrs[attr] += 1
print(f"Total FloatEvents: {fe_count}")
print(f"Attribute usage: {dict(fe_attrs)}")
# Show first FloatEvent
first_fe = v12.find('.//FloatEvent')
if first_fe is not None:
    print(f"First FloatEvent: {first_fe.attrib}")

print("\n" + "=" * 70)
print("4. TRACK COUNTS AND TYPES")
print("=" * 70)
track_types = Counter()
for tag in ("MidiTrack", "AudioTrack", "ReturnTrack", "MasterTrack", "PreHearTrack"):
    elems = ls.findall(f"Tracks/{tag}")
    track_types[tag] = len(elems)
    print(f"  {tag}: {len(elems)}")

# Template
print("Template:")
for tag in ("MidiTrack", "AudioTrack", "ReturnTrack", "MasterTrack", "PreHearTrack"):
    elems = ls_t.findall(f"Tracks/{tag}")
    print(f"  {tag}: {len(elems)}")

print("\n" + "=" * 70)
print("5. RETURN TRACK STRUCTURE COMPARISON")
print("=" * 70)
v12_ret = ls.findall("Tracks/ReturnTrack")
tmpl_ret = ls_t.findall("Tracks/ReturnTrack")
if v12_ret:
    print(f"V12 ReturnTrack[0] children: {[c.tag for c in v12_ret[0]]}")
if tmpl_ret:
    print(f"TMPL ReturnTrack[0] children: {[c.tag for c in tmpl_ret[0]]}")
    v_ret_tags = set(c.tag for c in v12_ret[0])
    t_ret_tags = set(c.tag for c in tmpl_ret[0])
    print(f"Missing from V12 return: {t_ret_tags - v_ret_tags}")
    print(f"Extra in V12 return: {v_ret_tags - t_ret_tags}")

print("\n" + "=" * 70)
print("6. MASTER TRACK STRUCTURE COMPARISON")
print("=" * 70)
v12_master = ls.find("MasterTrack")
tmpl_master = ls_t.find("MasterTrack")
if v12_master is not None:
    print(f"V12 MasterTrack children: {[c.tag for c in v12_master]}")
else:
    print("V12 MasterTrack: NOT FOUND")
if tmpl_master is not None:
    print(f"TMPL MasterTrack children: {[c.tag for c in tmpl_master]}")
    if v12_master is not None:
        v_tags = set(c.tag for c in v12_master)
        t_tags = set(c.tag for c in tmpl_master)
        print(f"Missing from V12 master: {t_tags - v_tags}")
        print(f"Extra in V12 master: {v_tags - t_tags}")

print("\n" + "=" * 70)
print("7. PREHEAR TRACK CHECK")
print("=" * 70)
v12_ph = ls.find("PreHearTrack")
tmpl_ph = ls_t.find("PreHearTrack")
if v12_ph is not None:
    print(f"V12 PreHearTrack children: {[c.tag for c in v12_ph]}")
else:
    print("V12 PreHearTrack: NOT FOUND!!!")
if tmpl_ph is not None:
    print(f"TMPL PreHearTrack children: {[c.tag for c in tmpl_ph]}")

print("\n" + "=" * 70)
print("8. SCENES CHECK")
print("=" * 70)
v12_scenes = ls.find("Scenes")
tmpl_scenes = ls_t.find("Scenes")
if v12_scenes is not None:
    print(f"V12 Scenes: {len(list(v12_scenes))} children")
    first_scene = list(v12_scenes)
    if first_scene:
        print(f"  First scene children: {[c.tag for c in first_scene[0]]}")
else:
    print("V12 Scenes: NOT FOUND!!!")
if tmpl_scenes is not None:
    print(f"TMPL Scenes: {len(list(tmpl_scenes))} children")
    first_scene = list(tmpl_scenes)
    if first_scene:
        print(f"  First scene children: {[c.tag for c in first_scene[0]]}")

print("\n" + "=" * 70)
print("9. TEMPLATE ELEMENTS NOT IN V12 (LIVESET LEVEL)")
print("=" * 70)
# Deep comparison of every child at LiveSet level  
for tmpl_child in ls_t:
    tag = tmpl_child.tag
    v12_child = ls.find(tag)
    if v12_child is None:
        print(f"  MISSING: {tag}")
        # Show template's content
        for sub in tmpl_child:
            val = sub.get("Value", "")
            print(f"    {sub.tag} Value={val}")
    else:
        # Compare children count
        t_subs = list(tmpl_child)
        v_subs = list(v12_child)
        if len(t_subs) != len(v_subs):
            pass  # Expected for tracks, scenes, etc.

print("\n" + "=" * 70)
print("10. MIDI NOTE EVENT ATTRIBUTES CHECK")
print("=" * 70)
mne_attrs = Counter()
mne_count = 0
for mne in v12.iter("MidiNoteEvent"):
    mne_count += 1
    for attr in mne.attrib:
        mne_attrs[attr] += 1
print(f"Total MidiNoteEvents: {mne_count}")
print(f"Attributes: {dict(mne_attrs)}")
# Show first one
first_mne = v12.find('.//MidiNoteEvent')
if first_mne is not None:
    print(f"First: {first_mne.attrib}")

print("\n" + "=" * 70)
print("11. CHECK IF V12 HAS ANY STRING VALUES WHERE INTS EXPECTED")
print("=" * 70)
# Check common int fields for non-int values
int_fields = ["LomId", "LomIdView", "Color", "TrackGroupId", "Id"]
issues = []
for field in int_fields:
    for elem in v12.iter(field):
        val = elem.get("Value")
        if val is not None and not val.lstrip("-").isdigit():
            path = []
            # Just show context
            issues.append(f"{field} Value={val}")
if issues:
    for i in issues[:30]:
        print(f"  {i}")
else:
    print("  No issues found")
