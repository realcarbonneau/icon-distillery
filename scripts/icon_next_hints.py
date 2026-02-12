#!/usr/bin/env python3
"""Find the next icon without hints in a theme's icons.json and list all image paths.

Usage:
    python scripts/icon_next_hints.py <theme>

Arguments:
    theme: Theme directory name (nuvola, oxygen, papirus, breeze)

For each icon, searches the theme directory for every file matching the bare
filename within the icon's context directories.  The worker does the analysis.

Examples:
    python scripts/icon_next_hints.py nuvola
    python scripts/icon_next_hints.py oxygen
"""

import os
import sys
from pathlib import Path

from icon_theme_processor import (
    ThemeCatalog, _PROJECT_DIR, fatal_error, save_json_compact_arrays,
)

# PNG magic header: first 8 bytes of any valid PNG file
_PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def rel_path(abs_path):
    """Convert absolute path to relative path from PROJECT_DIR."""
    rel = os.path.relpath(abs_path, _PROJECT_DIR)
    if not rel.startswith(".."):
        rel = "./" + rel
    return rel


def valid_png(path):
    """Check if file has a valid PNG magic header."""
    try:
        with open(path, "rb") as f:
            return f.read(8) == _PNG_MAGIC
    except (OSError, IOError):
        return False


def log_anomaly(theme, message):
    """Log to anomaly file in the theme directory."""
    anomaly_file = os.path.join(theme.dir, f"{theme.theme_id}_anomalies.txt")
    with open(anomaly_file, "a") as af:
        af.write(f"{message}\n")
    print(f"Logged to: {rel_path(anomaly_file)}")


def main():
    catalog = ThemeCatalog()

    if len(sys.argv) < 2:
        catalog.print_available()
        fatal_error("Usage: python scripts/icon_next_hints.py <theme>")

    theme = catalog.get_theme(sys.argv[1])
    json_path = theme.icons_path
    data = theme.icons_data

    icons = data.get("icons", {})
    total = len(icons)
    done = sum(1 for v in icons.values() if "hints" in v)

    for icon_id, icon_data in icons.items():
        if "hints" in icon_data:
            continue

        # Found the next Named Icon to process
        file_errors = []

        def log_file_error(error_msg):
            full_error = f"FILE_ERROR: {error_msg}"
            file_errors.append(full_error)
            log_anomaly(theme, f"{icon_id}: {full_error}")

        # Get file and context directly from icon_data
        filename = icon_data["file"]
        context = icon_data["context"]

        # Find all files in this context's directories (PNGs, SVGs, SVGZs)
        disk_files = theme.find_icon_files_in_context(context, filename)

        # IMPORTANT TODO: PNG creation from SVGs should be a separate
        # preparation script (see ICON_METADATA.md TODO #10).  This inline
        # conversion duplicates work that other scripts will also need.

        # Build viewable PNG list from disk files.
        # For each SVG/SVGZ, ensure a matching PNG exists (convert if needed).
        # PNGs found directly on disk are validated and collected.
        png_files = set()
        for path in disk_files:
            if path.endswith(".png"):
                if os.path.getsize(path) == 0:
                    log_file_error(f"PNG empty: {path}")
                elif not valid_png(path):
                    log_file_error(f"PNG invalid header: {path}")
                else:
                    png_files.add(path)
            elif path.endswith((".svg", ".svgz")):
                png_path = str(Path(path).with_suffix(".png"))
                if os.path.exists(png_path) and os.path.getsize(png_path) > 0 and valid_png(png_path):
                    png_files.add(png_path)
                else:
                    result = theme.convert_svg_to_png(path)
                    if not result.endswith(".png"):
                        log_file_error(result)
                    elif not os.path.exists(result) or os.path.getsize(result) == 0:
                        log_file_error(f"PNG missing or empty after conversion: {result}")
                    elif not valid_png(result):
                        log_file_error(f"PNG invalid header after conversion: {result}")
                    else:
                        png_files.add(result)
        png_files = sorted(png_files)

        # If file errors, set hints and skip to next icon
        if file_errors:
            icon_data["hints"] = file_errors
            save_json_compact_arrays(json_path, data)
            continue

        # Build file info for display
        file_info = []
        for path in png_files:
            info = theme.get_file_info(path)
            file_info.append(info)

        print(f"CURRENT JSON ENTRY ({rel_path(json_path)})")
        print(f"  \"key\": \"{icon_id}\"")

        # Sort by file size descending (largest first for worker)
        file_info.sort(key=lambda x: x["file_size"], reverse=True)

        print("DISK_FILES:")
        for info in file_info:
            print(f"  {info['file_size']}b  {rel_path(info['path'])}")

        # Worker instruction blocks
        print("NEXT STEP - WORKER INSTRUCTIONS")
        print("- View the largest PNG file (the first PNG in the list). Then, generate 5-8 \"hints\"")
        print("  based on what you SEE in the image + filename context. Then, edit the JSON to")
        print("  add \"hints\": [...] array for this icon's key. Format: \"hints\" must be a")
        print("  SINGLE LINE array, e.g.: \"hints\": [\"keyword1\", \"keyword2\", ...]")
        print("- If stuck (unreadable, missing, ambiguous): add \"hints\": [\"FATAL-ERROR\"] to the JSON,")
        print("  log the issue to the anomaly file, then run the script again to continue.")
        anomaly_path = rel_path(os.path.join(theme.dir, f"{theme.theme_id}_anomalies.txt"))
        print(f"  Anomaly log: {anomaly_path}")
        print("- Commit and push branch icon-hints after processing ~25 icons, as a safety")
        print("  against a power failure, however this is NOT mean you have completed the work!")
        print("- Run this script again to get the next icon")
        print("- Go back to step 1 and execute the steps again (do not stop after pushing)")
        print("  Do not stop to summarize, discuss, get feedback or for anything else.")
        print("  Just run the script again keep looping and keep working!")

        return

    # If we get here, no icons need processing
    print(f"ALL_DONE ({done}/{total} icons have hints)")


if __name__ == "__main__":
    main()
