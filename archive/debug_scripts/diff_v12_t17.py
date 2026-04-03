"""Compare V12 (crashes) vs t17 (loads fine) XML structure."""
import gzip
import xml.etree.ElementTree as ET

# V12
with gzip.open("output/ableton/Wild_Ones_V12.als", "rb") as f:
    v12 = ET.fromstring(f.read())

# A test file that loads fine (t17 = all tracks + returns)
with gzip.open("output/ableton/test_trackbuild/t17_15midi_2ret.als", "rb") as f:
    t17 = ET.fromstring(f.read())

ls_v12 = v12.find("LiveSet")
ls_t17 = t17.find("LiveSet")

print("=== LiveSet children ===")
v12_kids = [c.tag for c in ls_v12]
t17_kids = [c.tag for c in ls_t17]
print(f"V12: {len(v12_kids)} children")
print(f"T17: {len(t17_kids)} children")

# Which are in one but not the other
v12_set = set(v12_kids)
t17_set = set(t17_kids)
only_v12 = v12_set - t17_set
only_t17 = t17_set - v12_set
if only_v12:
    print(f"\nOnly in V12: {only_v12}")
if only_t17:
    print(f"\nOnly in T17: {only_t17}")

# Compare order
print(f"\nV12 order: {v12_kids}")
print(f"\nT17 order: {t17_kids}")

# Track count
v12_tracks = ls_v12.find("Tracks")
t17_tracks = ls_t17.find("Tracks")
print(f"\n=== Tracks ===")
print(f"V12: {len(list(v12_tracks))} tracks")
print(f"T17: {len(list(t17_tracks))} tracks")

# Compare first MIDI track structure (depth 2)
def get_children_deep(el, prefix="", depth=0, maxdepth=3):
    result = []
    for c in el:
        path = f"{prefix}/{c.tag}"
        result.append(path)
        if depth < maxdepth:
            result.extend(get_children_deep(c, path, depth + 1, maxdepth))
    return result

v12_t0 = list(v12_tracks)[0]
t17_t0 = list(t17_tracks)[0]
print(f"\n=== First MidiTrack direct children ===")
v12_t0_kids = [c.tag for c in v12_t0]
t17_t0_kids = [c.tag for c in t17_t0]
print(f"V12: {v12_t0_kids}")
print(f"T17: {t17_t0_kids}")

# Compare DeviceChain children
v12_dc = v12_t0.find("DeviceChain")
t17_dc = t17_t0.find("DeviceChain")
print(f"\n=== DeviceChain children ===")
v12_dc_kids = [c.tag for c in v12_dc]
t17_dc_kids = [c.tag for c in t17_dc]
print(f"V12: {v12_dc_kids}")
print(f"T17: {t17_dc_kids}")

# Compare Mixer children
v12_mixer = v12_dc.find("Mixer")
t17_mixer = t17_dc.find("Mixer")
if v12_mixer is not None and t17_mixer is not None:
    print(f"\n=== Mixer children ===")
    v12_mx = [c.tag for c in v12_mixer]
    t17_mx = [c.tag for c in t17_mixer]
    print(f"V12 ({len(v12_mx)}): {v12_mx}")
    print(f"T17 ({len(t17_mx)}): {t17_mx}")

# Compare MainSequencer children
v12_ms = v12_dc.find("MainSequencer")
t17_ms = t17_dc.find("MainSequencer")
if v12_ms is not None and t17_ms is not None:
    print(f"\n=== MainSequencer children ===")
    v12_msk = [c.tag for c in v12_ms]
    t17_msk = [c.tag for c in t17_ms]
    print(f"V12 ({len(v12_msk)}): {v12_msk}")
    print(f"T17 ({len(t17_msk)}): {t17_msk}")
    
    # Compare ClipSlotList
    v12_csl = v12_ms.find("ClipSlotList")
    t17_csl = t17_ms.find("ClipSlotList")
    if v12_csl is not None and t17_csl is not None:
        print(f"\n=== ClipSlotList ===")
        print(f"V12: {len(list(v12_csl))} slots")
        print(f"T17: {len(list(t17_csl))} slots")

# Compare return track structure
v12_rets = [t for t in v12_tracks if t.tag == "ReturnTrack"]
t17_rets = [t for t in t17_tracks if t.tag == "ReturnTrack"]
print(f"\n=== Return tracks ===")
print(f"V12: {len(v12_rets)}, T17: {len(t17_rets)}")

if v12_rets and t17_rets:
    v12_rdc = v12_rets[0].find("DeviceChain")
    t17_rdc = t17_rets[0].find("DeviceChain")
    print(f"V12 RetDC children: {[c.tag for c in v12_rdc]}")
    print(f"T17 RetDC children: {[c.tag for c in t17_rdc]}")
