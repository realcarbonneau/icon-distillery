#!/usr/bin/env python3
"""Compare source theme metadata against target consumer copy.

Usage:
    python scripts/taskcoach_compare.py <theme>

Arguments:
    theme: Theme id (oxygen, nuvola, papirus, etc.)

Compares icons.json (fields: label, hints, context, duplicates),
contexts.json, and ICON_MAPPING.json between the icon-source
(source of truth) and the target consumer copy at
../taskcoach/taskcoachlib/gui/icons/<theme>/

Examples:
    python scripts/taskcoach_compare.py oxygen
    python scripts/taskcoach_compare.py nuvola
"""

import json
import sys

from icon_theme_processor import ThemeCatalog, _PROJECT_DIR, usage_error


_TARGET_ICONS_DIR = _PROJECT_DIR / ".." / "taskcoach" / "taskcoachlib" / "gui" / "icons"


def _section_header(title):
    """Print a section header."""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def _load_json(path):
    """Load a JSON file, return parsed dict."""
    with open(path) as f:
        return json.load(f)


def _find_target_themes():
    """Find target theme dirs that contain icons.json."""
    if not _TARGET_ICONS_DIR.is_dir():
        return []
    themes = []
    for d in sorted(_TARGET_ICONS_DIR.iterdir()):
        if d.is_dir() and (d / "icons.json").is_file():
            themes.append(d.name)
    return themes


def compare_contexts(source_contexts, target_contexts,
                     source_path, target_path):
    """Section 1: Compare contexts.json between source and target."""
    _section_header("CONTEXTS COMPARISON")
    print(f"  source: {source_path}")
    print(f"  target: {target_path}")

    source_keys = set(source_contexts.keys())
    target_keys = set(target_contexts.keys())

    source_only = sorted(source_keys - target_keys)
    target_only = sorted(target_keys - source_keys)
    shared = sorted(source_keys & target_keys)

    diffs = []
    for context_id in shared:
        s_ctx = source_contexts[context_id]
        t_ctx = target_contexts[context_id]
        for field in ("xdg_context", "context_label"):
            s_val = s_ctx.get(field)
            t_val = t_ctx.get(field)
            if s_val != t_val:
                diffs.append((context_id, field, s_val, t_val))

    if not source_only and not target_only and not diffs:
        print(f"\nAll {len(shared)} contexts match.")
        return

    if source_only:
        print(f"\nSource only ({len(source_only)}):")
        for context_id in source_only:
            xdg = source_contexts[context_id].get("xdg_context", "?")
            print(f"  {context_id} ({xdg})")

    if target_only:
        print(f"\nTarget only ({len(target_only)}):")
        for context_id in target_only:
            xdg = target_contexts[context_id].get("xdg_context", "?")
            print(f"  {context_id} ({xdg})")

    if diffs:
        print(f"\nValue differences ({len(diffs)}):")
        for context_id, field, s_val, t_val in diffs:
            print(f"  {context_id}.{field}: source={s_val}  target={t_val}")


def compare_inventory(source_icons, target_icons, source_path, target_path):
    """Section 2: Compare icon_id presence/absence."""
    _section_header("ICON INVENTORY")
    print(f"  source: {source_path}")
    print(f"  target: {target_path}")

    source_ids = set(source_icons.keys())
    target_ids = set(target_icons.keys())

    shared = sorted(source_ids & target_ids)
    source_only = sorted(source_ids - target_ids)
    target_only = sorted(target_ids - source_ids)

    # Per-context counts
    ctx_source = {}
    ctx_target = {}
    ctx_match = {}
    for icon_id in source_ids:
        ctx = source_icons[icon_id].get("context", "(none)")
        ctx_source[ctx] = ctx_source.get(ctx, 0) + 1
    for icon_id in target_ids:
        ctx = target_icons[icon_id].get("context", "(none)")
        ctx_target[ctx] = ctx_target.get(ctx, 0) + 1
    for icon_id in shared:
        ctx = source_icons[icon_id].get("context", "(none)")
        ctx_match[ctx] = ctx_match.get(ctx, 0) + 1

    all_contexts = sorted(set(ctx_source) | set(ctx_target))
    ctx_width = max(len(c) for c in all_contexts) if all_contexts else 0

    print(f"\n  {'':>{ctx_width}}  {'source':>6}  {'target':>6}  {'match':>5}")
    for ctx in all_contexts:
        s = ctx_source.get(ctx, 0)
        t = ctx_target.get(ctx, 0)
        m = ctx_match.get(ctx, 0)
        print(f"  {ctx:<{ctx_width}}  {s:>6}  {t:>6}  {m:>5}")
    print(f"  {'TOTAL':<{ctx_width}}  {len(source_ids):>6}  {len(target_ids):>6}  {len(shared):>5}")

    if target_only:
        print(f"\nTarget only ({len(target_only)}) — UNEXPECTED:")
        for icon_id in target_only:
            print(f"  {icon_id}")

    return shared


def _json_fragment(field, value):
    """Format a field/value pair as a JSON fragment."""
    return json.dumps({field: value}, ensure_ascii=False, separators=(", ", ": "))[1:-1]


def compare_fields(source_icons, target_icons, shared_keys, source_path, target_path):
    """Section 4: Compare field values for shared icons.

    Groups by icon_id; for each differing property, shows the full
    JSON key: value fragment from both source and target.
    """
    _section_header("FIELD DIFFERENCES")
    print(f"  source: {source_path}")
    print(f"  target: {target_path}")

    icons_with_diffs = []

    for icon_id in shared_keys:
        s = source_icons[icon_id]
        t = target_icons[icon_id]

        compare_fields = ("label", "hints", "context", "duplicate_of",
                          "duplicates")
        field_diffs = []
        for field in compare_fields:
            s_val = s.get(field)
            t_val = t.get(field)
            if s_val != t_val:
                field_diffs.append((field, s_val, t_val))

        if field_diffs:
            icons_with_diffs.append((icon_id, field_diffs))

    if not icons_with_diffs:
        print(f"\nAll {len(shared_keys)} shared icons have matching fields.")
        return

    print(f"\n{len(icons_with_diffs)} icons with field differences:\n")
    for icon_id, field_diffs in icons_with_diffs:
        print(f"  {icon_id}")
        for field, s_val, t_val in field_diffs:
            print(f"    source: {_json_fragment(field, s_val)}")
            print(f"    target: {_json_fragment(field, t_val)}")
        print()


def validate_icon_mapping(theme_name, source_icons, source_icons_path):
    """Section 5: Validate ICON_MAPPING.json entries against source."""
    _section_header("ICON_MAPPING VALIDATION")

    mapping_path = (_TARGET_ICONS_DIR / "ICON_MAPPING.json").resolve()
    if not mapping_path.is_file():
        print("\nICON_MAPPING.json not found — skipping.")
        return

    print(f"  source: {source_icons_path}")
    print(f"  target: {mapping_path}")

    mapping = _load_json(mapping_path)

    # Filter entries whose source matches theme_name
    relevant = {}
    for icon_id, entry in mapping.items():
        if icon_id.startswith("_"):
            continue
        if entry.get("source") == theme_name:
            relevant[icon_id] = entry

    if not relevant:
        print(f"\nNo ICON_MAPPING entries with source={theme_name}.")
        return

    print(f"\n{len(relevant)} mapping entries for source={theme_name}")

    errors = []

    def _check_entry(icon_id, entry, prefix=""):
        """Check a single mapping entry. Returns list of error strings."""
        entry_errors = []
        category = entry.get("category", "")
        filename = entry.get("file", "")

        # Find matching source icon by category (context) + file
        matched_id = None
        for src_icon_id, icon in source_icons.items():
            if icon.get("context") == category and icon.get("file") == filename:
                matched_id = src_icon_id
                break

        label = f"{prefix}{icon_id} -> {category}/{filename}"

        if matched_id is None:
            entry_errors.append(f"  {label}: NOT FOUND in source")

        # Check duplicates sub-entries
        for dup in entry.get("duplicates", []):
            if dup.get("source") == theme_name:
                dup_errors = _check_entry(icon_id, dup,
                                          prefix=f"{prefix}  (dup) ")
                entry_errors.extend(dup_errors)

        return entry_errors

    for icon_id, entry in sorted(relevant.items()):
        entry_errors = _check_entry(icon_id, entry)
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

    # Check target theme exists
    target_theme_dir = (_TARGET_ICONS_DIR / theme_name).resolve()
    target_icons_path = target_theme_dir / "icons.json"
    target_contexts_path = target_theme_dir / "contexts.json"

    if not target_theme_dir.is_dir() or not target_icons_path.is_file():
        available = _find_target_themes()
        print(f"target theme '{theme_name}' not found.", file=sys.stderr)
        if available:
            print(f"Available target themes: {', '.join(available)}",
                  file=sys.stderr)
        else:
            print(f"No target themes found in {_TARGET_ICONS_DIR}", file=sys.stderr)
        sys.exit(1)

    # Load source theme
    theme = catalog.get_theme(theme_name)
    source_icons_data = theme.icons_data
    source_icons = source_icons_data.get("icons", source_icons_data)
    # Handle both formats: {"icons": {...}} and bare dict
    if "icons" in source_icons_data and isinstance(source_icons_data["icons"], dict):
        source_icons = source_icons_data["icons"]

    source_contexts = theme.contexts

    # Load target data
    target_data = _load_json(target_icons_path)
    target_icons = target_data.get("icons", target_data)
    if "icons" in target_data and isinstance(target_data["icons"], dict):
        target_icons = target_data["icons"]

    target_contexts = None
    if target_contexts_path.is_file():
        target_contexts = _load_json(target_contexts_path)

    # Section 1: Contexts
    if source_contexts and target_contexts:
        compare_contexts(source_contexts, target_contexts,
                         theme.contexts_path, target_contexts_path)
    elif not target_contexts:
        _section_header("CONTEXTS COMPARISON")
        print(f"\nTarget contexts.json not found: {target_contexts_path}")
    elif not source_contexts:
        _section_header("CONTEXTS COMPARISON")
        print(f"\nSource contexts.json not found: {theme.contexts_path}")

    # Section 2: Icon inventory
    shared_keys = compare_inventory(source_icons, target_icons,
                                    theme.icons_path, target_icons_path)

    if shared_keys:
        # Section 3: Field differences
        compare_fields(source_icons, target_icons, shared_keys,
                       theme.icons_path, target_icons_path)

    # Section 4: ICON_MAPPING validation
    validate_icon_mapping(theme_name, source_icons, theme.icons_path)

    # Summary
    print(file=sys.stderr)
    print(f"Summary: {len(source_icons)} source, {len(target_icons)} target, "
          f"{len(shared_keys)} shared", file=sys.stderr)


if __name__ == "__main__":
    main()
