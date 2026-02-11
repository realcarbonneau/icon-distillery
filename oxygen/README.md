# Oxygen Icons

Oxygen icon theme

## Introduction

Oxygen-icons is a freedesktop.org compatible icon theme.

## Known Anomalies

### 24x24/preferences/ directory

A `24x24/preferences/` directory exists on disk containing `preferences-kde-connect.png`,
but this directory is not declared in `index.theme`. The same icon exists properly under
`categories/` at 7 sizes (16, 22, 32, 48, 64, 128, 256) with full SVG sources.

This appears to be a misplaced version of the categories icon. It is an outlier that does
not follow any known pattern and is ignored.

### applets/ directories with mixed XDG contexts

The `applets` directory name appears in `index.theme` under two different XDG contexts:

- `256x256/applets` and `base/256x256/applets` have `Context=Applications`
- `applets/22x22` and `applets/32x32` have `Context=Status`

The 40 icons under `256x256/applets` (all KDE Plasma widgets) are mapped to the `apps`
internal context (which maps to `Applications`). The SVGs under `applets/22x22` and
`applets/32x32` (~140+ files, `Context=Status`) are not yet processed into `icons.json`.

### special/ directory — file-zoom ID conflicts

The `special/` directory (declared in `index.theme` as `Context=Actions`) contains 4 grey
zoom icons at sizes 16 and 22 (PNG only, no SVG sources).

`file-zoom-in.png` and `file-zoom-out.png` are grey page-size icons (small page/large
page), visually distinct from the blueish magnifying glass zoom icons in `actions/`. However,
`actions/file-zoom-in.png` and `actions/file-zoom-out.png` are symlinks to the generic
`zoom-in.png`/`zoom-out.png`, so the ID `oxygen_actions_file-zoom-in` is already taken
(marked `duplicate_of` `oxygen_actions_zoom-in`). The `special/` versions remain as
`oxygen_special_file-zoom-in` and `oxygen_special_file-zoom-out` with context `special`
pending ID resolution.
