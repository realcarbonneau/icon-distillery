#!/usr/bin/env python3
"""Generate 'label' field for icons in theme icons.json files.

Usage:
    python scripts/icon_generate_labels.py <theme> [--replace PATTERN REPLACEMENT ...]

Arguments:
    theme:   Theme directory name (nuvola, oxygen, papirus, breeze)
    --replace PATTERN REPLACEMENT
             Regex substitution applied to the filename stem before
             character validation. Can be specified multiple times;
             applied in order given.

Generates labels from filenames:
    - Replace c++ with Cpp (hardcoded)
    - Replace '-' and '_' with space
    - Apply --replace rules (if any)
    - Title case each word
    - Check final label for unexpected characters

Examples:
    python scripts/icon_generate_labels.py nuvola
    python scripts/icon_generate_labels.py oxygen --replace '\\.' ' '
    python scripts/icon_generate_labels.py oxygen --replace '\\.' ' ' --replace '\\+' 'plus'
"""

import json
import os
import re
import sys

from icon_theme_processor import ThemeCatalog, fatal_error, save_json_compact_arrays


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
        for pattern, repl in replacements:
            stem = re.sub(pattern, repl, stem)
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

    if len(sys.argv) < 2:
        catalog.print_available()
        fatal_error("Usage: python scripts/icon_generate_labels.py <theme>")

    theme = catalog[sys.argv[1]]
    replacements = []
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--replace':
            if i + 2 >= len(sys.argv):
                fatal_error("--replace requires PATTERN and REPLACEMENT")
            replacements.append((sys.argv[i + 1], sys.argv[i + 2]))
            i += 3
        else:
            fatal_error(f"Unknown argument '{sys.argv[i]}'")

    json_path = theme.icons_path
    data = theme.icons_data

    print(f"Theme: {theme.theme_id}")
    print(f"File: {json_path}")
    if replacements:
        for pattern, repl in replacements:
            print(f"  Replace: {pattern!r} -> {repl!r}")

    icons = data.get("icons", {})
    total = len(icons)
    already_have_name = 0
    names_added = 0
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

        icon_data["label"] = label
        names_added += 1

    if errors:
        print(f"\n--- ERRORS ({len(errors)}) - NOT PROCESSED ---")
        for e in errors:
            print(e)

    print(f"\n--- SUMMARY ---")
    print(f"Total icons: {total}")
    print(f"Already had name: {already_have_name}")
    print(f"Names added: {names_added}")
    print(f"Errors (skipped): {len(errors)}")

    if names_added > 0:
        save_json_compact_arrays(json_path, data)
        print(f"\nUpdated: {json_path}")
    else:
        print(f"\nNo changes needed.")


if __name__ == "__main__":
    main()
