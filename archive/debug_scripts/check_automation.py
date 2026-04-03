"""Inspect AutomationEnvelopes in V12 - these are the likely crash cause."""
import gzip
import xml.etree.ElementTree as ET
import os

base = os.path.dirname(__file__)

def load_als(path):
    with gzip.open(path, "rb") as f:
        return ET.fromstring(f.read())

v12 = load_als(os.path.join(base, "output", "ableton", "Wild_Ones_V12.als"))

# Find ALL AutomationEnvelopes across the entire document
print("=== ALL AUTOMATION ENVELOPES IN V12 ===\n")

def find_envelopes(root):
    """Find all AutomationEnvelope elements and their context."""
    results = []
    
    def search(elem, path=""):
        current = f"{path}/{elem.tag}" if path else elem.tag
        
        if elem.tag == "AutomationEnvelope":
            # Get the PointeeId
            pointee = elem.find(".//PointeeId")
            pointee_id = pointee.get("Value", "?") if pointee is not None else "MISSING"
            
            # Get automation events
            events = elem.findall(".//RealPoint") + elem.findall(".//FloatEvent")
            
            results.append({
                "path": current,
                "pointee_id": pointee_id,
                "event_count": len(events),
            })
        
        for child in elem:
            search(child, current)
    
    search(root)
    return results

envs = find_envelopes(v12)
print(f"Total AutomationEnvelopes: {len(envs)}")
for e in envs:
    short_path = e["path"].replace("Ableton/LiveSet/", "").replace("DeviceChain/DeviceChain/", "DC/")
    print(f"  PointeeId={e['pointee_id']}, Events={e['event_count']}, Path={short_path[:100]}")

# Now check: do the PointeeIds actually point to existing AutomationTargets?
print("\n=== POINTEE ID VALIDATION ===")

# Collect all AutomationTarget Ids (these are what PointeeIds should reference)
all_target_ids = set()
for elem in v12.iter():
    if elem.tag == "AutomationTarget":
        tid = elem.get("Id")
        if tid:
            all_target_ids.add(int(tid))

# Also collect Pointee Ids (these are cross-references)
all_pointee_ids = set()
for elem in v12.iter():
    if elem.tag == "Pointee":
        pid = elem.get("Id")
        if pid:
            all_pointee_ids.add(int(pid))

print(f"AutomationTarget Ids: {len(all_target_ids)}")
print(f"Pointee Ids: {len(all_pointee_ids)}")

# Check envelope PointeeIds
for e in envs:
    pid = e["pointee_id"]
    if pid == "MISSING":
        print(f"  PROBLEM: Envelope has no PointeeId! Path={e['path']}")
    elif pid.isdigit():
        pid_int = int(pid)
        if pid_int in all_target_ids:
            print(f"  OK: PointeeId {pid} -> resolved to AutomationTarget")
        elif pid_int in all_pointee_ids:
            print(f"  OK: PointeeId {pid} -> resolved to Pointee element")
        else:
            print(f"  DANGLING: PointeeId {pid} NOT FOUND in any target! Path={e['path']}")
    else:
        print(f"  PROBLEM: PointeeId '{pid}' is not numeric! Path={e['path']}")

# Also check ALL PointeeId references in the document (not just envelopes)
print("\n=== ALL POINTEEID REFERENCES ===")
dangling = []
for elem in v12.iter():
    if elem.tag == "PointeeId":
        pid = elem.get("Value", "?")
        if pid.isdigit():
            pid_int = int(pid)
            if pid_int not in all_target_ids and pid_int not in all_pointee_ids:
                # Find parent context
                dangling.append(pid)

print(f"Total PointeeId references: checked")
if dangling:
    print(f"DANGLING PointeeIds: {len(dangling)}")
    for d in dangling[:10]:
        print(f"  PointeeId {d} has no matching target")
else:
    print("All PointeeIds resolve correctly")
