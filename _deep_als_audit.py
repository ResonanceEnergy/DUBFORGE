"""Deep structural audit of the ALS file against Ableton Live 12 schema."""
import gzip
import xml.etree.ElementTree as ET
import sys

ALS_PATH = "output/ableton/Wild_Ones_V6.als"

with gzip.open(ALS_PATH, "rb") as f:
    xml_bytes = f.read()
xml_str = xml_bytes.decode("utf-8")
root = ET.fromstring(xml_str)

print("=" * 60)
print("DEEP ALS AUDIT")
print("=" * 60)

# 1. Root element
print(f"\n[1] Root: <{root.tag}> attribs={root.attrib}")
ls = root.find("LiveSet")
if ls is None:
    print("FATAL: No <LiveSet> element!")
    sys.exit(1)

# 2. LiveSet top-level children
ls_children = [c.tag for c in ls]
print(f"\n[2] LiveSet children ({len(ls_children)}): {ls_children}")

# 3. Required LiveSet children (from real Ableton 12 files)
REQUIRED_LS = [
    "NextPointeeId", "OverwriteProtectionNumber", "LomId", "LomIdView",
    "Tracks", "MasterTrack", "Scenes", "Transport", "SongMasterValues",
    "GlobalQuantisation", "AutoQuantisation", "Grid", "ScaleInformation",
    "InPointee", "OutPointee", "SendsPre", "Locators", "DetailClipKeyMidis",
    "TracksListWrapper", "VisibleTracksListWrapper", "ReturnTracksListWrapper",
    "ScenesListWrapper", "CuePointsListWrapper", "ChooserBar",
    "Annotation", "SoloOrPflSavedValue", "SoloAuditioningEnabled",
    "IsContentSelected", "ViewStateSessionMixerHeight",
    "ViewStateSessionTrackSheetMixerHeight",
    "ViewStateSmpteTimecodeFormat", "ViewStateSessionTrackSheetViewData",
    "CrossfadeCurve", "TempoWriteMode", "TimeSelection",
    "SequencerNavigator", "ViewStateDetailIsSample", "ContentLanes",
    "SignalTracing", "CompactArrangerControlBar", "CompactSessionControlBar",
]

print("\n[3] Missing required LiveSet children:")
missing_count = 0
for tag in REQUIRED_LS:
    if ls.find(tag) is None:
        print(f"  MISSING: <{tag}>")
        missing_count += 1
if missing_count == 0:
    print("  None — all present!")
else:
    print(f"  Total missing: {missing_count}")

# 4. NextPointeeId
npi = ls.find("NextPointeeId")
if npi is not None:
    print(f"\n[4] NextPointeeId Value={npi.get('Value')}")
else:
    print("\n[4] NextPointeeId: MISSING (critical!)")

# 5. Tracks
tracks_el = ls.find("Tracks")
if tracks_el is not None:
    audio = tracks_el.findall("AudioTrack")
    midi = tracks_el.findall("MidiTrack")
    ret = tracks_el.findall("ReturnTrack")
    print(f"\n[5] Tracks: {len(audio)} Audio, {len(midi)} MIDI, {len(ret)} Return")
else:
    print("\n[5] Tracks: MISSING!")

# 6. Check first AudioTrack deeply
if audio:
    t = audio[0]
    print(f"\n[6] First AudioTrack (Id={t.get('Id')}) children: {[c.tag for c in t]}")
    dc = t.find("DeviceChain")
    if dc:
        print(f"  DeviceChain children: {[c.tag for c in dc]}")
        ms = dc.find(".//MainSequencer")
        if ms:
            print(f"  MainSequencer children: {[c.tag for c in ms]}")
            ct = ms.find("ClipTimeable")
            if ct:
                aa = ct.find("ArrangerAutomation")
                if aa:
                    events = aa.find("Events")
                    clips = list(events) if events is not None else []
                    print(f"  ArrangerAutomation Events: {len(clips)} clips")
                    if clips:
                        c0 = clips[0]
                        print(f"    First clip: <{c0.tag}> attribs={dict(c0.attrib)}")
                        print(f"    Clip children: {[ch.tag for ch in c0]}")
                        # Check critical AudioClip fields
                        for field in ["Time", "LomId", "CurrentStart", "CurrentEnd",
                                      "Loop", "Name", "ColorIndex", "SampleRef", "WarpMode",
                                      "WarpMarkers", "SavedWarpMarkersForStretched",
                                      "MarkersGenerated", "IsSongTempoMaster"]:
                            el = c0.find(field)
                            if el is not None:
                                val = el.get("Value", el.text)
                                print(f"      {field}: {val}")
                            else:
                                print(f"      {field}: MISSING!")

# 7. MasterTrack structure
print(f"\n[7] MasterTrack structure:")
mt = ls.find("MasterTrack")
if mt is not None:
    print(f"  Children: {[c.tag for c in mt]}")
    mt_dc = mt.find("DeviceChain")
    if mt_dc:
        print(f"  DeviceChain children: {[c.tag for c in mt_dc]}")
        # Does master have MainSequencer?
        mt_ms = mt_dc.find("MainSequencer")
        if mt_ms:
            print("  MainSequencer: PRESENT")
        else:
            print("  MainSequencer: MISSING (normal for master)")

# 8. Check Transport
transport = ls.find("Transport")
if transport:
    print(f"\n[8] Transport children: {[c.tag for c in transport]}")
else:
    print("\n[8] Transport: MISSING!")

# 9. Verify all Pointee IDs are referenced by NextPointeeId
all_pointees = root.findall(".//{http://www.w3.org/1999/xhtml}Pointee") or root.findall(".//Pointee")
pointee_ids = [int(p.get("Id", 0)) for p in all_pointees if p.get("Id")]
if pointee_ids:
    max_pointee = max(pointee_ids)
    npi_val = int(npi.get("Value")) if npi is not None else 0
    print(f"\n[9] Pointee IDs: min={min(pointee_ids)}, max={max_pointee}, count={len(pointee_ids)}")
    print(f"    NextPointeeId={npi_val}")
    if npi_val <= max_pointee:
        print(f"    WARNING: NextPointeeId ({npi_val}) <= max Pointee ({max_pointee})!")
    else:
        print(f"    OK: NextPointeeId > max Pointee")

# 10. Check AutomationTarget IDs don't collide with Pointee IDs
all_at = root.findall(".//AutomationTarget")
all_mt = root.findall(".//ModulationTarget")
at_ids = set(int(a.get("Id")) for a in all_at if a.get("Id"))
mt_ids = set(int(m.get("Id")) for m in all_mt if m.get("Id"))
pt_ids = set(pointee_ids)
print(f"\n[10] ID ranges:")
print(f"  AutomationTarget: {min(at_ids)}-{max(at_ids)} ({len(at_ids)} unique)")
print(f"  ModulationTarget: {min(mt_ids)}-{max(mt_ids)} ({len(mt_ids)} unique)")
print(f"  Pointee: {min(pt_ids)}-{max(pt_ids)} ({len(pt_ids)} unique)")
all_ids = at_ids | mt_ids | pt_ids
print(f"  Combined unique: {len(all_ids)} (sum={len(at_ids)+len(mt_ids)+len(pt_ids)})")
if len(all_ids) < len(at_ids) + len(mt_ids) + len(pt_ids):
    overlap = (at_ids & mt_ids) | (at_ids & pt_ids) | (mt_ids & pt_ids)
    print(f"  COLLISION! Overlapping IDs: {overlap}")
else:
    print(f"  OK: No collisions between AT, MT, and Pointee IDs")

# Also check ControllerTargets IDs
ct_elements = []
for tag_name in root.iter():
    if "ControllerTargets" in tag_name.tag:
        ct_elements.append(tag_name)
ct_ids = set(int(c.get("Id")) for c in ct_elements if c.get("Id"))
if ct_ids:
    print(f"  ControllerTargets: {min(ct_ids)}-{max(ct_ids)} ({len(ct_ids)} unique)")
    all_ids2 = all_ids | ct_ids
    if len(all_ids2) < len(all_ids) + len(ct_ids):
        overlap2 = all_ids & ct_ids
        print(f"  COLLISION with ControllerTargets! Overlapping: {sorted(overlap2)[:20]}")
    else:
        print(f"  OK: No collisions with ControllerTargets")

# 11. Check NextPointeeId vs ALL ID types
all_numbered = at_ids | mt_ids | pt_ids | ct_ids
max_any = max(all_numbered) if all_numbered else 0
print(f"\n[11] Global max ID: {max_any}, NextPointeeId: {npi_val if npi is not None else 'MISSING'}")
if npi is not None and int(npi.get("Value")) <= max_any:
    print(f"  CRITICAL: NextPointeeId must be > {max_any}!")

# 12. Check AudioClip SampleRef paths
print(f"\n[12] AudioClip SampleRef check:")
for clip in root.iter("AudioClip"):
    name_el = clip.find(".//Name/EffectiveName")
    name = name_el.get("Value", "?") if name_el is not None else "?"
    sr = clip.find(".//SampleRef")
    if sr is not None:
        fr = sr.find(".//FileRef")
        if fr is not None:
            rel_path = fr.find("RelativePath")
            path_el = fr.find("Path")
            name_el2 = fr.find("Name")
            has_data = fr.find("Data")
            print(f"  {name}: Path={path_el.get('Value') if path_el is not None else 'NONE'}, "
                  f"Name={name_el2.get('Value') if name_el2 is not None else 'NONE'}, "
                  f"HasData={'yes' if has_data is not None else 'no'}")
            # Check RelativePath
            if rel_path is not None:
                rp_children = list(rel_path)
                print(f"    RelativePath: {len(rp_children)} elements")
                for rpc in rp_children[:3]:
                    print(f"      {rpc.tag} Dir={rpc.get('Dir')}")
        else:
            print(f"  {name}: NO FileRef!")
    else:
        print(f"  {name}: NO SampleRef!")

# 13. Check Locator Times are within song range
print(f"\n[13] Locator check:")
for loc in root.iter("Locator"):
    time_el = loc.find("Time")
    name_el = loc.find("Name/Value")
    t = float(time_el.get("Value")) if time_el is not None else -1
    n = name_el.get("Value") if name_el is not None else "?"
    print(f"  {n}: time={t}")

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
