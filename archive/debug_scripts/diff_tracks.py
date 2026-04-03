"""Detailed XML comparison of track 0 (DRUMS, works) vs track 2 (SUB, crashes)."""
import gzip
import xml.etree.ElementTree as ET
import os

base = os.path.dirname(__file__)
v12_path = os.path.join(base, "output", "ableton", "Wild_Ones_V12.als")

with gzip.open(v12_path, "rb") as f:
    raw = f.read()
root = ET.fromstring(raw)

tracks = root.findall(".//Tracks/MidiTrack")

def xml_to_str(elem, indent=0):
    """Pretty-print XML element."""
    lines = []
    tag = elem.tag
    attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
    children = list(elem)
    text = (elem.text or "").strip()
    
    prefix = "  " * indent
    if children:
        lines.append(f"{prefix}<{tag} {attrs}>".rstrip())
        for child in children:
            lines.extend(xml_to_str(child, indent + 1))
        lines.append(f"{prefix}</{tag}>")
    elif text:
        lines.append(f"{prefix}<{tag} {attrs}>{text}</{tag}>")
    else:
        lines.append(f"{prefix}<{tag} {attrs} />".rstrip())
    return lines

# Write track 0 and track 2 to files for comparison
for idx in [0, 2]:
    t = tracks[idx]
    lines = xml_to_str(t)
    fname = os.path.join(base, f"_track{idx}_dump.txt")
    with open(fname, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote _track{idx}_dump.txt ({len(lines)} lines)")

# Now do inline diff of key sections
def compare_elements(e1, e2, path="", depth=0):
    """Recursively compare two elements, printing differences."""
    diffs = []
    
    # Compare tag
    if e1.tag != e2.tag:
        diffs.append(f"[{path}] TAG: {e1.tag} vs {e2.tag}")
        return diffs
    
    current = f"{path}/{e1.tag}" if path else e1.tag
    
    # Compare attributes  
    for key in set(list(e1.attrib.keys()) + list(e2.attrib.keys())):
        v1 = e1.attrib.get(key, "(missing)")
        v2 = e2.attrib.get(key, "(missing)")
        if v1 != v2:
            diffs.append(f"[{current}] ATTR {key}: '{v1}' vs '{v2}'")
    
    # Compare children count
    c1 = list(e1)
    c2 = list(e2)
    
    if len(c1) != len(c2):
        tags1 = [c.tag for c in c1]
        tags2 = [c.tag for c in c2]
        diffs.append(f"[{current}] CHILDREN: {len(c1)} vs {len(c2)}")
        # Find which tags differ
        for t in set(tags1) - set(tags2):
            diffs.append(f"  Only in track0: {t}")
        for t in set(tags2) - set(tags1):
            diffs.append(f"  Only in track2: {t}")
        return diffs
    
    # Compare each child pair
    for child1, child2 in zip(c1, c2):
        if child1.tag != child2.tag:
            diffs.append(f"[{current}] CHILD ORDER: {child1.tag} vs {child2.tag}")
        else:
            child_diffs = compare_elements(child1, child2, current, depth + 1)
            diffs.extend(child_diffs)
    
    return diffs

print("\n=== ELEMENT-BY-ELEMENT DIFF (Track 0 vs Track 2) ===")
print("(Ignoring expected differences: Id, Color, Name, AutomationTarget Ids, clip data)")
print()

t0 = tracks[0]
t2 = tracks[2]

# Compare DeviceChain deeply (most likely source of issue)
dc0 = t0.find("DeviceChain")
dc2 = t2.find("DeviceChain")

diffs = compare_elements(dc0, dc2, "DeviceChain")

# Filter out expected differences
for d in diffs:
    # Skip known-different things
    skip = False
    for pattern in ["ATTR Id:", "ATTR Value:", "EffectiveName", "UserName", 
                     "AutomationTarget", "PointeeId", "annotation",
                     "Annotation", "Color"]:
        if pattern.lower() in d.lower():
            skip = True
            break
    if not skip:
        print(d)

if not diffs:
    print("NO DIFFERENCES in DeviceChain between tracks!")

# Now compare excluding AutomationTarget Ids and known varying values
print("\n=== ALL ATTRIBUTE DIFFERENCES IN DeviceChain ===")
for d in diffs[:50]:
    print(d)
if len(diffs) > 50:
    print(f"... and {len(diffs) - 50} more")

# Check if there's something in the Mixer section specifically
print("\n=== MIXER COMPARISON ===")
mixer0 = dc0.find("Mixer")
mixer2 = dc2.find("Mixer")
if mixer0 is not None and mixer2 is not None:
    print("Track 0 Mixer children:")
    for child in mixer0:
        attrs = " ".join(f'{k}="{v[:30]}"' for k, v in child.attrib.items())
        n = len(list(child))
        print(f"  {child.tag} [{attrs}] ({n} children)")
    print("Track 2 Mixer children:")
    for child in mixer2:
        attrs = " ".join(f'{k}="{v[:30]}"' for k, v in child.attrib.items())
        n = len(list(child))
        print(f"  {child.tag} [{attrs}] ({n} children)")

# Check Sends specifically
print("\n=== SENDS STRUCTURE ===")
for idx in [0, 2]:
    t = tracks[idx]
    print(f"\nTrack {idx}:")
    sends = t.find(".//Mixer/Sends")
    if sends is not None:
        print(f"  Sends: {len(list(sends))} children")
        for child in sends:
            print(f"    {child.tag} [{' '.join(f'{k}={v}' for k,v in child.attrib.items())}]")
            for cc in child:
                print(f"      {cc.tag} [{' '.join(f'{k}={v[:30]}' for k,v in cc.attrib.items())}]")
                for ccc in cc:
                    a = " ".join(f'{k}={v[:30]}' for k,v in ccc.attrib.items())
                    print(f"        {ccc.tag} [{a}]")
    else:
        print("  Sends: NOT FOUND")
