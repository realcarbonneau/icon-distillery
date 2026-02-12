#!/usr/bin/env python3
"""Rebuild effective_sizes in ICON_THEME_CATALOG.json from index.theme files.

For each theme with an index.theme, collects all effective sizes (Size x Scale)
from the parsed index directory entries. For themes with variants, aggregates
sizes across all variants into one list at the top-level catalog entry.

Themes without index.theme are skipped.

Usage:
    python scripts/icon_rebuild_catalog_sizes.py
"""

import json
import os
import sys

from icon_theme_processor import ThemeCatalog, save_json_compact_arrays


def main():
    catalog = ThemeCatalog()

    # Collect effective_sizes per top-level theme key (across all variants)
    theme_sizes = {}

    for theme_id in catalog.theme_ids():
        theme = catalog.get_theme(theme_id)
        index_path = os.path.join(theme.dir, "index.theme")
        if not os.path.isfile(index_path):
            print(f"  no index.theme, skipping")
            continue

        dir_map = theme.index
        print(f"  {len(dir_map)} index entries")

        if theme.theme_base_id not in theme_sizes:
            theme_sizes[theme.theme_base_id] = set()

        for meta in dir_map.values():
            theme_sizes[theme.theme_base_id].add(meta["effective_size"])

    # Update catalog
    catalog_path = catalog.catalog_path()
    with open(catalog_path) as f:
        catalog_data = json.load(f)

    updated = False
    for theme_base_id, sizes in theme_sizes.items():
        new_sizes = sorted(sizes)
        old_sizes = catalog_data[theme_base_id].get("effective_sizes", [])

        if new_sizes != old_sizes:
            print(f"  {theme_base_id} effective_sizes: {old_sizes} -> {new_sizes}")
            catalog_data[theme_base_id]["effective_sizes"] = new_sizes
            updated = True
        else:
            print(f"  {theme_base_id}: no changes")

    if updated:
        save_json_compact_arrays(catalog_path, catalog_data)
        print(f"\nUpdated {catalog_path}")
    else:
        print(f"\nNo changes needed")


if __name__ == "__main__":
    main()
