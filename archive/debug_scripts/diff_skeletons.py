"""Diff old s9_bare_skeleton (loads) vs new bisect_noClips (crashes) to find regression."""
import gzip
import xml.etree.ElementTree as ET
import os
from collections import defaultdict

base = os.path.dirname(__file__)

def load_als(path):
    with gzip.open(path, "rb") as f:
        return ET.fromstring(f.read())

old = load_als(os.path.join(base, "output", "ableton", "test_v12strip", "s9_bare_skeleton.als"))
new = load_als(os.path.join(base, "output", "ableton", "test_bisect", "bisect_noClips.als"))

def compare_deep(e1, e2, path="", max_diffs=100):
    """Deep recursive comparison, returning list of differences."""
    diffs = []
    if len(diffs) >= max_diffs:
        return diffs
    
    current = f"{path}/{e1.tag}" if path else e1.tag
    
    # Compare tag
    if e1.tag != e2.tag:
        diffs.append(f"TAG DIFF at {path}: {e1.tag} vs {e2.tag}")
        return diffs
    
    # Compare attributes
    all_keys = set(list(e1.attrib.keys()) + list(e2.attrib.keys()))
    for key in sorted(all_keys):
        v1 = e1.attrib.get(key, "(MISSING)")
        v2 = e2.attrib.get(key, "(MISSING)")
        if v1 != v2:
            diffs.append(f"ATTR at {current} [{key}]: '{v1}' vs '{v2}'")
    
    # Compare children
    c1 = list(e1)
    c2 = list(e2)
    
    if len(c1) != len(c2):
        t1 = [c.tag for c in c1]
        t2 = [c.tag for c in c2]
        diffs.append(f"CHILD COUNT at {current}: {len(c1)} vs {len(c2)}")
        # Show which tags are extra/missing
        from collections import Counter
        ct1 = Counter(t1)
        ct2 = Counter(t2)
        for tag in set(list(ct1.keys()) + list(ct2.keys())):
            if ct1.get(tag, 0) != ct2.get(tag, 0):
                diffs.append(f"  {tag}: {ct1.get(tag, 0)} vs {ct2.get(tag, 0)}")
        return diffs
    
    for ch1, ch2 in zip(c1, c2):
        if len(diffs) >= max_diffs:
            break
        diffs.extend(compare_deep(ch1, ch2, current, max_diffs - len(diffs)))
    
    return diffs

# Compare at LiveSet level first — skip IDs/values that are expected to differ
print("=== FULL DIFF: s9_bare_skeleton (OLD/LOADS) vs bisect_noClips (NEW/CRASHES) ===\n")

old_ls = old.find("LiveSet")
new_ls = new.find("LiveSet")

diffs = compare_deep(old_ls, new_ls, "LiveSet", 200)

# Filter out AutomationTarget/ControllerTarget Id differences (expected to differ)
significant = []
for d in diffs:
    # Skip expected differences
    skip = False
    if "AutomationTarget" in d and "[Id]" in d:
        skip = True
    if "ModulationTarget" in d and "[Id]" in d:
        skip = True
    if "Pointee" in d and "[Id]" in d:
        skip = True
    if "ControllerTargets" in d and "[Id]" in d:
        skip = True
    if "NextPointeeId" in d:
        skip = True
    if "NextId" in d and "NoteIdGenerator" in d:
        skip = True
    
    if not skip:
        significant.append(d)

print(f"Total diffs: {len(diffs)}")
print(f"Significant diffs (non-Id): {len(significant)}")
print()

for d in significant:
    print(d)

if not significant:
    print("NO significant differences! Only Id values differ.")
    print("\nShowing ALL diffs:")
    for d in diffs[:30]:
        print(d)
