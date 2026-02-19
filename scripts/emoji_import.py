#!/usr/bin/env python3
"""Import emoji files from a source directory into a theme's context subdirectories.

Parses emoji-test.txt to map codepoint sequences to Unicode emoji groups,
then copies files from a flat source directory into context-sorted subdirs.

Usage:
    python scripts/emoji_import.py <theme-dir> <source-dir> [--dest scalable|NxN]

Arguments:
    theme-dir   Theme directory name (e.g., noto-emoji, twemoji)
    source-dir  Flat directory of emoji files (SVG or PNG)
    --dest      Target subdirectory under theme (default: auto-detect from files)
                Use "scalable" for SVGs, or "128x128" etc. for PNGs.

The script requires in the theme directory:
    - contexts.json   (maps context IDs to emoji_group strings)
    - emoji-test.txt  (Unicode emoji test data file)

Filename formats auto-detected:
    - Noto:    emoji_u1f600.svg, emoji_u1f469_1f3fd.png
    - Twemoji: 1f600.svg, 1f469-1f3fd.png

Examples:
    python scripts/emoji_import.py noto-emoji ../icons/noto-emoji-main/svg
    python scripts/emoji_import.py noto-emoji ../icons/noto-emoji-main/png/128 --dest 128x128
"""

import os
import re
import shutil
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).parent
_PROJECT_DIR = _SCRIPT_DIR.parent


def parse_emoji_test(filepath):
    """Parse emoji-test.txt, return dict mapping codepoint tuple -> group name.

    Handles all qualification levels (fully-qualified, minimally-qualified,
    unqualified, component). Keys are tuples of uppercase hex strings.
    """
    mapping = {}
    current_group = None

    with open(filepath) as f:
        for line in f:
            line = line.strip()

            # Track current group
            if line.startswith("# group:"):
                current_group = line.split(":", 1)[1].strip()
                continue

            # Skip comments and blanks
            if not line or line.startswith("#"):
                continue

            # Parse: "1F600 ; fully-qualified # 😀 E1.0 grinning face"
            if ";" not in line:
                continue

            codepoints_str = line.split(";")[0].strip()
            codepoints = tuple(cp.upper() for cp in codepoints_str.split())

            if current_group and codepoints not in mapping:
                mapping[codepoints] = current_group

    return mapping


def parse_contexts(filepath):
    """Parse contexts.json, return dict mapping emoji_group -> context_id."""
    import json
    with open(filepath) as f:
        data = json.load(f)

    group_to_context = {}
    for context_id, meta in data.items():
        emoji_group = meta.get("emoji_group")
        if emoji_group:
            group_to_context[emoji_group] = context_id

    return group_to_context


def decode_filename(filename):
    """Extract codepoint tuple from emoji filename. Auto-detects format.

    Noto:    emoji_u1f600_1f3fd.svg -> ('1F600', '1F3FD')
    Twemoji: 1f600-1f3fd.svg       -> ('1F600', '1F3FD')
    Noto alt: u1f645.png            -> ('1F645',)
    """
    stem = Path(filename).stem

    # Noto format: emoji_u{hex}_{hex}...
    if stem.startswith("emoji_u"):
        parts = stem[len("emoji_u"):].split("_")
        return tuple(p.upper() for p in parts)

    # Noto alt format: u{hex}-u{hex}...
    if stem.startswith("u") and not stem.startswith("un"):
        # Split on -u or _ separators
        parts = re.split(r'[-_]', stem)
        return tuple(p.lstrip("u").upper() for p in parts)

    # Twemoji format: {hex}-{hex}...
    parts = stem.split("-")
    return tuple(p.upper() for p in parts)


def lookup_group(codepoints, emoji_mapping):
    """Look up group for codepoints, trying with and without FE0F."""
    # Direct lookup
    if codepoints in emoji_mapping:
        return emoji_mapping[codepoints]

    # Try adding FE0F after base codepoint (common for single-char emoji)
    if len(codepoints) == 1:
        with_vs = codepoints + ("FE0F",)
        if with_vs in emoji_mapping:
            return emoji_mapping[with_vs]

    # Try removing all FE0F (variation selectors)
    without_fe0f = tuple(cp for cp in codepoints if cp != "FE0F")
    if without_fe0f != codepoints and without_fe0f in emoji_mapping:
        return emoji_mapping[without_fe0f]

    # Try inserting FE0F after first codepoint
    if len(codepoints) >= 2 and "FE0F" not in codepoints:
        with_vs = (codepoints[0], "FE0F") + codepoints[1:]
        if with_vs in emoji_mapping:
            return emoji_mapping[with_vs]

    return None


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(1)

    theme_name = sys.argv[1]
    source_dir = Path(sys.argv[2])
    theme_dir = _PROJECT_DIR / theme_name

    # Parse --dest flag
    dest_subdir = None
    for i, arg in enumerate(sys.argv[3:], 3):
        if arg == "--dest" and i + 1 < len(sys.argv):
            dest_subdir = sys.argv[i + 1]

    # Validate paths
    if not source_dir.is_dir():
        print(f"Error: source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    emoji_test_path = theme_dir / "emoji-test.txt"
    contexts_path = theme_dir / "contexts.json"

    if not emoji_test_path.exists():
        print(f"Error: {emoji_test_path} not found", file=sys.stderr)
        sys.exit(1)
    if not contexts_path.exists():
        print(f"Error: {contexts_path} not found", file=sys.stderr)
        sys.exit(1)

    # Parse reference data
    print(f"Parsing {emoji_test_path.name}...")
    emoji_mapping = parse_emoji_test(emoji_test_path)
    print(f"  {len(emoji_mapping)} codepoint sequences loaded")

    group_to_context = parse_contexts(contexts_path)
    print(f"  {len(group_to_context)} context mappings loaded")

    # Collect source files
    source_files = sorted([
        f for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() in (".svg", ".svgz", ".png")
    ])
    print(f"  {len(source_files)} source files found in {source_dir}")

    # Auto-detect dest if not specified
    if dest_subdir is None:
        ext = source_files[0].suffix.lower() if source_files else ".svg"
        if ext in (".svg", ".svgz"):
            dest_subdir = "scalable"
        else:
            print("Error: --dest required for PNG files (e.g., --dest 128x128)",
                  file=sys.stderr)
            sys.exit(1)

    dest_base = theme_dir / dest_subdir
    print(f"  Destination: {dest_base}")
    print()

    # Process files
    copied = 0
    unmapped = []
    context_counts = {}

    for src_file in source_files:
        codepoints = decode_filename(src_file.name)
        group = lookup_group(codepoints, emoji_mapping)

        if group is None:
            unmapped.append((src_file.name, codepoints))
            continue

        context_id = group_to_context.get(group)
        if context_id is None:
            unmapped.append((src_file.name, codepoints))
            continue

        # Ensure dest context directory exists
        dest_dir = dest_base / context_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy file
        dest_file = dest_dir / src_file.name
        shutil.copy2(src_file, dest_file)
        copied += 1
        context_counts[context_id] = context_counts.get(context_id, 0) + 1

    # Report
    print(f"Copied: {copied}")
    for ctx in sorted(context_counts):
        print(f"  {ctx}: {context_counts[ctx]}")

    if unmapped:
        print(f"\nUnmapped: {len(unmapped)}")
        for name, cps in unmapped[:20]:
            print(f"  {name}  ({' '.join(cps)})")
        if len(unmapped) > 20:
            print(f"  ... and {len(unmapped) - 20} more")


if __name__ == "__main__":
    main()
