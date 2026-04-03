"""Verify: automation crashes if first event doesn't start at beginning of time."""
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

target_id = None
for mt in base_root.iter("MidiTrack"):
    if mt.get("Id") == "14":
        target_id = mt.find("DeviceChain/Mixer/Volume/AutomationTarget").get("Id")
        break

def make_test(events_data, label):
    """Create test with given events [(time, value), ...]"""
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
        for i, (t, v) in enumerate(events_data):
            e = ET.SubElement(events, "FloatEvent", Id=str(i))
            e.set("Time", str(t))
            e.set("Value", str(v))
        atvs = ET.SubElement(auto, "AutomationTransformViewState")
        itp = ET.SubElement(atvs, "IsTransformPending")
        itp.set("Value", "false")
        ET.SubElement(atvs, "TimeAndValueTransforms")
        break

    dst = out_dir / f"start_{label}.als"
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
    xml_bytes = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    with gzip.open(dst, "wb") as f:
        f.write(xml_bytes.encode("utf-8"))
    return dst

def test_file(dst):
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
    subprocess.run(["taskkill", "/f", "/im", "Ableton Live 12 Standard.exe"], capture_output=True)
    time_mod.sleep(2)
    return crashed

tests = [
    # (events, label, description)
    ([(64.0, 0.2), (96.0, 1.0)], "at64", "First event at 64 (no anchor)"),
    ([(1.0, 0.5), (96.0, 1.0)], "at1", "First event at 1.0"),
    ([(0.1, 0.5), (96.0, 1.0)], "at0p1", "First event at 0.1"),
    ([(0.0, 0.5), (64.0, 0.2), (96.0, 1.0), (192.0, 0.2), (224.0, 1.0)], "anchor0", "Anchor at 0 + RISER data"),
    ([(-63072000, 0.85), (64.0, 0.2), (96.0, 1.0), (192.0, 0.2), (224.0, 1.0)], "sentinel", "Sentinel anchor + RISER data"),
]

print("=== FIRST-EVENT POSITION TESTS ===")
for events, label, desc in tests:
    dst = make_test(events, label)
    crashed = test_file(dst)
    status = "CRASH" if crashed else "OK"
    print(f"  {desc}: {status}")
