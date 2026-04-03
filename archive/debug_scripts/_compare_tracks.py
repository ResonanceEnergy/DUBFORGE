"""Compare track structure: template vs generated."""
import gzip
import xml.etree.ElementTree as ET

TEMPLATE = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"

# Template - first AudioTrack  
with gzip.open(TEMPLATE, "rb") as f:
    tmpl = ET.fromstring(f.read())
tmpl_ls = tmpl.find("LiveSet")
tmpl_tracks = tmpl_ls.find("Tracks")

print("=== TEMPLATE AudioTrack structure ===")
for t in tmpl_tracks:
    if t.tag == "AudioTrack":
        print(f"AudioTrack Id={t.get('Id')} children:")
        for c in t:
            n = len(list(c))
            print(f"  {c.tag} ({n} children)")
        break

# Generated - first AudioTrack
with gzip.open("output/ableton/Wild_Ones_V9.als", "rb") as f:
    gen = ET.fromstring(f.read())
gen_ls = gen.find("LiveSet")
gen_tracks = gen_ls.find("Tracks")

print("\n=== GENERATED AudioTrack structure ===")
for t in gen_tracks:
    if t.tag == "AudioTrack":
        print(f"AudioTrack Id={t.get('Id')} children:")
        for c in t:
            n = len(list(c))
            print(f"  {c.tag} ({n} children)")
        break

# Compare DeviceChain children
print("\n=== TEMPLATE AudioTrack DeviceChain ===")
for t in tmpl_tracks:
    if t.tag == "AudioTrack":
        dc = t.find("DeviceChain")
        if dc is not None:
            for c in dc:
                n = len(list(c))
                print(f"  {c.tag} ({n} children)")
        break

print("\n=== GENERATED AudioTrack DeviceChain ===")
for t in gen_tracks:
    if t.tag == "AudioTrack":
        dc = t.find("DeviceChain")
        if dc is not None:
            for c in dc:
                n = len(list(c))
                print(f"  {c.tag} ({n} children)")
        break

# Check the MainTrack's Tempo in generated
print("\n=== GENERATED MainTrack Mixer/Tempo ===")
gen_mt = gen_ls.find("MainTrack")
tempo_el = gen_mt.find("DeviceChain/Mixer/Tempo")
if tempo_el is not None:
    manual = tempo_el.find("Manual")
    if manual is not None:
        print(f"Tempo Manual={manual.get('Value')}")
    else:
        print(f"Tempo element children:")
        for c in tempo_el:
            print(f"  {c.tag} = {c.get('Value', '')}")
else:
    print("No Tempo element found in MainTrack Mixer")

# Check return track sends matching
print("\n=== MainTrack Sends count ===")
sends = gen_mt.find("DeviceChain/Mixer/Sends")
if sends is not None:
    holders = list(sends)
    print(f"  SendHolders: {len(holders)}")
    for h in holders:
        print(f"    TrackSendHolder Id={h.get('Id')}")
