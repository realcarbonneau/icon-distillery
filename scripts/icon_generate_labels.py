#!/usr/bin/env python3
"""Generate 'label' field for icons in theme icons.json files.

Usage:
    python scripts/icon_generate_labels.py <theme> [--replace OLD NEW ...] [--simulate]

Arguments:
    theme:   Theme directory name (nuvola, oxygen, papirus, breeze)
    --replace OLD NEW
             String substitution applied to the filename stem before
             character validation. Can be specified multiple times;
             applied in order given.
    --simulate
             Show what would change without writing to icons.json.

Generates labels from filenames:
    - Replace c++ with Cpp (hardcoded)
    - Replace '-' and '_' with space
    - Apply --replace rules (if any)
    - Title case each word
    - Check final label for unexpected characters

Examples:
    python scripts/icon_generate_labels.py nuvola
    python scripts/icon_generate_labels.py oxygen --replace '.' ' '
    python scripts/icon_generate_labels.py oxygen --simulate --replace '.' ' ' --replace '+' 'plus'
"""

import os
import re
import sys

from icon_theme_processor import ThemeCatalog, save_json_compact_arrays, usage_error


def generate_label(filename, replacements=None):
    """Generate display label from filename.

    Order: strip ext, c++ -> Cpp, -/_ -> space, custom replacements, title case.

    Examples:
        printer.png -> Printer
        multimedia-player.png -> Multimedia Player
        text-x-c++src.png -> Text X Cpp Src
    """
    stem = os.path.splitext(filename)[0]
    stem = stem.replace('c++', 'Cpp ')
    stem = stem.replace('-', ' ').replace('_', ' ')
    if replacements:
        for old, new in replacements:
            stem = stem.replace(old, new)
    return stem.title()


def check_label(label):
    """Check if label has unexpected characters.

    Expected: a-z, A-Z, 0-9, and space.
    Returns list of unexpected characters found, or empty list if clean.
    """
    unexpected = re.findall(r'[^a-zA-Z0-9 ]', label)
    return list(set(unexpected))


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        catalog.print_available()
        usage_error(__doc__)

    theme = catalog.get_theme(sys.argv[1])
    replacements = []
    simulate = False
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--replace':
            if i + 2 >= len(sys.argv):
                usage_error(__doc__, "--replace requires OLD and NEW arguments")
            replacements.append((sys.argv[i + 1], sys.argv[i + 2]))
            i += 3
        elif sys.argv[i] == '--simulate':
            simulate = True
            i += 1
        else:
            usage_error(__doc__, f"Unknown argument '{sys.argv[i]}'")

    json_path = theme.icons_path
    data = theme.icons_data

    print(f"File: {json_path}")
    if simulate:
        print(f"Mode: SIMULATE (no changes will be written)")
    if replacements:
        for old, new in replacements:
            print(f"  Replace: {old!r} -> {new!r}")

    icons = data.get("icons", {})
    total = len(icons)
    already_have_name = 0
    names_added = 0
    changes = []
    errors = []

    for icon_id, icon_data in icons.items():
        if "label" in icon_data:
            already_have_name += 1
            continue

        filename = icon_data.get("file", "")
        if not filename:
            errors.append(f"ERROR: {icon_id} has no 'file' field")
            continue

        label = generate_label(filename, replacements)

        unexpected = check_label(label)
        if unexpected:
            errors.append(f"{icon_id}\n    Label: \"{label}\"  ERROR: unexpected characters: {unexpected}")
            continue

        changes.append((icon_id, filename, label))
        if not simulate:
            icon_data["label"] = label
        names_added += 1

    if changes:
        print(f"\n--- CHANGES ({len(changes)}) ---")
        for icon_id, filename, label in changes:
            print(f"  {icon_id}")
            print(f"    {filename} -> \"{label}\"")

    if errors:
        print(f"\n--- ERRORS ({len(errors)}) - NOT PROCESSED ---")
        for e in errors:
            print(e)

    print(f"\n--- SUMMARY ---")
    print(f"Total icons: {total}")
    print(f"Already had name: {already_have_name}")
    print(f"Names added: {names_added}")
    print(f"Errors (skipped): {len(errors)}")

    if simulate:
        print(f"\nSimulation complete. No changes written.")
    elif names_added > 0:
        save_json_compact_arrays(json_path, data)
        print(f"\nUpdated: {json_path}")
    else:
        print(f"\nNo changes needed.")


if __name__ == "__main__":
    main()
