# icon-distillery

Post-processing for common icon theme packs. Normalizes themes to PNG at standard sizes, extracts hints, flags duplicates, and saves metadata in JSON files at the top level.

## Objectives

- Normalize icon theme packs to PNG for standard sizes (16, 22, 32, 48, 64, 128, 256)
- Extract hint metadata from icon names and categories
- Flag duplicate icons (identical images across names/sizes)
- Save metadata as JSON files at the top level of each theme
- Maintain a catalog of all imported theme packs

## Theme Packs

| Theme   | Source                | Sizes                              | Formats  | Status  |
|---------|-----------------------|------------------------------------|----------|---------|
| nuvola  | David Vignoni (2004)  | 16, 22, 32, 48, 64, 128, 256, SVG | PNG, SVG | Raw     |
