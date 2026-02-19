#!/usr/bin/env python3
"""Render SVGs from scalable/{context}/ to PNGs at a target pixel size.

Driven by icons.json — only icons listed in the JSON are rendered.
Creates destination directories on disk if they don't exist yet.

Usage:
    python scripts/icon_render_png.py <theme> <size> [--force] [--context <id>]

Arguments:
    theme       Theme directory name (e.g., noto-emoji)
    size        Target pixel size (e.g., 128). Output goes to {size}x{size}/{context}/
    --force     Re-render even if PNG already exists
    --context   Render only one context (e.g., smileys-emotion)

Prerequisites:
    - icons.json must exist with icon entries
    - scalable/{context}/ directories must contain SVG source files

Examples:
    python scripts/icon_render_png.py noto-emoji 128
    python scripts/icon_render_png.py noto-emoji 128 --force
    python scripts/icon_render_png.py noto-emoji 32 --context smileys-emotion

See RENDERING.md for detailed flow documentation.
"""

import os
import subprocess
import sys

from PIL import Image

from icon_theme_processor import (
    ThemeCatalog, save_json_compact_arrays, fatal_error, usage_error,
)

# PNG magic header: first 8 bytes of any valid PNG file
_PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


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


def main():
    # --- Parse CLI arguments ---
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        catalog = ThemeCatalog()
        catalog.print_available()
        usage_error(__doc__)

    theme_name = sys.argv[1]
    try:
        target_size = int(sys.argv[2])
    except ValueError:
        usage_error(__doc__, f"size must be an integer, got: {sys.argv[2]}")

    force = "--force" in sys.argv
    context_filter = None
    for i, arg in enumerate(sys.argv[3:], 3):
        if arg == "--context" and i + 1 < len(sys.argv):
            context_filter = sys.argv[i + 1]

    # --- Load theme and icons.json ---
    catalog = ThemeCatalog()
    theme = catalog.get_theme(theme_name)
    json_path = theme.icons_path
    data = theme.icons_data

    icons = data.get("icons", {})
    if not icons:
        fatal_error(f"icons.json missing or empty for theme '{theme.theme_id}'")

    # --- Check for Inkscape ---
    try:
        subprocess.run(["inkscape", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        fatal_error("inkscape not found. Install with: apt install inkscape")

    # --- Render from icons.json ---
    size_prefix = f"{target_size}x{target_size}"
    total_rendered = 0
    total_skipped = 0
    total_failed = 0
    total_missing_svg = 0
    context_counts = {}

    print(f"Target size: {target_size}px ({size_prefix})")
    print(f"Source: icons.json ({len(icons)} entries)")
    if context_filter:
        print(f"Context filter: {context_filter}")
    print()

    for icon_id, icon_data in icons.items():
        context = icon_data.get("context", "")
        if context_filter and context != context_filter:
            continue

        filename = icon_data["file"]
        stem = os.path.splitext(filename)[0]

        # Source SVG
        svg_path = os.path.join(theme.dir, "scalable", context, stem + ".svg")
        if not os.path.isfile(svg_path):
            total_missing_svg += 1
            continue

        # Destination PNG
        png_dir = os.path.join(theme.dir, size_prefix, context)
        png_path = os.path.join(png_dir, stem + ".png")

        # Skip if PNG exists on disk and is valid
        if os.path.exists(png_path) and valid_png(png_path) and not force:
            total_skipped += 1
            context_counts.setdefault(context, [0, 0, 0])
            context_counts[context][1] += 1
            continue

        # Create destination directory
        os.makedirs(png_dir, exist_ok=True)

        # Render via Inkscape (constrain by width first)
        try:
            result = subprocess.run(
                [
                    "inkscape", svg_path,
                    "--export-type=png",
                    f"--export-filename={png_path}",
                    f"--export-width={target_size}",
                ],
                capture_output=True, timeout=30,
            )
            # If portrait SVG, height exceeds target — re-render constrained by height
            if result.returncode == 0 and valid_png(png_path):
                img = Image.open(png_path)
                if img.height > target_size:
                    result = subprocess.run(
                        [
                            "inkscape", svg_path,
                            "--export-type=png",
                            f"--export-filename={png_path}",
                            f"--export-height={target_size}",
                        ],
                        capture_output=True, timeout=30,
                    )
            if result.returncode == 0 and valid_png(png_path):
                # Fit onto square transparent canvas if not already square
                img = Image.open(png_path)
                if img.size != (target_size, target_size):
                    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
                    x = (target_size - img.width) // 2
                    y = (target_size - img.height) // 2
                    canvas.paste(img, (x, y))
                    canvas.save(png_path)

                total_rendered += 1
                context_counts.setdefault(context, [0, 0, 0])
                context_counts[context][0] += 1

                # Update sizes in icons.json if not already listed
                sizes = icon_data.get("sizes", [])
                if target_size not in sizes:
                    sizes.append(target_size)
                    sizes.sort()
                    icon_data["sizes"] = sizes
            else:
                if os.path.exists(png_path):
                    os.remove(png_path)
                stderr = result.stderr.decode(errors="replace").strip()
                log_anomaly(theme, f"{icon_id}: Render failed - {stderr}")
                total_failed += 1
                context_counts.setdefault(context, [0, 0, 0])
                context_counts[context][2] += 1
        except Exception as e:
            log_anomaly(theme, f"{icon_id}: Render failed - {e}")
            total_failed += 1
            context_counts.setdefault(context, [0, 0, 0])
            context_counts[context][2] += 1

    # --- Per-context summary ---
    for context in sorted(context_counts.keys()):
        rendered, skipped, failed = context_counts[context]
        status = f"rendered={rendered}"
        if skipped:
            status += f" skipped={skipped}"
        if failed:
            status += f" failed={failed}"
        print(f"  {context}: {status}")

    # --- Save updated icons.json ---
    if total_rendered > 0:
        save_json_compact_arrays(json_path, data)

    # --- Summary ---
    print()
    print(f"Total: rendered={total_rendered} skipped={total_skipped} failed={total_failed}")
    if total_missing_svg:
        print(f"  ({total_missing_svg} entries had no SVG source)")
    if total_rendered > 0:
        print(f"  Updated sizes in icons.json")

    if total_failed:
        anomaly_path = os.path.join(theme.dir, f"{theme.theme_id}_anomalies.txt")
        print(f"Failures logged to: {anomaly_path}")


if __name__ == "__main__":
    main()
