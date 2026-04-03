"""Generate two test ALS files: one with Serum 2, one without."""
import gzip, os
import xml.etree.ElementTree as ET
from engine.als_generator import build_als_xml, ALSProject, ALSTrack

os.makedirs("output/ableton", exist_ok=True)

# With Serum 2
t1 = ALSTrack(name="Bass", track_type="midi", device_names=["Serum 2"])
p1 = ALSProject(name="with_serum2", bpm=140, tracks=[t1])
r1 = build_als_xml(p1)
xml1 = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(r1, encoding="unicode").encode("utf-8")
with open("output/ableton/_test_with_serum.als", "wb") as f:
    f.write(gzip.compress(xml1))
print("Wrote _test_with_serum.als")

# Without Serum 2 (same track structure, no VST3)
t2 = ALSTrack(name="Bass", track_type="midi")
p2 = ALSProject(name="no_serum", bpm=140, tracks=[t2])
r2 = build_als_xml(p2)
xml2 = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(r2, encoding="unicode").encode("utf-8")
with open("output/ableton/_test_no_serum.als", "wb") as f:
    f.write(gzip.compress(xml2))
print("Wrote _test_no_serum.als")
