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
- **Inkscape** must be installed (`apt install inkscape`)

## Flow

1. **Parse CLI arguments** — Accept `<theme>` and `<size>`. Optional `--force` to re-render existing PNGs. Optional `--context <id>` to limit to one context.

2. **Load theme via ThemeCatalog** — Uses `icon_theme_processor.py`. Calls `catalog.get_theme(theme)` which lazy-loads `icons.json`.

3. **Iterate icons.json entries** — For each entry in `data["icons"]`, read `file` and `context`. Derive SVG source path from `scalable/{context}/{stem}.svg`. Skip if `--context` filter doesn't match.

4. **Check PNG on disk** — Compute destination path `{size}x{size}/{context}/{stem}.png`. If it exists and has valid PNG magic bytes and `--force` is not set, skip.

5. **Render SVG → PNG** — Call Inkscape CLI (`--export-type=png --export-width=<size>`) to render the SVG. Validate output has PNG magic bytes. Log failures to `{theme_id}_anomalies.txt`.

6. **Fit to square canvas** — If the rendered PNG is not square (e.g., flags with 2:1 aspect ratio), composite it centered onto a transparent `{size}x{size}` RGBA canvas using PIL. This ensures all output PNGs are uniform square dimensions with transparent padding.

7. **Update sizes in icons.json** — After successful render, add the target size to the entry's `sizes` array if not already present. Save the updated JSON using `save_json_compact_arrays()`.

8. **Report summary** — Print per-context counts (rendered, skipped, failed) and total. Note entries with no SVG source (e.g., region flags with PNGs only).

## Design Notes

- **icons.json is the source of truth** — only icons listed in the JSON are rendered. Stray SVGs not in the JSON are ignored.
- The `sizes` array in each icon entry tracks which PNG sizes exist on disk. The render script updates this automatically after successful renders.
- The `scalable/` directory holds SVG source material. Some icons may have pre-rendered PNGs (copied from upstream) but no SVG source — these are skipped silently.
- Run multiple times with different sizes to build up PNG sets (e.g., `16`, `32`, `128`).

## Renderer: Inkscape over CairoSVG

The script originally used CairoSVG (`cairosvg.svg2png()`) but was switched to Inkscape for correctness.

**CairoSVG limitations discovered:**

- **Entity declarations blocked** — `noto-emoji/scalable/flags/AS.svg` (American Samoa) is an Adobe Illustrator export with `<!ENTITY>` declarations in its DOCTYPE. CairoSVG blocks these as an XML External Entity (XXE) security measure (`EntitiesForbidden`). The `unsafe=True` parameter bypasses this, but introduces other risks.

- **ViewBox overflow not clipped** — The same AS.svg has eagle drawing paths with y-coordinates extending to ~766, beyond its `viewBox="0 0 1000 500"`. Per the SVG spec, the root `<svg>` element defaults to `overflow="hidden"`, so content outside the viewBox should be invisible. CairoSVG does not implement this: "Clipping thanks to the overflow property is not supported" (cairosvg.org/svg_support). This rendered a visible "shadow eagle" below the flag.

**Inkscape** handles both cases correctly — it resolves entity declarations and clips to the viewBox per the SVG spec. The tradeoff is speed (subprocess per icon vs in-process library call), but correctness wins.
