"""Find where Tempo element lives in template and generated ALS."""
import gzip
import xml.etree.ElementTree as ET

TEMPLATE = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"

# Template
with gzip.open(TEMPLATE, "rb") as f:
    root = ET.fromstring(f.read())

print("=== TEMPLATE: all <Tempo> elements ===")
for el in root.iter("Tempo"):
    manual = el.find("Manual")
    manual_val = manual.get("Value") if manual is not None else None
    val = el.get("Value", "")
    n = len(list(el))
    print(f"  <Tempo> Value={repr(val)} Manual={manual_val} children={n}")

# Also check MasterTrack/MainTrack
ls = root.find("LiveSet")
mt = ls.find("MainTrack")
if mt is not None:
    print("\nMainTrack DeviceChain children:")
    dc = mt.find("DeviceChain")
    if dc is not None:
        for c in dc:
            print(f"  {c.tag}")
    # Check mixer
    mixer = mt.find("DeviceChain/Mixer")
    if mixer is not None:
        tempo = mixer.find("Tempo")
        if tempo is not None:
            manual = tempo.find("Manual")
            print(f"\nMainTrack/DeviceChain/Mixer/Tempo Manual={manual.get('Value') if manual else 'N/A'}")

# Generated
print("\n=== GENERATED: all <Tempo> elements ===")
with gzip.open("output/ableton/Wild_Ones_V9.als", "rb") as f:
    gen = ET.fromstring(f.read())
for el in gen.iter("Tempo"):
    manual = el.find("Manual")
    manual_val = manual.get("Value") if manual is not None else None
    val = el.get("Value", "")
    print(f"  <Tempo> Value={repr(val)} Manual={manual_val}")

# Check MainTrack Mixer Tempo in generated
gen_ls = gen.find("LiveSet")
gen_mt = gen_ls.find("MainTrack")
if gen_mt:
    mixer = gen_mt.find("DeviceChain/Mixer")
    if mixer:
        for c in mixer:
            print(f"  MainTrack Mixer child: {c.tag}")
