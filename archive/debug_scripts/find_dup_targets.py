"""Find all duplicate Pointee/Target IDs in V12 and Mini."""
import gzip
import xml.etree.ElementTree as ET
import os
from collections import defaultdict

base = os.path.dirname(__file__)

def find_all_ids(root):
    """Find every element with an Id attribute that's a target/pointee."""
    ids = defaultdict(list)
    
    def recurse(elem, path=""):
        current = f"{path}/{elem.tag}" if path else elem.tag
        
        # These element types use Ids that must be globally unique
        if elem.tag in ("AutomationTarget", "ModulationTarget", "Pointee") or \
           elem.tag.startswith("ControllerTargets."):
            eid = elem.get("Id")
            if eid:
                ids[int(eid)].append(current)
        
        for child in elem:
            recurse(child, current)
    
    recurse(root)
    return ids

for name, relpath in [("Mini", "output/ableton/_test_mini.als"),
                       ("V12", "output/ableton/Wild_Ones_V12.als")]:
    path = os.path.join(base, relpath)
    with gzip.open(path, "rb") as f:
        root = ET.fromstring(f.read())
    
    ids = find_all_ids(root)
    total = sum(len(v) for v in ids.values())
    dupes = {k: v for k, v in ids.items() if len(v) > 1}
    
    print(f"\n=== {name} ===")
    print(f"Total target IDs: {total}, Unique: {len(ids)}, Duplicated: {len(dupes)}")
    
    if dupes:
        print(f"\nDuplicate IDs (showing locations):")
        for eid in sorted(dupes.keys())[:20]:
            locs = dupes[eid]
            print(f"  Id={eid} appears {len(locs)} times:")
            for loc in locs:
                # Shorten path for readability
                short = loc.replace("Ableton/LiveSet/", "")
                short = short.replace("DeviceChain/DeviceChain/", "DC/")
                short = short.replace("MainSequencer/", "MS/")
                short = short.replace("FreezeSequencer/", "FS/")
                print(f"    {short[:120]}")
        if len(dupes) > 20:
            print(f"  ... and {len(dupes) - 20} more duplicated IDs")
