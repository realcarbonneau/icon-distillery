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
| oxygen  | KDE Project           | 8, 16, 22, 24, 32, 48, 64, 128, 256 | PNG, SVG | Raw     |

## Example

| Primary | Duplicate |
|---------|-----------|
| ![printer](nuvola/128x128/devices/printer.png) | ![klpq](nuvola/128x128/apps/klpq.png) |
| Key: `nuvola_devices_printer` | Key: `nuvola_apps_klpq` |
| Label: **Printer** | Label: **Klpq** |
| Sizes: 16, 22, 32, 48, 64, 128 | Sizes: 16, 22, 32, 48, 64, 128 |
| Hints: printer, print, inkjet, paper, output, hardware | Hints: printer, print, queue, paper, jobs, spooler |
| Duplicates: `nuvola_apps_kjobviewer`, `nuvola_apps_klpq`, `nuvola_apps_preferences-desktop-printer`, `nuvola_actions_printmgr` | Duplicate of: `nuvola_devices_printer` |

Same image, different filenames — duplicates are linked bidirectionally. Labels are generated from filenames. Hints are 5-8 keywords describing what the icon visually depicts.
