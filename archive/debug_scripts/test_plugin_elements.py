"""Test additional Vst3PluginInfo elements that Ableton might require."""
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
    error_type = "OK"
    if "invalid uuid" in new_log:
        error_type = "INVALID_UUID"
    elif "is corrupt" in new_log:
        error_type = "CORRUPT"
    elif "Fatal Error" in new_log or "EXCEPTION_ACCESS" in new_log:
        error_type = "FATAL"
    print(f"  {label}: {error_type}")
    if error_type != "OK":
        for line in new_log.split("\n"):
            if "error:" in line.lower() or "fatal" in line.lower():
                print(f"    {line.strip()[:180]}")
    return error_type == "OK"


def inject(als_in, als_out, plugin_xml):
    with gzip.open(als_in, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()
    npid_elem = root.find(".//NextPointeeId")
    npid = int(npid_elem.get("Value"))
    npid_elem.set("Value", str(npid + 10))
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


# Test variants — each adds different elements
VARIANTS = {
    # E: Add DevIdentifier (the string from PluginScanDb)
    "E_dev_identifier": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
<DevIdentifier Value="device:vst3:instr:56534558-6673-5073-6572-756d20320000" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>""",

    # F: Add Flags element (from PluginScanDb: Flags=1)
    "F_flags_inputs_outputs": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
<Flags Value="1" />
<NumberOfInputs Value="0" />
<NumberOfOutputs Value="2" />
<SdkVersion Value="VST 3.7.12" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>""",

    # G: Add OverriddenPersistentDeviceId with UUID
    "G_persistent_id": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<OverriddenPersistentDeviceId Value="device:vst3:instr:56534558-6673-5073-6572-756d20320000" />
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>""",

    # H: Add both OverriddenPersistentDeviceId and Preset/Buffer elements
    "H_with_preset": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<OverriddenPersistentDeviceId Value="device:vst3:instr:56534558-6673-5073-6572-756d20320000" />
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Preset><Value /></Preset>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>""",

    # I: Kitchen sink — all possible elements
    "I_kitchen_sink": """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="ATID"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<OverriddenPersistentDeviceId Value="device:vst3:instr:56534558-6673-5073-6572-756d20320000" />
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
<Flags Value="1" />
<DevIdentifier Value="device:vst3:instr:56534558-6673-5073-6572-756d20320000" />
</Vst3PluginInfo></PluginDesc>
<Preset><Value /></Preset>
<Name Value="Serum 2" />
<ParameterList />
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
