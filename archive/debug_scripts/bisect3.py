"""Test if track Id renumbering fixes the crash."""
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

# Test: keep only tracks 2+3 but renumber Ids to 0 and 1
r = copy.deepcopy(root)
te = r.find("LiveSet/Tracks")
mt = te.findall("MidiTrack")
for t in mt[4:]:
    te.remove(t)
for t in mt[:2]:
    te.remove(t)
# Renumber remaining tracks
remaining = te.findall("MidiTrack")
for i, t in enumerate(remaining):
    old_id = t.get("Id")
    t.set("Id", str(i))
    print(f"Renumbered track Id {old_id} -> {i}")
# Also renumber return tracks
for i, rt in enumerate(te.findall("ReturnTrack")):
    new_id = len(remaining) + i
    old_id = rt.get("Id")
    rt.set("Id", str(new_id))
    print(f"Renumbered return track Id {old_id} -> {new_id}")
save_als(r, "bisect_tracks2and3_renumbered.als")

# Another test: keep all 15 tracks + 2 returns as-is, but look at
# whether removing all automation envelopes helps
r = copy.deepcopy(root)
for t in r.findall(".//MidiTrack"):
    ae = t.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            for env in list(envs):
                envs.remove(env)
for t in r.findall(".//ReturnTrack"):
    ae = t.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            for env in list(envs):
                envs.remove(env)
save_als(r, "bisect_noAutomation.als")

# Test: just 3 tracks but renumber correctly
r = copy.deepcopy(root)
te = r.find("LiveSet/Tracks")
mt = te.findall("MidiTrack")
for t in mt[3:]:
    te.remove(t)
# Don't renumber — they're already 0,1,2
# But renumber returns
for i, rt in enumerate(te.findall("ReturnTrack")):
    new_id = 3 + i
    old_id = rt.get("Id")
    rt.set("Id", str(new_id))
    print(f"Renumbered return Id {old_id} -> {new_id}")
save_als(r, "bisect_3tracks_fixedReturnIds.als")

print("Done")
