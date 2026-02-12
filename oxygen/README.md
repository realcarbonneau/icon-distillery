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
