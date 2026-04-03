"""Check remaining template details."""
import gzip
import xml.etree.ElementTree as ET

TEMPLATE = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"
with gzip.open(TEMPLATE, "rb") as f:
    root = ET.fromstring(f.read())
ls = root.find("LiveSet")

# MidiTrack ControllerLayoutCustomization
tracks = ls.find("Tracks")
for t in tracks:
    if t.tag == "MidiTrack":
        clc = t.find("ControllerLayoutCustomization")
        if clc is not None:
            print("MidiTrack ControllerLayoutCustomization:")
            for c in clc:
                val = c.get("Value", "")
                print(f"  <{c.tag} Value=\"{val}\"/>")
        break

# MainTrack Sends
mt = ls.find("MainTrack")
sends = mt.find("DeviceChain/Mixer/Sends")
print(f"\nMainTrack Mixer Sends children: {len(list(sends))}")
for s in sends:
    print(f"  tag={s.tag}")

# Check ReturnTrack DeviceChain/DeviceChain/Devices
print("\nReturnTrack Devices:")
for t in tracks:
    if t.tag == "ReturnTrack":
        devices = t.find("DeviceChain/DeviceChain/Devices")
        if devices is not None:
            for d in devices:
                print(f"  <{d.tag}> (children={len(list(d))})")
        else:
            print("  No Devices element")
        
        # Check full ReturnTrack children
        print(f"\nReturnTrack children:")
        for c in t:
            print(f"  {c.tag}")
        break

# Check FreezeSequencer difference on return tracks 
print("\nReturnTrack FreezeSequencer:")
for t in tracks:
    if t.tag == "ReturnTrack":
        fs = t.find("DeviceChain/FreezeSequencer")
        if fs is not None:
            print("  Children:")
            for c in fs:
                print(f"    {c.tag} (children={len(list(c))})")
                if c.tag == "ClipSlotList":
                    for cs in c:
                        print(f"      {cs.tag}")
        break
