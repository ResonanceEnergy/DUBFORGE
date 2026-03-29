"""Check PointeeId references in generated ALS."""
import gzip
import xml.etree.ElementTree as ET

with gzip.open('output/ableton/Wild_Ones_V6.als', 'rb') as f:
    tree = ET.parse(f)
root = tree.getroot()

# Collect all AutomationTarget IDs
at_ids = set()
for at in root.iter('AutomationTarget'):
    at_ids.add(at.get('Id', '?'))

# Collect all ModulationTarget IDs
mt_ids = set()
for mt in root.iter('ModulationTarget'):
    mt_ids.add(mt.get('Id', '?'))

all_target_ids = at_ids | mt_ids

print("=== TARGET IDS ===")
print(f"AutomationTarget count: {len(at_ids)}")
print(f"ModulationTarget count: {len(mt_ids)}")
print(f"Combined unique: {len(all_target_ids)}")
print(f"Has Id=0 in AutomationTarget: {'0' in at_ids}")
print(f"Has Id=0 in ModulationTarget: {'0' in mt_ids}")
print()

# Find all PointeeId elements
print("=== ALL PointeeId REFERENCES ===")
pointee_ids = []
for p in root.iter('PointeeId'):
    val = p.get('Value', '?')
    pointee_ids.append(val)
    
print(f"Total PointeeId elements: {len(pointee_ids)}")
pointee_set = set(pointee_ids)
print(f"Unique PointeeId values: {pointee_set}")
print()

# Check which PointeeIds are NOT in any target
dangling = pointee_set - all_target_ids
print(f"=== DANGLING PointeeIds (not in any target) ===")
print(f"Dangling values: {dangling}")
print(f"Count of PointeeId=0: {pointee_ids.count('0')}")
print()

# Show context of each automation envelope
print("=== AUTOMATION ENVELOPE DETAILS ===")
for env in root.iter('AutomationEnvelope'):
    pointee = env.find('.//PointeeId')
    pid = pointee.get('Value', '?') if pointee is not None else 'MISSING'
    
    # Get EnvelopeTarget info
    env_target = env.find('EnvelopeTarget')
    if env_target is not None:
        children = [c.tag for c in env_target]
        print(f"  PointeeId={pid}  EnvelopeTarget children: {children}")
    else:
        print(f"  PointeeId={pid}  NO EnvelopeTarget")

print()

# Show AutomationEnvelopes parent context
print("=== AUTOMATION ENVELOPES IN CONTEXT ===")
# Walk tree to find AutomationEnvelope parents
def find_parents(root, target_tag):
    """Find all elements that contain target_tag as descendant."""
    results = []
    for parent in root.iter():
        for child in parent:
            if child.tag == target_tag:
                results.append((parent.tag, parent.get('Id', ''), child))
    return results

for parent_tag, parent_id, env in find_parents(root, 'AutomationEnvelope'):
    pointee = env.find('.//PointeeId')
    pid = pointee.get('Value', '?') if pointee is not None else 'MISSING'
    print(f"  Parent: {parent_tag} Id={parent_id}  PointeeId={pid}")

# Also check AutomationEnvelopes container
print()
print("=== AutomationEnvelopes CONTAINERS ===")
for container in root.iter('AutomationEnvelopes'):
    parent = None
    # Find parent
    for p in root.iter():
        if container in list(p):
            parent = p
            break
    envs = container.findall('.//AutomationEnvelope')
    pids = [e.find('.//PointeeId').get('Value','?') for e in envs if e.find('.//PointeeId') is not None]
    parent_info = f"{parent.tag} Id={parent.get('Id','')}" if parent else "?"
    print(f"  Container in {parent_info}: {len(envs)} envelopes, PointeeIds={pids}")
