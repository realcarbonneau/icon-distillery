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

## The taskcoach Theme: Own Drawings

Task Coach's custom icons are drawn here, not taken from an upstream
set. The Markdown icons (`markdown_icon`, `markdown_side_navy_icon`,
`markdown_side_blue_icon`) are the first with SVG sources, in
`taskcoach/scalable/actions/`.

- **One drawing per pixel grid.** A drawing is sharp only at sizes its
  grid divides. `markdown_icon.svg` is on a 32 unit grid (32, 64, 128);
  `markdown_icon-16.svg` and `markdown_icon-22.svg` are the 16 and 22
  pixel drawings. The side-by-side icons are on a 16 unit grid (16, 32,
  48, 64, 128) with a `-22.svg` each. The size suffix marks a drawing
  for that size only.
- **Rendered by hand.** `icon_render_png.py` takes one SVG per icon and
  writes `{size}x{size}/{context}/`, which this flat theme does not
  have (`16x16/` holds the PNGs directly). Render each size with the
  same Inkscape call into `{size}x{size}/`:
  `inkscape FILE.svg --export-type=png --export-filename=OUT.png --export-width=N`.
  `icon_build_check_icons.py taskcoach` then checks the sizes against
  `icons.json`; it skips `scalable/`, which `index.theme` does not list.
- **Which is used.** Task Coach ships `markdown_icon` (the M over its
  down arrow, on a blue tile) at 16, 22 and 32; the two side-by-side
  icons are alternates kept here only. The reasons are in Task Coach's
  `docs/ICON_LIBRARY.md`, "TaskCoach Custom Icons".
