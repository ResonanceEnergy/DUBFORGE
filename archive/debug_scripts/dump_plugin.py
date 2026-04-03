"""Dump the PluginDevice XML from the generated Apology V4 to inspect structure."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

als = Path("output/ableton/Apology_V4.als")
with gzip.open(als, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

# Find all PluginDevice elements
for pd in root.iter("PluginDevice"):
    parent_tag = "?"
    # Walk up to find track name
    xml_str = ET.tostring(pd, encoding="unicode")
    print(f"PluginDevice Id={pd.get('Id')}:")
    print(xml_str[:2000])
    print("---")
