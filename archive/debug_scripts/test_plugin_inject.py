"""Inject one PluginDevice variant into V12 and test with _quick_test logic."""
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
    """Return True if loads OK, False if crashed."""
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

    crashed = any(kw in new_log for kw in
                  ["Fatal Error", "EXCEPTION_ACCESS_VIOLATION",
                   "Unhandled exception", "invalid uuid"])

    if proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=10)
        except: pass

    for line in new_log.split("\n"):
        line = line.strip()
        if any(k in line.lower() for k in ["fatal", "exception", "error:", "loading doc", "loaded doc", "invalid"]):
            print(f"  LOG: {line[:200]}")

    return not crashed


def inject_into_first_midi(als_in, als_out, plugin_xml_str):
    with gzip.open(als_in, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()
    track = list(root.iter("MidiTrack"))[0]
    outer_dc = track.find("DeviceChain")
    # Find inner DeviceChain (after FreezeSequencer)
    inner_dc = None
    found_freeze = False
    for child in outer_dc:
        if child.tag == "FreezeSequencer":
            found_freeze = True
        elif child.tag == "DeviceChain" and found_freeze:
            inner_dc = child
            break
    if inner_dc is None:
        print("ERROR: Can't find inner DeviceChain")
        return False
    devices = inner_dc.find("Devices")
    if devices is None:
        devices = ET.SubElement(inner_dc, "Devices")
    plugin_elem = ET.fromstring(plugin_xml_str)
    devices.append(plugin_elem)
    with gzip.open(als_out, "wb") as f:
        tree.write(f, xml_declaration=True, encoding="UTF-8")
    return True


# The variant to test — pass variant name as argument
VARIANTS = {
    "full_serum2": """<PluginDevice Id="100">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="29901"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>""",

    "zeroed_uid": """<PluginDevice Id="100">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="29901"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="0" /><Field2 Value="0" /><Field3 Value="0" /><Field4 Value="0" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="" /><Vendor Value="" /><Category Value="" />
</Vst3PluginInfo></PluginDesc>
<Name Value="" /><ParameterList />
</PluginDevice>""",

    "no_plugin_device": "",  # empty — just test baseline
}

if __name__ == "__main__":
    variant = sys.argv[1] if len(sys.argv) > 1 else "full_serum2"

    if variant not in VARIANTS:
        print(f"Unknown variant: {variant}")
        print(f"Available: {list(VARIANTS.keys())}")
        sys.exit(1)

    xml_str = VARIANTS[variant]
    out_path = os.path.join(OUT_DIR, f"plugin_{variant}.als")

    if variant == "no_plugin_device":
        # Just test the base file
        print(f"Testing baseline (no injection)...")
        ok = test_als(INPUT)
    else:
        print(f"Injecting variant '{variant}' into first MIDI track...")
        if not inject_into_first_midi(INPUT, out_path, xml_str):
            sys.exit(1)
        print(f"Testing {out_path}...")
        ok = test_als(out_path)

    print(f"\nRESULT: {'OK' if ok else 'CRASH'}")
