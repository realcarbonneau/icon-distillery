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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

from icon_theme_processor import ThemeCatalog, fatal_error, save_json_compact_arrays


def rel_path(abs_path):
    """Convert absolute path to relative path from PROJECT_DIR."""
    rel = os.path.relpath(abs_path, PROJECT_DIR)
    if not rel.startswith(".."):
        rel = "./" + rel
    return rel


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

    theme = catalog[sys.argv[1]]
    json_path = theme.icons_path
    data = theme.icons_data

    icons = data.get("icons", {})
    total = len(icons)
    done = sum(1 for v in icons.values() if "hints" in v or "inherits" in v)

    for icon_id, icon_data in icons.items():
        if "hints" in icon_data or "inherits" in icon_data:
            continue

        # Found the next Named Icon to process
        file_errors = []

        def log_file_error(error_msg):
            full_error = f"FILE_ERROR: {error_msg}"
            file_errors.append(full_error)
            log_anomaly(theme, f"{icon_id}: {full_error}")

        # Validate and extract context/file from icon_data
        validated = theme.validate_icon_data(icon_id, icon_data)
        context = validated["internal_context_id"]
        filename = validated["file"]

        # FIRST PASS: Find SVGs and convert to PNG
        initial_hits = theme.find_icon_files_in_context(context, filename)
        svg_files = [p for p in initial_hits if p.endswith(".svg")]

        # Step 2: For each SVG, convert to PNG
        for svg_path in svg_files:
            result = theme.convert_svg_to_png(svg_path)
            if not result.endswith(".png"):
                log_file_error(result)

        # Step 3: Verify all PNGs exist with non-zero size
        for svg_path in svg_files:
            png_path = svg_path[:-4] + ".png"
            if not os.path.exists(png_path):
                log_file_error(f"PNG missing after conversion: {png_path}")
            elif os.path.getsize(png_path) == 0:
                log_file_error(f"PNG has zero size: {png_path}")

        # If file errors, set hints and skip to next icon
        if file_errors:
            icon_data["hints"] = file_errors
            save_json_compact_arrays(json_path, data)
            continue

        # Step 4: Find all PNGs
        all_hits = [p for p in theme.find_icon_files_in_context(context, filename) if p.endswith(".png")]

        # Build file info (already filtered to context)
        file_info = []
        for path in all_hits:
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
