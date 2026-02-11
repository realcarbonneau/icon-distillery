#!/usr/bin/env python3
"""Build or verify icons.json inventory from index.theme and disk files.

Scans the theme directory for all PNG/SVG/SVGZ files in directories
declared in index.theme, skipping symlinks (files and directories)
and files in undeclared directories.

Modes:
  - If icons.json does not exist, builds it from disk scan.
  - If icons.json exists, reports differences:
      INDEXED ON DISK, NOT IN JSON — icons in valid index.theme
          directories but missing from icons.json
      IN JSON, NOT IN INDEXED DIRS — icons in icons.json but not found
          in any index.theme-declared directory on disk
      SIZE MISMATCH — icons where the sizes list differs
  - With --update-inserts: adds missing icons to icons.json.
      Does NOT remove or modify existing entries.

Usage:
    python scripts/icon_build_check_icons.py <theme> [--update-inserts]
"""

import os
import sys

from icon_theme_processor import ThemeCatalog, fatal_error, save_json_compact_arrays


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2:
        catalog.print_available()
        fatal_error("Usage: python scripts/icon_build_check_icons.py <theme> [--update-inserts]")

    theme_arg = None
    update_inserts = False
    for arg in sys.argv[1:]:
        if arg == "--update-inserts":
            update_inserts = True
        elif theme_arg is None:
            theme_arg = arg
        else:
            fatal_error(f"Unknown argument '{arg}'")

    if theme_arg is None:
        fatal_error("Theme argument required")

    theme = catalog[theme_arg]

    print(f"Theme: {theme.theme_id}")
    print(f"Directory: {theme.dir}")
    print(f"Scanning disk against index.theme...")

    discovered = theme.scan_directory()
    print(f"  Found {len(discovered)} icons on disk")

    json_path = theme.icons_path

    if not os.path.isfile(json_path):
        # Build new icons.json
        icons = {}
        for icon_id, info in sorted(discovered.items()):
            context = icon_id.split("_")[1] if "_" in icon_id else None
            entry = {
                "file": info["file"],
                "sizes": info["sizes"],
                "context": context,
            }
            if "symbolic" not in entry:
                stem, _ = os.path.splitext(info["file"])
                if stem.endswith("-symbolic"):
                    entry["symbolic"] = True
            icons[icon_id] = entry
        data = {
            "_comment": f"Auto-maintained catalog for {theme.theme_id} "
                        f"external theme. Icons/sizes are additive only.",
            "icons": icons,
        }
        save_json_compact_arrays(json_path, data)
        print(f"\nCreated {json_path} with {len(icons)} icons")
        return

    # Compare with existing icons.json
    data = theme.icons_data
    existing = data.get("icons", {})
    print(f"  icons.json has {len(existing)} icons")

    disk_ids = set(discovered.keys())
    json_ids = set(existing.keys())

    on_disk_not_json = sorted(disk_ids - json_ids)
    in_json_not_disk = sorted(json_ids - disk_ids)

    # Check size mismatches on shared icons
    size_mismatches = []
    for icon_id in sorted(disk_ids & json_ids):
        disk_sizes = discovered[icon_id]["sizes"]
        json_sizes = existing[icon_id].get("sizes", [])
        if disk_sizes != json_sizes:
            size_mismatches.append((icon_id, json_sizes, disk_sizes))

    # Report
    print(f"\nINDEXED ON DISK, NOT IN JSON: {len(on_disk_not_json)} icons")
    if on_disk_not_json:
        for icon_id in on_disk_not_json:
            info = discovered[icon_id]
            print(f"  {icon_id}")
            print(f"    file: {info['file']}  sizes: {info['sizes']}  "
                  f"xdg_context: {info['xdg_context']}")
    else:
        print(f"  *** None ***")

    print(f"\nIN JSON, NOT IN INDEXED DIRS: {len(in_json_not_disk)} icons")
    if in_json_not_disk:
        for icon_id in in_json_not_disk:
            info = existing[icon_id]
            print(f"  {icon_id}")
            print(f"    file: {info.get('file', '?')}  "
                  f"sizes: {info.get('sizes', '?')}  "
                  f"context: {info.get('context', '?')}")
    else:
        print(f"  *** None ***")

    print(f"\nSIZE MISMATCH: {len(size_mismatches)} icons")
    if size_mismatches:
        for icon_id, json_sizes, disk_sizes in size_mismatches:
            print(f"  {icon_id}")
            print(f"    json: {json_sizes}  disk: {disk_sizes}")
    else:
        print(f"  *** None ***")

    if not on_disk_not_json and not in_json_not_disk and not size_mismatches:
        print(f"\nAll {len(existing)} icons match between disk and icons.json")
    else:
        total = len(on_disk_not_json) + len(in_json_not_disk) + len(size_mismatches)
        print(f"\n{total} differences found")

    # Update inserts mode
    if not update_inserts:
        return
    if not on_disk_not_json:
        print("\nNo icons to insert")
        return

    added = 0
    for icon_id in on_disk_not_json:
        info = discovered[icon_id]
        context = icon_id.split("_")[1] if "_" in icon_id else None
        entry = {
            "file": info["file"],
            "sizes": info["sizes"],
            "context": context,
        }
        stem, _ = os.path.splitext(info["file"])
        if stem.endswith("-symbolic"):
            entry["symbolic"] = True
        existing[icon_id] = entry
        added += 1

    # Re-sort icons by key
    data["icons"] = dict(sorted(existing.items()))
    save_json_compact_arrays(json_path, data)
    print(f"\nInserted {added} icons into {json_path}")


if __name__ == "__main__":
    main()
