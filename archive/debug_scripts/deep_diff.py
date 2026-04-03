"""Deep structural diff: V12 ALS vs Ableton factory template.
Finds missing elements, wrong value types, and structural mismatches."""
import gzip
import xml.etree.ElementTree as ET
from collections import defaultdict

def get_schema(elem, path="", depth=0, max_depth=20):
    """Recursively build a schema map: path -> (has_value, sample_value, child_count)."""
    schema = {}
    tag = elem.tag
    full_path = f"{path}/{tag}" if path else tag
    val = elem.get("Value")
    children = list(elem)
    schema[full_path] = {
        "value": val,
        "attrs": sorted(elem.attrib.keys()),
        "children": [c.tag for c in children],
        "child_count": len(children),
    }
    if depth < max_depth:
        for child in children:
            schema.update(get_schema(child, full_path, depth + 1, max_depth))
    return schema


with gzip.open('output/ableton/Wild_Ones_V12.als', 'rb') as f:
    v12 = ET.fromstring(f.read())
with gzip.open(
    r'C:\Users\gripa\AppData\Roaming\Ableton\Live 12.3.6\Preferences'
    r'\Crash\2026_03_28__01_12_39_BaseFiles\DefaultLiveSet.als', 'rb'
) as f:
    tmpl = ET.fromstring(f.read())

# Compare first MidiTrack deeply
v12_mt = v12.find('.//MidiTrack')
tmpl_mt = tmpl.find('.//MidiTrack')

v12_schema = get_schema(v12_mt, max_depth=15)
tmpl_schema = get_schema(tmpl_mt, max_depth=15)

# Find paths in template not in V12
print("=" * 70)
print("MISSING FROM V12 (exists in template but not in V12)")
print("=" * 70)
missing_paths = sorted(set(tmpl_schema.keys()) - set(v12_schema.keys()))
for p in missing_paths:
    info = tmpl_schema[p]
    val_str = f" Value={info['value']}" if info['value'] else ""
    print(f"  {p}{val_str}")

# Find paths in V12 not in template
print()
print("=" * 70)
print("EXTRA IN V12 (exists in V12 but not in template)")
print("=" * 70)
extra_paths = sorted(set(v12_schema.keys()) - set(tmpl_schema.keys()))
for p in extra_paths:
    info = v12_schema[p]
    val_str = f" Value={info['value']}" if info['value'] else ""
    print(f"  {p}{val_str}")

# Compare shared paths for structural differences
print()
print("=" * 70)
print("STRUCTURAL DIFFERENCES (shared paths)")
print("=" * 70)
shared = sorted(set(v12_schema.keys()) & set(tmpl_schema.keys()))
for p in shared:
    v = v12_schema[p]
    t = tmpl_schema[p]
    diffs = []
    # Check if children list differs
    if sorted(v["children"]) != sorted(t["children"]):
        v_only = set(v["children"]) - set(t["children"])
        t_only = set(t["children"]) - set(v["children"])
        if t_only:
            diffs.append(f"missing children: {t_only}")
        if v_only:
            diffs.append(f"extra children: {v_only}")
    # Check value type mismatch (int expected but got string)
    if v["value"] is not None and t["value"] is not None:
        t_is_int = t["value"].lstrip("-").isdigit()
        v_is_int = v["value"].lstrip("-").isdigit()
        if t_is_int and not v_is_int:
            diffs.append(f"TYPE MISMATCH: template={t['value']} (int), v12={v['value']} (string)")
    if diffs:
        print(f"  {p}")
        for d in diffs:
            print(f"    -> {d}")

# Also check ALL Value attributes that should be int but aren't
print()
print("=" * 70)
print("ALL NON-INTEGER VALUES WHERE TEMPLATE HAS INTEGER")
print("=" * 70)
count = 0
for p in shared:
    v = v12_schema[p]
    t = tmpl_schema[p]
    if v["value"] is not None and t["value"] is not None:
        t_is_num = t["value"].lstrip("-").replace(".", "").isdigit()
        v_is_num = v["value"].lstrip("-").replace(".", "").isdigit()
        if t_is_num and not v_is_num:
            print(f"  {p}: template={t['value']}, v12={v['value']}")
            count += 1
if count == 0:
    print("  None found!")
