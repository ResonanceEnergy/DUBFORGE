"""Map automation envelope parameter names to AutomationTarget IDs."""
import gzip
import xml.etree.ElementTree as ET

with gzip.open('output/ableton/Wild_Ones_V6.als', 'rb') as f:
    tree = ET.parse(f)
root = tree.getroot()

# For AudioTrack 0, show MixerDevice parameter AutomationTarget IDs
print("=== AudioTrack 0 MixerDevice AutomationTarget IDs ===")
for at in root.iter('AudioTrack'):
    if at.get('Id') == '0':
        mixer = at.find('.//MixerDevice')
        if mixer is not None:
            for param in mixer:
                targets = param.findall('.//AutomationTarget')
                for t in targets:
                    print(f"  {param.tag} -> AutomationTarget Id={t.get('Id')}")
        break

# List ALL bad envelopes with their ParameterName values
print()
print("=== ALL BAD ENVELOPES (ParameterName, no EnvelopeTarget) ===")
for track_type in ['AudioTrack', 'MidiTrack', 'ReturnTrack']:
    for track in root.iter(track_type):
        tid = track.get('Id', '?')
        # Find track name
        name_el = track.find('.//UserName')
        track_name = name_el.get('Value', '?') if name_el is not None else '?'
        
        auto_envs_container = track.find('.//AutomationEnvelopes')
        if auto_envs_container is not None:
            envelopes = auto_envs_container.find('Envelopes')
            if envelopes is not None:
                for env in envelopes:
                    pname = env.find('ParameterName')
                    env_target = env.find('EnvelopeTarget')
                    
                    if pname is not None:
                        # Count FloatEvents
                        events = env.findall('.//FloatEvent')
                        print(f"  {track_type} Id={tid} '{track_name}': "
                              f"ParameterName={pname.get('Value','?')} "
                              f"({len(events)} events)")
                    elif env_target is not None:
                        pid = env_target.find('PointeeId')
                        pid_val = pid.get('Value', '?') if pid is not None else '?'
                        print(f"  {track_type} Id={tid} '{track_name}': "
                              f"EnvelopeTarget PointeeId={pid_val} (GOOD)")

# Show factory template structure for comparison
print()
print("=== FACTORY TEMPLATE AUTOMATION ===")
factory_path = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"
with gzip.open(factory_path, 'rb') as f:
    ftree = ET.parse(f)
froot = ftree.getroot()

# Check if factory has any AutomationEnvelopes  
for track_type in ['AudioTrack', 'MidiTrack', 'ReturnTrack', 'MainTrack', 'PreHearTrack']:
    for track in froot.iter(track_type):
        tid = track.get('Id', '?')
        auto_envs_container = track.find('.//AutomationEnvelopes')
        if auto_envs_container is not None:
            envelopes = auto_envs_container.find('Envelopes')
            if envelopes is not None:
                for env in envelopes:
                    env_target = env.find('EnvelopeTarget')
                    if env_target is not None:
                        pid = env_target.find('PointeeId')
                        pid_val = pid.get('Value', '?') if pid is not None else '?'
                        print(f"  {track_type} Id={tid}: EnvelopeTarget PointeeId={pid_val}")
