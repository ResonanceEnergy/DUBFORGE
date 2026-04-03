"""Create 3-track and 4-track bisect variants."""
import gzip
import xml.etree.ElementTree as ET
import os
import copy

base = os.path.dirname(__file__)
v12_path = os.path.join(base, "output", "ableton", "Wild_Ones_V12.als")
out_dir = os.path.join(base, "output", "ableton", "test_bisect")

with gzip.open(v12_path, "rb") as f:
    raw = f.read()
root = ET.fromstring(raw)

def save_als(root_elem, filename):
    xml_bytes = ET.tostring(root_elem, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    path = os.path.join(out_dir, filename)
    with gzip.open(path, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))
    print(f"Saved: {filename} ({os.path.getsize(path)} bytes)")

for n in [3, 4]:
    r = copy.deepcopy(root)
    te = r.find("LiveSet/Tracks")
    mt = te.findall("MidiTrack")
    for t in mt[n:]:
        te.remove(t)
    save_als(r, f"bisect_{n}tracks.als")

# Also: 2 tracks but WITHOUT return tracks
r = copy.deepcopy(root)
te = r.find("LiveSet/Tracks")
mt = te.findall("MidiTrack")
for t in mt[2:]:
    te.remove(t)
for rt in te.findall("ReturnTrack"):
    te.remove(rt)
save_als(r, "bisect_2tracks_noReturns.als")

# Test specific tracks: skip DRUMS+BASS, try tracks 3-4 only
r = copy.deepcopy(root)
te = r.find("LiveSet/Tracks")
mt = te.findall("MidiTrack")
# Remove tracks 0-1 and 4+
for t in mt[4:]:
    te.remove(t)
for t in mt[:2]:
    te.remove(t)
save_als(r, "bisect_tracks2and3_only.als")  # SUB + GROWL

print("Done")
