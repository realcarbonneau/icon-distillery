#!/usr/bin/env python3
"""Report filenames appearing in multiple XDG contexts.

Usage:
    python scripts/icon_context_conflicts.py <theme>

Arguments:
    theme: Theme directory name (nuvola, oxygen, papirus, breeze)

Per the XDG spec, Context is organizational only and not a namespace — the
same filename in different contexts creates ambiguous icon lookup.

Examples:
    python scripts/icon_context_conflicts.py papirus
    python scripts/icon_context_conflicts.py oxygen
"""

import os
import sys
from collections import defaultdict

from icon_theme_processor import ThemeCatalog, usage_error


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        catalog.print_available()
        usage_error(__doc__)

    theme = catalog.get_theme(sys.argv[1])
    start_path = theme.dir

    discovered = theme.scan_directory()
    print(f"Found {len(discovered)} unique icons", file=sys.stderr)

    # Group by bare filename across contexts
    # filename -> {context -> [relative_paths]}
    file_contexts = defaultdict(lambda: defaultdict(list))
    for icon_id, info in discovered.items():
        filename = info["file"]
        context = info["xdg_context"] or "(none)"
        for size in info["sizes"]:
            for path in info["paths"][size]:
                rel = os.path.relpath(path, start_path)
                file_contexts[filename][context].append(rel)

    # Find filenames in 2+ contexts
    conflicts = {fn: ctxs for fn, ctxs in file_contexts.items()
                 if len(ctxs) >= 2}

    if not conflicts:
        print("No cross-context conflicts found.", file=sys.stderr)
        return

    # Build flat rows: (filename, context, path)
    rows = []
    for filename, ctxs in conflicts.items():
        for context, paths in ctxs.items():
            for path in paths:
                rows.append((filename, context, path))

    rows.sort()

    print("=" * 70)
    print("CROSS-CONTEXT CONFLICTS (same filename in different contexts)")
    print("=" * 70)
    print()

    for filename, context, path in rows:
        print(f"{filename} {context} {path}")

    print(f"\n{len(conflicts)} filenames in multiple contexts, "
          f"{len(rows)} total entries", file=sys.stderr)


if __name__ == "__main__":
    main()
