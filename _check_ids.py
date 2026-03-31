"""Check for broken automation references in generated ALS."""
import gzip
import xml.etree.ElementTree as ET

with gzip.open("output/ableton/Wild_Ones_V9.als", "rb") as f:
    root = ET.fromstring(f.read())
ls = root.find("LiveSet")

# Collect ALL AutomationTarget/ModulationTarget IDs
all_target_ids = set()
for at in root.iter("AutomationTarget"):
    all_target_ids.add(at.get("Id"))
for mt in root.iter("ModulationTarget"):
    all_target_ids.add(mt.get("Id"))
print(f"Total AutomationTarget/ModulationTarget IDs: {len(all_target_ids)}")

# Check all PointeeId references - do they reference valid targets?
broken_refs = []
for pe in root.iter("PointeeId"):
    pid = pe.get("Value")
    if pid and pid != "0" and pid not in all_target_ids:
        broken_refs.append(pid)
print(f"Broken PointeeId references: {len(broken_refs)}")
if broken_refs[:5]:
    print(f"  First 5: {broken_refs[:5]}")

# Check MainTrack automation envelopes
main_track = ls.find("MainTrack")
if main_track is not None:
    ae = main_track.find("AutomationEnvelopes")
    if ae is not None:
        envs = ae.find("Envelopes")
        if envs is not None:
            env_list = list(envs)
            print(f"\nMainTrack AutomationEnvelopes: {len(env_list)} envelopes")
            for env in env_list:
                et = env.find("EnvelopeTarget/PointeeId")
                if et is not None:
                    pid = et.get("Value")
                    valid = pid in all_target_ids
                    print(f"  PointeeId={pid} valid={valid}")

# Check all ID uniqueness
all_pointee = []
for p in root.iter("Pointee"):
    all_pointee.append(p.get("Id"))
print(f"\nPointee elements: {len(all_pointee)}")

# Check for duplicate IDs
from collections import Counter
id_counts = Counter(all_pointee)
dups = {k: v for k, v in id_counts.items() if v > 1}
if dups:
    print(f"DUPLICATE Pointee IDs: {dups}")
else:
    print("No duplicate Pointee IDs")

# Check AutomationTarget ID uniqueness
at_ids = []
for at in root.iter("AutomationTarget"):
    at_ids.append(at.get("Id"))
at_dups = {k: v for k, v in Counter(at_ids).items() if v > 1}
if at_dups:
    print(f"DUPLICATE AutomationTarget IDs: {dict(list(at_dups.items())[:5])}")
else:
    print("No duplicate AutomationTarget IDs")

# Check if the file path referenced in first audio clip exists
for clip in root.iter("AudioClip"):
    fr = clip.find("SampleRef/FileRef/Path")
    if fr is not None:
        path = fr.get("Value", "")
        import os
        exists = os.path.exists(path)
        print(f"\nFirst AudioClip path: {path[:70]}...")
        print(f"  File exists: {exists}")
        break
