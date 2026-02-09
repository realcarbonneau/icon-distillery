# Icon Metadata

## Table of Contents

- [Directory Convention](#directory-convention)
- [ICON_THEME_CATALOG.json](#icon_theme_catalogjson)
- [metadata.json (Per-Theme)](#metadatajson-per-theme)
- [Icon Keys](#icon-keys)
- [Path Patterns](#path-patterns)
- [Hints](#hints)
- [Duplicates](#duplicates)
- [Labels](#labels)

## Directory Convention

Each theme pack lives in a top-level directory whose name **is** the theme key. The directory name must match the key used in `ICON_THEME_CATALOG.json` and in icon key prefixes.

```
icon-distillery/
  scripts/
    ICON_THEME_CATALOG.json
    icon_theme_processor.py
    icon_next_hints.py
    icon_duplicates.py
    icon_generate_names.py
  nuvola/                       <- directory name = theme key "nuvola"
    metadata.json
    index.theme
    16x16/{category}/{file}
    ...
  oxygen/                       <- directory name = theme key "oxygen"
    metadata.json
    16x16/{category}/{file}
    ...
```

## ICON_THEME_CATALOG.json

Located in `scripts/`. Defines theme-level metadata. Each key is a theme identifier matching its directory name.

| Field | Description |
|-------|-------------|
| `name` | Display name (e.g., "Nuvola") |
| `url` | Project homepage |
| `license` | SPDX license identifier |
| `path_pattern` | Path template for icon files (see [Path Patterns](#path-patterns)) |
| `sizes` | Array of available icon sizes |
| `categories` | Array of valid category directory names |
| `note` | Optional notes |

## metadata.json (Per-Theme)

Located at `{theme}/metadata.json`. Contains the icon catalog for that theme: every discovered icon with its sizes, hints, labels, and duplicate relationships.

| Field | Description |
|-------|-------------|
| `sizes` | Array of sizes found on disk for this icon |
| `category` | XDG category (e.g., "actions", "apps", "devices") |
| `file` | Original filename with extension |
| `label` | Display name, generated from filename |
| `hints` | Array of 5-8 search keywords (see [Hints](#hints)) |
| `duplicates` | Array of icon keys that are duplicates of this primary |
| `duplicate_of` | Icon key of the primary if this icon is a duplicate |

## Icon Keys

Keys follow the format `{theme}_{category}_{stem}` where stem is the filename without extension.

Examples:
- `nuvola_devices_print_printer` — theme "nuvola", category "devices", file "print_printer.png"
- `oxygen_actions_edit-copy` — theme "oxygen", category "actions", file "edit-copy.png"

For themes without categories, the format is `{theme}_{stem}`.

## Path Patterns

Each theme defines a `path_pattern` in the catalog that describes its directory layout. Tokens:

| Token | Description | Example |
|-------|-------------|---------|
| `{theme}` | Theme directory (stripped during parsing) | `nuvola` |
| `{size}x{size}` | Dimension directory | `48x48` |
| `{size}` | Bare size number | `48` |
| `{category}` | Category directory | `actions` |
| `{file}` | Filename with extension | `edit-copy.png` |

Most themes use `{theme}/{size}x{size}/{category}/{file}`. Breeze is the exception: `{theme}/{category}/{size}/{file}`.

## Hints

Hints are 5-8 keywords per icon used for search and discovery. They describe what the icon **visually depicts**, not just what the filename says.

Rules:
- View the icon at ALL available sizes before writing hints
- Describe what you SEE (e.g., "red heart with glossy highlight")
- Include both literal descriptors and use-case keywords
- Small sizes (16px) can look very different from large sizes (128px)

Example:
```json
"hints": ["printer", "print", "inkjet", "paper", "output", "hardware", "document", "tray"]
```

## Duplicates

Icons that are visually identical across names are linked bidirectionally:

- The **primary** icon gets a `duplicates` array listing the duplicate keys
- Each **duplicate** icon gets a `duplicate_of` field pointing to the primary key

Duplicates are detected by MD5 content hash using `icon_duplicates.py`.

## Labels

Generated from filenames by `icon_generate_names.py`:
- Strip file extension
- Replace `-` and `_` with spaces
- Title case each word

Example: `print_printer.png` becomes `Print Printer`
