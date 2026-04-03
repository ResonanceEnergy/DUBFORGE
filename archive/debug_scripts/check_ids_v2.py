"""Check ALS XML for list elements with missing Id attributes."""
import gzip
import xml.etree.ElementTree as ET
import sys
import os

def check_als_ids(als_path):
    """Decompress ALS and check for list elements with inconsistent Id attributes."""
    print(f"Checking: {als_path}")
    
    with gzip.open(als_path, "rb") as f:
        raw = f.read()
    
    root = ET.fromstring(raw)
    
    problems = []
    
    def check_element(elem, path=""):
        current_path = f"{path}/{elem.tag}" if path else elem.tag
        
        # Check if this element's children form a "list" (some have Id, some don't)
        children_with_id = []
        children_without_id = []
        
        child_tags = {}
        for child in elem:
            tag = child.tag
            if tag not in child_tags:
                child_tags[tag] = {"with_id": [], "without_id": []}
            if "Id" in child.attrib:
                child_tags[tag]["with_id"].append(child)
            else:
                child_tags[tag]["without_id"].append(child)
        
        # Check for mixed Id/no-Id within same tag group
        for tag, info in child_tags.items():
            if info["with_id"] and info["without_id"]:
                problems.append({
                    "parent": current_path,
                    "tag": tag,
                    "with_id": len(info["with_id"]),
                    "without_id": len(info["without_id"]),
                })
            
            # Also check: does this look like a list container?
            # (parent has multiple children with same tag, and they should all have Ids)
            total = len(info["with_id"]) + len(info["without_id"])
            if total > 1 and info["without_id"]:
                problems.append({
                    "parent": current_path,
                    "tag": tag,
                    "total": total,
                    "missing_id": len(info["without_id"]),
                    "type": "list_without_ids"
                })
        
        # Recurse
        for child in elem:
            check_element(child, current_path)
    
    check_element(root)
    
    if problems:
        print(f"  FOUND {len(problems)} PROBLEMS:")
        seen = set()
        for p in problems:
            key = (p["parent"], p["tag"])
            if key in seen:
                continue
            seen.add(key)
            if "type" in p and p["type"] == "list_without_ids":
                print(f"    LIST: {p['parent']}/{p['tag']} — {p['missing_id']}/{p['total']} children missing Id")
            else:
                print(f"    MIXED: {p['parent']}/{p['tag']} — {p['with_id']} with Id, {p['without_id']} without Id")
    else:
        print("  NO PROBLEMS — all list members have consistent Ids")
    
    return problems


if __name__ == "__main__":
    base = os.path.dirname(__file__)
    
    files = [
        os.path.join(base, "output", "ableton", "_test_mini.als"),
        os.path.join(base, "output", "ableton", "Wild_Ones_V12.als"),
    ]
    
    for f in files:
        if os.path.exists(f):
            check_als_ids(f)
            print()
