#!/usr/bin/env python3
"""Detect and tag symbolic (monochrome) icons in icons.json.

Pass 1 — Collect symbolic evidence by walking the theme directory:
  - Files in */symbolic/ or */symbolic-*/ directories (real or symlink targets)
  - Files whose stem ends with -symbolic

Pass 2 — Update icons.json:
  - For each icon without a "symbolic" property, set true if its filename
    matches the symbolic set. Does not overwrite existing values.

Usage:
    python scripts/icon_build_check_symbolic.py <theme>
"""

import os
import sys

from icon_theme_processor import (
    ICON_EXTENSIONS, ThemeCatalog, fatal_error, save_json_compact_arrays,
)


def is_symbolic_dir(dirpath, base):
    """Check if a directory path is a symbolic directory."""
    rel = os.path.relpath(dirpath, base)
    parts = rel.split(os.sep)
    return any(p == "symbolic" or p.startswith("symbolic-") for p in parts)


def collect_symbolic_files(theme_dir):
    """Walk theme directory and collect filenames that are symbolic.

    Returns a set of filenames (e.g., {"battery-symbolic.svg"}).
    """
    symbolic = set()
    base = theme_dir

    for dirpath, dirnames, filenames in os.walk(base):
        in_symbolic_dir = is_symbolic_dir(dirpath, base)

        for fn in filenames:
            stem, ext = os.path.splitext(fn)
            if ext.lower() not in ICON_EXTENSIONS:
                continue

            full = os.path.join(dirpath, fn)

            if in_symbolic_dir:
                if os.path.islink(full):
                    # Resolve symlink target, add its filename
                    target = os.path.realpath(full)
                    if os.path.isfile(target):
                        symbolic.add(os.path.basename(target))
                else:
                    symbolic.add(fn)

            # Anywhere: stem ends with -symbolic
            if stem.endswith("-symbolic"):
                symbolic.add(fn)

    return symbolic


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2:
        catalog.print_available()
        fatal_error("Usage: python scripts/icon_build_check_symbolic.py <theme>")

    theme = catalog[sys.argv[1]]

    print(f"Theme: {theme.theme_id}")
    print(f"Directory: {theme.dir}")

    # Pass 1: Collect symbolic files
    print(f"Scanning for symbolic icons...")
    symbolic_files = collect_symbolic_files(theme.dir)
    print(f"  Found {len(symbolic_files)} symbolic filenames")

    # Pass 2: Update icons.json
    data = theme.icons_data
    icons = data.get("icons", {})

    # Build reverse map: filename -> icon_ids
    file_to_icons = {}
    for icon_id, icon_data in icons.items():
        fn = icon_data.get("file")
        if fn:
            if fn not in file_to_icons:
                file_to_icons[fn] = []
            file_to_icons[fn].append(icon_id)

    updated = 0
    already_set = 0
    missing = 0
    for fn in sorted(symbolic_files):
        if fn not in file_to_icons:
            print(f"  WARNING: No icon entry for {fn}")
            missing += 1
            continue
        for icon_id in file_to_icons[fn]:
            icon_data = icons[icon_id]
            if "symbolic" in icon_data:
                already_set += 1
                continue
            icon_data["symbolic"] = True
            updated += 1

    print(f"  Already set: {already_set}")
    print(f"  Updated: {updated}")
    if missing:
        print(f"  Missing from icons.json: {missing}")

    if updated > 0:
        save_json_compact_arrays(theme.icons_path, data)
        print(f"  Saved {theme.icons_path}")
    else:
        print(f"  No changes needed")


if __name__ == "__main__":
    main()
