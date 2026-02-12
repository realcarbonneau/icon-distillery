#!/usr/bin/env python3
"""Build or check contexts.json for each theme from index.theme.

For each theme with an index.theme, collects the unique XDG Context= values
and derives the internal_context_id (lowercase) for each.

If contexts.json does not exist, builds it.
If contexts.json already exists, checks against index.theme and reports
differences for manual review — does NOT auto-update.

Also validates icons.json icons: checks that every icon has a context
property and that every context value is a valid internal_context_id.

Also updates the xdg_contexts summary list in ICON_THEME_CATALOG.json,
aggregated across all variants per base theme.

Usage:
    python scripts/icon_build_check_contexts.py <theme>
"""

import json
import os
import sys

from icon_theme_processor import ThemeCatalog, save_json_compact_arrays, usage_error


# Default overrides applied after lowercase conversion.
_DEFAULT_CONTEXT_IDS = {
    "applications": "apps",
}


def build_contexts_from_index(theme_index_dir_map):
    """Build contexts dict from parsed index.theme dir_map.

    Skips directory entries with no Context= (permitted by XDG spec).

    Returns:
        dict keyed by internal_context_id, each value has
        xdg_context and context_label.
    """
    contexts = {}
    for dir_path, meta in theme_index_dir_map.items():
        xdg_context = meta["xdg_context"]
        if xdg_context is None:
            continue
        internal_context_id = xdg_context.lower()
        internal_context_id = _DEFAULT_CONTEXT_IDS.get(
            internal_context_id, internal_context_id)
        if internal_context_id not in contexts:
            contexts[internal_context_id] = {
                "xdg_context": xdg_context,
                "context_label": xdg_context,
            }
    return dict(sorted(contexts.items()))


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        catalog.print_available()
        usage_error(__doc__)

    theme = catalog.get_theme(sys.argv[1])
    had_differences = False

    contexts = build_contexts_from_index(theme.index)
    existing = theme.contexts
    contexts_path = theme.contexts_path

    if existing is None:
        save_json_compact_arrays(contexts_path, contexts)
        keys = ", ".join(contexts.keys())
        print(f"  {theme.theme_id}: created contexts.json ({len(contexts)} contexts: {keys})")
    else:
        # Compare existing with generated from index
        existing_keys = set(existing.keys())
        contexts_keys = set(contexts.keys())

        in_json_not_theme_index = existing_keys - contexts_keys
        in_theme_index_not_json = contexts_keys - existing_keys

        # Check for xdg_context value changes on shared keys
        xdg_changed = []
        for key in sorted(existing_keys & contexts_keys):
            old_xdg = existing[key].get("xdg_context")
            new_xdg = contexts[key].get("xdg_context")
            if old_xdg != new_xdg:
                xdg_changed.append((key, old_xdg, new_xdg))

        if not in_json_not_theme_index and not in_theme_index_not_json and not xdg_changed:
            print(f"  {theme.theme_id}: contexts.json up to date ({len(existing)} contexts)")
        else:
            had_differences = True
            print(f"  {theme.theme_id}: DIFFERENCES FOUND")

            if in_theme_index_not_json:
                for key in sorted(in_theme_index_not_json):
                    xdg = contexts[key]["xdg_context"]
                    print(f"    IN THEME-INDEX, NOT IN JSON: {key} (xdg_context={xdg})")

            if in_json_not_theme_index:
                for key in sorted(in_json_not_theme_index):
                    xdg = existing[key].get("xdg_context", "?")
                    print(f"    IN JSON, NOT IN THEME-INDEX: {key} (xdg_context={xdg})")

            if xdg_changed:
                for key, old_xdg, new_xdg in xdg_changed:
                    print(f"    XDG_CONTEXT CHANGED: {key}: {old_xdg} -> {new_xdg}")

            print(f"    Manual review required. Edit {contexts_path}")

        # Validate icons.json icon contexts
        if os.path.isfile(theme.icons_path):
            valid_contexts = existing_keys
            metadata = theme.icons_data
            icons = metadata.get("icons", {})
            missing_context = []
            invalid_context = {}
            for icon_id, icon_data in icons.items():
                ctx = icon_data.get("context")
                if ctx is None:
                    missing_context.append(icon_id)
                elif ctx not in valid_contexts:
                    if ctx not in invalid_context:
                        invalid_context[ctx] = []
                    invalid_context[ctx].append(icon_id)

            if missing_context or invalid_context:
                had_differences = True
                print(f"  {theme.theme_id}: METADATA CONTEXT ERRORS")
                if missing_context:
                    print(f"    MISSING CONTEXT: {len(missing_context)} icons have no context property")
                    for icon_id in missing_context:
                        print(f"      {icon_id}")
                if invalid_context:
                    for ctx, icon_ids in sorted(invalid_context.items()):
                        print(f"    INVALID CONTEXT '{ctx}': {len(icon_ids)} icons")
                        for icon_id in icon_ids:
                            print(f"      {icon_id}")
            else:
                if icons:
                    print(f"  {theme.theme_id}: icons.json contexts valid ({len(icons)} icons)")

    # Update xdg_contexts in catalog
    xdg_set = {ctx_info["xdg_context"] for ctx_info in contexts.values()}
    catalog_path = catalog.catalog_path()
    with open(catalog_path) as f:
        catalog_data = json.load(f)

    new_list = sorted(xdg_set)
    old_list = catalog_data[theme.theme_base_id].get("xdg_contexts", [])
    if new_list != old_list:
        print(f"  {theme.theme_base_id} xdg_contexts: {old_list} -> {new_list}")
        catalog_data[theme.theme_base_id]["xdg_contexts"] = new_list
        save_json_compact_arrays(catalog_path, catalog_data)
        print(f"\nUpdated {catalog_path}")

    if had_differences:
        print("\nDifferences found — manual intervention required.")


if __name__ == "__main__":
    main()
