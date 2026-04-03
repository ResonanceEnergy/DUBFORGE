"""Strip ALL AutomationEnvelope content from V12 for testing."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

src = Path("output/ableton/Wild_Ones_V12.als")
dst = Path("output/ableton/test_bisect/v12_no_auto.als")
dst.parent.mkdir(parents=True, exist_ok=True)

with gzip.open(src, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

# Strip all Envelopes children (keep the AutomationEnvelopes/Envelopes container empty)
count = 0
for envs in root.iter("Envelopes"):
    for child in list(envs):
        envs.remove(child)
        count += 1

print(f"Removed {count} AutomationEnvelope elements")

xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
with gzip.open(dst, "wb") as f:
    f.write(xml_bytes.encode("utf-8"))
print(f"Wrote: {dst}")
