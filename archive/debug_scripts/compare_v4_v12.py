"""Compare Apology V4 (with VST3 - crashes) vs V4-no-VST3 (loads OK).
Generate V4 without VST3 to compare XML structures."""
import gzip
import xml.etree.ElementTree as ET
import os


def get_tree(path):
    with gzip.open(path, "rb") as f:
        return ET.parse(f)


def element_structure(elem, depth=0, max_depth=4):
    """Get structural summary of element."""
    result = []
    indent = "  " * depth
    attrs = " ".join(f'{k}="{v}"' for k, v in sorted(elem.attrib.items()))
    tag_str = f"{indent}<{elem.tag}"
    if attrs:
        tag_str += f" {attrs}"
    tag_str += ">"
    result.append(tag_str)
    if depth < max_depth:
        for child in elem:
            result.extend(element_structure(child, depth + 1, max_depth))
    return result


# Compare the crashed V4 (with plugins) against V12 (no plugins, loads OK)
v4_path = r"C:\dev\SuperAgency-Shared\repos\DUBFORGE\output\ableton\Apology_V4.als"
v12_path = r"C:\dev\SuperAgency-Shared\repos\DUBFORGE\output\ableton\Wild_Ones_V12.als"

v4 = get_tree(v4_path).getroot()
v12 = get_tree(v12_path).getroot()

# Compare first MidiTrack's inner DeviceChain structure
def get_inner_dc(root):
    track = list(root.iter("MidiTrack"))[0]
    outer_dc = track.find("DeviceChain")
    found_freeze = False
    for child in outer_dc:
        if child.tag == "FreezeSequencer":
            found_freeze = True
        elif child.tag == "DeviceChain" and found_freeze:
            return child
    return None

v4_dc = get_inner_dc(v4)
v12_dc = get_inner_dc(v12)

print("=== V4 (crashes) - first MidiTrack inner DeviceChain ===")
for line in element_structure(v4_dc, max_depth=5):
    print(line)

print("\n=== V12 (loads OK) - first MidiTrack inner DeviceChain ===")
for line in element_structure(v12_dc, max_depth=5):
    print(line)

# Also dump the Devices children for V4 and V12
print("\n=== V4 Devices children ===")
v4_devices = v4_dc.find("Devices")
if v4_devices is not None:
    for child in v4_devices:
        print(f"  <{child.tag} Id='{child.get('Id', '')}'> children: {[c.tag for c in child]}")
else:
    print("  No Devices element")

print("\n=== V12 Devices children ===")
v12_devices = v12_dc.find("Devices")
if v12_devices is not None:
    for child in v12_devices:
        print(f"  <{child.tag} Id='{child.get('Id', '')}'> children: {[c.tag for c in child]}")
else:
    print("  No Devices element (empty)")

# Compare top-level LiveSet structure
print("\n=== LiveSet direct children (V4) ===")
v4_ls = v4.find("LiveSet")
for child in v4_ls:
    print(f"  <{child.tag}> children={len(child)}")

print("\n=== LiveSet direct children (V12) ===")
v12_ls = v12.find("LiveSet")
for child in v12_ls:
    print(f"  <{child.tag}> children={len(child)}")
