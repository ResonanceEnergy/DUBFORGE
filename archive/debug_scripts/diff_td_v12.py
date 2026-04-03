"""Deep structural diff between td_full_no_devices.als (works) and Wild_Ones_V12.als (crashes).
Finds every XML element/attribute difference."""
import gzip, sys
from xml.etree import ElementTree as ET
from pathlib import Path


def load_als(path):
    with gzip.open(str(path), "rb") as f:
        return ET.fromstring(f.read())


def tag_path(elem, parent_map):
    """Build a full tag path for an element."""
    parts = []
    e = elem
    while e is not None:
        tag = e.tag
        eid = e.get("Id", "")
        if eid:
            tag += f"[{eid}]"
        parts.append(tag)
        e = parent_map.get(e)
    return "/".join(reversed(parts))


def collect_structure(root):
    """Collect all element paths with their attributes and text."""
    parent_map = {c: p for p in root.iter() for c in p}
    parent_map[root] = None
    result = {}
    for elem in root.iter():
        path = tag_path(elem, parent_map)
        attrs = dict(elem.attrib)
        text = (elem.text or "").strip()
        children = [c.tag for c in elem]
        result[path] = {"attrs": attrs, "text": text, "children": children, "tag": elem.tag}
    return result


def compare_live_set_level(td_root, v12_root):
    """Compare LiveSet direct children."""
    td_ls = td_root.find("LiveSet")
    v12_ls = v12_root.find("LiveSet")
    if td_ls is None or v12_ls is None:
        print("ERROR: Can't find LiveSet!")
        return
    td_kids = [c.tag for c in td_ls]
    v12_kids = [c.tag for c in v12_ls]
    print("=== LiveSet children ===")
    print(f"  td:  {td_kids}")
    print(f"  v12: {v12_kids}")
    if td_kids != v12_kids:
        print("  ** DIFFERENT ORDER/COUNT **")
        td_set = set(td_kids)
        v12_set = set(v12_kids)
        if v12_set - td_set:
            print(f"  V12 has extra: {v12_set - td_set}")
        if td_set - v12_set:
            print(f"  td has extra: {td_set - v12_set}")


def compare_tracks(td_root, v12_root, track_type="Tracks"):
    """Compare track child element ordering."""
    td_ls = td_root.find("LiveSet")
    v12_ls = v12_root.find("LiveSet")
    td_tracks_elem = td_ls.find(track_type)
    v12_tracks_elem = v12_ls.find(track_type)
    if td_tracks_elem is None or v12_tracks_elem is None:
        print(f"  {track_type}: one is missing")
        return

    td_tracks = list(td_tracks_elem)
    v12_tracks = list(v12_tracks_elem)
    print(f"\n=== {track_type}: td has {len(td_tracks)}, v12 has {len(v12_tracks)} ===")

    for i, (tt, vt) in enumerate(zip(td_tracks, v12_tracks)):
        td_name = ""
        v12_name = ""
        # Try to get track name
        for path in ["DeviceChain/Mixer/../../../Name/EffectiveName",
                      "Name/EffectiveName", "Name/UserName"]:
            n = tt.find(path)
            if n is not None and n.get("Value"):
                td_name = n.get("Value")
                break
        for path in ["DeviceChain/Mixer/../../../Name/EffectiveName",
                      "Name/EffectiveName", "Name/UserName"]:
            n = vt.find(path)
            if n is not None and n.get("Value"):
                v12_name = n.get("Value")
                break

        td_children = [c.tag for c in tt]
        v12_children = [c.tag for c in vt]

        if td_children != v12_children:
            print(f"\n  Track {i} (td='{td_name}' v12='{v12_name}'): CHILDREN DIFFER")
            print(f"    td:  {td_children}")
            print(f"    v12: {v12_children}")
        else:
            # Compare DeviceChain children
            td_dc = tt.find("DeviceChain")
            v12_dc = vt.find("DeviceChain")
            if td_dc is not None and v12_dc is not None:
                td_dc_kids = [c.tag for c in td_dc]
                v12_dc_kids = [c.tag for c in v12_dc]
                if td_dc_kids != v12_dc_kids:
                    print(f"\n  Track {i} (td='{td_name}' v12='{v12_name}'): DeviceChain CHILDREN DIFFER")
                    print(f"    td:  {td_dc_kids}")
                    print(f"    v12: {v12_dc_kids}")


def compare_first_midi_track_deep(td_root, v12_root):
    """Deep compare first MidiTrack between td and v12."""
    td_ls = td_root.find("LiveSet")
    v12_ls = v12_root.find("LiveSet")
    td_tracks = td_ls.find("Tracks")
    v12_tracks = v12_ls.find("Tracks")

    td_midi = [t for t in td_tracks if t.tag == "MidiTrack"]
    v12_midi = [t for t in v12_tracks if t.tag == "MidiTrack"]

    if not td_midi or not v12_midi:
        print("No MidiTracks found!")
        return

    print(f"\n=== Deep compare first MidiTrack ===")
    _deep_elem_compare(td_midi[0], v12_midi[0], "MidiTrack[0]", depth=0, max_depth=4)


def _deep_elem_compare(e1, e2, path, depth, max_depth):
    """Recursively compare two elements."""
    if depth > max_depth:
        return

    # Compare tag
    if e1.tag != e2.tag:
        print(f"  {'  '*depth}{path}: tag differs: {e1.tag} vs {e2.tag}")
        return

    # Compare attributes
    a1 = dict(e1.attrib)
    a2 = dict(e2.attrib)
    if a1 != a2:
        for k in set(list(a1.keys()) + list(a2.keys())):
            if a1.get(k) != a2.get(k):
                print(f"  {'  '*depth}{path}/@{k}: {a1.get(k)!r} vs {a2.get(k)!r}")

    # Compare text
    t1 = (e1.text or "").strip()
    t2 = (e2.text or "").strip()
    if t1 != t2 and len(t1) < 200 and len(t2) < 200:
        print(f"  {'  '*depth}{path}/text: {t1!r} vs {t2!r}")

    # Compare children
    c1 = list(e1)
    c2 = list(e2)
    tags1 = [c.tag for c in c1]
    tags2 = [c.tag for c in c2]
    if tags1 != tags2:
        print(f"  {'  '*depth}{path}: children differ:")
        print(f"  {'  '*depth}  td:  {tags1}")
        print(f"  {'  '*depth}  v12: {tags2}")
        # Still compare what we can
        for i in range(min(len(c1), len(c2))):
            if c1[i].tag == c2[i].tag:
                _deep_elem_compare(c1[i], c2[i], f"{path}/{c1[i].tag}", depth+1, max_depth)
    else:
        for i in range(len(c1)):
            tag = c1[i].tag
            eid = c1[i].get("Id", "")
            p = f"{path}/{tag}"
            if eid:
                p += f"[{eid}]"
            _deep_elem_compare(c1[i], c2[i], p, depth+1, max_depth)


def compare_automation_targets(td_root, v12_root):
    """Compare AutomationTarget IDs to find conflicts."""
    for label, root in [("td", td_root), ("v12", v12_root)]:
        targets = {}
        for elem in root.iter():
            if elem.tag == "AutomationTarget":
                tid = elem.get("Id", "?")
                # find parent chain
                targets.setdefault(tid, []).append(elem.tag)

        dups = {k: v for k, v in targets.items() if len(v) > 1}
        print(f"\n=== {label}: {len(targets)} AutomationTargets, {len(dups)} duplicate IDs ===")
        if dups:
            for k, v in sorted(dups.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                print(f"  ID {k}: {len(v)} occurrences")


def compare_id_ranges(td_root, v12_root):
    """Compare NextPointeeId vs max used ID."""
    for label, root in [("td", td_root), ("v12", v12_root)]:
        ls = root.find("LiveSet")
        npi = ls.find("NextPointeeId")
        npi_val = int(npi.get("Value", "0")) if npi is not None else 0

        max_id = 0
        for elem in root.iter():
            for attr_name, attr_val in elem.attrib.items():
                if attr_name == "Id" and attr_val.isdigit():
                    max_id = max(max_id, int(attr_val))
            if elem.tag == "AutomationTarget":
                tid = elem.get("Id", "0")
                if tid.isdigit():
                    max_id = max(max_id, int(tid))

        print(f"\n=== {label}: NextPointeeId={npi_val}, max used ID={max_id} ===")
        if max_id >= npi_val:
            print(f"  ** WARNING: max ID ({max_id}) >= NextPointeeId ({npi_val})! **")


# ══════════════════════════════════════════════════════════════════════
td_path = Path("output/ableton/test_trackbuild/td_full_no_devices.als")
v12_path = Path("output/ableton/Wild_Ones_V12.als")

print(f"Comparing:\n  td:  {td_path}\n  v12: {v12_path}\n")
td = load_als(td_path)
v12 = load_als(v12_path)

compare_live_set_level(td, v12)
compare_tracks(td, v12)
compare_first_midi_track_deep(td, v12)
compare_automation_targets(td, v12)
compare_id_ranges(td, v12)
