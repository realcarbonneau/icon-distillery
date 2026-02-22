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
    ThemeCatalog, _PROJECT_DIR, save_json_compact_arrays, usage_error,
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

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        catalog.print_available()
        usage_error(__doc__)

    theme = catalog.get_theme(sys.argv[1])
    json_path = theme.icons_path
    data = theme.icons_data

    icons = data.get("icons", {})
    total = len(icons)
    target_hints = 10
    done = sum(1 for v in icons.values()
               if len(v.get("hints", [])) >= target_hints)

    for icon_id, icon_data in icons.items():
        existing_hints = icon_data.get("hints", [])
        if len(existing_hints) >= target_hints:
            continue

        # Found the next Named Icon to process
        file_errors = []

        def log_file_error(error_msg):
            full_error = f"FILE_ERROR: {error_msg}"
            file_errors.append(full_error)
            log_anomaly(theme, f"{icon_id}: {full_error}")

        # Get file and context directly from icon_data
        filename = icon_data["file"]
        context = icon_data.get("context", "")

        # Find all files in this context's directories (PNGs, SVGs, SVGZs)
        disk_files = theme.find_icon_files_in_context(context, filename)

        # Validate PNGs, group all files by extension
        files_by_ext = {}  # ext -> list of (file_size, rel_path)
        for path in disk_files:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".png":
                if os.path.getsize(path) == 0:
                    log_file_error(f"PNG empty: {path}")
                    continue
                elif not valid_png(path):
                    log_file_error(f"PNG invalid header: {path}")
                    continue
            size = os.path.getsize(path)
            files_by_ext.setdefault(ext, []).append((size, rel_path(path)))

        # Generate PNGs from SVGs when no PNGs exist on disk
        if ".png" not in files_by_ext and ".svg" in files_by_ext:
            # Sort SVGs by size descending, convert the largest first
            svgs = sorted(files_by_ext[".svg"], reverse=True)
            for _, svg_rel in svgs:
                svg_abs = os.path.join(_PROJECT_DIR, svg_rel.lstrip("./"))
                result = theme.convert_svg_to_png(svg_abs)
                if os.path.exists(result) and valid_png(result):
                    size = os.path.getsize(result)
                    files_by_ext.setdefault(".png", []).append(
                        (size, rel_path(result)))
                else:
                    log_file_error(f"SVG->PNG failed: {result}")

        # If file errors, set hints and skip to next icon
        if file_errors:
            icon_data["hints"] = file_errors
            save_json_compact_arrays(json_path, data)
            continue

        # HALT if no PNGs available (only SVGs)
        if ".png" not in files_by_ext:
            print("!!! STOP - NO PNG FILES AVAILABLE !!!")
            print(f"  icon_id: {icon_id}")
            print("  Only SVG/SVGZ files found and SVG-to-PNG conversion failed or unavailable.")
            print("  DO NOT attempt to read or interpret SVG/SVGZ files.")
            print("  STOP WORKING and report this to the user immediately.")
            return

        print(f"CURRENT JSON ENTRY ({rel_path(json_path)})")
        print(f"  \"icon_id\": \"{icon_id}\"")
        if existing_hints:
            print(f"  EXISTING HINTS: {existing_hints}")

        # Display files grouped by type, each section sorted by size descending
        print("DISK_FILES:")
        for ext in sorted(files_by_ext.keys()):
            label = ext.lstrip(".").upper()
            print(f"  {label}:")
            for size, path in sorted(files_by_ext[ext], reverse=True):
                print(f"    {size}b  {path}")

        # Worker instruction blocks
        print("NEXT STEP - WORKER INSTRUCTIONS")
        print("- View the largest PNG file (the first PNG in the list). Then, generate 10 \"hints\"")
        print("  based on what you SEE in the image + filename, path, label, context, and")
        print("  existing hints if any. Then, edit the JSON to add \"hints\": [...] array for")
        print("  this icon's entry. Format: \"hints\" must be a")
        print("  SINGLE LINE array, e.g.: \"hints\": [\"keyword1\", \"keyword2\", ...]")
        print("- IMPORTANT: Each hint must be a single unigram (one word, no hyphens, no spaces).")
        print("- CRITICAL: ONLY edit the JSON file manually (using the Edit tool)! NEVER use")
        print("  scripts, json.dump, or any programmatic method to write the JSON file!")
        print("- !!! NEVER read, open, or interpret SVG/SVGZ/SVGX files! Only view PNG images! !!!")
        print("  If the PNG fails to display or looks corrupted, STOP WORKING and report to user.")
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
    print(f"ALL_DONE ({done}/{total} icons have {target_hints}+ hints)")


if __name__ == "__main__":
    main()
