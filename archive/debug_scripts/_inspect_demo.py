"""Inspect Ableton demo song for plugin device XML structure."""
import gzip
import xml.etree.ElementTree as ET

demo = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Core Library\Lessons\Demo Songs\Chuck Sutton - Patience (Live 12 Intro Demo).als"

with gzip.open(demo, "rb") as f:
    root = ET.fromstring(f.read())

# Find all unique device tags
device_tags = set()
for devices_elem in root.iter("Devices"):
    for dev in devices_elem:
        device_tags.add(dev.tag)

print("All device types found in demo song:")
for t in sorted(device_tags):
    print(f"  {t}")

# Look for any PluginDevice or VST references
print("\n--- Plugin/VST related elements ---")
for elem in root.iter():
    if "Plugin" in elem.tag or "Vst" in elem.tag:
        attrs = dict(elem.attrib)
        text_preview = (elem.text or "")[:60]
        print(f"  <{elem.tag}> attrs={attrs} text={text_preview!r}")

# Show first PluginDevice in full
print("\n--- First PluginDevice (if any) ---")
for pd in root.iter("PluginDevice"):
    xml_str = ET.tostring(pd, encoding="unicode")
    print(xml_str[:3000])
    print("...")
    break

# Check the creative tools template
print("\n--- Creative Tools Template ---")
creative_templates = [
    r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Core Library\Defaults\Creating Sounds\Instruments\Drift",
]
import glob, os
inst_path = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Core Library\Defaults\Creating Sounds\Instruments"
if os.path.exists(inst_path):
    subdirs = os.listdir(inst_path)
    print(f"  Instrument folders: {subdirs[:10]}")
