"""Compare LiveSet-level structure between Mini (works) and V12 (crashes)."""
import gzip
import xml.etree.ElementTree as ET
import os

base = os.path.dirname(__file__)

def load_als(path):
    with gzip.open(path, "rb") as f:
        return ET.fromstring(f.read())

mini = load_als(os.path.join(base, "output", "ableton", "_test_mini.als"))
v12 = load_als(os.path.join(base, "output", "ableton", "Wild_Ones_V12.als"))

mini_ls = mini.find("LiveSet")
v12_ls = v12.find("LiveSet")

print("=== LIVESET TOP-LEVEL CHILDREN ===")
mini_tags = [(c.tag, c.attrib) for c in mini_ls]
v12_tags = [(c.tag, c.attrib) for c in v12_ls]

max_len = max(len(mini_tags), len(v12_tags))
for i in range(max_len):
    m = mini_tags[i] if i < len(mini_tags) else ("(missing)", {})
    v = v12_tags[i] if i < len(v12_tags) else ("(missing)", {})
    match = " OK" if m[0] == v[0] else " *** DIFF ***"
    print(f"  [{i:2d}] Mini: {m[0]:35s}  V12: {v[0]:35s}{match}")

# Compare Scenes
print("\n=== SCENES ===")
mini_scenes = mini_ls.findall("Scenes/Scene")
v12_scenes = v12_ls.findall("Scenes/Scene")
print(f"Mini: {len(mini_scenes)} scenes, V12: {len(v12_scenes)} scenes")

if v12_scenes:
    # Check first scene structure
    s = v12_scenes[0]
    print(f"\nV12 Scene[0] children:")
    for c in s:
        attrs = " ".join(f'{k}="{v[:30]}"' for k,v in c.attrib.items())
        n = len(list(c))
        print(f"  {c.tag} [{attrs}] ({n} children)")
    
    # Check ClipSlotSnapshots
    for i, scene in enumerate(v12_scenes):
        css = scene.findall("ClipSlotSnapshots/ClipSlotSnapshot")
        print(f"  Scene[{i}] Id={scene.get('Id','?')}: {len(css)} ClipSlotSnapshots")

# Compare Locators
print("\n=== LOCATORS (Cue Points) ===")
mini_locs = mini_ls.findall(".//Locators/Locators/Locator")
v12_locs = v12_ls.findall(".//Locators/Locators/Locator")
print(f"Mini: {len(mini_locs)}, V12: {len(v12_locs)}")
for loc in v12_locs[:5]:
    lid = loc.get("Id", "?")
    time_el = loc.find("Time")
    name_el = loc.find("Name")
    t = time_el.get("Value", "?") if time_el is not None else "?"
    n = name_el.get("Value", "?") if name_el is not None else "?"
    print(f"  Locator Id={lid} Time={t} Name={n}")

# Compare MasterTrack
print("\n=== MASTER TRACK ===")
for label, ls in [("Mini", mini_ls), ("V12", v12_ls)]:
    mt = ls.find("MasterTrack")
    if mt is not None:
        children = [(c.tag, len(list(c))) for c in mt]
        print(f"{label} MasterTrack: {len(children)} children")
        for tag, n in children:
            print(f"  {tag} ({n} children)")

# Compare Transport
print("\n=== TRANSPORT ===")
for label, ls in [("Mini", mini_ls), ("V12", v12_ls)]:
    t = ls.find("Transport")
    if t is not None:
        print(f"{label} Transport:")
        for c in t:
            v = c.get("Value", "")
            n = len(list(c))
            if v:
                print(f"  {c.tag} = {v}")
            else:
                print(f"  {c.tag} ({n} children)")

# Check NextPointeeId
print("\n=== NEXT POINTEE ID ===")
for label, ls in [("Mini", mini_ls), ("V12", v12_ls)]:
    npi = ls.find("NextPointeeId")
    print(f"{label}: {npi.get('Value', '?') if npi is not None else 'NOT FOUND'}")

# Check AutomationTarget id ranges
print("\n=== AUTOMATION TARGET ID RANGES ===")
for label, ls in [("Mini", mini_ls), ("V12", v12_ls)]:
    all_ids = []
    for at in ls.iter():
        if at.tag in ("AutomationTarget", "ModulationTarget", "Pointee",
                       "ControllerTargets.0", "ControllerTargets.1"):
            aid = at.get("Id")
            if aid:
                try:
                    all_ids.append(int(aid))
                except ValueError:
                    pass
    # Also get Ids from any element with dotted tag
    for at in ls.iter():
        if "." in at.tag and at.tag.startswith("ControllerTargets"):
            aid = at.get("Id")
            if aid:
                try:
                    all_ids.append(int(aid))
                except ValueError:
                    pass
    
    if all_ids:
        print(f"{label}: {len(all_ids)} target IDs, range [{min(all_ids)}, {max(all_ids)}]")
        npi = ls.find("NextPointeeId")
        npi_val = int(npi.get("Value", "0")) if npi is not None else 0
        over = [i for i in all_ids if i >= npi_val]
        if over:
            print(f"  WARNING: {len(over)} IDs >= NextPointeeId ({npi_val}): {over[:10]}")
        # Check for duplicates
        dupes = [i for i in set(all_ids) if all_ids.count(i) > 1]
        if dupes:
            print(f"  WARNING: {len(dupes)} DUPLICATE IDs: {sorted(dupes)[:10]}")
    else:
        print(f"{label}: No target IDs found")
