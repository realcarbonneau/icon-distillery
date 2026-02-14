# Icon Metadata

## Table of Contents

- [Directory Convention](#directory-convention)
- [ICON_THEME_CATALOG.json](#icon_theme_catalogjson)
- [icons.json (Per-Theme)](#iconsjson-per-theme)
- [contexts.json (Per-Theme)](#contextsjson-per-theme)
- [Context Architecture](#context-architecture)
- [Icon IDs](#icon-ids)
- [Path Patterns](#path-patterns)
- [Hints](#hints)
- [Duplicates](#duplicates)
- [Labels](#labels)
- [Scripts](#scripts)
- [icon_theme_processor.py API](#icon_theme_processorpy-api)
- [TODO](#todo)

## Directory Convention

Each theme pack lives in a top-level directory whose name **is** the theme id. The directory name must match the id used in `ICON_THEME_CATALOG.json` and in icon id prefixes.

```
icon-distillery/
  scripts/
    ICON_THEME_CATALOG.json
    icon_theme_processor.py        <- shared library (ThemeCatalog, Theme)
    icon_build_check_icons.py      <- verify/update icons.json vs disk
    icon_build_check_contexts.py   <- verify/build contexts.json
    icon_build_check_symbolic.py   <- detect and tag symbolic icons
    icon_duplicates.py             <- find duplicate icons by content hash
    icon_generate_labels.py        <- generate label fields from filenames
    icon_next_hints.py             <- find next icon needing hints
    icon_rebuild_catalog_sizes.py  <- rebuild effective_sizes in catalog
  nuvola/                       <- directory name = theme id "nuvola"
    icons.json
    contexts.json
    index.theme
    16x16/{context}/{file}
    ...
  oxygen/                       <- directory name = theme id "oxygen"
    icons.json
    contexts.json
    index.theme
    base/16x16/{context}/{file}
    ...
```

## index.theme (Canonical Source)

The `index.theme` file is the **canonical source** for each theme's directory structure. It defines every valid directory and its metadata:

- **Directory path** (e.g., `16x16/actions`, `base/22x22/intl`) — filesystem locator only, no semantic meaning
- **Effective size** = Size x Scale (e.g., Size=16, Scale=2 → effective size 32)
- **XDG Context** (`Context=`) — the canonical context identifier (e.g., "Actions", "Applications", "International"). This is the authoritative source for what a directory represents. See [Context Architecture](#context-architecture).

All parsing, glob building, and path matching use the index.theme data directly. The catalog's `effective_sizes` and `xdg_contexts` fields are summaries derived from the index by `icon_rebuild_catalog_sizes.py` and `icon_build_check_contexts.py` respectively — they exist for reporting, not for validation.

## ICON_THEME_CATALOG.json

Located in `scripts/`. Defines theme-level metadata. Each key is a theme identifier matching its directory name.

| Field | Description |
|-------|-------------|
| `label` | Display name (e.g., "Nuvola") |
| `siblings_theme_ids` | Array of theme ids for related themes (e.g., light/dark variants of the same icon set). Informational only — not used by processing scripts. |
| `url` | Project homepage |
| `license` | SPDX license identifier |
| `effective_sizes` | Summary of available effective icon sizes, i.e. Size x Scale (derived from index.theme by `icon_rebuild_catalog_sizes.py`) |
| `xdg_contexts` | Summary of XDG Context= values (derived from index.theme by `icon_build_check_contexts.py`) |
| `path_pattern` | Path template for themes without index.theme (see [Path Patterns](#path-patterns)) |
| `notes` | Optional notes |

## icons.json (Per-Theme)

Located at `{theme}/icons.json`. Contains the icon catalog for that theme: every discovered icon with its sizes, hints, labels, and duplicate relationships.

| Field | Description |
|-------|-------------|
| `sizes` | Array of sizes found on disk for this icon |
| `context` | Context id — `lowercase(xdg_context)` (e.g., "actions", "applications", "devices"). See [Context Architecture](#context-architecture). |
| `file` | Original filename with extension |
| `label` | Display name, generated from filename |
| `hints` | Array of 5-8 search keywords (see [Hints](#hints)) |
| `duplicates` | Array of icon ids that are duplicates of this primary |
| `duplicate_of` | Icon id of the primary if this icon is a duplicate |
| `symbolic` | `true` when the icon is a symbolic (monochrome) icon — designed to be recolored by the desktop environment to match the current theme. May be detected by the `-symbolic` suffix in folder names, file names, or manually set. Can be set to `false` explicitly. Defaults to `false` when absent. |
| `notes` | Optional freeform string to document exceptional issues (e.g., corrupted filenames, upstream quirks) |

## contexts.json (Per-Theme)

Located at `{theme}/contexts.json`. Maps internal context ids to XDG context metadata. Generated from `index.theme` by `icon_build_check_contexts.py`.

The key is the `internal_context_id`, used throughout the system for icon ids, file lookups, and context_map indexing. See [Context Architecture](#context-architecture).

| Field | Description |
|-------|-------------|
| `xdg_context` | The canonical XDG `Context=` value from index.theme (e.g., "Actions", "Applications") |
| `context_label` | Display label for UI. Defaults to `xdg_context`, can be manually overridden (e.g., "Applications" → "Apps") |

Example:
```json
{
  "actions": {
    "xdg_context": "Actions",
    "context_label": "Actions"
  },
  "applications": {
    "xdg_context": "Applications",
    "context_label": "Applications"
  },
  "filesystems": {
    "xdg_context": "FileSystems",
    "context_label": "FileSystems"
  },
  "mimetypes": {
    "xdg_context": "MimeTypes",
    "context_label": "MimeTypes"
  }
}
```

## Context Architecture

**Context= in index.theme is canon.** Per the XDG spec, directory names are filesystem path locators with no semantic meaning. The `Context=` field is the authoritative source for what a directory represents.

The `internal_context_id` is a mapping key in `contexts.json` that maps to exactly one XDG context. It is often the lowercase version of the `xdg_context` (e.g., `"actions"` for `Context=Actions`), but this is just a default starting point suggestion. For example, `"apps"` for `Applications`. Once set, the `internal_context_id` is **immutable** — it will not change even if the upstream `xdg_context` is later renamed or updated. The same immutability rule applies to icon ids: once an icon id is assigned, it does not change.

The `internal_context_id` is used in icon ids, `context_map` lookups, and as the key in `contexts.json`. Each `internal_context_id` maps to exactly one `xdg_context` — the mapping is one-to-one.

The XDG Icon Naming Specification defines ~11 standard contexts (Actions, Animations, Applications, Categories, Devices, Emblems, Emotes, International, MimeTypes, Places, Status). The older Icon Theme Specification also defines FileSystems (largely superseded by Places in newer themes). Themes may use non-standard contexts; the `contexts.json` file documents whatever contexts a theme actually uses.

## Icon IDs

Keys follow the format `{theme}_{context}_{stem}` where stem is the filename without extension.

Examples:
- `nuvola_devices_print_printer` — theme "nuvola", context "devices", file "print_printer.png"
- `oxygen_actions_edit-copy` — theme "oxygen", context "actions", file "edit-copy.png"

For themes without contexts, the format is `{theme}_{stem}`.

## Path Patterns

Themes with an `index.theme` file use XDG directory metadata for parsing (sizes, contexts, and scale are read from the INI sections). The `path_pattern` field is only used as a fallback for themes without index.theme.

Fallback tokens:

| Token | Description | Example |
|-------|-------------|---------|
| `{theme}` | Theme directory (stripped during parsing) | `nuvola` |
| `{size}x{size}` | Dimension directory | `48x48` |
| `{size}` | Bare size number | `48` |
| `{context}` | Context directory | `actions` |
| `{file}` | Filename with extension | `edit-copy.png` |

## Hints

Hints are 5-8 keywords per icon used for search and discovery. They describe what the icon **visually depicts**, not just what the filename says.

The hints script (`icon_next_hints.py`) assumes the metadata JSON and index.theme are complete and coherent. If icons are missing, sizes are wrong, or the index is out of sync, run the coherence validation scripts first (see [TODO](#todo)).

Rules:
- View the icon at ALL available sizes before writing hints
- Describe what you SEE (e.g., "red heart with glossy highlight")
- Include both literal descriptors and use-case keywords
- Small sizes (16px) can look very different from large sizes (128px)
- Only search within the icon's own context directory — the same filename in a different context may be a visually different icon (see [Duplicates — Cross-Context Filenames](#cross-context-filenames))

Example:
```json
"hints": ["printer", "print", "inkjet", "paper", "output", "hardware", "document", "tray"]
```

## Duplicates

Icons that are visually identical across names are linked bidirectionally:

- The **primary** icon gets a `duplicates` array listing the duplicate keys
- Each **duplicate** icon gets a `duplicate_of` field pointing to the primary id

Duplicates are detected by MD5 content hash using `icon_duplicates.py`, then confirmed by visual review of each icon at all available sizes.

### Cross-Context Filenames

The XDG icon theme spec defines context as an organizational grouping, not a filesystem namespace. However, in practice **the same filename in different contexts can be a visually different icon**. For example, `folder.png` in `places` (a folder icon) vs `folder.png` in `actions` (a folder-related action) may be entirely different images.

This has two consequences:

1. **Icon ids include context for uniqueness.** The id format `{theme}_{context}_{stem}` is required because the stem alone does not uniquely identify an icon within a theme.
2. **Cross-context duplicate detection is separate from within-context hints.** The hints script (`icon_next_hints.py`) only searches within the icon's own context. The duplicates script (`icon_duplicates.py`) scans across all contexts to detect identical files that share a filename or hash.

When the duplicates script finds the same filename in multiple contexts with matching hashes, those are true cross-context duplicates and should be linked. When the hashes differ, they are distinct icons that happen to share a name.

## Labels

Generated from filenames by `icon_generate_labels.py`. Processing order:

1. Strip file extension
2. Replace `c++` with `Cpp` (hardcoded)
3. Replace `-` and `_` with spaces
4. Apply custom `--replace` regex rules (if provided)
5. Title case each word
6. Validate — any remaining non-alphanumeric characters (except spaces) are flagged as errors

The `--replace` option handles filenames with special characters (e.g., dots in MIME types, `+` in format names). Can be specified multiple times. See script help for usage.

Examples:
- `print_printer.png` → `Print Printer`
- `text-x-c++src.png` → `Text X Cpp Src`
- `application-atom+xml.png` with `--replace '\+' ' '` → `Application Atom Xml`

## Scripts

All scripts live in `scripts/` and use `icon_theme_processor.py` as a shared library. Run from the project root.

### Typical Processing Sequence

When onboarding a new theme, run scripts in this order:

| Step | Script | Purpose |
|------|--------|---------|
| 1 | `icon_build_check_contexts.py` | Build `contexts.json` from `index.theme` |
| 2 | `icon_build_check_icons.py` | Build `icons.json` inventory from disk scan |
| 3 | `icon_rebuild_catalog_sizes.py` | Rebuild `effective_sizes` in the catalog |
| 4 | `icon_build_check_symbolic.py` | Detect and tag symbolic (monochrome) icons |
| 5 | `icon_generate_labels.py` | Generate display labels from filenames |
| 6 | `icon_duplicates.py` | Find duplicate icons by content hash, then manually link them in `icons.json` |
| 6a | `icon_context_conflicts.py` | Report filenames appearing in multiple XDG contexts |
| 6b | `taskcoach_compare.py` | Compare distillery theme metadata against TaskCoach consumer copy |
| 7 | `icon_next_hints.py` | Add 5-8 search hints per icon (manual, one at a time) |
| | | |
| 2a | `icon_build_check_icons.py --update-sizes` | Maintenance: sync sizes arrays with disk |
| 2b | `icon_build_check_icons.py --insert-missing` | Maintenance: add newly discovered icons to `icons.json` |

Steps 1-3 establish the foundational metadata from `index.theme` and disk. Steps 4-5 can be run in any order. Step 6 (duplicates) should come before step 7 (hints) so that duplicate icons can share hints. Steps 2a-2b are for incremental updates after the initial build. All scripts can be re-run to verify consistency.

### icon_build_check_icons.py

Verify and update the `icons.json` inventory against what's on disk. Scans the theme directory for PNG/SVG/SVGZ files in directories declared in `index.theme`, skipping symlinks (files and directories).

```
python scripts/icon_build_check_icons.py <theme> [--insert-missing] [--update-sizes]
```

- With no flags: reports differences between `icons.json` and disk (icons missing from JSON, icons in JSON but not on disk or symlink-only, and size mismatches)
- `--insert-missing` — add icons found on disk but missing from `icons.json` (does not remove or modify existing entries)
- `--update-sizes` — update `sizes` arrays in `icons.json` to match what's actually on disk

If `icons.json` does not exist, builds it from the disk scan.

### icon_build_check_contexts.py

Build or verify `contexts.json` from `index.theme`. Also updates the `xdg_contexts` summary in `ICON_THEME_CATALOG.json`.

```
python scripts/icon_build_check_contexts.py [theme]
```

- If `contexts.json` doesn't exist: builds it
- If it exists: checks against `index.theme` and reports differences
- Validates every icon in `icons.json` has a valid context
- Optional `theme` argument filters to a single theme; omit to process all themes

### icon_build_check_symbolic.py

Detect and tag symbolic (monochrome) icons in `icons.json` by collecting evidence from directory structure and filenames.

```
python scripts/icon_build_check_symbolic.py <theme>
```

- Pass 1: collects symbolic evidence from `*/symbolic/` or `*/symbolic-*/` directories and `-symbolic` filename suffixes
- Pass 2: sets `"symbolic": true` on matching icons that don't already have the property (does not overwrite existing values)

### icon_duplicates.py

Find duplicate icon files by content hash. Reports full duplicates (all sizes match) and partial duplicates (some sizes match).

```
python scripts/icon_duplicates.py <theme>
```

- Hashes all icon files and groups by content
- Reports icons already marked with `duplicate_of` / `duplicates` metadata
- Used to identify candidates for duplicate linking in `icons.json`

### icon_context_conflicts.py

Report filenames that appear in multiple XDG contexts. Per the XDG spec, Context is organizational only and not a namespace — the same filename in different contexts creates ambiguous icon lookup.

```
python scripts/icon_context_conflicts.py <theme>
```

- Scans all indexed directories via `scan_directory()`
- Groups files by filename, reports those in 2+ contexts
- Output sorted by filename, context, path

### taskcoach_compare.py

Compare distillery theme metadata against the TaskCoach consumer copy at `../taskcoach/taskcoachlib/gui/icons/<theme>/`. Reports drift between the source of truth (distillery) and the consumer.

```
python scripts/taskcoach_compare.py <theme>
```

Report sections:
- **Contexts comparison** — diff `contexts.json` (distillery-only, TC-only, value mismatches)
- **Icon inventory** — icon key presence/absence, distillery-only grouped by context, TC-only (unexpected)
- **Source_sizes comparison** — TC `source_sizes` vs distillery `sizes`, with TC local `sizes` for context
- **Field differences** — label, hints (content diff + order-only), context, `duplicate_of`, `duplicates`
- **ICON_MAPPING validation** — validates `ICON_MAPPING.json` entries where `source` matches the theme: checks category/file exists in distillery, compares `source_sizes`, checks duplicate sub-entries

Clean sections show "All N items match" with no noise. Summary counts go to stderr.

### icon_generate_labels.py

Generate `label` fields for icons from filenames.

```
python scripts/icon_generate_labels.py <theme> [--replace PATTERN REPLACEMENT ...]
```

- Transforms filename stem: strip extension, replace `c++` → `Cpp`, replace `-` and `_` with spaces, apply `--replace` rules, title case
- `--replace PATTERN REPLACEMENT` — regex substitution pairs applied before title casing (can be specified multiple times)
- Flags errors for any remaining non-alphanumeric characters (except spaces)

Example: `python scripts/icon_generate_labels.py oxygen --replace '\.' ' ' --replace '\+' 'plus'`

### icon_next_hints.py

Find the next icon without hints and display its image files for visual review.

```
python scripts/icon_next_hints.py <theme>
```

- Finds the first icon in `icons.json` missing a `hints` property
- Searches the icon's context directories for all size variants
- Converts SVGs to PNG if needed for viewing
- Logs anomalies (missing files, zero-size PNGs) to `{theme_id}_anomalies.txt`

### icon_rebuild_catalog_sizes.py

Rebuild `effective_sizes` in `ICON_THEME_CATALOG.json` from `index.theme` files.

```
python scripts/icon_rebuild_catalog_sizes.py
```

- No arguments — processes all themes with `index.theme`
- Collects effective sizes (Size x Scale) from each theme's index
- Updates each theme's catalog entry independently
- Updates the catalog file if changes are detected

## icon_theme_processor.py API

The shared library `scripts/icon_theme_processor.py` provides two classes and one utility function.

### ThemeCatalog

Entry point. Loads `ICON_THEME_CATALOG.json` and creates `Theme` objects. Skipped themes (`skip: true`) are excluded from iteration but accessible via `catalog[theme_id]`.

```python
catalog = ThemeCatalog()

catalog[theme_id]       # Get Theme by id (fatal if not found)
for theme in catalog:   # Iterate non-skipped Theme objects
theme_id in catalog     # Membership check (includes skipped)
len(catalog)            # Count of non-skipped themes
catalog.items()         # (theme_id, Theme) pairs
catalog.keys()          # Non-skipped theme_ids

catalog.raw             # Mutable catalog dict (for scripts that update fields)
catalog.path            # Path to ICON_THEME_CATALOG.json
catalog.save()          # Write catalog JSON to disk
catalog.print_available()  # Print theme list to stderr
```

### Theme

Represents a single theme. Created by `ThemeCatalog` — callers should not construct directly. All heavy data is lazy-loaded on first access.

**Attributes (set in constructor):**

| Attribute | Description |
|-----------|-------------|
| `theme_id` | Theme id (e.g., "papirus-dark", "oxygen") |
| `theme_base_id` | Base catalog key (e.g., "papirus", "oxygen") |
| `config` | Raw catalog config dict for the base theme |
| `dir` | Absolute path to theme directory |
| `icons_path` | Absolute path to icons.json |
| `contexts_path` | Absolute path to contexts.json |

**Lazy-loaded properties:**

| Property | Description |
|----------|-------------|
| `index` | Parsed index.theme dir_map (fatal if missing) |
| `context_map` | Dict mapping `internal_context_id` → list of index entries |
| `icons_data` | Parsed icons.json dict (fatal if missing) |
| `contexts` | Parsed contexts.json dict, or `None` if file doesn't exist |

**Processing methods:**

| Method | Description |
|--------|-------------|
| `generate_id(internal_context_id, filename)` | Generate icon id: `{theme}_{context}_{stem}` |
| `get_file_info(path)` | Build file info dict for an icon file path |
| `add_file_hash(file_info)` | Add MD5 hash (12 hex chars) to file info dict |
| `match_dir(path, is_file=False)` | Match a path against the index dir_map (fatal if not found) |
| `strip_dir_base(path)` | Strip theme dir from a path, return relative path |
| `scan_directory(base=None)` | Scan directory and build inventory of all icons |
| `validate_icon_data(icon_id, icon_data)` | Validate icon_data has required file property |
| `find_all_on_disk(filename)` | Find all files matching filename across theme directory |
| `find_icon_files_in_context(internal_context_id, filename)` | Find all size variants of an icon within its context |
| `convert_svg_to_png(svg_path)` | Convert SVG to PNG, return path or error string |

### save_json_compact_arrays(filepath, data)

Module-level utility. Writes JSON with `indent=2` but collapses arrays onto single lines for readability.

## TODO

1. **Build index.theme for breeze, taskcoach, and legacy.** These themes don't ship an index.theme and currently use `path_pattern` as a fallback. Once we generate index.theme files for them, the path_pattern fallback can be removed entirely.
2. ~~**Store context labels for UI display.**~~ Done — `contexts.json` stores `context_label` per context, generated by `icon_build_check_contexts.py`.
3. ~~**Review icon id nomenclature and uniqueness.**~~ Done — icon ids use `{theme}_{internal_context_id}_{stem}` format, with `internal_context_id = lowercase(xdg_context)`. Context is immutable once set. See [Context Architecture](#context-architecture).
4. **Coherence validation script.** Create a script that reviews index.theme and metadata JSON for coherence: verifies every icon in the JSON has matching files on disk at the declared sizes, every file on disk has an entry in the JSON, and all index.theme directories are consistent with the catalog. Other scripts (hints, labels) assume coherence and should not run until validation passes.
5. **Review sibling theme dedup (Dark/Light).** For sibling themes (e.g., Papirus, Papirus-Dark, Papirus-Light), review whether duplicates should be detected within each theme or across siblings. In theory, shared files across variants should be symlinks. Needs investigation.
6. **Lowercase icon IDs.** `generate_id()` currently uses the filename stem as-is, producing mixed-case icon IDs (e.g., `oxygen_actions_Info-amarok`, `papirus_actions_SuggestionError`). Icon IDs should be fully lowercase. Affected: 12 in oxygen, 1 in nuvola, 2,056 in papirus. Fix: add `.lower()` to stem in `generate_id()`, then rekey all existing icons.json entries.
7. ~~**Remove symlink-only icons from icons.json.**~~ Done — removed all symlink-only entries and cross-context symlink aliases from oxygen/icons.json. Run `icon_build_check_icons.py` to verify.
8. **Update sizes to match disk.** Run `icon_build_check_icons.py <theme> --update-sizes` to sync sizes arrays in icons.json with what's actually on disk. Use `--insert-missing` to add newly discovered icons.
9. **Decide on custom_sizes / source_sizes tracking.** When generating missing PNG sizes (e.g., rendering a 16px PNG from a symbolic SVG), we need a way to distinguish original upstream sizes from locally generated ones in icons.json. Options: `sizes` = all available + `source_sizes` = original (omit when identical); or `sizes` = original + `generated_sizes` = added. Note: symbolic SVGs already have a size (e.g., `[22]`) from the directory they sit in — after generating PNGs at other sizes, `sizes` would grow (e.g., `[16, 22, 32]`) and we need `generated_sizes` or similar to record which ones we created. Leaning toward a `generated_sizes` array since it only appears when we've added something, keeping the JSON lean. First real test case: generate PNGs for all applet symbolic SVGs that only have SVG files and no raster sizes.
10. **Separate SVG-to-PNG conversion script.** Currently `icon_next_hints.py` converts SVGs to PNG inline as a side effect while processing hints. This should be a dedicated preparation script (e.g., `icon_convert_svgs.py`) that walks the index.theme directories, finds all SVG/SVGZ files, and pre-converts them to PNGs. The icons.json already has the filename (as `.png`), so we know what the expected output is. The script should prepare all icon sizes in advance based on what index.theme declares for SVGs, if applicable. Once this script exists, `icon_next_hints.py` can drop its SVG conversion logic and only deal with PNGs.
