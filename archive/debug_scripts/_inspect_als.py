"""Extract PluginDevice XML from the ALS and the reference (stripped) ALS."""
import gzip
import xml.etree.ElementTree as ET
import xml.dom.minidom

def print_element(elem, label, max_lines=200):
    rough = ET.tostring(elem, encoding="unicode")
    pretty = xml.dom.minidom.parseString(rough).toprettyxml(indent="  ")
    lines = pretty.split("\n")
    print(f"\n=== {label} ({len(lines)} lines) ===")
    for j, line in enumerate(lines[:max_lines]):
        print(line)
    if len(lines) > max_lines:
        print(f"... ({len(lines) - max_lines} more lines)")

# V10 ALS (with PluginDevice - crashes)
als_path = r"C:\dev\SuperAgency-Shared\repos\DUBFORGE\output\ableton\Wild_Ones_V10.als"
with gzip.open(als_path) as f:
    tree = ET.parse(f)
root = tree.getroot()

# Find PluginDevice elements
plugins = list(root.iter("PluginDevice"))
print(f"PluginDevice count: {len(plugins)}")

if plugins:
    print_element(plugins[0], "First PluginDevice (full XML)")

# Find the Devices parent
for track in root.iter("MidiTrack"):
    dc = track.find("DeviceChain")
    if dc is None:
        continue
    # Walk to find Devices element
    for elem in dc.iter():
        if elem.tag == "Devices":
            print(f"\nDevices parent tag: {elem.tag}")
            print(f"Devices children: {[c.tag for c in elem]}")
            break
    break
