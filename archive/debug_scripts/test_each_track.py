"""Test automation on each track individually to find which ones crash."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
import time
import copy

src = Path("output/ableton/test_bisect/v12_no_auto.als")
out_dir = Path("output/ableton/test_bisect")
ableton = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
prefs = Path.home() / "AppData/Roaming/Ableton/Live 12.3.6/Preferences"
log_path = prefs / "Log.txt"

# Load the base no-auto file
with gzip.open(src, "rb") as f:
    base_tree = ET.parse(f)
base_root = base_tree.getroot()

# Get all MidiTrack IDs
tracks_elem = base_root.find(".//Tracks")
track_ids = [(mt.get("Id"), mt.find(".//Name/EffectiveName").get("Value", "?"))
             for mt in tracks_elem.findall("MidiTrack")]

print(f"Found {len(track_ids)} MidiTracks")
for tid, name in track_ids:
    print(f"  Track Id={tid}: {name}")

results = {}

for tid, name in track_ids:
    # Deep copy the base
    root = copy.deepcopy(base_root)
    tracks = root.find(".//Tracks")
    
    # Find this track
    target = None
    for mt in tracks.findall("MidiTrack"):
        if mt.get("Id") == tid:
            target = mt
            break
    
    if target is None:
        print(f"  Track {tid} ({name}): NOT FOUND")
        continue
    
    # Get Volume AutomationTarget Id
    dc = target.find("DeviceChain")
    mixer = dc.find("Mixer")
    vol = mixer.find("Volume")
    at = vol.find("AutomationTarget")
    target_id = at.get("Id")
    
    # Add envelope
    ae = target.find("AutomationEnvelopes")
    envs = ae.find("Envelopes")
    env = ET.SubElement(envs, "AutomationEnvelope", Id="0")
    et_elem = ET.SubElement(env, "EnvelopeTarget")
    ptid = ET.SubElement(et_elem, "PointeeId")
    ptid.set("Value", target_id)
    auto = ET.SubElement(env, "Automation")
    events = ET.SubElement(auto, "Events")
    e1 = ET.SubElement(events, "FloatEvent", Id="0")
    e1.set("Time", "0.0")
    e1.set("Value", "0.5")
    e2 = ET.SubElement(events, "FloatEvent", Id="1")
    e2.set("Time", "16.0")
    e2.set("Value", "1.0")
    atvs = ET.SubElement(auto, "AutomationTransformViewState")
    itp = ET.SubElement(atvs, "IsTransformPending")
    itp.set("Value", "false")
    ET.SubElement(atvs, "TimeAndValueTransforms")
    
    # Save
    dst = out_dir / f"auto_track_{tid}.als"
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    with gzip.open(dst, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))
    
    # Clear crash state
    for cf in ["CrashDetection.cfg", "CrashRecoveryInfo.cfg"]:
        p = prefs / cf
        if p.exists():
            p.unlink()
    
    # Kill any running Ableton
    subprocess.run(["taskkill", "/f", "/im", "Ableton Live 12 Standard.exe"],
                    capture_output=True)
    time.sleep(1)
    
    # Mark log position
    log_size_before = log_path.stat().st_size if log_path.exists() else 0
    
    # Launch
    proc = subprocess.Popen([ableton, str(dst.resolve())])
    time.sleep(8)  # Quick check
    
    # Check log
    crashed = False
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
            lf.seek(log_size_before)
            new_log = lf.read()
            if "EXCEPTION_ACCESS_VIOLATION" in new_log or "Fatal Error" in new_log:
                crashed = True
    
    status = "CRASH" if crashed else "OK"
    results[f"{tid}:{name}"] = status
    print(f"  Track {tid:>2} ({name:>12}): Volume AT={target_id} → {status}")
    
    # Kill Ableton
    subprocess.run(["taskkill", "/f", "/im", "Ableton Live 12 Standard.exe"],
                    capture_output=True)
    time.sleep(2)

print()
print("=== SUMMARY ===")
for k, v in results.items():
    print(f"  {k}: {v}")
