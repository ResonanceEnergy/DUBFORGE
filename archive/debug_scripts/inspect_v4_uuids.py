"""Inspect Apology V4 ALS for UUID strings and ID consistency."""
import gzip
import xml.etree.ElementTree as ET
import re

path = r"C:\dev\SuperAgency-Shared\repos\DUBFORGE\output\ableton\Apology_V4.als"
with gzip.open(path, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

# Check NextPointeeId
for el in root.iter("NextPointeeId"):
    print(f"NextPointeeId: {el.get('Value')}")

# Check max AutomationTarget Id
max_id = 0
for at in root.iter("AutomationTarget"):
    aid = int(at.get("Id", "0"))
    if aid > max_id:
        max_id = aid
print(f"Max AutomationTarget Id: {max_id}")

# Check all PluginDevice elements
print("\n=== PluginDevice elements ===")
for i, pd in enumerate(root.iter("PluginDevice")):
    print(f"PluginDevice #{i}: Id={pd.get('Id')}")
    desc = pd.find("PluginDesc")
    if desc is not None:
        for child in desc:
            print(f"  PluginDesc child: <{child.tag} Id='{child.get('Id', '')}'>")
            if child.tag == "Vst3PluginInfo":
                uid = child.find("Uid")
                if uid is not None:
                    fields = uid.find("Fields")
                    if fields is not None:
                        vals = []
                        for f in fields:
                            vals.append(f"{f.tag}={f.get('Value')}")
                        print(f"    Uid Fields: {', '.join(vals)}")

# Check for UUID-like strings anywhere
uuid_pat = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
print("\n=== UUID-like strings in XML ===")
found_any = False
for elem in root.iter():
    if elem.text and uuid_pat.search(elem.text):
        print(f"UUID in text: <{elem.tag}>{elem.text}</{elem.tag}>")
        found_any = True
    for attr, val in elem.attrib.items():
        if uuid_pat.search(val):
            print(f"UUID in attr: <{elem.tag} {attr}='{val}'>")
            found_any = True
if not found_any:
    print("  None found")

# Check all elements with Id > NextPointeeId
npid_el = root.find(".//NextPointeeId")
npid = int(npid_el.get("Value")) if npid_el is not None else 0
print(f"\n=== IDs exceeding NextPointeeId ({npid}) ===")
overflow = 0
for elem in root.iter():
    eid = elem.get("Id")
    if eid and eid.isdigit():
        if int(eid) >= npid:
            overflow += 1
            if overflow <= 5:
                print(f"  <{elem.tag} Id='{eid}'> >= NextPointeeId")
if overflow:
    print(f"  ... total: {overflow} elements with Id >= NextPointeeId")
else:
    print("  None (all IDs valid)")

# Check for empty Value attrs that might be parsed as UUID
print("\n=== Empty string Values in critical elements ===")
for tag in ["SourceContext", "LastPresetRef", "UniqueDeviceId", "BranchSourceContext"]:
    for elem in root.iter(tag):
        val_child = elem.find("Value")
        if val_child is not None:
            # Check if Value has text or children
            has_text = val_child.text and val_child.text.strip()
            has_children = len(val_child) > 0
            if not has_text and not has_children:
                parent = None
                for p in root.iter():
                    if elem in list(p):
                        parent = p
                        break
                print(f"  <{tag}><Value/> (empty) in <{parent.tag if parent else '?'}>")
