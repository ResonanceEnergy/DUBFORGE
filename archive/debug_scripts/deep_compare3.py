"""Deep structural XML comparison: working _test_mini vs crashing V12.

Compares element tag hierarchy, attribute patterns, and identifies
any structural differences that could cause Ableton to crash.
"""
import xml.etree.ElementTree as ET
from collections import Counter


def compare_liveset_children(mini_root, v12_root):
    """Compare direct children of LiveSet."""
    mini_ls = mini_root.find("LiveSet")
    v12_ls = v12_root.find("LiveSet")
    
    print("=" * 70)
    print("LiveSet DIRECT CHILDREN comparison")
    print("=" * 70)
    mini_children = [c.tag for c in mini_ls]
    v12_children = [c.tag for c in v12_ls]
    
    print(f"Mini: {len(mini_children)} children")
    print(f"V12:  {len(v12_children)} children")
    
    max_len = max(len(mini_children), len(v12_children))
    for i in range(max_len):
        m = mini_children[i] if i < len(mini_children) else "---"
        v = v12_children[i] if i < len(v12_children) else "---"
        marker = "  " if m == v else "!!"
        print(f"  {marker} [{i:2d}] mini={m:40s} v12={v}")


def compare_first_track(mini_root, v12_root):
    print("\n" + "=" * 70)
    print("FIRST MidiTrack children comparison")
    print("=" * 70)
    
    for label, root in [("Mini", mini_root), ("V12", v12_root)]:
        track = root.find(".//Tracks/MidiTrack")
        children = [c.tag for c in track] if track is not None else []
        print(f"\n  {label} ({len(children)} children):")
        for i, c in enumerate(children):
            print(f"    [{i:2d}] {c}")


def compare_device_chain(mini_root, v12_root):
    print("\n" + "=" * 70)
    print("DeviceChain comparison (first MidiTrack)")
    print("=" * 70)
    
    for label, root in [("Mini", mini_root), ("V12", v12_root)]:
        track = root.find(".//Tracks/MidiTrack")
        dc = track.find("DeviceChain") if track is not None else None
        if dc is None:
            print(f"  {label}: NO DeviceChain")
            continue
        print(f"\n  {label} DeviceChain children:")
        for i, c in enumerate(dc):
            print(f"    [{i:2d}] {c.tag}")
            for j, sc in enumerate(c):
                attrs = f"  attrs={dict(sc.attrib)}" if sc.attrib else ""
                nchild = len(list(sc))
                extra = f"  ({nchild} children)" if nchild else ""
                print(f"          [{j:2d}] {sc.tag}{attrs}{extra}")


def compare_midi_clip(mini_root, v12_root):
    print("\n" + "=" * 70)
    print("First MidiClip children comparison")
    print("=" * 70)
    
    for label, root in [("Mini", mini_root), ("V12", v12_root)]:
        clip = root.find(".//MidiClip")
        if clip is None:
            print(f"  {label}: NO MidiClip")
            continue
        print(f"\n  {label} MidiClip children:")
        for i, c in enumerate(clip):
            nchild = len(list(c))
            attrs = f"  {dict(c.attrib)}" if c.attrib else ""
            extra = f"  ({nchild} children)" if nchild else ""
            print(f"    [{i:2d}] {c.tag}{attrs}{extra}")


def compare_return_tracks(mini_root, v12_root):
    print("\n" + "=" * 70)
    print("ReturnTrack comparison")
    print("=" * 70)
    
    for label, root in [("Mini", mini_root), ("V12", v12_root)]:
        returns = root.findall(".//Tracks/ReturnTrack")
        print(f"\n  {label}: {len(returns)} ReturnTracks")
        for ri, rt in enumerate(returns):
            dc = rt.find("DeviceChain")
            if dc is None:
                print(f"    RT[{ri}]: NO DeviceChain")
                continue
            print(f"    RT[{ri}] DeviceChain children:")
            for i, c in enumerate(dc):
                print(f"      [{i:2d}] {c.tag}")
                for j, sc in enumerate(c):
                    attrs = f"  {dict(sc.attrib)}" if sc.attrib else ""
                    print(f"            [{j:2d}] {sc.tag}{attrs}")


def compare_scenes(mini_root, v12_root):
    print("\n" + "=" * 70)
    print("Scene comparison")
    print("=" * 70)
    
    for label, root in [("Mini", mini_root), ("V12", v12_root)]:
        scenes = root.findall(".//Scenes/Scene")
        print(f"\n  {label}: {len(scenes)} Scenes")
        if scenes:
            s0 = scenes[0]
            print(f"    Scene[0] children:")
            for i, c in enumerate(s0):
                attrs = f"  {dict(c.attrib)}" if c.attrib else ""
                print(f"      [{i:2d}] {c.tag}{attrs}")


def check_ids(root, label):
    print(f"\n  {label} IDs:")
    at_ids = []
    for at in root.findall(".//AutomationTarget"):
        id_val = at.get("Id")
        if id_val:
            at_ids.append(int(id_val))
    print(f"    AutomationTarget IDs: {len(at_ids)} total, {len(set(at_ids))} unique")
    dupes = [id for id, count in Counter(at_ids).items() if count > 1]
    if dupes:
        print(f"    DUPLICATE IDs: {dupes[:20]}")
    npi = root.find(".//NextPointeeId")
    if npi is not None:
        npi_val = int(npi.get("Value", "0"))
        max_at = max(at_ids) if at_ids else 0
        print(f"    NextPointeeId={npi_val}, max AT ID={max_at}")
        if npi_val <= max_at:
            print(f"    !! WARNING: NextPointeeId <= max AT ID")


def check_clip_slots(root, label):
    print(f"\n  {label} ClipSlots:")
    scenes = root.findall(".//Scenes/Scene")
    print(f"    Scenes: {len(scenes)}")
    for track in root.findall(".//Tracks/MidiTrack")[:3]:
        name_el = track.find(".//Name/EffectiveName")
        name = name_el.get("Value", "?") if name_el is not None else "?"
        slots = track.findall(".//ClipSlotList/ClipSlot")
        print(f"    Track '{name}': {len(slots)} ClipSlots")


def main():
    mini = ET.parse("output/ableton/_test_mini_raw.xml").getroot()
    v12 = ET.parse("output/ableton/_v12_raw.xml").getroot()
    
    compare_liveset_children(mini, v12)
    compare_first_track(mini, v12)
    compare_device_chain(mini, v12)
    compare_midi_clip(mini, v12)
    compare_return_tracks(mini, v12)
    compare_scenes(mini, v12)
    
    print("\n" + "=" * 70)
    print("ID ANALYSIS")
    print("=" * 70)
    check_ids(mini, "Mini")
    check_ids(v12, "V12")
    
    print("\n" + "=" * 70)
    print("CLIP SLOT ANALYSIS")
    print("=" * 70)
    check_clip_slots(mini, "Mini")
    check_clip_slots(v12, "V12")


if __name__ == "__main__":
    main()
