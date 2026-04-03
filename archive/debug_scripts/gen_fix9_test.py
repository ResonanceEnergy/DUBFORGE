"""Generate test ALS files with Fix 9 (default scene) for crash testing."""
import sys, gzip, xml.etree.ElementTree as ET
sys.path.insert(0, ".")
from engine.als_generator import ALSProject, ALSTrack, build_als_xml

# --- Test 1: No VST3, empty scenes (was crashing before Fix 9) ---
proj = ALSProject(name="Fix9 Test No Serum", bpm=140.0)
proj.tracks.append(ALSTrack(name="Bass", track_type="midi",
                             volume_db=-3.0, pan=0.0))
tree = build_als_xml(proj, "_test_fix9_noserum.als")

ls = tree.find("LiveSet")
scenes_elem = ls.find("Scenes")
scene_children = list(scenes_elem)
print(f"Scenes children: {len(scene_children)}")
for c in scene_children:
    print(f"  {c.tag} Id={c.get('Id')}")

out1 = "_test_fix9_noserum.als"
raw = ET.tostring(tree, encoding="unicode", xml_declaration=False)
xml_bytes = ('<?xml version="1.0" encoding="UTF-8"?>\n' + raw).encode("utf-8")
with gzip.open(out1, "wb") as f:
    f.write(xml_bytes)
print(f"Wrote {out1}")

# --- Test 2: With Serum 2 VST3 ---
proj2 = ALSProject(name="Fix9 Test Serum", bpm=140.0)
proj2.tracks.append(ALSTrack(
    name="Serum Bass", track_type="midi",
    volume_db=-3.0, pan=0.0,
    device_names=["Serum 2"],
))
tree2 = build_als_xml(proj2, "_test_fix9_serum.als")

out2 = "_test_fix9_serum.als"
raw2 = ET.tostring(tree2, encoding="unicode", xml_declaration=False)
xml_bytes2 = ('<?xml version="1.0" encoding="UTF-8"?>\n' + raw2).encode("utf-8")
with gzip.open(out2, "wb") as f:
    f.write(xml_bytes2)
print(f"Wrote {out2}")
