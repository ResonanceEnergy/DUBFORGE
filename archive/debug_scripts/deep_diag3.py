"""Compare detailed element ordering and structure between V12 and template."""
import gzip
import xml.etree.ElementTree as ET

with gzip.open('output/ableton/Wild_Ones_V12.als', 'rb') as f:
    v12 = ET.fromstring(f.read())
with gzip.open(
    r'C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences'
    r'\Crash\2026_03_28__01_12_39_BaseFiles\DefaultLiveSet.als', 'rb'
) as f:
    tmpl = ET.fromstring(f.read())

ls = v12.find('LiveSet')
ls_t = tmpl.find('LiveSet')

print("=" * 70)
print("1. MIDI TRACK CHILD ORDER COMPARISON")
print("=" * 70)
v12_mt = v12.find('.//MidiTrack')
tmpl_mt = tmpl.find('.//MidiTrack')
print(f"V12 MidiTrack children: {[c.tag for c in v12_mt]}")
print(f"TMPL MidiTrack children: {[c.tag for c in tmpl_mt]}")

print("\n" + "=" * 70)
print("2. TEMPLATE SCENE FULL XML (first scene)")
print("=" * 70)
tmpl_scenes = ls_t.find("Scenes")
if tmpl_scenes is not None:
    first_scene = list(tmpl_scenes)[0]
    for el in first_scene:
        val = el.get("Value", "")
        children = [c.tag for c in el]
        if children:
            print(f"  <{el.tag}> children: {children}")
            for c in el:
                cv = c.get("Value", "")
                cc = [x.tag for x in c]
                if cc:
                    print(f"    <{c.tag}> children: {cc}")
                    for x in c:
                        xv = x.get("Value", "")
                        print(f"      <{x.tag} Value=\"{xv}\"/>")
                else:
                    print(f"    <{c.tag} Value=\"{cv}\"/>")
        else:
            print(f"  <{el.tag} Value=\"{val}\"/>")

print("\n" + "=" * 70)
print("3. V12 SCENE FULL XML (first scene)")
print("=" * 70)
v12_scenes = ls.find("Scenes")
if v12_scenes is not None:
    first_scene = list(v12_scenes)[0]
    for el in first_scene:
        val = el.get("Value", "")
        children = [c.tag for c in el]
        if children:
            print(f"  <{el.tag}> children: {children}")
            for c in el:
                cv = c.get("Value", "")
                print(f"    <{c.tag} Value=\"{cv}\"/>")
        else:
            print(f"  <{el.tag} Value=\"{val}\"/>")

print("\n" + "=" * 70)
print("4. MAINTRACK DEVCHAIN/MIXER STRUCTURE")
print("=" * 70)
mt = ls.find("MainTrack")
mt_t = ls_t.find("MainTrack")
if mt is not None:
    print("V12 MainTrack children:", [c.tag for c in mt])
    dc = mt.find("DeviceChain")
    if dc:
        print("V12 MainTrack/DeviceChain children:", [c.tag for c in dc])
        mixer = dc.find("Mixer")
        if mixer:
            print("V12 MainTrack/Mixer children:", [c.tag for c in mixer])
if mt_t is not None:
    print("TMPL MainTrack children:", [c.tag for c in mt_t])
    dc = mt_t.find("DeviceChain")
    if dc:
        print("TMPL MainTrack/DeviceChain children:", [c.tag for c in dc])
        mixer = dc.find("Mixer")
        if mixer:
            print("TMPL MainTrack/Mixer children:", [c.tag for c in mixer])

print("\n" + "=" * 70)
print("5. V12 MidiTrack DeviceChain FULL STRUCTURE")
print("=" * 70)
v12_dc = v12_mt.find("DeviceChain")
tmpl_dc = tmpl_mt.find("DeviceChain")
print(f"V12 DC children: {[c.tag for c in v12_dc]}")
print(f"TMPL DC children: {[c.tag for c in tmpl_dc]}")
# Compare MainSequencer children
v12_ms = v12_dc.find("MainSequencer")
tmpl_ms = tmpl_dc.find("MainSequencer")
if v12_ms is not None:
    print(f"\nV12 MainSequencer children: {[c.tag for c in v12_ms]}")
if tmpl_ms is not None:
    print(f"TMPL MainSequencer children: {[c.tag for c in tmpl_ms]}")

# Compare FreezeSequencer children
v12_fs = v12_dc.find("FreezeSequencer")
tmpl_fs = tmpl_dc.find("FreezeSequencer")
if v12_fs is not None:
    print(f"\nV12 FreezeSequencer children: {[c.tag for c in v12_fs]}")
if tmpl_fs is not None:
    print(f"TMPL FreezeSequencer children: {[c.tag for c in tmpl_fs]}")

print("\n" + "=" * 70)
print("6. CHECK TEMPLATE MainTrack NextPointeeId")
print("=" * 70)
print(f"V12 NextPointeeId: {ls.find('NextPointeeId').get('Value')}")
print(f"TMPL NextPointeeId: {ls_t.find('NextPointeeId').get('Value')}")

# Check if MainTrack's AutomationTarget IDs are within range
for at in mt_t.iter("AutomationTarget"):
    print(f"  TMPL MainTrack AutomationTarget Id={at.get('Id')}")
for at in mt.iter("AutomationTarget"):
    print(f"  V12 MainTrack AutomationTarget Id={at.get('Id')}")

print("\n" + "=" * 70)
print("7. V12 MAINSEQUENCER ClipSlotList")
print("=" * 70)
csl = v12_ms.find("ClipSlotList")
if csl is not None:
    slots = list(csl)
    print(f"V12 ClipSlot count: {len(slots)}")
    if slots:
        first_slot = slots[0]
        print(f"First slot Id={first_slot.get('Id')}, children: {[c.tag for c in first_slot]}")
        # What's in the ClipSlot Value child?
        cs_v = first_slot.find("ClipSlot")
        if cs_v:
            print(f"  ClipSlot children: {[c.tag for c in cs_v]}")

tmpl_csl = tmpl_ms.find("ClipSlotList")
if tmpl_csl is not None:
    tmpl_slots = list(tmpl_csl)
    print(f"TMPL ClipSlot count: {len(tmpl_slots)}")
    if tmpl_slots:
        first_slot = tmpl_slots[0]
        print(f"First slot Id={first_slot.get('Id')}, children: {[c.tag for c in first_slot]}")

print("\n" + "=" * 70)
print("8. V12 CLIPSLOT STRUCTURE")
print("=" * 70)
# Check what _build_clip_slots actually creates 
if csl is not None:
    for slot in list(csl)[:2]:
        print(f"ClipSlot Id={slot.get('Id')}:")
        for child in slot:
            print(f"  <{child.tag}", end="")
            for k, v in child.attrib.items():
                print(f" {k}=\"{v}\"", end="")
            print("/>")
            for subchild in child:
                print(f"    <{subchild.tag}", end="")
                for k, v in subchild.attrib.items():
                    print(f" {k}=\"{v}\"", end="")
                print("/>")
