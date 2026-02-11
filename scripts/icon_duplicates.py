#!/usr/bin/env python3
"""Find duplicate icon files by content hash, grouped by icon name.

Usage:
    python scripts/icon_duplicates.py <theme>

Arguments:
    theme: Theme directory name (nuvola, oxygen, papirus, breeze)

Reports icons where ALL sizes are duplicates first (full duplicates),
then icons with partial duplicates.

Examples:
    python scripts/icon_duplicates.py nuvola
    python scripts/icon_duplicates.py oxygen
"""

import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from icon_theme_processor import ThemeCatalog, fatal_error


def load_catalog_marked(data):
    """Extract duplicate marking info from metadata.

    Args:
        data: Parsed icons.json dict.

    Returns:
        (has_duplicates, has_duplicate_of, refers_to_map, catalog_by_name)
    """
    icons = data.get("icons", {})
    has_duplicates = set()  # icons with "duplicates" array (primary icons)
    has_duplicate_of = set()  # icons with "duplicate_of" field
    refers_to_map = {}  # target_id -> list of referrer keys
    catalog_by_name = {}  # icon key -> icon info dict

    for key, info in icons.items():
        catalog_by_name[key] = info

        if "duplicates" in info:
            has_duplicates.add(key)
        if "duplicate_of" in info:
            has_duplicate_of.add(key)
            target = info["duplicate_of"]
            if target not in refers_to_map:
                refers_to_map[target] = []
            refers_to_map[target].append(key)

    return has_duplicates, has_duplicate_of, refers_to_map, catalog_by_name


def hash_file(path):
    """Return MD5 hash of file contents."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def find_icons(start_path):
    """Find all PNG and SVG files under start_path."""
    icons = []
    for root, dirs, files in os.walk(start_path):
        for name in files:
            if name.lower().endswith((".png", ".svg")):
                icons.append(os.path.join(root, name))
    return icons


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2:
        catalog.print_available()
        fatal_error("Usage: python scripts/icon_duplicates.py <theme>")

    theme = catalog[sys.argv[1]]
    start_path = theme.dir

    print(f"Theme: {theme.theme_id}", file=sys.stderr)
    print(f"Scanning: {start_path}", file=sys.stderr)

    # Load metadata to see which icons are already marked
    data = theme.icons_data
    has_duplicates, has_duplicate_of, refers_to_map, catalog_by_name = load_catalog_marked(data)

    def get_dup_of(icon_id):
        """Get duplicate_of value for icon, or None."""
        return catalog_by_name.get(icon_id, {}).get("duplicate_of")

    def print_dup_of(icon_id, indent="    "):
        """Print HAS duplicate_of line if icon has one. Returns the value."""
        dup_of = get_dup_of(icon_id)
        if dup_of:
            print(f"{indent}HAS duplicate_of: {dup_of}")
        return dup_of

    def print_sym_target(sym_target, indent="              "):
        """Print SYMLINK TO line if icon at this size is a symlink."""
        if sym_target:
            print(f"{indent}SYMLINK TO -> {sym_target}")

    def print_symlink_dirs(file_paths):
        """Print SYMLINK DIRS section if any file path traverses a symlink directory.

        Note: Should never trigger because find_icons() uses os.walk which
        does not follow symlink directories. Kept as a safeguard.
        """
        sdirs = set()
        for rel_path in file_paths:
            for p in Path(rel_path).parents:
                key = str(p)
                if key in theme_symlink_dirs:
                    sdirs.add((key, theme_symlink_dirs[key]))
        if sdirs:
            print("      SYMLINK DIRS:")
            for source, target in sorted(sdirs):
                print(f"          {source}/ -> {target}/")

    # Find all icons
    all_files = find_icons(start_path)
    print(f"Found {len(all_files)} icon files", file=sys.stderr)

    # Build icon inventory: icon_id -> {size: (path, hash)}
    icons = defaultdict(dict)

    for i, path in enumerate(all_files):
        if (i + 1) % 500 == 0:
            print(f"Processing: {i + 1}/{len(all_files)}", file=sys.stderr)

        info = theme.get_file_info(path)
        size = info["effective_size"]
        context = info["xdg_context"]
        filename = info["file"]

        # Use canonical key from theme processor
        icon_id = theme.generate_id(context, filename)

        try:
            h = hash_file(path)
            rel_path = os.path.relpath(path, start_path)
            is_sym = Path(path).is_symlink()
            sym_target = None
            if is_sym:
                sym_target = os.path.relpath(os.path.realpath(path), start_path)
            icons[icon_id][size] = {
                "path": rel_path,
                "hash": h,
                "file_size": os.path.getsize(path),
                "is_symlink": is_sym,
                "symlink_target": sym_target,
            }
        except Exception as e:
            print(f"Error hashing {path}: {e}", file=sys.stderr)

    print(f"Found {len(icons)} unique icons", file=sys.stderr)

    # Scan for symlink directories under theme root (keyed by relative path)
    theme_symlink_dirs = {}  # rel_path -> target_rel_path
    for root, dirs, _files in os.walk(start_path, followlinks=False):
        for d in dirs:
            full = os.path.join(root, d)
            if os.path.islink(full):
                rel = os.path.relpath(full, start_path)
                target = os.path.relpath(os.path.realpath(full), os.path.realpath(start_path))
                theme_symlink_dirs[rel] = target

    # Build hash signature for each icon (sorted tuple of (size, hash) pairs)
    # This lets us compare if two icons have identical content at all sizes
    icon_signatures = {}  # icon_name -> signature (frozenset of hashes)
    for icon_name, size_data in icons.items():
        # Signature is just the set of hashes (size-independent)
        hashes = frozenset(d["hash"] for d in size_data.values())
        icon_signatures[icon_name] = hashes

    # Group icons by their hash sets to find full duplicates
    # Full duplicate = icons that have the exact same set of hashes
    sig_to_icons = defaultdict(list)
    for icon_name, sig in icon_signatures.items():
        sig_to_icons[sig].append(icon_name)

    # Find groups where all sizes match between icons
    full_dup_groups = []  # [(icon_names, sizes_info)]
    partial_dup_groups = []  # icons with some but not all sizes matching

    # Track which icons are already in full duplicate groups
    in_full_dup = set()

    # First pass: find icons with identical hash signatures
    for sig, icon_names in sig_to_icons.items():
        if len(icon_names) > 1:
            # These icons have the same set of hashes - full duplicates
            full_dup_groups.append(icon_names)
            in_full_dup.update(icon_names)

    # Second pass: find partial duplicates (same hash at individual sizes)
    # Build hash -> [(icon_name, size)] mapping
    hash_to_occurrences = defaultdict(list)
    for icon_name, size_data in icons.items():
        for size, d in size_data.items():
            hash_to_occurrences[d["hash"]].append((icon_name, size, d["path"]))

    # Find hashes that appear in multiple icons (partial dups)
    partial_dups = defaultdict(list)  # hash -> [(icon_name, size, path)]
    for h, occurrences in hash_to_occurrences.items():
        # Get unique icon names for this hash
        unique_icons = set(icon_name for icon_name, size, path in occurrences)
        if len(unique_icons) > 1:
            # This hash appears in multiple different icons
            partial_dups[h] = occurrences

    # Output
    print(f"\nFull duplicates: {len(full_dup_groups)} groups", file=sys.stderr)
    print(f"Partial duplicate hashes: {len(partial_dups)}", file=sys.stderr)
    print()

    # Section 1: Full duplicates (all sizes identical)
    if full_dup_groups:
        print("=" * 70)
        print("FULL DUPLICATES (all sizes of these icons are identical)")
        print("=" * 70)
        print()
        print("IMPORTANT INSTRUCTIONS: Process each duplicate group below ONE AT A TIME.")
        print("For each group, carefully review ALL icon names and choose the best")
        print("primary — typically the most generic or standard freedesktop name.")
        print()
        print("DO NOT use automation scripts. Each group must be reviewed and edited")
        print("by hand to ensure the correct primary is chosen.")
        print()
        print("Steps for each group:")
        print("  1. Read every icon name in the group")
        print("  2. Pick the best primary icon for the group")
        print("  3. On the primary entry in icons.json, add a \"duplicates\" array")
        print("     listing all the other keys")
        print("  4. On each copy entry in icons.json, add \"duplicate_of\" pointing")
        print("     to the primary key")
        print()
        print("Example (from nuvola — 1 primary + 2 copies):")
        print("  PRIMARY — gets \"duplicates\" array:")
        print("    \"nuvola_devices_media-optical\": {")
        print("      \"context\": \"devices\",")
        print("      \"file\": \"media-optical.png\",")
        print("      \"sizes\": [16, 22, 32, 48, 64, 128],")
        print("      \"duplicates\": [\"nuvola_actions_cd\", \"nuvola_actions_mix_cd\"],")
        print("      \"label\": \"Media Optical\"")
        print("    }")
        print("  COPY 1 — gets \"duplicate_of\":")
        print("    \"nuvola_actions_cd\": {")
        print("      \"context\": \"actions\",")
        print("      \"file\": \"cd.png\",")
        print("      \"sizes\": [16, 22, 32, 48],")
        print("      \"duplicate_of\": \"nuvola_devices_media-optical\",")
        print("      \"label\": \"Cd\"")
        print("    }")
        print("  COPY 2 — gets \"duplicate_of\":")
        print("    \"nuvola_actions_mix_cd\": {")
        print("      \"context\": \"actions\",")
        print("      \"file\": \"mix_cd.png\",")
        print("      \"sizes\": [22],")
        print("      \"duplicate_of\": \"nuvola_devices_media-optical\",")
        print("      \"label\": \"Mix Cd\"")
        print("    }")
        print()

        # Sort by group size descending, then by first icon name
        full_dup_groups.sort(key=lambda g: (-len(g), g[0]))

        for group in full_dup_groups:
            # Get size count from first icon in group
            first_icon = group[0]
            size_count = len(icons[first_icon])

            # Find icons that refer to any icon in this group via duplicate_of
            referring_icons = []
            for icon_id in group:
                if icon_id in refers_to_map:
                    for ref_id in refers_to_map[icon_id]:
                        if ref_id not in group:  # Don't include icons already in group
                            referring_icons.append(ref_id)

            # Check if ALL icons in this group are marked (either PRIMARY or duplicate_of)
            all_marked = all(n in has_duplicates or n in has_duplicate_of for n in group)
            marked_str = " [DONE]" if all_marked else ""

            print(f"# {len(group)} identical icons ({size_count} size{'s' if size_count != 1 else ''} each):{marked_str}")
            if not all_marked:
                print("    WORKER INSTRUCTIONS:")
                print(f"      DUPLICATES: {len(group)} identical icon files found.")
                print(f"        Pick one as primary, add \"duplicates\" array with the other keys.")
                print(f"        For each copy, add \"duplicate_of\" pointing to the primary key.")
                print("      ALL SIZES MATCH: Every file of every icon in this group is identical.")
                if referring_icons:
                    print("      DUPLICATE_OF REFERRERS:")
                    for ref_id in sorted(referring_icons):
                        print(f"        {ref_id}")
            # Show symlink dirs found in file paths of this group
            all_paths = [d["path"] for n in group for d in icons[n].values()]
            print_symlink_dirs(all_paths)
            for icon_name in sorted(group):
                size_data = icons[icon_name]
                sizes = sorted(size_data.keys())

                # Show marked status for each icon
                if icon_name in has_duplicates:
                    status = " [PRIMARY]"
                else:
                    status = ""

                print(f"    {icon_name}{status}")
                print_dup_of(icon_name, indent="        ")

                for size in sizes:
                    d = size_data[size]
                    sym_tag = "  (symlink)" if d["is_symlink"] else ""
                    print(f"        {size:4d}px  {d['hash'][:12]}  {d['path']}{sym_tag}")
                    print_sym_target(d["symlink_target"], indent="              ")

            # Show referrers and targets summary
            if referring_icons:
                print(f"    [+{len(referring_icons)} referrers: {', '.join(sorted(referring_icons))}]")

            targets_outside = set()
            for icon_id in group:
                icon_info = catalog_by_name.get(icon_id, {})
                dup_of = icon_info.get("duplicate_of")
                if dup_of and dup_of not in group:
                    targets_outside.add(dup_of)
            if targets_outside:
                print(f"    [This group refers to: {', '.join(sorted(targets_outside))}]")

            print()

    # Section 2: Partial duplicates - grouped by icon name
    # Find icons that have at least one size with a duplicate (excluding full dups)
    icons_with_partial_dups = set()
    for h, occurrences in partial_dups.items():
        unique_icons = set(icon_name for icon_name, size, path in occurrences)
        # Only consider icons not already in full duplicate groups
        non_full_dup_icons = unique_icons - in_full_dup
        if len(non_full_dup_icons) >= 1 and len(unique_icons) > 1:
            icons_with_partial_dups.update(non_full_dup_icons)

    if icons_with_partial_dups:
        print("=" * 70)
        print("PARTIAL DUPLICATES (icons with some matching files)")
        print("=" * 70)
        print()

        # Build reverse lookup: hash -> list of (icon_name, size) for duplicates
        hash_to_other_icons = defaultdict(list)
        for h, occurrences in partial_dups.items():
            for icon_name, size, path in occurrences:
                hash_to_other_icons[h].append((icon_name, size))

        # Sort icons by number of duplicate matches, then by name
        def count_dup_matches(icon_name):
            count = 0
            for size, (path, h, *_) in icons[icon_name].items():
                others = [n for n, s in hash_to_other_icons.get(h, []) if n != icon_name]
                count += len(others)
            return count

        sorted_icons = sorted(icons_with_partial_dups,
                              key=lambda n: (-count_dup_matches(n), n))

        for icon_name in sorted_icons:
            size_data = icons[icon_name]
            sizes = sorted(size_data.keys())

            # Collect ALL matching icons - track OTHER icon's matched sizes
            all_matches = {}  # other_name -> set of OTHER's sizes that matched
            for size, d in size_data.items():
                for other_name, other_size in hash_to_other_icons.get(d["hash"], []):
                    if other_name != icon_name:
                        if other_name not in all_matches:
                            all_matches[other_name] = set()
                        all_matches[other_name].add(other_size)  # Track THEIR size

            # Separate full-dup matches
            full_dup_matches = {k: v for k, v in all_matches.items() if k in in_full_dup}

            # Check if ALL sizes match a single other icon
            all_sizes_match_icon = None
            for other_name, match_sizes in all_matches.items():
                if match_sizes == set(sizes):
                    all_sizes_match_icon = other_name
                    break

            # Determine flags
            is_superset = False  # has more sizes AND matches all of other's sizes
            all_sizes_match = False  # ALL of our sizes match another icon
            all_sizes_match_icons = []  # icons where all our sizes match
            is_largest_match = False  # matches at largest common size
            has_multiple_full_dups = len(full_dup_matches) >= 2

            # Check superset and all-sizes-match against ALL matches
            for other_name, matched_other_sizes in all_matches.items():
                other_all_sizes = set(icons[other_name].keys())
                # Superset: we have more sizes AND matched ALL of their sizes
                if len(size_data) > len(other_all_sizes) and matched_other_sizes == other_all_sizes:
                    is_superset = True
                # All sizes match: ALL of our sizes match this other icon
                if len(matched_other_sizes) == len(size_data):
                    all_sizes_match = True
                    all_sizes_match_icons.append(other_name)

            for other_name, matched_other_sizes in full_dup_matches.items():
                # Check largest match: match at largest common size
                other_sizes = set(icons[other_name].keys())
                common_sizes = set(sizes) & other_sizes
                if common_sizes:
                    largest_common = max(common_sizes)
                    if largest_common in matched_other_sizes:
                        is_largest_match = True

            # Check if any matching full-dup icon has referrers (exclude self)
            referrer_info = []
            for other_id in full_dup_matches:
                if other_id in refers_to_map:
                    for ref_id in refers_to_map[other_id]:
                        if ref_id != icon_name:  # Don't include self
                            referrer_info.append(ref_id)
            has_referrers = len(referrer_info) > 0

            # Build status flags
            flags = []
            if all_sizes_match:
                flags.append("[ALL SIZES MATCH]")
            if is_superset:
                flags.append("[SUSPECTED SUPERSET]")
            if is_largest_match and not is_superset:
                flags.append("[REVIEW LARGEST]")
            if has_multiple_full_dups:
                flags.append("[REVIEW DUPLICATES]")
            if has_referrers:
                flags.append("[DUPLICATE_OF REFERRERS]")
            # Check catalog for duplicate_of and duplicates
            icon_info = catalog_by_name.get(icon_name, {})
            icon_dup_of = get_dup_of(icon_name)
            if icon_dup_of:
                flags.append("[DONE-DUPLICATE-OF]")

            # Check if this icon is [DONE] as PRIMARY
            # Requirements: has duplicates list, all listed have duplicate_of pointing here,
            # and all hash-matched icons are in the list
            icon_dups = icon_info.get("duplicates", [])
            is_done_primary = False
            if icon_dups:
                # Get all icons that match ALL our sizes (candidates for duplicates)
                expected_dups = set()
                for other_id, matched_sizes in all_matches.items():
                    # If other icon matches at ALL of our sizes, it should be a duplicate
                    if len(matched_sizes) == len(sizes):
                        expected_dups.add(other_id)

                # Check 1: All listed duplicates have duplicate_of pointing to us
                all_point_back = all(get_dup_of(d) == icon_name for d in icon_dups)

                # Check 2: All expected duplicates are in the list
                all_listed = expected_dups <= set(icon_dups)

                is_done_primary = all_point_back and all_listed
                if is_done_primary:
                    flags.append("[DONE-PRIMARY]")

            flag_str = " " + " ".join(flags) if flags else ""

            print(f"# {icon_name} ({len(sizes)} sizes){flag_str}")
            print_dup_of(icon_name)
            if icon_dups:
                print(f"    JSON DUPLICATES LIST:")
                for dup_id in icon_dups:
                    print(f"      {dup_id}")

            # Find largest PNG for this icon
            png_paths = [(s, d["path"]) for s, d in size_data.items() if d["path"].endswith('.png')]
            if not png_paths:
                continue  # Skip if no PNG
            largest_png = max(png_paths, key=lambda x: x[0])[1]

            # Print worker instructions if there are any duplicates
            if all_matches:
                print("    WORKER INSTRUCTIONS:")
                print(f"      DUPLICATES: {len(all_matches)} duplicate icon files found.")
                print(f"        If primary, add \"duplicates\" array with duplicate keys.")
                print(f"        If copy, add \"duplicate_of\" pointing to the primary key.")
                if all_sizes_match:
                    print("      ALL SIZES MATCH: Every size of this icon matches another icon.")
                    print("      This icon is likely duplicate_of that icon.")
                if is_superset:
                    print("      SUPERSET SUSPECTED: This icon has more sizes than matching icons.")
                    print("      This icon is likely the PRIMARY.")
                if is_largest_match and not is_superset:
                    print("      LARGEST MATCH: Largest common size is identical to [FULL-DUP] icons.")
                if has_multiple_full_dups:
                    print(f"      MULTIPLE DUPLICATES: Matches {len(full_dup_matches)} [FULL-DUP] icons.")
                if has_referrers:
                    print("      DUPLICATE_OF REFERRERS:")
                    for ref_id in sorted(referrer_info):
                        print(f"        {ref_id}")
                print("      ACTION - REQUIRED STEPS:")
                print("        1. List ALL sizes for EACH icon being compared")
                print("        2. View EVERY size for each icon - no exceptions")
                print("        3. DESCRIBE what you see in detail and search for differences")
                print("        4. WARNING: Different hashes may be visually identical!")
                print("        5. Compare side-by-side at each common size")
                print("        6. Only skip if images are VISUALLY DIFFERENT after viewing ALL")
                print("      Review these sections:")
                for match_id in sorted(all_matches.keys()):
                    print(f"        {match_id}")

            # Show symlink dirs found in file paths of this icon
            print_symlink_dirs([d["path"] for d in size_data.values()])

            for size in sizes:
                d = size_data[size]
                sym_tag = "  (symlink)" if d["is_symlink"] else ""
                # Find other icons with same hash at this size
                others = [(k, s) for k, s in hash_to_other_icons.get(d["hash"], [])
                          if k != icon_name]

                if others:
                    print(f"  {size:4d}px  {d['hash'][:12]}  {d['path']}  (duplicate){sym_tag}")
                    print_sym_target(d["symlink_target"], indent="          -> ")
                    for other_id, other_size in sorted(others):
                        other_d = icons[other_id][other_size]
                        other_sym_tag = "  (symlink)" if other_d["is_symlink"] else ""
                        print(f"  {other_size:4d}px  {d['hash'][:12]}  {other_d['path']}  (duplicate){other_sym_tag}")
                        print_sym_target(other_d["symlink_target"], indent="          -> ")
                        print_dup_of(other_id, indent="          -> ")
                else:
                    print(f"  {size:4d}px  {d['hash'][:12]}  {d['path']}  (unique){sym_tag}")
                    print_sym_target(d["symlink_target"], indent="          -> ")

            print()


if __name__ == "__main__":
    main()
