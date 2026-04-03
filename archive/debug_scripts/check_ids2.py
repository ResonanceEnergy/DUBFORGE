"""Check ID allocation: NextPointeeId, max IDs, duplicates."""
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

# Template NextPointeeId
tp = Path(r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als")
with gzip.open(tp, "rb") as f:
    root = ET.parse(f).getroot()
ls = root.find("LiveSet")
npi = ls.find("NextPointeeId")
print(f"Template NextPointeeId = {npi.get('Value')}")

ids = []
for at in root.iter("AutomationTarget"):
    ids.append(int(at.get("Id", "0")))
for mt in root.iter("ModulationTarget"):
    ids.append(int(mt.get("Id", "0")))
for p in root.iter("Pointee"):
    ids.append(int(p.get("Id", "0")))
for elem in root.iter():
    if elem.tag.startswith("ControllerTargets."):
        ids.append(int(elem.get("Id", "0")))
print(f"Template Ids: min={min(ids)}, max={max(ids)}, count={len(ids)}")

# V12 NextPointeeId
v12 = Path("output/ableton/Wild_Ones_V12.als")
with gzip.open(v12, "rb") as f:
    v12root = ET.parse(f).getroot()
v12ls = v12root.find("LiveSet")
v12npi = v12ls.find("NextPointeeId")
print(f"V12 NextPointeeId = {v12npi.get('Value')}")

v12ids = []
for at in v12root.iter("AutomationTarget"):
    v12ids.append(int(at.get("Id", "0")))
for mt in v12root.iter("ModulationTarget"):
    v12ids.append(int(mt.get("Id", "0")))
for p in v12root.iter("Pointee"):
    v12ids.append(int(p.get("Id", "0")))
for elem in v12root.iter():
    if elem.tag.startswith("ControllerTargets."):
        v12ids.append(int(elem.get("Id", "0")))
print(f"V12 Ids: min={min(v12ids)}, max={max(v12ids)}, count={len(v12ids)}")

# Check duplicates
c = Counter(v12ids)
dups = [(k, v) for k, v in c.items() if v > 1]
if dups:
    print(f"DUPLICATE IDs in V12: {dups[:20]}")
else:
    print("No duplicate IDs in V12")

# Check if any generated ID clashes with template reserved range
start = int(npi.get("Value"))
below_start = [x for x in v12ids if x < start and x not in ids]
if below_start:
    print(f"IDs below template NextPointeeId but NOT in template: {sorted(below_start)[:20]}")
