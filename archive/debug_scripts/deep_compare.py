"""Deep comparison of V12 vs template for ReturnTrack and MasterTrack."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path


def load(p):
    with gzip.open(str(p), "rb") as f:
        return ET.fromstring(f.read())


def children_deep(el, prefix="", depth=0, max_depth=3):
    """Return list of (path, attrib_dict, text)."""
    items = []
    tag = el.tag
    path = f"{prefix}/{tag}" if prefix else tag
    items.append((depth, path, dict(el.attrib), (el.text or "").strip()))
    if depth < max_depth:
        for ch in el:
            items.extend(children_deep(ch, path, depth + 1, max_depth))
    return items


tmpl = load(Path(r"C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences\Crash\2026_03_28__01_12_39_BaseFiles\DefaultLiveSet.als"))
v12 = load(Path("output/ableton/Wild_Ones_V12.als"))

ls_t = tmpl.find(".//LiveSet")
ls_v = v12.find(".//LiveSet")

# ============ RETURN TRACKS ============
print("=" * 70)
print(" RETURN TRACK COMPARISON (first return track only)")
print("=" * 70)

rt_t = ls_t.find(".//Tracks/ReturnTrack")
rt_v = ls_v.find(".//Tracks/ReturnTrack")

if rt_t is None:
    print("Template has no ReturnTrack!")
else:
    print(f"\nTemplate ReturnTrack children: {[c.tag for c in rt_t]}")
    
if rt_v is None:
    print("V12 has no ReturnTrack!")
else:
    print(f"V12 ReturnTrack children:      {[c.tag for c in rt_v]}")

# Compare child by child
if rt_t is not None and rt_v is not None:
    tags_t = [c.tag for c in rt_t]
    tags_v = [c.tag for c in rt_v]
    
    if tags_t == tags_v:
        print("\nChild tags: MATCH")
    else:
        print(f"\nChild tags DIFFER:")
        print(f"  Template: {tags_t}")
        print(f"  V12:      {tags_v}")
        # Find missing/extra
        for t in tags_t:
            if t not in tags_v:
                print(f"  MISSING in V12: {t}")
        for t in tags_v:
            if t not in tags_t:
                print(f"  EXTRA in V12: {t}")

    # Compare DeviceChain children
    dc_t = rt_t.find("DeviceChain")
    dc_v = rt_v.find("DeviceChain")
    if dc_t is not None and dc_v is not None:
        dct = [c.tag for c in dc_t]
        dcv = [c.tag for c in dc_v]
        print(f"\nDeviceChain template: {dct}")
        print(f"DeviceChain V12:      {dcv}")
        if dct != dcv:
            for t in dct:
                if t not in dcv:
                    print(f"  MISSING in V12 DC: {t}")
            for t in dcv:
                if t not in dct:
                    print(f"  EXTRA in V12 DC: {t}")

# ============ MASTER TRACK ============
print("\n" + "=" * 70)
print(" MASTER TRACK COMPARISON")
print("=" * 70)

mt_t = ls_t.find("MasterTrack")
mt_v = ls_v.find("MasterTrack")

if mt_t is not None:
    print(f"\nTemplate MasterTrack children: {[c.tag for c in mt_t]}")
if mt_v is not None:
    print(f"V12 MasterTrack children:      {[c.tag for c in mt_v]}")

if mt_t is not None and mt_v is not None:
    tags_t = [c.tag for c in mt_t]
    tags_v = [c.tag for c in mt_v]
    if tags_t == tags_v:
        print("\nChild tags: MATCH")
    else:
        print(f"\nChild tags DIFFER:")
        for i, (a, b) in enumerate(zip(tags_t, tags_v)):
            if a != b:
                print(f"  [{i}] tmpl={a} vs v12={b}")
        if len(tags_t) != len(tags_v):
            print(f"  Different count: tmpl={len(tags_t)} vs v12={len(tags_v)}")

    # Compare DeviceChain
    dc_t = mt_t.find("DeviceChain")
    dc_v = mt_v.find("DeviceChain")
    if dc_t is not None and dc_v is not None:
        dct = [c.tag for c in dc_t]
        dcv = [c.tag for c in dc_v]
        print(f"\nMasterTrack DC template: {dct}")
        print(f"MasterTrack DC V12:      {dcv}")
        if dct != dcv:
            for t in dct:
                if t not in dcv:
                    print(f"  MISSING: {t}")
            for t in dcv:
                if t not in dct:
                    print(f"  EXTRA: {t}")

# ============ PREHEAR TRACK ============
print("\n" + "=" * 70)
print(" PREHEAR TRACK COMPARISON")
print("=" * 70)

ph_t = ls_t.find("PreHearTrack")
ph_v = ls_v.find("PreHearTrack")

if ph_t is not None and ph_v is not None:
    tags_t = [c.tag for c in ph_t]
    tags_v = [c.tag for c in ph_v]
    if tags_t == tags_v:
        print(f"Child tags: MATCH ({len(tags_t)} children)")
    else:
        print(f"DIFFER: tmpl={tags_t}")
        print(f"        v12={tags_v}")

# ============ TOP LEVEL LIVESET ============
print("\n" + "=" * 70)
print(" LIVESET TOP-LEVEL COMPARISON")
print("=" * 70)

tags_t = [c.tag for c in ls_t]
tags_v = [c.tag for c in ls_v]
print(f"Template: {len(tags_t)} children")
print(f"V12:      {len(tags_v)} children")

if tags_t == tags_v:
    print("Tags + order: MATCH")
else:
    print("DIFFER!")
    for i, (a, b) in enumerate(zip(tags_t, tags_v)):
        if a != b:
            print(f"  [{i}] tmpl={a} vs v12={b}")
    # Find missing/extra by set
    missing = set(tags_t) - set(tags_v)
    extra = set(tags_v) - set(tags_t)
    if missing:
        print(f"  Missing in V12: {missing}")
    if extra:
        print(f"  Extra in V12: {extra}")

# Compare value nodes that might differ
print("\n--- Checking key LiveSet value nodes ---")
for tag in ["NextPointeeId", "OverwriteProtectionNumber", "LomId",
            "InKey", "SoloOrPFMode", "KeyboardLayout", "ViewStateSessionMixerHeight"]:
    t_el = ls_t.find(tag)
    v_el = ls_v.find(tag)
    t_val = t_el.get("Value") if t_el is not None else "MISSING"
    v_val = v_el.get("Value") if v_el is not None else "MISSING"
    match = "OK" if t_val == v_val or (t_val != "MISSING" and v_val != "MISSING") else "MISMATCH"
    print(f"  {tag}: tmpl={t_val} v12={v_val} [{match}]")
