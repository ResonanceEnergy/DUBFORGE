"""Full-depth element-by-element diff between td (loads) and V12 (crashes).
Reports every structural difference at any depth."""
import gzip, sys
from xml.etree import ElementTree as ET
from pathlib import Path
from collections import Counter


def load_als(path):
    with gzip.open(str(path), "rb") as f:
        return ET.fromstring(f.read())


def elem_signature(elem):
    """Tag + sorted attrs as a signature."""
    return (elem.tag, tuple(sorted(elem.attrib.items())))


def count_elements(root):
    """Count total elements by tag."""
    c = Counter()
    for e in root.iter():
        c[e.tag] += 1
    return c


def find_all_paths(root, tag):
    """Find all elements with given tag and return their value."""
    results = []
    for elem in root.iter():
        if elem.tag == tag:
            val = elem.get("Value", elem.text or "")
            results.append(val)
    return results


def compare_element_counts(r1, r2, label1, label2):
    """Compare element tag counts between two trees."""
    c1 = count_elements(r1)
    c2 = count_elements(r2)
    all_tags = sorted(set(list(c1.keys()) + list(c2.keys())))
    diffs = []
    for tag in all_tags:
        n1 = c1.get(tag, 0)
        n2 = c2.get(tag, 0)
        if n1 != n2:
            diffs.append((tag, n1, n2))
    return diffs


def compare_midi_track_structure(t1, t2, idx):
    """Compare two MidiTrack elements fully."""
    diffs = []
    _compare_recursive(t1, t2, f"MidiTrack[{idx}]", diffs, max_depth=20)
    return diffs


def _compare_recursive(e1, e2, path, diffs, max_depth, depth=0):
    if depth > max_depth:
        return

    # Tag
    if e1.tag != e2.tag:
        diffs.append(f"{path}: TAG {e1.tag} vs {e2.tag}")
        return

    # Attributes
    a1, a2 = dict(e1.attrib), dict(e2.attrib)
    for k in sorted(set(list(a1.keys()) + list(a2.keys()))):
        v1, v2 = a1.get(k), a2.get(k)
        if v1 != v2:
            # Skip Id differences (expected) and Value differences (data, not structure)
            if k == "Id":
                continue
            if k == "Value":
                # Only report if it seems structural (not just different note data)
                try:
                    float(v1)
                    float(v2)
                    continue  # numeric values differ - that's data
                except (ValueError, TypeError):
                    if v1 != v2:
                        diffs.append(f"{path}/@{k}: {v1!r} vs {v2!r}")

    # Children structure (tags only)
    c1 = list(e1)
    c2 = list(e2)
    tags1 = [c.tag for c in c1]
    tags2 = [c.tag for c in c2]

    if tags1 != tags2:
        diffs.append(f"{path}: children differ - td:{tags1} v12:{tags2}")
        # Try to align by matching tags
        i1, i2 = 0, 0
        while i1 < len(c1) and i2 < len(c2):
            if c1[i1].tag == c2[i2].tag:
                _compare_recursive(c1[i1], c2[i2],
                                   f"{path}/{c1[i1].tag}", diffs, max_depth, depth+1)
                i1 += 1
                i2 += 1
            elif c1[i1].tag in tags2[i2:]:
                diffs.append(f"{path}: v12 has extra {c2[i2].tag} before {c1[i1].tag}")
                i2 += 1
            else:
                diffs.append(f"{path}: td has extra {c1[i1].tag}")
                i1 += 1
    else:
        for i in range(len(c1)):
            tag = c1[i].tag
            _compare_recursive(c1[i], c2[i],
                               f"{path}/{tag}", diffs, max_depth, depth+1)


def validate_midi_notes(root, label):
    """Check for invalid MIDI note values."""
    issues = []
    for note_elem in root.iter():
        if note_elem.tag in ("KeyTrack", "MidiNoteEvent"):
            continue
        if note_elem.tag == "MidiKey":
            val_elem = note_elem.find(".")
            # In ALS, notes are in KeyTracks
            pass
    # Look at KeyTrack structure
    for kt in root.iter("KeyTrack"):
        midi_key = kt.find("MidiKey")
        if midi_key is not None:
            v = midi_key.get("Value", "")
            if v.isdigit():
                p = int(v)
                if p < 0 or p > 127:
                    issues.append(f"Invalid pitch: {p}")
    # Look at NoteEvents
    for ne in root.iter("MidiNoteEvent"):
        t = ne.get("Time", "0")
        dur = ne.get("Duration", "0")
        vel = ne.get("Velocity", "0")
        pitch = ne.get("NoteId", "")  # note: NoteId isn't pitch
        try:
            tf = float(t)
            df = float(dur)
            vf = float(vel)
            if df <= 0:
                issues.append(f"Zero/negative duration: {dur} at time {t}")
            if vf < 0 or vf > 127:
                issues.append(f"Invalid velocity: {vel} at time {t}")
            if tf < 0:
                issues.append(f"Negative time: {t}")
        except ValueError:
            issues.append(f"Non-numeric value in MidiNoteEvent: t={t} d={dur} v={vel}")
    return issues


# ══════════════════════════════════════════════════════════════════════
td = load_als(Path("output/ableton/test_trackbuild/td_full_no_devices.als"))
v12 = load_als(Path("output/ableton/Wild_Ones_V12.als"))

print("=" * 60)
print("ELEMENT COUNT DIFFERENCES")
print("=" * 60)
diffs = compare_element_counts(td, v12, "td", "v12")
if diffs:
    for tag, n1, n2 in diffs:
        print(f"  {tag}: td={n1}, v12={n2}")
else:
    print("  No element count differences!")

print("\n" + "=" * 60)
print("TRACK-BY-TRACK STRUCTURAL COMPARISON")
print("=" * 60)

td_ls = td.find("LiveSet")
v12_ls = v12.find("LiveSet")
td_tracks = list(td_ls.find("Tracks"))
v12_tracks = list(v12_ls.find("Tracks"))

for i in range(min(len(td_tracks), len(v12_tracks))):
    diffs = compare_midi_track_structure(td_tracks[i], v12_tracks[i], i)
    if diffs:
        # Get track name
        name1 = td_tracks[i].find(".//Name/EffectiveName")
        name2 = v12_tracks[i].find(".//Name/EffectiveName")
        n1 = name1.get("Value", "?") if name1 is not None else "?"
        n2 = name2.get("Value", "?") if name2 is not None else "?"
        print(f"\nTrack {i} (td='{n1}' v12='{n2}'): {len(diffs)} structural diffs")
        for d in diffs[:20]:  # limit output
            print(f"  {d}")
        if len(diffs) > 20:
            print(f"  ... and {len(diffs)-20} more")

# Compare MainTrack, PreHearTrack
print("\n" + "=" * 60)
print("MAIN/PREHEAR TRACK COMPARISON")
print("=" * 60)
for tag in ("MainTrack", "PreHearTrack"):
    e1 = td_ls.find(tag)
    e2 = v12_ls.find(tag)
    if e1 is not None and e2 is not None:
        d = []
        _compare_recursive(e1, e2, tag, d, 20)
        if d:
            print(f"\n{tag}: {len(d)} diffs")
            for x in d[:10]:
                print(f"  {x}")

# Validate MIDI notes in V12
print("\n" + "=" * 60)
print("V12 MIDI NOTE VALIDATION")
print("=" * 60)
issues = validate_midi_notes(v12, "V12")
if issues:
    for i in issues[:20]:
        print(f"  {i}")
else:
    print("  No invalid MIDI note values found")

# Compare SendsPre
print("\n" + "=" * 60)
print("SENDSPRE COMPARISON")
print("=" * 60)
sp1 = td_ls.find("SendsPre")
sp2 = v12_ls.find("SendsPre")
if sp1 is not None and sp2 is not None:
    d = []
    _compare_recursive(sp1, sp2, "SendsPre", d, 10)
    if d:
        for x in d:
            print(f"  {x}")
    else:
        print("  Identical")
