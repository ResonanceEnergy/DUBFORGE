"""Minimal test: inject a single PluginDevice into a working ALS and test."""
import gzip
import xml.etree.ElementTree as ET
import shutil
import subprocess
import time
import os
import sys

BASE = r"C:\dev\SuperAgency-Shared\repos\DUBFORGE"
INPUT = os.path.join(BASE, "output", "ableton", "Wild_Ones_V12.als")
OUTPUT_DIR = os.path.join(BASE, "output", "ableton", "test_bisect")
PREFS = r"C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences"
ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clear_crash_state():
    for fn in ("CrashDetection.cfg", "CrashRecoveryInfo.cfg"):
        p = os.path.join(PREFS, fn)
        if os.path.exists(p):
            os.remove(p)
    for d in ("Crash", "BaseFiles"):
        p = os.path.join(PREFS, d)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)


def test_als(path, label=""):
    clear_crash_state()
    proc = subprocess.Popen([ABLETON, path])
    time.sleep(18)
    log_path = os.path.join(PREFS, "Log.txt")
    with open(log_path, "r", errors="replace") as f:
        log = f.read()
    crashed = "Fatal Error" in log or "FatalError" in log
    if proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=10)
    result = "CRASH" if crashed else "OK"
    print(f"  {label}: {result}")
    if crashed:
        for line in log.split("\n"):
            if "error:" in line.lower() or "fatal" in line.lower():
                print(f"    LOG: {line.strip()}")
    return not crashed


def inject_plugin(als_path, out_path, plugin_xml_str):
    """Inject plugin XML into first MIDI track's inner DeviceChain/Devices."""
    with gzip.open(als_path, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()

    # Find first MidiTrack's inner DeviceChain > Devices
    midi_tracks = list(root.iter("MidiTrack"))
    if not midi_tracks:
        print("No MidiTrack found!")
        return False

    track = midi_tracks[0]
    # Navigate: MidiTrack > DeviceChain > ... > DeviceChain > Devices
    outer_dc = track.find("DeviceChain")
    inner_dc = outer_dc.find(".//DeviceChain/DeviceChain")
    if inner_dc is None:
        # Try direct path
        freeze = outer_dc.find("FreezeSequencer")
        inner_dc = None
        for child in outer_dc:
            if child.tag == "DeviceChain" and child is not outer_dc:
                inner_dc = child
                break
        if inner_dc is None:
            # After FreezeSequencer
            children = list(outer_dc)
            for i, ch in enumerate(children):
                if ch.tag == "FreezeSequencer":
                    for j in range(i+1, len(children)):
                        if children[j].tag == "DeviceChain":
                            inner_dc = children[j]
                            break
                    break

    if inner_dc is None:
        print("Could not find inner DeviceChain!")
        return False

    devices = inner_dc.find("Devices")
    if devices is None:
        devices = ET.SubElement(inner_dc, "Devices")

    # Inject plugin element
    plugin_elem = ET.fromstring(plugin_xml_str)
    devices.append(plugin_elem)

    with gzip.open(out_path, "wb") as f:
        tree.write(f, xml_declaration=True, encoding="UTF-8")
    return True


# ========================================================================
# Test variants
# ========================================================================
TESTS = {
    # Test 1: Ultra-minimal, just Vst3PluginInfo with Uid
    "minimal_uid_only": """<PluginDevice Id="100">
<LomId Value="0" />
<LomIdView Value="0" />
<IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="29901"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" />
<LastPresetRef><Value /></LastPresetRef>
<LockedScripts />
<IsFolded Value="false" />
<ShouldShowPresetName Value="true" />
<UserName Value="" />
<Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" />
<TransportFlags Value="7" />
<Uid><Fields>
<Field1 Value="1448297816" />
<Field2 Value="1718833267" />
<Field3 Value="1701999981" />
<Field4 Value="540147712" />
</Fields></Uid>
<DeviceType Value="1" />
<Name Value="Serum 2" />
<Vendor Value="Xfer Records" />
<Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" />
<ParameterList />
</PluginDevice>""",

    # Test 2: No PluginDesc — just empty PluginDevice shell
    "no_plugindesc": """<PluginDevice Id="100">
<LomId Value="0" />
<LomIdView Value="0" />
<IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="29901"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" />
<LastPresetRef><Value /></LastPresetRef>
<LockedScripts />
<IsFolded Value="false" />
<ShouldShowPresetName Value="true" />
<UserName Value="" />
<Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" />
<TransportFlags Value="7" />
<Uid><Fields>
<Field1 Value="0" />
<Field2 Value="0" />
<Field3 Value="0" />
<Field4 Value="0" />
</Fields></Uid>
<DeviceType Value="1" />
<Name Value="" />
<Vendor Value="" />
<Category Value="" />
</Vst3PluginInfo></PluginDesc>
<Name Value="" />
<ParameterList />
</PluginDevice>""",

    # Test 3: VstPluginInfo instead of Vst3PluginInfo (different format)
    "vst2_style": """<PluginDevice Id="100">
<LomId Value="0" />
<LomIdView Value="0" />
<IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="29901"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" />
<LastPresetRef><Value /></LastPresetRef>
<LockedScripts />
<IsFolded Value="false" />
<ShouldShowPresetName Value="true" />
<UserName Value="" />
<Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><VstPluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" />
<Path Value="" />
<PlugName Value="Serum 2" />
<UniqueId Value="0" />
<Inputs Value="0" />
<Outputs Value="2" />
</VstPluginInfo></PluginDesc>
<Name Value="Serum 2" />
<ParameterList />
</PluginDevice>""",
}

if __name__ == "__main__":
    if not os.path.exists(INPUT):
        print(f"Base file not found: {INPUT}")
        sys.exit(1)

    # First verify base file still loads
    print("=== Verifying base file (no plugins) ===")
    test_als(INPUT, "Wild_Ones_V12 (baseline)")

    for name, xml in TESTS.items():
        out = os.path.join(OUTPUT_DIR, f"plugin_test_{name}.als")
        print(f"\n=== Test: {name} ===")
        if inject_plugin(INPUT, out, xml):
            test_als(out, name)
        else:
            print(f"  SKIP: injection failed")
