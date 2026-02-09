#!/usr/bin/env python3
"""Generate 'label' field for icons in theme metadata.json files.

Usage:
    python scripts/icon_generate_names.py <theme>

Arguments:
    theme: Theme directory name (nuvola, oxygen, papirus, breeze)

Generates labels from filenames:
    - Remove extension (.png, .svg)
    - Replace '-' and '_' with space
    - Title case each word

Logs warnings for filenames with unexpected characters (not [a-zA-Z0-9_-]).

Examples:
    python scripts/icon_generate_names.py nuvola
    python scripts/icon_generate_names.py oxygen
"""

import json
import os
import re
import sys

# Path setup — theme dirs are siblings of scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def discover_themes():
    """Discover available themes by finding directories with metadata.json."""
    themes = []
    for entry in sorted(os.listdir(PROJECT_DIR)):
        metadata = os.path.join(PROJECT_DIR, entry, "metadata.json")
        if os.path.isfile(metadata):
            themes.append(entry)
    return themes


def save_json_compact_arrays(filepath, data):
    """Save JSON with indent=2 but arrays on single lines."""
    text = json.dumps(data, indent=2)
    def collapse_array(match):
        content = match.group(0)
        collapsed = re.sub(r'\[\s+', '[', content)
        collapsed = re.sub(r'\s+\]', ']', collapsed)
        collapsed = re.sub(r',\s+', ', ', collapsed)
        return collapsed
    text = re.sub(r'\[\s*\n\s+[^\[\]]*?\s*\]', collapse_array, text)
    with open(filepath, "w") as f:
        f.write(text)


def generate_name_from_filename(filename):
    """Generate display name from filename.

    - Remove extension
    - Replace '-' and '_' with space
    - Title case each word

    Examples:
        printer.png -> Printer
        multimedia-player.png -> Multimedia Player
        print_printer.png -> Print Printer
    """
    stem = os.path.splitext(filename)[0]
    name = stem.replace('-', ' ').replace('_', ' ')
    name = name.title()
    return name


def check_unexpected_characters(filename):
    """Check if filename has unexpected characters.

    Expected: a-z, A-Z, 0-9, -, _, and . (for extension)
    Returns list of unexpected characters found, or empty list if clean.
    """
    stem = os.path.splitext(filename)[0]
    unexpected = re.findall(r'[^a-zA-Z0-9_-]', stem)
    return list(set(unexpected))


def main():
    available = discover_themes()

    if len(sys.argv) < 2:
        print("Usage: python scripts/icon_generate_names.py <theme>", file=sys.stderr)
        print(f"Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    theme = sys.argv[1]
    json_path = os.path.join(PROJECT_DIR, theme, "metadata.json")

    if not os.path.isfile(json_path):
        print(f"Error: {json_path} not found", file=sys.stderr)
        print(f"Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    print(f"Theme: {theme}")
    print(f"File: {json_path}")

    with open(json_path) as f:
        data = json.load(f)

    icons = data.get("icons", {})
    total = len(icons)
    already_have_name = 0
    names_added = 0
    errors = []

    for icon_key, icon_data in icons.items():
        if "label" in icon_data:
            already_have_name += 1
            continue

        filename = icon_data.get("file", "")
        if not filename:
            errors.append(f"ERROR: {icon_key} has no 'file' field")
            continue

        unexpected = check_unexpected_characters(filename)
        if unexpected:
            errors.append(f"ERROR: {icon_key} has unexpected characters: {unexpected}")
            continue

        name = generate_name_from_filename(filename)
        icon_data["label"] = name
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
