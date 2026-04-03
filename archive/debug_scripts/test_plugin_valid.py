"""Inject one PluginDevice with VALID IDs into V12 and test.
Must update NextPointeeId to cover the injected AutomationTarget."""
import gzip
import xml.etree.ElementTree as ET
import os
import sys
import subprocess
import time
import shutil

BASE = r"C:\dev\SuperAgency-Shared\repos\DUBFORGE"
INPUT = os.path.join(BASE, "output", "ableton", "Wild_Ones_V12.als")
OUT_DIR = os.path.join(BASE, "output", "ableton", "test_bisect")
ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")
os.makedirs(OUT_DIR, exist_ok=True)


def test_als(path):
    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
    time.sleep(2)
    for f in ("CrashDetection.cfg", "CrashRecoveryInfo.cfg"):
        try: os.remove(os.path.join(PREFS, f))
        except OSError: pass
    for d in ("Crash", "BaseFiles"):
        p = os.path.join(PREFS, d)
        if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True)
    log_start = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
    proc = subprocess.Popen([ABLETON, path])
    time.sleep(20)
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        f.seek(log_start)
        new_log = f.read()
    if proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=10)
        except: pass
    # Print relevant lines
    for line in new_log.split("\n"):
        line = line.strip()
        if any(k in line.lower() for k in ["fatal", "exception", "error:", "loading doc",
                                             "loaded doc", "invalid", "corrupt"]):
            print(f"  LOG: {line[:200]}")
    crashed = any(kw in new_log for kw in
                  ["Fatal Error", "EXCEPTION_ACCESS_VIOLATION",
                   "Unhandled exception", "invalid uuid", "is corrupt"])
    return not crashed


def inject_plugin_proper(als_in, als_out, auto_target_id):
    """Inject PluginDevice with proper IDs."""
    with gzip.open(als_in, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()

    # Get current NextPointeeId
    npid_elem = root.find(".//NextPointeeId")
    current_npid = int(npid_elem.get("Value"))
    print(f"  Current NextPointeeId: {current_npid}")

    # Use an ID just below current NextPointeeId
    at_id = auto_target_id if auto_target_id else current_npid
    new_npid = max(current_npid, at_id + 10)
    npid_elem.set("Value", str(new_npid))
    print(f"  AutomationTarget Id: {at_id}")
    print(f"  New NextPointeeId: {new_npid}")

    track = list(root.iter("MidiTrack"))[0]
    outer_dc = track.find("DeviceChain")
    found_freeze = False
    inner_dc = None
    for child in outer_dc:
        if child.tag == "FreezeSequencer":
            found_freeze = True
        elif child.tag == "DeviceChain" and found_freeze:
            inner_dc = child
            break

    devices = inner_dc.find("Devices")
    if devices is None:
        devices = ET.SubElement(inner_dc, "Devices")

    # Build PluginDevice with proper ID
    xml_str = f"""<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="{at_id}"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>"""

    devices.append(ET.fromstring(xml_str))

    with gzip.open(als_out, "wb") as f:
        tree.write(f, xml_declaration=True, encoding="UTF-8")
    return True


if __name__ == "__main__":
    out = os.path.join(OUT_DIR, "plugin_valid_ids.als")
    print("Injecting PluginDevice with valid IDs...")
    # Read current NextPointeeId from V12
    with gzip.open(INPUT, "rb") as f:
        tree = ET.parse(f)
    npid = int(tree.getroot().find(".//NextPointeeId").get("Value"))
    inject_plugin_proper(INPUT, out, npid)
    print(f"\nTesting {out}...")
    ok = test_als(out)
    print(f"\nRESULT: {'OK' if ok else 'CRASH'}")
