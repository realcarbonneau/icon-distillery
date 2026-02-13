# Papirus Icons

Papirus icon theme

## Introduction

Papirus is a freedesktop.org compatible SVG icon theme with multiple variants (Papirus, Papirus-Dark, Papirus-Light).

## Known Anomalies

### panel/ and status/ directories share Context=Status

Both `panel/` and `status/` directories are declared as `Context=Status` in `index.theme`. The `panel/` directories contain simplified icons designed for small system tray display, while `status/` directories contain full-size status icons.

One filename collision exists: `avatar-default.svg` appears in both `panel/` and `status/` at sizes 22 and 24. All four files have different content — the panel versions (~589 bytes) are simpler than the status versions (~1286 bytes). The scan maps both to `papirus_status_avatar-default`, creating a path conflict. To be reviewed later.

### scalable/ directories not in index.theme

The `scalable/` directories are not declared in `index.theme` and are therefore not scanned or indexed. However, they may contain unique colored icons that don't exist elsewhere in the theme. For example, `multimedia-player-ipod.svgz` in oxygen's scalable directory is a colored iPod icon, while all matching `multimedia-player-ipod*` entries in the indexed directories are symbolic icons that look nothing like it. To be reviewed later.

### Partial duplicate flagging needs visual review

Many duplicate groups flagged in `icons.json` were identified by hash matching at only 16px, while larger sizes did not match. These need to be revisited:

1. **16px-only hash matches are unreliable.** At 16px, many different icons are simplified to the same shape (e.g. a right-arrow for both "indent" and "play"). The largest available size must be viewed for both icons — if they are visually different at the largest size, they are NOT duplicates and the flags must be removed.

2. **Primary assignment errors.** Some groups where only 16px existed for one icon were flagged with that single-size icon as the primary. The superset icon (the one with more sizes) must always be the primary. These need to be corrected so `duplicates` is on the superset and `duplicate_of` points from the smaller icon to the superset.
