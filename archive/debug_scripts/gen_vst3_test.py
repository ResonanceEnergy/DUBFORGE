"""Generate a test ALS with the fixed VST3 PluginDevice."""
import gzip, os
import xml.etree.ElementTree as ET
from engine.als_generator import build_als_xml, ALSProject, ALSTrack

t = ALSTrack(name="Bass", track_type="midi", device_names=["Serum 2"])
proj = ALSProject(name="vst3_test", bpm=140, tracks=[t])
root = build_als_xml(proj)

xml_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
xml_decl = b'<?xml version="1.0" encoding="UTF-8"?>\n'
gz_data = gzip.compress(xml_decl + xml_bytes)

os.makedirs("output/ableton", exist_ok=True)
out = "output/ableton/_test_vst3_fix.als"
with open(out, "wb") as f:
    f.write(gz_data)
print(f"Wrote {out} ({len(gz_data)} bytes)")
