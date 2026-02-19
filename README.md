# icon-distillery

Post-processing for common icon theme packs. Normalizes themes to PNG at standard sizes, extracts hints, flags duplicates, and saves metadata in JSON files at the top level.

## Objectives

- Normalize icon theme packs to PNG for standard sizes (16, 22, 32, 48, 64, 128, 256)
- Extract hint metadata from icon names and categories
- Flag duplicate icons (identical images across names/sizes)
- Save metadata as JSON files at the top level of each theme
- Maintain a catalog of all imported theme packs
- Render PNGs from scalable SVG sources — see [RENDERING.md](RENDERING.md)

## Theme Packs

| Theme   | Source                | Sizes                                | Formats  | Status  |
|---------|----------------------|--------------------------------------|----------|---------|
| nuvola  | David Vignoni (2004) | 16, 22, 32, 48, 64, 128, 256, SVG   | PNG, SVG | Raw     |
| oxygen  | KDE Project          | 8, 16, 22, 24, 32, 48, 64, 128, 256 | PNG, SVG | Raw     |

### Emoji Packs

| Theme   | Source              | Version | Sizes    | Formats  | Status  |
|---------|---------------------|---------|----------|----------|---------|
| noto-emoji | Google Noto Emoji   |      | 32, 72, 128, 512, SVG | PNG, SVG | Planned |
| twemoji | Twitter/X Twemoji   | 14.0    | 72, SVG  | PNG, SVG | Abandoned |

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

## Emoji Icons

Emoji packs use the [Unicode Emoji Standard (UTS #51)](https://unicode.org/reports/tr51/) for categorization. Each emoji is assigned to a group defined in the official [`emoji-test.txt`](https://unicode.org/Public/emoji/14.0/emoji-test.txt) data file. Filenames follow the Unicode codepoint encoding — see [EMOJI_ENCODING.md](EMOJI_ENCODING.md) for the full reference on how codepoint sequences map to filenames, including ZWJ, skin tones, gender, keycaps, and flags.

### Emoji Context Mapping

| Context ID          | XDG Context       | Context Label         | Emoji Group           |
|---------------------|-------------------|-----------------------|-----------------------|
| smileys-emotion     | SmileysEmotion    | Smileys & Emotion     | Smileys & Emotion     |
| people-body         | PeopleBody        | People & Body         | People & Body         |
| component           | Component         | Component             | Component             |
| animals-nature      | AnimalsNature     | Animals & Nature      | Animals & Nature      |
| food-drink          | FoodDrink         | Food & Drink          | Food & Drink          |
| travel-places       | TravelPlaces      | Travel & Places       | Travel & Places       |
| activities          | Activities        | Activities            | Activities            |
| objects             | Objects           | Objects               | Objects               |
| symbols             | Symbols           | Symbols               | Symbols               |
| flags               | Flags             | Flags                 | Flags                 |

- **Context ID**: Internal identifier used in `contexts.json` and `icons.json`
- **XDG Context**: CamelCase identifier used in `index.theme` for tooling compatibility
- **Context Label**: Human-readable display name (matches the official Unicode emoji group name)
- **Emoji Group**: Exact string from `emoji-test.txt` `# group:` lines, used for parsing

Group assignments are defined by the Unicode Consortium and maintained in `emoji-test.txt`. There is no algorithmic rule mapping codepoints to groups — it is a lookup table.

### Twemoji

- Source: https://github.com/twitter/twemoji
- License: MIT (code), CC-BY 4.0 (graphics)
- Emoji version: 14.0
- Assets: 3689 SVG + 72x72 PNG
- Reference data: `emoji-test.txt` v14.0 — https://unicode.org/Public/emoji/14.0/emoji-test.txt
- Status: Essentially abandoned by Twitter/X since 2022. A community fork exists (https://github.com/jdecked/twemoji) but it is volunteer-maintained with uncertain long-term viability. Frozen at Emoji 14.0 — no new Unicode emoji releases will be supported.

### Noto Emoji (primary)

- Source: https://github.com/googlefonts/noto-emoji
- License: Apache 2.0 (code), SIL OFL 1.1 (fonts)
- Assets: SVG + 128x128 PNG
- Reference data: `emoji-test.txt` — https://unicode.org/Public/emoji/latest/emoji-test.txt
- Actively maintained by Google as part of the Noto fonts project
- Keeps up with new Unicode emoji releases
- Default emoji font on Android and ChromeOS
- Noto is the safer long-term choice for building on

### References

- Unicode Emoji Standard (UTS #51): https://unicode.org/reports/tr51/
- Full Emoji List: https://unicode.org/emoji/charts/full-emoji-list.html
