#!/usr/bin/env python3
"""Compare distillery theme metadata against TaskCoach consumer copy.

Usage:
    python scripts/taskcoach_compare.py <theme>

Arguments:
    theme: Theme id (oxygen, nuvola, papirus, etc.)

Compares icons.json, contexts.json, and ICON_MAPPING.json between the
icon-distillery (source of truth) and the TaskCoach consumer copy at
../taskcoach/taskcoachlib/gui/icons/<theme>/

Examples:
    python scripts/taskcoach_compare.py oxygen
    python scripts/taskcoach_compare.py nuvola
"""

import json
import sys
from pathlib import Path

from icon_theme_processor import ThemeCatalog, _PROJECT_DIR, usage_error


_TC_ICONS_DIR = _PROJECT_DIR / ".." / "taskcoach" / "taskcoachlib" / "gui" / "icons"


def _section_header(title):
    """Print a section header."""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def _load_tc_json(path):
    """Load a JSON file, return parsed dict."""
    with open(path) as f:
        return json.load(f)


def _find_tc_themes():
    """Find TC theme dirs that contain icons.json."""
    if not _TC_ICONS_DIR.is_dir():
        return []
    themes = []
    for d in sorted(_TC_ICONS_DIR.iterdir()):
        if d.is_dir() and (d / "icons.json").is_file():
            themes.append(d.name)
    return themes


def compare_contexts(distillery_contexts, tc_contexts,
                     dist_path, tc_path):
    """Section 1: Compare contexts.json between distillery and TC."""
    _section_header("CONTEXTS COMPARISON")
    print(f"  source: {dist_path}")
    print(f"  target: {tc_path}")

    dist_keys = set(distillery_contexts.keys())
    tc_keys = set(tc_contexts.keys())

    dist_only = sorted(dist_keys - tc_keys)
    tc_only = sorted(tc_keys - dist_keys)
    shared = sorted(dist_keys & tc_keys)

    diffs = []
    for key in shared:
        d_ctx = distillery_contexts[key]
        t_ctx = tc_contexts[key]
        for field in ("xdg_context", "context_label"):
            d_val = d_ctx.get(field)
            t_val = t_ctx.get(field)
            if d_val != t_val:
                diffs.append((key, field, d_val, t_val))

    if not dist_only and not tc_only and not diffs:
        print(f"\nAll {len(shared)} contexts match.")
        return

    if dist_only:
        print(f"\nDistillery only ({len(dist_only)}):")
        for key in dist_only:
            xdg = distillery_contexts[key].get("xdg_context", "?")
            print(f"  {key} ({xdg})")

    if tc_only:
        print(f"\nTaskCoach only ({len(tc_only)}):")
        for key in tc_only:
            xdg = tc_contexts[key].get("xdg_context", "?")
            print(f"  {key} ({xdg})")

    if diffs:
        print(f"\nValue differences ({len(diffs)}):")
        for key, field, d_val, t_val in diffs:
            print(f"  {key}.{field}: distillery={d_val}  tc={t_val}")


def compare_inventory(dist_icons, tc_icons, dist_path, tc_path):
    """Section 2: Compare icon key presence/absence."""
    _section_header("ICON INVENTORY")
    print(f"  source: {dist_path}")
    print(f"  target: {tc_path}")

    dist_keys = set(dist_icons.keys())
    tc_keys = set(tc_icons.keys())

    shared = sorted(dist_keys & tc_keys)
    dist_only = sorted(dist_keys - tc_keys)
    tc_only = sorted(tc_keys - dist_keys)

    print(f"\nShared: {len(shared)}")

    if dist_only:
        # Group by context
        by_context = {}
        for key in dist_only:
            ctx = dist_icons[key].get("context", "(none)")
            if ctx not in by_context:
                by_context[ctx] = []
            by_context[ctx].append(key)

        print(f"Distillery only: {len(dist_only)}")
        for ctx in sorted(by_context.keys()):
            print(f"  {ctx}: {len(by_context[ctx])}")

    if tc_only:
        print(f"\nTaskCoach only ({len(tc_only)}) — UNEXPECTED:")
        for key in tc_only:
            print(f"  {key}")

    return shared


def compare_sizes(dist_icons, tc_icons, shared_keys, dist_path, tc_path):
    """Section 3: Compare source_sizes (TC) vs sizes (distillery)."""
    _section_header("SOURCE_SIZES COMPARISON")
    print(f"  source: {dist_path}")
    print(f"  target: {tc_path}")

    mismatches = []
    for key in shared_keys:
        dist_sizes = dist_icons[key].get("sizes", [])
        tc_source_sizes = tc_icons[key].get("source_sizes", [])
        if dist_sizes != tc_source_sizes:
            tc_local_sizes = tc_icons[key].get("sizes", [])
            mismatches.append((key, dist_sizes, tc_source_sizes, tc_local_sizes))

    if not mismatches:
        print(f"\nAll {len(shared_keys)} shared icons have matching sizes.")
        return

    print(f"\nMismatches ({len(mismatches)}):")
    for key, dist_sizes, tc_source, tc_local in mismatches:
        print(f"  {key}")
        print(f"    distillery sizes:    {dist_sizes}")
        print(f"    tc source_sizes:     {tc_source}")
        print(f"    tc local sizes:      {tc_local}")


def compare_fields(dist_icons, tc_icons, shared_keys, dist_path, tc_path):
    """Section 4: Compare field values for shared icons."""
    _section_header("FIELD DIFFERENCES")
    print(f"  source: {dist_path}")
    print(f"  target: {tc_path}")

    label_diffs = []
    hint_diffs = []
    context_diffs = []
    dup_of_diffs = []
    duplicates_diffs = []

    for key in shared_keys:
        d = dist_icons[key]
        t = tc_icons[key]

        # Label
        d_label = d.get("label")
        t_label = t.get("label")
        if d_label != t_label:
            label_diffs.append((key, d_label, t_label))

        # Hints
        d_hints = d.get("hints", [])
        t_hints = t.get("hints", [])
        if d_hints != t_hints:
            d_set = set(d_hints)
            t_set = set(t_hints)
            if d_set == t_set:
                hint_diffs.append((key, "order-only", d_hints, t_hints))
            else:
                added = sorted(d_set - t_set)
                removed = sorted(t_set - d_set)
                hint_diffs.append((key, "content", added, removed))

        # Context
        d_ctx = d.get("context")
        t_ctx = t.get("context")
        if d_ctx != t_ctx:
            context_diffs.append((key, d_ctx, t_ctx))

        # duplicate_of
        d_dup_of = d.get("duplicate_of")
        t_dup_of = t.get("duplicate_of")
        if d_dup_of != t_dup_of:
            dup_of_diffs.append((key, d_dup_of, t_dup_of))

        # duplicates
        d_dups = d.get("duplicates", [])
        t_dups = t.get("duplicates", [])
        if d_dups != t_dups:
            duplicates_diffs.append((key, d_dups, t_dups))

    total = (len(label_diffs) + len(hint_diffs) + len(context_diffs)
             + len(dup_of_diffs) + len(duplicates_diffs))

    if total == 0:
        print(f"\nAll {len(shared_keys)} shared icons have matching fields.")
        return

    if label_diffs:
        print(f"\nLabel differences ({len(label_diffs)}):")
        for key, d_val, t_val in label_diffs:
            print(f"  {key}")
            print(f"    distillery: {d_val}")
            print(f"    tc:         {t_val}")

    if hint_diffs:
        content_diffs = [h for h in hint_diffs if h[1] == "content"]
        order_diffs = [h for h in hint_diffs if h[1] == "order-only"]

        if content_diffs:
            print(f"\nHint differences ({len(content_diffs)}):")
            for key, _, added, removed in content_diffs:
                parts = []
                if added:
                    parts.append(f"in distillery only: {added}")
                if removed:
                    parts.append(f"in tc only: {removed}")
                print(f"  {key}: {'; '.join(parts)}")

        if order_diffs:
            print(f"\nHint order-only differences ({len(order_diffs)}):")
            for key, _, d_hints, t_hints in order_diffs:
                print(f"  {key}")

    if context_diffs:
        print(f"\nContext differences ({len(context_diffs)}):")
        for key, d_val, t_val in context_diffs:
            print(f"  {key}: distillery={d_val}  tc={t_val}")

    if dup_of_diffs:
        print(f"\nduplicate_of differences ({len(dup_of_diffs)}):")
        for key, d_val, t_val in dup_of_diffs:
            print(f"  {key}: distillery={d_val}  tc={t_val}")

    if duplicates_diffs:
        print(f"\nduplicates differences ({len(duplicates_diffs)}):")
        for key, d_val, t_val in duplicates_diffs:
            print(f"  {key}")
            print(f"    distillery: {d_val}")
            print(f"    tc:         {t_val}")


def validate_icon_mapping(theme_name, dist_icons, dist_icons_path):
    """Section 5: Validate ICON_MAPPING.json entries against distillery."""
    _section_header("ICON_MAPPING VALIDATION")

    mapping_path = (_TC_ICONS_DIR / "ICON_MAPPING.json").resolve()
    if not mapping_path.is_file():
        print("\nICON_MAPPING.json not found — skipping.")
        return

    print(f"  source: {dist_icons_path}")
    print(f"  target: {mapping_path}")

    mapping = _load_tc_json(mapping_path)

    # Filter entries whose source matches theme_name
    relevant = {}
    for icon_name, entry in mapping.items():
        if icon_name.startswith("_"):
            continue
        if entry.get("source") == theme_name:
            relevant[icon_name] = entry

    if not relevant:
        print(f"\nNo ICON_MAPPING entries with source={theme_name}.")
        return

    print(f"\n{len(relevant)} mapping entries for source={theme_name}")

    errors = []

    def _check_entry(icon_name, entry, prefix=""):
        """Check a single mapping entry. Returns list of error strings."""
        entry_errors = []
        category = entry.get("category", "")
        filename = entry.get("file", "")
        source_sizes_str = entry.get("source_sizes", "")

        # Find matching distillery icon by category (context) + file
        matched_key = None
        for key, icon in dist_icons.items():
            if icon.get("context") == category and icon.get("file") == filename:
                matched_key = key
                break

        label = f"{prefix}{icon_name} -> {category}/{filename}"

        if matched_key is None:
            entry_errors.append(f"  {label}: NOT FOUND in distillery")
        else:
            # Compare source_sizes
            if source_sizes_str:
                try:
                    mapping_sizes = [int(x) for x in source_sizes_str.split(",")]
                except ValueError:
                    entry_errors.append(
                        f"  {label}: invalid source_sizes '{source_sizes_str}'")
                    mapping_sizes = None

                if mapping_sizes is not None:
                    dist_sizes = dist_icons[matched_key].get("sizes", [])
                    if mapping_sizes != dist_sizes:
                        entry_errors.append(
                            f"  {label}: sizes mismatch\n"
                            f"    mapping source_sizes: {mapping_sizes}\n"
                            f"    distillery sizes:     {dist_sizes}")

        # Check duplicates sub-entries
        for dup in entry.get("duplicates", []):
            if dup.get("source") == theme_name:
                dup_errors = _check_entry(icon_name, dup,
                                          prefix=f"{prefix}  (dup) ")
                entry_errors.extend(dup_errors)

        return entry_errors

    for icon_name, entry in sorted(relevant.items()):
        entry_errors = _check_entry(icon_name, entry)
        errors.extend(entry_errors)

    if not errors:
        print(f"All {len(relevant)} entries valid.")
    else:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(err)


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        catalog.print_available()
        usage_error(__doc__)

    theme_name = sys.argv[1]

    # Check TC theme exists
    tc_theme_dir = (_TC_ICONS_DIR / theme_name).resolve()
    tc_icons_path = tc_theme_dir / "icons.json"
    tc_contexts_path = tc_theme_dir / "contexts.json"

    if not tc_theme_dir.is_dir() or not tc_icons_path.is_file():
        available = _find_tc_themes()
        print(f"TaskCoach theme '{theme_name}' not found.", file=sys.stderr)
        if available:
            print(f"Available TC themes: {', '.join(available)}",
                  file=sys.stderr)
        else:
            print(f"No TC themes found in {_TC_ICONS_DIR}", file=sys.stderr)
        sys.exit(1)

    # Load distillery theme
    theme = catalog.get_theme(theme_name)
    dist_icons_data = theme.icons_data
    dist_icons = dist_icons_data.get("icons", dist_icons_data)
    # Handle both formats: {"icons": {...}} and bare dict
    if "icons" in dist_icons_data and isinstance(dist_icons_data["icons"], dict):
        dist_icons = dist_icons_data["icons"]

    dist_contexts = theme.contexts

    # Load TC data
    tc_data = _load_tc_json(tc_icons_path)
    tc_icons = tc_data.get("icons", tc_data)
    if "icons" in tc_data and isinstance(tc_data["icons"], dict):
        tc_icons = tc_data["icons"]

    tc_contexts = None
    if tc_contexts_path.is_file():
        tc_contexts = _load_tc_json(tc_contexts_path)

    # Section 1: Contexts
    if dist_contexts and tc_contexts:
        compare_contexts(dist_contexts, tc_contexts,
                         theme.contexts_path, tc_contexts_path)
    elif not tc_contexts:
        _section_header("CONTEXTS COMPARISON")
        print(f"\nTaskCoach contexts.json not found: {tc_contexts_path}")
    elif not dist_contexts:
        _section_header("CONTEXTS COMPARISON")
        print(f"\nDistillery contexts.json not found: {theme.contexts_path}")

    # Section 2: Icon inventory
    shared_keys = compare_inventory(dist_icons, tc_icons,
                                    theme.icons_path, tc_icons_path)

    if shared_keys:
        # Section 3: Sizes
        compare_sizes(dist_icons, tc_icons, shared_keys,
                      theme.icons_path, tc_icons_path)

        # Section 4: Field differences
        compare_fields(dist_icons, tc_icons, shared_keys,
                       theme.icons_path, tc_icons_path)

    # Section 5: ICON_MAPPING validation
    validate_icon_mapping(theme_name, dist_icons, theme.icons_path)

    # Summary
    print(file=sys.stderr)
    print(f"Summary: {len(dist_icons)} distillery, {len(tc_icons)} tc, "
          f"{len(shared_keys)} shared", file=sys.stderr)


if __name__ == "__main__":
    main()
