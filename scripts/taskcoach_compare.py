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
    for key in shared:
        s_ctx = source_contexts[key]
        t_ctx = target_contexts[key]
        for field in ("xdg_context", "context_label"):
            s_val = s_ctx.get(field)
            t_val = t_ctx.get(field)
            if s_val != t_val:
                diffs.append((key, field, s_val, t_val))

    if not source_only and not target_only and not diffs:
        print(f"\nAll {len(shared)} contexts match.")
        return

    if source_only:
        print(f"\nSource only ({len(source_only)}):")
        for key in source_only:
            xdg = source_contexts[key].get("xdg_context", "?")
            print(f"  {key} ({xdg})")

    if target_only:
        print(f"\nTarget only ({len(target_only)}):")
        for key in target_only:
            xdg = target_contexts[key].get("xdg_context", "?")
            print(f"  {key} ({xdg})")

    if diffs:
        print(f"\nValue differences ({len(diffs)}):")
        for key, field, s_val, t_val in diffs:
            print(f"  {key}.{field}: source={s_val}  target={t_val}")


def compare_inventory(source_icons, target_icons, source_path, target_path):
    """Section 2: Compare icon key presence/absence."""
    _section_header("ICON INVENTORY")
    print(f"  source: {source_path}")
    print(f"  target: {target_path}")

    source_keys = set(source_icons.keys())
    target_keys = set(target_icons.keys())

    shared = sorted(source_keys & target_keys)
    source_only = sorted(source_keys - target_keys)
    target_only = sorted(target_keys - source_keys)

    # Per-context counts
    ctx_source = {}
    ctx_target = {}
    ctx_match = {}
    for key in source_keys:
        ctx = source_icons[key].get("context", "(none)")
        ctx_source[ctx] = ctx_source.get(ctx, 0) + 1
    for key in target_keys:
        ctx = target_icons[key].get("context", "(none)")
        ctx_target[ctx] = ctx_target.get(ctx, 0) + 1
    for key in shared:
        ctx = source_icons[key].get("context", "(none)")
        ctx_match[ctx] = ctx_match.get(ctx, 0) + 1

    all_contexts = sorted(set(ctx_source) | set(ctx_target))
    ctx_width = max(len(c) for c in all_contexts) if all_contexts else 0

    print(f"\n  {'':>{ctx_width}}  {'source':>6}  {'target':>6}  {'match':>5}")
    for ctx in all_contexts:
        s = ctx_source.get(ctx, 0)
        t = ctx_target.get(ctx, 0)
        m = ctx_match.get(ctx, 0)
        print(f"  {ctx:<{ctx_width}}  {s:>6}  {t:>6}  {m:>5}")
    print(f"  {'TOTAL':<{ctx_width}}  {len(source_keys):>6}  {len(target_keys):>6}  {len(shared):>5}")

    if target_only:
        print(f"\nTarget only ({len(target_only)}) — UNEXPECTED:")
        for key in target_only:
            print(f"  {key}")

    return shared


def compare_fields(source_icons, target_icons, shared_keys, source_path, target_path):
    """Section 4: Compare field values for shared icons."""
    _section_header("FIELD DIFFERENCES")
    print(f"  source: {source_path}")
    print(f"  target: {target_path}")

    label_diffs = []
    hint_diffs = []
    context_diffs = []
    dup_of_diffs = []
    duplicates_diffs = []

    for key in shared_keys:
        s = source_icons[key]
        t = target_icons[key]

        # Label
        s_label = s.get("label")
        t_label = t.get("label")
        if s_label != t_label:
            label_diffs.append((key, s_label, t_label))

        # Hints
        s_hints = s.get("hints", [])
        t_hints = t.get("hints", [])
        if s_hints != t_hints:
            hint_diffs.append((key, s_hints, t_hints))

        # Context
        s_ctx = s.get("context")
        t_ctx = t.get("context")
        if s_ctx != t_ctx:
            context_diffs.append((key, s_ctx, t_ctx))

        # duplicate_of
        s_dup_of = s.get("duplicate_of")
        t_dup_of = t.get("duplicate_of")
        if s_dup_of != t_dup_of:
            dup_of_diffs.append((key, s_dup_of, t_dup_of))

        # duplicates
        s_dups = s.get("duplicates", [])
        t_dups = t.get("duplicates", [])
        if s_dups != t_dups:
            duplicates_diffs.append((key, s_dups, t_dups))

    total = (len(label_diffs) + len(hint_diffs) + len(context_diffs)
             + len(dup_of_diffs) + len(duplicates_diffs))

    if total == 0:
        print(f"\nAll {len(shared_keys)} shared icons have matching fields.")
        return

    if label_diffs:
        print(f"\nLabel differences ({len(label_diffs)}):")
        for key, s_val, t_val in label_diffs:
            print(f"  {key}")
            print(f"    source: {s_val}")
            print(f"    target: {t_val}")

    if hint_diffs:
        print(f"\nHint differences ({len(hint_diffs)}):")
        for key, s_val, t_val in hint_diffs:
            print(f"  {key}")
            print(f"    source: {s_val}")
            print(f"    target: {t_val}")

    if context_diffs:
        print(f"\nContext differences ({len(context_diffs)}):")
        for key, s_val, t_val in context_diffs:
            print(f"  {key}: source={s_val}  target={t_val}")

    if dup_of_diffs:
        print(f"\nduplicate_of differences ({len(dup_of_diffs)}):")
        for key, s_val, t_val in dup_of_diffs:
            print(f"  {key}: source={s_val}  target={t_val}")

    if duplicates_diffs:
        print(f"\nduplicates differences ({len(duplicates_diffs)}):")
        for key, s_val, t_val in duplicates_diffs:
            print(f"  {key}")
            print(f"    source: {s_val}")
            print(f"    target: {t_val}")


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

        # Find matching source icon by category (context) + file
        matched_key = None
        for key, icon in source_icons.items():
            if icon.get("context") == category and icon.get("file") == filename:
                matched_key = key
                break

        label = f"{prefix}{icon_name} -> {category}/{filename}"

        if matched_key is None:
            entry_errors.append(f"  {label}: NOT FOUND in source")

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
