"""Binary search: which PluginDevice element causes 'invalid uuid string'?"""
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


def test_als(path, label):
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
    
    crash_kws = ["Fatal Error", "EXCEPTION_ACCESS_VIOLATION", "Unhandled exception", 
                 "invalid uuid", "is corrupt"]
    crashed = any(kw in new_log for kw in crash_kws)
    # Find specific error
    error_type = "OK"
    if "invalid uuid" in new_log:
        error_type = "INVALID_UUID"
    elif "is corrupt" in new_log:
        error_type = "CORRUPT"
    elif "Fatal Error" in new_log:
        error_type = "FATAL"
    
    print(f"  {label}: {error_type}")
    if crashed:
        for line in new_log.split("\n"):
            if "error:" in line.lower() or "fatal" in line.lower():
                print(f"    {line.strip()[:150]}")
    return not crashed


def inject(als_in, als_out, plugin_xml, next_pid_bump=10):
    with gzip.open(als_in, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()
    npid_elem = root.find(".//NextPointeeId")
    npid = int(npid_elem.get("Value"))
    npid_elem.set("Value", str(npid + next_pid_bump))
    
    track = list(root.iter("MidiTrack"))[0]
    outer_dc = track.find("DeviceChain")
    found_freeze = False
    for child in outer_dc:
        if child.tag == "FreezeSequencer":
            found_freeze = True
        elif child.tag == "DeviceChain" and found_freeze:
            inner_dc = child
            break
    devices = inner_dc.find("Devices")
    if devices is None:
        devices = ET.SubElement(inner_dc, "Devices")
    devices.append(ET.fromstring(plugin_xml.replace("ATID", str(npid))))
    
    with gzip.open(als_out, "wb") as f:
        tree.write(f, xml_declaration=True, encoding="UTF-8")


# Test variants
VARIANTS = {
    # A: Full PluginDevice (known crash)
    "A_full": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
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

    # B: Empty PluginDesc (no Vst3PluginInfo at all)
    "B_empty_desc": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc />
<Name Value="" /><ParameterList />
</PluginDevice>""",

    # C: Vst3PluginInfo but NO Uid element
    "C_no_uid": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>""",

    # D: Uid with Splice CID (known loaded plugin from log: ABCDEF01-9182-FAEB-5370-6C6358793761)
    # CID bytes: AB CD EF 01 91 82 FA EB 53 70 6C 63 58 79 37 61
    # As signed int32 BE: -1412567295, -1853817109, 1400007779, 1484109665
    "D_splice_uid": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="-1412567295" /><Field2 Value="-1853817109" /><Field3 Value="1400007779" /><Field4 Value="1484109665" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="SpliceAbletonLive" /><Vendor Value="Splice" /><Category Value="Instrument" />
</Vst3PluginInfo></PluginDesc>
<Name Value="SpliceAbletonLive" /><ParameterList />
</PluginDevice>""",
}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else None
    
    if which and which in VARIANTS:
        tests = {which: VARIANTS[which]}
    elif which:
        print(f"Unknown: {which}. Available: {list(VARIANTS.keys())}")
        sys.exit(1)
    else:
        tests = VARIANTS
    
    for name, xml in tests.items():
        out = os.path.join(OUT_DIR, f"bisect_{name}.als")
        print(f"\n=== {name} ===")
        inject(INPUT, out, xml)
        test_als(out, name)
