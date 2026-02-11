#!/usr/bin/env python3
"""Rebuild effective_sizes in ICON_THEME_CATALOG.json from index.theme files.

For each theme with an index.theme, collects all effective sizes (Size x Scale)
from the parsed index directory entries. For themes with variants, aggregates
sizes across all variants into one list at the top-level catalog entry.

Themes without index.theme are skipped.

Usage:
    python scripts/icon_rebuild_catalog_sizes.py
"""

import os
import sys

from icon_theme_processor import ThemeCatalog


def main():
    catalog = ThemeCatalog()

    # Collect effective_sizes per top-level theme key (across all variants)
    theme_sizes = {}

    for theme in catalog:
        index_path = os.path.join(theme.dir, "index.theme")
        if not os.path.isfile(index_path):
            print(f"  {theme.theme_id}: no index.theme, skipping")
            continue

        dir_map = theme.index
        print(f"  {theme.theme_id}: {len(dir_map)} index entries")

        if theme.theme_base_id not in theme_sizes:
            theme_sizes[theme.theme_base_id] = set()

        for meta in dir_map.values():
            theme_sizes[theme.theme_base_id].add(meta["effective_size"])

    # Update catalog
    updated = False
    for theme_base_id, sizes in theme_sizes.items():
        config = catalog.raw[theme_base_id]
        new_sizes = sorted(sizes)
        old_sizes = config.get("effective_sizes", [])

        if new_sizes != old_sizes:
            print(f"  {theme_base_id} effective_sizes: {old_sizes} -> {new_sizes}")
            config["effective_sizes"] = new_sizes
            updated = True
        else:
            print(f"  {theme_base_id}: no changes")

    if updated:
        catalog.save()
        print(f"\nUpdated {catalog.path}")
    else:
        print(f"\nNo changes needed")


if __name__ == "__main__":
    main()
