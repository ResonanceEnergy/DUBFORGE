"""
DUBFORGE Engine — Ableton Drum Rack Builder

Generate Ableton Live .adg (Ableton Device Group) XML files from the
DUBFORGE 128 Rack zone specification (engine/dojo.py build_128_rack).

Each .adg is a Drum Rack with 128 zones mapped 1:1 to MIDI notes 0-127,
organised by the Fibonacci-distributed categories from the Dojo doctrine.

Outputs:
    - DUBFORGE_128_Rack.adg — full 128-zone Drum Rack
    - Per-category .adg files (SUB_BASS.adg, KICKS.adg, etc.)
    - Zone map JSON for reference
"""

import gzip
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from engine.dojo import build_128_rack


# ═══════════════════════════════════════════════════════════════════════════
# ADG XML STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════
# Ableton .adg files are gzipped XML. The structure for a Drum Rack is:
#
#   <Ableton>
#     <DrumGroupDevice>
#       <Branches>
#         <DrumBranch Id="N">    ← one per active pad
#           <Name Value="..." />
#           <ReceivingNote Value="N" />   ← MIDI note 0-127
#           ...
#         </DrumBranch>
#       </Branches>
#     </DrumGroupDevice>
#   </Ableton>


def _make_ableton_root() -> ET.Element:
    """Create the root <Ableton> element."""
    root = ET.Element("Ableton")
    root.set("MajorVersion", "5")
    root.set("MinorVersion", "12.0_12117")
    root.set("SchemaChangeCount", "10")
    root.set("Creator", "Ableton Live 12.1d1")
    root.set("Revision", "")
    return root


def _make_drum_rack(zones: list[dict],
                    categories: list[dict],
                    name: str = "DUBFORGE 128 Rack") -> ET.Element:
    """Build the DrumGroupDevice XML tree from zone data."""
    device = ET.Element("DrumGroupDevice")
    device.set("Id", "0")

    # Device metadata
    ET.SubElement(device, "LomId").set("Value", "0")
    ET.SubElement(device, "IsExpanded").set("Value", "true")

    user_name = ET.SubElement(device, "UserName")
    user_name.set("Value", name)

    annotation = ET.SubElement(device, "Annotation")
    annotation.set("Value",
                   f"DUBFORGE 128 Rack — {len(zones)} zones, "
                   f"{len(categories)} categories, Fibonacci distribution")

    # On/Off
    on_param = ET.SubElement(device, "On")
    manual = ET.SubElement(on_param, "Manual")
    manual.set("Value", "true")

    # Branches (one DrumBranch per zone)
    branches = ET.SubElement(device, "Branches")

    # Build category colour lookup
    cat_colors = {}
    color_idx = 0
    for cat in categories:
        cat_colors[cat["name"]] = color_idx
        color_idx = (color_idx + 1) % 16

    for zone in zones:
        note = zone["note_start"]
        branch = ET.SubElement(branches, "DrumBranch")
        branch.set("Id", str(note))

        # Branch name
        branch_name = ET.SubElement(branch, "Name")
        branch_name.set("Value", zone.get("label", f"Pad {note}"))

        # Colour (mapped from category)
        color = ET.SubElement(branch, "Color")
        color.set("Value", str(cat_colors.get(zone["category"], 0)))

        # Receiving note = MIDI note for this pad
        recv = ET.SubElement(branch, "ReceivingNote")
        recv.set("Value", str(note))

        # Send level
        send = ET.SubElement(branch, "SendsListSendPreset")
        ET.SubElement(send, "Value").set("Value", "0")

        # Empty device chain (user will drag samples in)
        dev_chain = ET.SubElement(branch, "DeviceChain")
        midi_to_audio = ET.SubElement(dev_chain, "MidiToAudioDeviceChain")
        devices = ET.SubElement(midi_to_audio, "Devices")

        # Simpler placeholder so Ableton sees a valid chain
        simpler = ET.SubElement(devices, "OriginalSimpler")
        simpler.set("Id", str(1000 + note))
        simp_name = ET.SubElement(simpler, "UserName")
        simp_name.set("Value", zone.get("label", f"Pad {note}"))

    return device


def build_adg_xml(zones: list[dict],
                  categories: list[dict],
                  name: str = "DUBFORGE 128 Rack") -> bytes:
    """Build complete .adg XML content (not yet gzipped)."""
    root = _make_ableton_root()
    device = _make_drum_rack(zones, categories, name)
    root.append(device)
    return ET.tostring(root, encoding="unicode", xml_declaration=True).encode("utf-8")


def write_adg(path: str, xml_bytes: bytes) -> str:
    """Write gzipped .adg file (Ableton's native format)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(str(p), "wb") as f:
        f.write(xml_bytes)
    return str(p)


# ═══════════════════════════════════════════════════════════════════════════
# FULL 128 RACK EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_128_rack_adg(output_dir: str = "output") -> list[str]:
    """Export the full DUBFORGE 128 Rack as .adg + per-category .adg files."""
    rack_data = build_128_rack()
    zones = rack_data["zones"]
    categories = rack_data["categories"]

    out = Path(output_dir) / "ableton" / "drum_racks"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    # Full 128 Rack
    xml = build_adg_xml(zones, categories, "DUBFORGE 128 Rack")
    full_path = write_adg(str(out / "DUBFORGE_128_Rack.adg"), xml)
    paths.append(full_path)

    # Per-category .adg files
    for cat in categories:
        cat_name = cat["name"]
        cat_zones = [z for z in zones if z["category"] == cat_name]
        if not cat_zones:
            continue
        safe_name = cat_name.replace(" ", "_").replace("/", "_")
        cat_xml = build_adg_xml(cat_zones, [cat],
                                f"DUBFORGE {cat_name}")
        cat_path = write_adg(
            str(out / f"DUBFORGE_{safe_name}.adg"), cat_xml)
        paths.append(cat_path)

    # Zone map JSON reference
    zone_map = {
        "rack": "DUBFORGE 128 Rack",
        "total_zones": len(zones),
        "categories": [{
            "name": c["name"],
            "zone_count": c["zone_count"],
            "note_range": f"{c['note_range_start']}-{c['note_range_end']}",
            "color": c["color"],
        } for c in categories],
    }
    map_path = out / "zone_map.json"
    with open(map_path, "w") as f:
        json.dump(zone_map, f, indent=2)
    paths.append(str(map_path))

    return paths


def main() -> None:
    print("═══ Ableton Drum Rack Builder ═══")
    paths = export_128_rack_adg()
    print(f"  ✓ {len(paths)} files generated:")
    for p in paths:
        print(f"    {p}")


if __name__ == "__main__":
    main()
