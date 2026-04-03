"""Extract track structure from Ableton's factory template."""
import gzip
import xml.etree.ElementTree as ET

with gzip.open(
    r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als",
    "rb",
) as f:
    root = ET.fromstring(f.read())

ls = root.find("LiveSet")

# Track child order
tracks = ls.find("Tracks")
for t in tracks:
    tag = t.tag
    tid = t.get("Id", "?")
    name_el = t.find("Name/EffectiveName")
    tname = name_el.get("Value", "?") if name_el is not None else "?"
    print(f"=== {tag} Id={tid} name={tname} ===")
    for ch in t:
        print(f"  {ch.tag}")
    print()

# MainTrack
mt = ls.find("MainTrack")
print("=== MainTrack ===")
for ch in mt:
    print(f"  {ch.tag}")

# PreHearTrack
ph = ls.find("PreHearTrack")
print("\n=== PreHearTrack ===")
for ch in ph:
    print(f"  {ch.tag}")

# AudioClip deep structure from first audio track
print("\n=== First AudioClip structure ===")
for t in tracks:
    dc = t.find("DeviceChain")
    if dc is None:
        continue
    ms = dc.find("MainSequencer")
    if ms is None:
        continue
    ct = ms.find("ClipTimeable")
    if ct is None:
        continue
    aa = ct.find("ArrangerAutomation")
    if aa is None:
        continue
    evts = aa.find("Events")
    if evts is None:
        continue
    clips = list(evts)
    if clips:
        c = clips[0]
        print(f"AudioClip children ({len(list(c))}):")
        for sub in c:
            val_attr = sub.get("Value", "")
            n_children = len(list(sub))
            extra = ""
            if val_attr:
                extra = f' Value="{val_attr}"'
            elif n_children:
                extra = f" ({n_children} children)"
            print(f"  {sub.tag}{extra}")
        break

# FileRef structure
print("\n=== SampleRef/FileRef structure ===")
for t in tracks:
    dc = t.find("DeviceChain")
    if dc is None:
        continue
    ms = dc.find("MainSequencer")
    if ms is None:
        continue
    ct = ms.find("ClipTimeable")
    if ct is None:
        continue
    aa = ct.find("ArrangerAutomation")
    if aa is None:
        continue
    evts = aa.find("Events")
    if evts is None:
        continue
    clips = list(evts)
    if clips:
        sr = clips[0].find("SampleRef")
        if sr is not None:
            print(f"SampleRef children ({len(list(sr))}):")
            for sub in sr:
                print(f"  {sub.tag}")
                for sub2 in sub:
                    v = sub2.get("Value", "")
                    print(f"    {sub2.tag} Value={v!r}")
        break
