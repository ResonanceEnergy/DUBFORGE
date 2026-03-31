"""Deep inspection of generated Wild_Ones_V9.als vs factory template."""
import gzip
import xml.etree.ElementTree as ET

# Load generated ALS
with gzip.open("output/ableton/Wild_Ones_V9.als", "rb") as f:
    gen_root = ET.fromstring(f.read())

gen_ls = gen_root.find("LiveSet")

print("=== GENERATED ALS ===")
print(f"Root tag: {gen_root.tag}")
print(f"  MajorVersion={gen_root.get('MajorVersion')}")
print(f"  MinorVersion={gen_root.get('MinorVersion')}")
print(f"  Creator={gen_root.get('Creator')}")
print()

print("LiveSet children (in order):")
for child in gen_ls:
    tag = child.tag
    val = child.get("Value", "")
    if val:
        print(f"  <{tag} Value={repr(val[:50])}/>")
    else:
        n = len(list(child))
        print(f"  <{tag}/> ({n} children)")
print()

# Check MainTrack vs MasterTrack
mt = gen_ls.find("MainTrack")
mt2 = gen_ls.find("MasterTrack")
print(f"MainTrack found: {mt is not None}")
print(f"MasterTrack found: {mt2 is not None}")

# Tempo
for path in ["Transport/Tempo/Manual", "Tempo/Manual"]:
    el = gen_ls.find(path)
    if el is not None:
        print(f"Tempo ({path}): {el.get('Value')}")

# Tracks
tracks = gen_ls.find("Tracks")
if tracks is not None:
    print(f"\nTracks ({len(list(tracks))}):")
    for t in tracks:
        name_el = t.find("Name/EffectiveName")
        name = name_el.get("Value") if name_el is not None else "?"
        print(f"  <{t.tag} Id={t.get('Id')}> name={name}")

# Check first audio track's FileRef
print("\n=== FileRef sample (first audio track) ===")
for t in tracks:
    if t.tag == "AudioTrack":
        # Find SampleRef/FileRef
        for fr in t.iter("FileRef"):
            rpt = fr.find("RelativePathType")
            rp = fr.find("RelativePath")
            p = fr.find("Path")
            print(f"  RelativePathType: {rpt.get('Value') if rpt is not None else 'MISSING'}")
            print(f"  RelativePath: {rp.get('Value')[:80] if rp is not None else 'MISSING'}")
            print(f"  Path: {p.get('Value')[:80] if p is not None else 'MISSING'}")
            break
        break

# Check if PreHearTrack exists
ph = gen_ls.find("PreHearTrack")
print(f"\nPreHearTrack found: {ph is not None}")

# Check SendsPre
sp = gen_ls.find("SendsPre")
print(f"SendsPre found: {sp is not None}")
if sp is not None:
    print(f"  SendsPre children: {len(list(sp))}")

# Check NextPointeeId
npi = gen_ls.find("NextPointeeId")
print(f"NextPointeeId: {npi.get('Value') if npi is not None else 'MISSING'}")

# Compare element ORDER vs template
print("\n=== Element order comparison ===")
TEMPLATE = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"
with gzip.open(TEMPLATE, "rb") as f:
    tmpl_root = ET.fromstring(f.read())
tmpl_ls = tmpl_root.find("LiveSet")

tmpl_order = [c.tag for c in tmpl_ls]
gen_order = [c.tag for c in gen_ls]

print("Template element order:")
for i, tag in enumerate(tmpl_order):
    marker = " <<< MISSING" if tag not in gen_order else ""
    print(f"  {i:2d}. {tag}{marker}")

print(f"\nGenerated has {len(gen_order)} elements, template has {len(tmpl_order)} elements")

# Check for elements in generated but not template
gen_only = [t for t in gen_order if t not in tmpl_order]
if gen_only:
    print(f"Elements in generated but NOT in template: {gen_only}")

tmpl_only = [t for t in tmpl_order if t not in gen_order]
if tmpl_only:
    print(f"Elements in template but NOT in generated: {tmpl_only}")
