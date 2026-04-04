#!/usr/bin/env python3
"""Extract VST3 ProcessorState / ControllerState hex from an Ableton ALS file.

Usage
-----
    python3 tools/extract_vst3_state.py <path-to-als> [--plugin "Serum 2"]

Workflow
--------
1. Open Ableton Live, create a new set
2. Add a MIDI track with Serum 2 (or any VST3)
3. Load your desired preset inside the plugin
4. Save the ALS (File → Save)
5. Run this script on the saved .als file

The script decompresses the gzipped XML, finds all PluginDevice elements,
extracts the ProcessorState and ControllerState hex blobs, and either:
  - Prints them as Python bytes.fromhex() literals
  - Writes them to a .py file you can import

This gives you Ableton-native IBStream state bytes that are guaranteed
compatible with Ableton's VST3 host.
"""
from __future__ import annotations

import argparse
import gzip
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path


def decompress_als(path: Path) -> bytes:
    """Read and decompress an ALS file (gzipped XML)."""
    raw = path.read_bytes()
    try:
        return gzip.decompress(raw)
    except gzip.BadGzipFile:
        # Might already be uncompressed XML (e.g. during development)
        if raw.startswith(b"<?xml") or raw.startswith(b"<Ableton"):
            return raw
        raise


def find_plugin_states(xml_bytes: bytes, plugin_filter: str | None = None) -> list[dict]:
    """Parse ALS XML and extract all VST3 plugin states.

    Returns a list of dicts with keys:
        name, track_name, processor_state_hex, controller_state_hex,
        processor_state_bytes, controller_state_bytes
    """
    root = ET.fromstring(xml_bytes)
    results = []

    # Find all PluginDevice elements (Ableton's wrapper for VST3)
    for pd in root.iter("PluginDevice"):
        # Get the Vst3PluginInfo inside PluginDesc
        plugin_desc = pd.find("PluginDesc")
        if plugin_desc is None:
            continue

        vst3_info = plugin_desc.find("Vst3PluginInfo")
        if vst3_info is None:
            continue

        # Get plugin name
        name_el = vst3_info.find("Name")
        plugin_name = name_el.get("Value", "") if name_el is not None else ""

        if plugin_filter and plugin_filter.lower() not in plugin_name.lower():
            continue

        # Navigate to Vst3Preset which contains the state
        vst3_preset = vst3_info.find(".//Vst3Preset")
        if vst3_preset is None:
            continue

        # Extract ProcessorState
        ps_el = vst3_preset.find("ProcessorState")
        ps_hex = ""
        ps_bytes = b""
        if ps_el is not None and ps_el.text and ps_el.text.strip():
            ps_hex = ps_el.text.strip()
            try:
                ps_bytes = bytes.fromhex(ps_hex)
            except ValueError:
                print(f"  WARNING: ProcessorState hex invalid for {plugin_name}",
                      file=sys.stderr)

        # Extract ControllerState
        cs_el = vst3_preset.find("ControllerState")
        cs_hex = ""
        cs_bytes = b""
        if cs_el is not None and cs_el.text and cs_el.text.strip():
            cs_hex = cs_el.text.strip()
            try:
                cs_bytes = bytes.fromhex(cs_hex)
            except ValueError:
                print(f"  WARNING: ControllerState hex invalid for {plugin_name}",
                      file=sys.stderr)

        # Try to find which track this belongs to
        track_name = _find_parent_track_name(root, pd)

        results.append({
            "name": plugin_name,
            "track_name": track_name,
            "processor_state_hex": ps_hex,
            "controller_state_hex": cs_hex,
            "processor_state_bytes": ps_bytes,
            "controller_state_bytes": cs_bytes,
        })

    return results


def _find_parent_track_name(root: ET.Element, target: ET.Element) -> str:
    """Best-effort: walk the tree to find which track contains this device."""
    # Build parent map
    parent_map = {child: parent for parent in root.iter() for child in parent}

    node = target
    while node is not None:
        # Check if this element has a Name child with a UserName attribute
        name_el = node.find("Name")
        if name_el is not None:
            effective = name_el.get("EffectiveName")
            if effective:
                return effective
            user = name_el.get("UserName")
            if user:
                return user
        node = parent_map.get(node)
    return "<unknown>"


def format_hex_literal(raw_bytes: bytes, var_name: str, width: int = 64) -> str:
    """Format bytes as a Python bytes.fromhex() multi-line literal."""
    if not raw_bytes:
        return f"{var_name} = None  # empty in ALS"

    hex_str = raw_bytes.hex().upper()
    lines = [f'    "{hex_str[i:i+width]}"' for i in range(0, len(hex_str), width)]
    return f"{var_name} = bytes.fromhex(\n" + "\n".join(lines) + "\n)"


def main():
    parser = argparse.ArgumentParser(
        description="Extract VST3 state from Ableton ALS files")
    parser.add_argument("als_file", type=Path,
                        help="Path to .als file (gzipped XML)")
    parser.add_argument("--plugin", "-p", type=str, default=None,
                        help="Filter by plugin name (e.g. 'Serum 2')")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Write Python module with state constants")
    parser.add_argument("--first", action="store_true",
                        help="Only extract the first matching plugin instance")
    parser.add_argument("--raw-hex", action="store_true",
                        help="Print raw hex strings instead of Python literals")
    args = parser.parse_args()

    if not args.als_file.exists():
        print(f"ERROR: {args.als_file} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading: {args.als_file}")
    xml_bytes = decompress_als(args.als_file)
    print(f"Decompressed: {len(xml_bytes):,} bytes of XML")

    states = find_plugin_states(xml_bytes, args.plugin)

    if not states:
        print("No VST3 plugin states found!", file=sys.stderr)
        if args.plugin:
            print(f"  (filter was: '{args.plugin}')", file=sys.stderr)
        sys.exit(1)

    print(f"\nFound {len(states)} VST3 plugin instance(s):\n")

    for i, st in enumerate(states):
        ps_size = len(st["processor_state_bytes"])
        cs_size = len(st["controller_state_bytes"])
        print(f"  [{i}] {st['name']!r} on track {st['track_name']!r}")
        print(f"      ProcessorState: {ps_size:,} bytes")
        print(f"      ControllerState: {cs_size:,} bytes")

        if args.first and i == 0:
            break

    # Select which entries to output
    entries = [states[0]] if args.first else states

    if args.raw_hex:
        for st in entries:
            print(f"\n--- {st['name']} (track: {st['track_name']}) ---")
            print(f"ProcessorState ({len(st['processor_state_bytes'])} bytes):")
            print(st["processor_state_hex"])
            print(f"\nControllerState ({len(st['controller_state_bytes'])} bytes):")
            print(st["controller_state_hex"])
        return

    if args.output:
        _write_python_module(args.output, entries)
    else:
        # Print Python literals to stdout
        for st in entries:
            print(f"\n# --- {st['name']} (track: {st['track_name']}) ---")
            print(format_hex_literal(
                st["processor_state_bytes"],
                f"PROCESSOR_STATE_{_safe_name(st['name'])}"
            ))
            print()
            print(format_hex_literal(
                st["controller_state_bytes"],
                f"CONTROLLER_STATE_{_safe_name(st['name'])}"
            ))


def _safe_name(plugin_name: str) -> str:
    """Convert plugin name to a valid Python identifier."""
    return plugin_name.upper().replace(" ", "_").replace("-", "_").replace(".", "_")


def _write_python_module(path: Path, entries: list[dict]):
    """Write extracted states as a Python module."""
    lines = [
        '"""VST3 plugin states extracted from an Ableton-saved ALS file.',
        '',
        'These bytes are Ableton-native IBStream format, captured by:',
        '  1. Loading the plugin in Ableton Live',
        '  2. Setting the desired preset',
        '  3. Saving the ALS',
        '  4. Running: python3 tools/extract_vst3_state.py <file.als>',
        '',
        'Compatible with Ableton\'s VST3 host setState() — unlike JUCE/pedalboard',
        'captured state which uses a different IBStream serialization.',
        '"""',
        '',
    ]

    for st in entries:
        lines.append(f"# Plugin: {st['name']}, Track: {st['track_name']}")
        lines.append(f"# ProcessorState: {len(st['processor_state_bytes']):,} bytes")
        lines.append(format_hex_literal(
            st["processor_state_bytes"],
            f"PROCESSOR_STATE_{_safe_name(st['name'])}"
        ))
        lines.append("")
        lines.append(f"# ControllerState: {len(st['controller_state_bytes']):,} bytes")
        lines.append(format_hex_literal(
            st["controller_state_bytes"],
            f"CONTROLLER_STATE_{_safe_name(st['name'])}"
        ))
        lines.append("")

    path.write_text("\n".join(lines) + "\n")
    print(f"\nWrote state module: {path}")


if __name__ == "__main__":
    main()
