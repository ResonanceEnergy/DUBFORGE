"""Binary search for the automation TIME threshold that causes crashes."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import copy
import subprocess
import time as time_mod

base = Path("output/ableton/test_bisect/v12_no_auto.als")
out_dir = Path("output/ableton/test_bisect")
ableton = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
prefs = Path.home() / "AppData/Roaming/Ableton/Live 12.3.6/Preferences"
log_path = prefs / "Log.txt"

with gzip.open(base, "rb") as f:
    base_tree = ET.parse(f)
base_root = base_tree.getroot()

# Get RISER track Volume target
riser = None
for mt in base_root.iter("MidiTrack"):
    if mt.get("Id") == "14":
        riser = mt
        break
dc = riser.find("DeviceChain")
target_id = dc.find("Mixer/Volume/AutomationTarget").get("Id")
print(f"RISER Volume target: {target_id}")

# First check: what's the arrangement length?
# Check ArrangementEndTime or similar in the root
for tag in ["ArrangementEndTime", "SongLength", "EndMark"]:
    for el in base_root.iter(tag):
        print(f"  {tag}: {el.get('Value', el.text)}")

# Check all scene times  
for scene in base_root.iter("Scene"):
    sid = scene.get("Id")
    # Check if there's a Position or Tempo element
    # Actually, scenes in arrangement are in order, lengths determined by clips

# Check the actual clip positions on RISER track
print("\nRISER track clips:")
for clip in riser.iter("MidiClip"):
    cid = clip.get("Id")
    cs = clip.find("CurrentStart")
    ce = clip.find("CurrentEnd")
    start_val = cs.get("Value") if cs is not None else "?"
    end_val = ce.get("Value") if ce is not None else "?"
    name_el = clip.find("Name")
    name = name_el.get("Value") if name_el is not None else "?"
    print(f"  Clip {cid}: {name} -> [{start_val}, {end_val}]")

def test_time(max_time, label):
    """Create and test an envelope with 2 events at time 0 and max_time."""
    root = copy.deepcopy(base_root)
    for mt in root.iter("MidiTrack"):
        if mt.get("Id") != "14":
            continue
        ae = mt.find("AutomationEnvelopes")
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
        e2.set("Time", str(float(max_time)))
        e2.set("Value", "1.0")
        atvs = ET.SubElement(auto, "AutomationTransformViewState")
        itp = ET.SubElement(atvs, "IsTransformPending")
        itp.set("Value", "false")
        ET.SubElement(atvs, "TimeAndValueTransforms")
        break

    dst = out_dir / f"time_test_{label}.als"
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    with gzip.open(dst, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))

    # Clear crash state
    for cf in ["CrashDetection.cfg", "CrashRecoveryInfo.cfg"]:
        p = prefs / cf
        if p.exists():
            p.unlink()
    subprocess.run(["taskkill", "/f", "/im", "Ableton Live 12 Standard.exe"], capture_output=True)
    time_mod.sleep(1)

    log_size_before = log_path.stat().st_size if log_path.exists() else 0
    proc = subprocess.Popen([ableton, str(dst.resolve())])
    time_mod.sleep(8)

    crashed = False
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
            lf.seek(log_size_before)
            new_log = lf.read()
            if "EXCEPTION_ACCESS_VIOLATION" in new_log or "Fatal Error" in new_log:
                crashed = True

    status = "CRASH" if crashed else "OK"
    print(f"  Time 0→{max_time}: {status}")

    subprocess.run(["taskkill", "/f", "/im", "Ableton Live 12 Standard.exe"], capture_output=True)
    time_mod.sleep(2)
    return crashed

# Test specific thresholds
# We know: 160 works, 224 crashes. 
# Let me also check if starting at 64 (not 0) with short range still crashes
# First: test the max time values
print("\n=== TIME RANGE TESTS ===")
for t in [160, 192, 200, 210, 220, 224, 256, 416]:
    test_time(t, str(t))
