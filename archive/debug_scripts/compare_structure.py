"""Compare top-level XML structure of V12 roundtrip (working) vs generated (crashing)."""
import gzip, xml.etree.ElementTree as ET


def dump_structure(path, label, depth=3):
    with open(path, "rb") as f:
        raw = gzip.decompress(f.read())
    root = ET.fromstring(raw)
    print(f"\n{'='*60}")
    print(f"{label}: {path}")
    print(f"{'='*60}")

    def show(elem, indent=0, max_depth=depth):
        if indent > max_depth:
            return
        attrs = " ".join(f'{k}={v}' for k, v in elem.attrib.items())
        children = len(list(elem))
        tag = f"<{elem.tag} {attrs}>" if attrs else f"<{elem.tag}>"
        text = f"  [{children} children]" if children > 0 else ""
        print(f"{'  '*indent}{tag}{text}")
        for child in elem:
            show(child, indent + 1, max_depth)

    show(root)


dump_structure(r"output\ableton\test_bisect\v12_roundtrip.als", "V12 roundtrip (OK)")
dump_structure(r"output\ableton\_test_no_serum.als", "Generated no VST3 (CRASH)")
