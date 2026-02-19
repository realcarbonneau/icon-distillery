# SVG→PNG Rendering

Batch renders SVGs to PNGs at a specified pixel size, driven by `icons.json`.

## Script

```
python scripts/icon_render_png.py <theme> <size> [--force] [--context <id>]
```

- `<theme>` — theme directory name (e.g., `noto-emoji`)
- `<size>` — target pixel size (e.g., `128`). Output goes to `{size}x{size}/{context}/`
- `--force` — re-render even if PNG already exists
- `--context <id>` — render only one context (e.g., `smileys-emotion`)

## Prerequisites

- `icons.json` must exist with icon entries (each entry has `file`, `context`, `sizes`)
- `scalable/{context}/` directories must contain the SVG source files

## Flow

1. **Parse CLI arguments** — Accept `<theme>` and `<size>`. Optional `--force` to re-render existing PNGs. Optional `--context <id>` to limit to one context.

2. **Load theme via ThemeCatalog** — Uses `icon_theme_processor.py`. Calls `catalog.get_theme(theme)` which lazy-loads `icons.json`.

3. **Iterate icons.json entries** — For each entry in `data["icons"]`, read `file` and `context`. Derive SVG source path from `scalable/{context}/{stem}.svg`. Skip if `--context` filter doesn't match.

4. **Check PNG on disk** — Compute destination path `{size}x{size}/{context}/{stem}.png`. If it exists and has valid PNG magic bytes and `--force` is not set, skip.

5. **Render SVG → PNG** — Call `cairosvg.svg2png()` with target width/height. Validate output has PNG magic bytes. Log failures to `{theme_id}_anomalies.txt`.

6. **Update sizes in icons.json** — After successful render, add the target size to the entry's `sizes` array if not already present. Save the updated JSON using `save_json_compact_arrays()`.

7. **Report summary** — Print per-context counts (rendered, skipped, failed) and total. Note entries with no SVG source (e.g., region flags with PNGs only).

## Design Notes

- **icons.json is the source of truth** — only icons listed in the JSON are rendered. Stray SVGs not in the JSON are ignored.
- The `sizes` array in each icon entry tracks which PNG sizes exist on disk. The render script updates this automatically after successful renders.
- The `scalable/` directory holds SVG source material. Some icons may have pre-rendered PNGs (copied from upstream) but no SVG source — these are skipped silently.
- Run multiple times with different sizes to build up PNG sets (e.g., `16`, `32`, `128`).
