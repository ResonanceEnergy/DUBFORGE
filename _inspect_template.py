"""Inspect Ableton factory template structure."""
import gzip
import xml.etree.ElementTree as ET

TEMPLATE = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"

with gzip.open(TEMPLATE, "rb") as f:
    root = ET.fromstring(f.read())

ls = root.find("LiveSet")
print("LiveSet children:")
for child in ls:
    attrs = " ".join(f'{k}="{v[:40]}"' for k, v in list(child.attrib.items())[:2])
    print(f"  <{child.tag} {attrs}/>")

print()

# MainTrack vs MasterTrack
mt = ls.find("MainTrack")
mt2 = ls.find("MasterTrack")
print(f"MainTrack found: {mt is not None}")
print(f"MasterTrack found: {mt2 is not None}")

# Template tempo
tempo = ls.find("Transport/Tempo/Manual")
if tempo is not None:
    print(f"Template tempo: {tempo.get('Value')}")

# ReturnTracks
rt = ls.find("ReturnTracks")
print(f"ReturnTracks section found: {rt is not None}")
if rt is not None:
    for child in rt:
        print(f"  <{child.tag} Id={child.get('Id')}/>")

# Tracks section
tracks = ls.find("Tracks")
if tracks is not None:
    print(f"\nTracks section ({len(list(tracks))} tracks):")
    for t in tracks:
        print(f"  <{t.tag} Id={t.get('Id')}/>")

# FileRef sample from template
print("\nMainTrack routing:")
audio_out = ls.find("MainTrack/DeviceChain/AudioOutputRouting/Target")
if audio_out is not None:
    print(f"  AudioOutputRouting Target: {audio_out.get('Value')}")

# Pre-hear track
ph = ls.find("PreHearTrack")
print(f"\nPreHearTrack found: {ph is not None}")

# SendsPre
sp = ls.find("SendsPre")
print(f"SendsPre found: {sp is not None}")
if sp is not None:
    for child in sp:
        print(f"  <{child.tag} Id={child.get('Id')} Value={child.get('Value')}/>")
