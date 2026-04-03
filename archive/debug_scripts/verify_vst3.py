"""Verify PluginDevice in the Serum 2 test file."""
import gzip, xml.etree.ElementTree as ET

with gzip.open("_test_fix9_serum.als", "rb") as f:
    tree = ET.parse(f)

root = tree.getroot()
found = False
for pd in root.iter("PluginDevice"):
    found = True
    print("Found PluginDevice")
    uid = pd.find(".//Vst3PluginInfo/Uid")
    if uid is not None:
        for c in uid:
            print("  {} = {}".format(c.tag, c.get("Value")))
    dn = pd.find(".//Vst3PluginInfo/DeviceName")
    if dn is not None:
        print("  DeviceName = {}".format(dn.get("Value")))

if not found:
    print("No PluginDevice found!")
