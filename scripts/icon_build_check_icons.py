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
      IN JSON, NOT-INDEXED OR SYMLINK-ONLY OR NOT-ON-DISK — icons in
          icons.json but not found in any index.theme-declared directory
          on disk, or only present as symlinks, or missing entirely
      SIZE MISMATCH — icons where the sizes list differs
  - With --insert-missing: adds missing icons to icons.json.
      Does NOT remove or modify existing entries.
  - With --update-sizes: updates sizes arrays in icons.json to match disk.

Usage:
    python scripts/icon_build_check_icons.py <theme> [--insert-missing] [--update-sizes]
"""

import os
import sys

from icon_theme_processor import ThemeCatalog, save_json_compact_arrays, usage_error


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        catalog.print_available()
        usage_error(__doc__)

    theme_arg = None
    insert_missing = False
    update_sizes = False
    for arg in sys.argv[1:]:
        if arg == "--insert-missing":
            insert_missing = True
        elif arg == "--update-sizes":
            update_sizes = True
        elif theme_arg is None:
            theme_arg = arg
        else:
            usage_error(__doc__, f"Unknown argument '{arg}'")

    theme = catalog.get_theme(theme_arg)
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

    # Check path conflicts (multiple files of same extension at same icon id + size)
    # One file per extension type is permitted (e.g. one .svg + one .png is OK).
    from collections import Counter

    def _has_type_conflict(paths):
        exts = Counter(os.path.splitext(p)[1].lower() for p in paths)
        return any(c > 1 for c in exts.values())

    path_conflicts = []
    for icon_id in sorted(discovered):
        info = discovered[icon_id]
        for size in info["sizes"]:
            paths = info["paths"][size]
            if len(paths) > 1 and _has_type_conflict(paths):
                path_conflicts.append((icon_id, size, paths))
                break
    # Build full conflict info for reporting
    conflict_details = []
    for icon_id, _, _ in path_conflicts:
        info = discovered[icon_id]
        size_paths = {}
        for size in info["sizes"]:
            paths = info["paths"][size]
            if len(paths) > 1 and _has_type_conflict(paths):
                size_paths[size] = paths
        conflict_details.append((icon_id, size_paths))

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

    print(f"\nIN JSON, NOT-INDEXED OR SYMLINK-ONLY OR NOT-ON-DISK: {len(in_json_not_disk)} icons")
    if in_json_not_disk:
        for icon_id in in_json_not_disk:
            info = existing[icon_id]
            fn = info.get('file', '?')
            files = []
            for dirpath, dirnames, filenames in os.walk(theme.dir):
                dirnames[:] = [d for d in dirnames
                               if not os.path.islink(os.path.join(dirpath, d))]
                if fn in filenames:
                    full = os.path.join(dirpath, fn)
                    rel = theme.strip_dir_base(full)
                    is_link = os.path.islink(full)
                    if is_link:
                        raw_target = os.readlink(full)
                        dir_part = os.path.dirname(rel)
                        resolved = os.path.normpath(
                            os.path.join(dir_part, raw_target))
                        files.append(f"    {rel} -> {resolved}")
                    else:
                        files.append(f"    {rel} [REAL]")
            has_real = any("[REAL]" in f for f in files)
            if not files:
                flag = "[NOT-ON-DISK]"
            elif has_real:
                flag = "[MIXED]"
            else:
                flag = "[100%-SYMLINKS]"
            print(f"  {icon_id} {flag}")
            for f in files:
                print(f)
    else:
        print(f"  *** None ***")

    print(f"\nSIZE MISMATCH: {len(size_mismatches)} icons")
    if size_mismatches:
        for icon_id, json_sizes, disk_sizes in size_mismatches:
            print(f"  {icon_id}")
            print(f"    json: {json_sizes}  disk: {disk_sizes}")
    else:
        print(f"  *** None ***")

    print(f"\nPATH CONFLICTS: {len(conflict_details)} icons")
    if conflict_details:
        for icon_id, size_paths in conflict_details:
            print(f"  {icon_id}")
            for size, paths in sorted(size_paths.items()):
                rel_paths = [theme.strip_dir_base(p) for p in paths]
                print(f"    size {size}: {len(paths)} files")
                for rp in rel_paths:
                    print(f"      {rp}")
    else:
        print(f"  *** None ***")

    all_issues = [on_disk_not_json, in_json_not_disk, size_mismatches,
                  conflict_details]
    if not any(all_issues):
        print(f"\nAll {len(existing)} icons match between disk and icons.json")
    else:
        total = sum(len(x) for x in all_issues)
        print(f"\n{total} differences found")

    # Update sizes mode
    if update_sizes and size_mismatches:
        updated = 0
        for icon_id, json_sizes, disk_sizes in size_mismatches:
            existing[icon_id]["sizes"] = disk_sizes
            updated += 1
        save_json_compact_arrays(json_path, data)
        print(f"\nUpdated sizes for {updated} icons in {json_path}")
    elif update_sizes:
        print("\nNo size mismatches to update")

    # Update inserts mode
    if not insert_missing:
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

    save_json_compact_arrays(json_path, data)
    print(f"\nInserted {added} icons into {json_path}")


if __name__ == "__main__":
    main()
