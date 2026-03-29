"""Extract default ALS template structure."""
import gzip, xml.etree.ElementTree as ET, xml.dom.minidom

REF = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"
with gzip.open(REF, "rb") as f:
    xml_bytes = f.read()

root = ET.fromstring(xml_bytes.decode("utf-8"))
print("ROOT:", root.tag, root.attrib)

ls = root.find("LiveSet")
print(f"\nLiveSet children ({len(list(ls))}):")
for c in ls:
    val = c.get("Value", "")
    kids = len(list(c))
    if val:
        print(f"  <{c.tag} Value=\"{val}\" />")
    elif kids == 0:
        print(f"  <{c.tag} />")
    else:
        print(f"  <{c.tag}> ({kids} children)")

# Print the elements we're missing (non-track, non-scene)
print("\n\n=== MISSING ELEMENTS (full XML) ===\n")
NEED = [
    "SongMasterValues", "GlobalQuantisation", "AutoQuantisation", "Grid",
    "ScaleInformation", "InPointee", "OutPointee", "SendsPre",
    "DetailClipKeyMidis", "TracksListWrapper", "VisibleTracksListWrapper",
    "ReturnTracksListWrapper", "ScenesListWrapper", "CuePointsListWrapper",
    "ChooserBar", "SoloOrPflSavedValue", "SoloAuditioningEnabled",
    "IsContentSelected", "ViewStateSessionMixerHeight",
    "ViewStateSessionTrackSheetMixerHeight",
    "ViewStateSmpteTimecodeFormat", "ViewStateSessionTrackSheetViewData",
    "CrossfadeCurve", "TempoWriteMode", "TimeSelection",
    "SequencerNavigator", "ViewStateDetailIsSample", "ContentLanes",
    "SignalTracing", "CompactArrangerControlBar", "CompactSessionControlBar",
]

for tag in NEED:
    el = ls.find(tag)
    if el is not None:
        raw = ET.tostring(el, encoding="unicode")
        # Pretty print if short enough
        if len(raw) < 2000:
            try:
                pretty = xml.dom.minidom.parseString(raw).toprettyxml(indent="  ")
                # Remove xml declaration line
                pretty = "\n".join(pretty.split("\n")[1:])
                print(f"--- {tag} ---")
                print(pretty)
            except:
                print(f"--- {tag} ---")
                print(raw)
        else:
            print(f"--- {tag} --- (truncated, {len(raw)} chars)")
            print(raw[:500] + "...")
    else:
        print(f"--- {tag} --- NOT FOUND in default template either")

# Also check Transport structure
print("\n\n=== TRANSPORT (default) ===")
transport = ls.find("Transport")
if transport:
    raw = ET.tostring(transport, encoding="unicode")
    print(f"({len(raw)} chars)")

# Check MasterTrack extras
print("\n\n=== MasterTrack children ===")
mt = ls.find("MasterTrack")
if mt:
    for c in mt:
        print(f"  <{c.tag}>")

# Check AudioClip structure from Sample Reference
print("\n\n=== SAMPLE REFERENCE ALS (first AudioClip) ===")
REF2 = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Core Library\Ableton Folder Info\Sample Reference.als"
try:
    with gzip.open(REF2, "rb") as f:
        xml2 = f.read().decode("utf-8")
    root2 = ET.fromstring(xml2)
    clip = root2.find(".//AudioClip")
    if clip:
        print(f"AudioClip attribs: {dict(clip.attrib)}")
        print(f"AudioClip children: {[c.tag for c in clip]}")
        # Show each child's value or children count
        for c in clip:
            val = c.get("Value", "")
            kids = len(list(c))
            if val:
                print(f"    <{c.tag} Value=\"{val}\" />")
            elif kids:
                print(f"    <{c.tag}> ({kids} children)")
            else:
                print(f"    <{c.tag} />")
except Exception as e:
    print(f"Error: {e}")
