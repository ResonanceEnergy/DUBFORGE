"""Verify ALS output structure."""
import gzip
import xml.etree.ElementTree as ET

with gzip.open('output/ableton/Wild_Ones_V6.als', 'rb') as f:
    xml_str = f.read().decode('utf-8')

root = ET.fromstring(xml_str)
print(f"Root: {root.tag} MajorVersion={root.get('MajorVersion')} MinorVersion={root.get('MinorVersion')}")
print(f"Creator: {root.get('Creator')}")
ls = root.find('LiveSet')
print(f"NextPointeeId: {ls.find('NextPointeeId').get('Value')}")
print(f"OverwriteProtectionNumber: {ls.find('OverwriteProtectionNumber').get('Value')}")

# Transport
transport = ls.find('Transport')
tempo = transport.find('Tempo/Manual')
print(f"Tempo: {tempo.get('Value')}")
tempo_at = transport.find('Tempo/AutomationTarget')
print(f"Tempo AutomationTarget Id: {tempo_at.get('Id') if tempo_at is not None else 'MISSING'}")

# Tracks
tracks = ls.find('Tracks')
all_tracks = list(tracks)
print(f"\nTotal tracks: {len(all_tracks)}")
for t in all_tracks:
    name = t.find('.//Name/EffectiveName').get('Value')
    ttype = t.tag
    vol_elem = t.find('.//Mixer/Volume/Manual')
    vol_val = vol_elem.get('Value') if vol_elem is not None else 'N/A'
    dc = t.find('DeviceChain')
    has_main_seq = dc.find('MainSequencer') is not None if dc is not None else False
    has_freeze_seq = dc.find('FreezeSequencer') is not None if dc is not None else False
    has_controllers = dc.find('.//MidiControllers') is not None if dc is not None else False
    n_controller_targets = len(dc.findall('.//MidiControllers/*')) if has_controllers else 0
    clips = len(dc.findall('.//AudioClip')) if dc is not None else 0
    autos = len(t.findall('.//AutomationEnvelope'))
    # Check routing
    audio_out = dc.find('.//AudioOutputRouting/Target') if dc is not None else None
    routing = audio_out.get('Value') if audio_out is not None else 'N/A'
    print(f"  {ttype:12s} {name:10s} vol_lin={vol_val:>14s} MainSeq={has_main_seq} FreezeSeq={has_freeze_seq} MidiCtrl={n_controller_targets:>3d} clips={clips} autos={autos} out={routing}")

# Master
mt = ls.find('MasterTrack')
if mt is not None:
    mv = mt.find('.//Mixer/Volume/Manual')
    print(f"\nMasterTrack: vol_linear={mv.get('Value') if mv is not None else 'N/A'}")
    mo = mt.find('.//AudioOutputRouting/Target')
    print(f"  Output routing: {mo.get('Value') if mo is not None else 'N/A'}")

# Scenes
scenes = ls.findall('.//Scenes/Scene')
print(f"\nScenes: {len(scenes)}")
for s in scenes:
    print(f"  {s.find('Name/EffectiveName').get('Value')}")

# Locators
locs = ls.findall('.//Locators/Locators/Locator')
print(f"\nLocators/CuePoints: {len(locs)}")
for loc in locs[:5]:
    print(f"  {loc.find('Name/Value').get('Value')} @ beat {loc.find('Time').get('Value')}")
if len(locs) > 5:
    print(f"  ... and {len(locs)-5} more")

# Volume sanity check
print("\n--- Volume dB-to-Linear sanity check ---")
import math
for track in all_tracks:
    name = track.find('.//Name/EffectiveName').get('Value')
    vol_elem = track.find('.//Mixer/Volume/Manual')
    if vol_elem is not None:
        lin = float(vol_elem.get('Value'))
        if lin > 0:
            db = 20 * math.log10(lin)
        else:
            db = -70.0
        print(f"  {name:10s}: linear={lin:.6f}  ({db:+.1f} dB)")

print(f"\nTotal XML size: {len(xml_str):,} chars")
print("\nDONE - ALS verification complete")
