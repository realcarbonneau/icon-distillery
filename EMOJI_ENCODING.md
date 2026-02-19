# Emoji Codepoint Encoding Reference

Reference for how Unicode emoji codepoints map to Noto Color Emoji filenames and how `emoji-test.txt` relates to the SVG source files.

## Filename Format

Noto emoji SVGs use the pattern:

```
emoji_u{HEX}[_{HEX}...].svg
```

- Prefix: `emoji_u`
- Codepoints: lowercase hex, separated by underscores
- Extension: `.svg` (source) or `.png` (rendered)
- **FE0F (variation selector) is omitted** from filenames
- **200D (ZWJ) is included** in filenames

## Key Unicode Codepoints

| Codepoint | Name                        | Role in sequences                        |
|-----------|-----------------------------|------------------------------------------|
| `200D`    | Zero Width Joiner (ZWJ)     | Glues parts into compound emoji          |
| `FE0F`    | Variation Selector 16       | Requests emoji presentation (vs text)    |
| `FE0E`    | Variation Selector 15       | Requests text presentation               |
| `20E3`    | Combining Enclosing Keycap  | Turns digit/symbol into keycap emoji     |
| `1F3FB`–`1F3FF` | Skin Tone Modifiers   | Fitzpatrick scale (light → dark)         |
| `2640`    | Female Sign ♀               | Gender modifier (woman)                  |
| `2642`    | Male Sign ♂                 | Gender modifier (man)                    |
| `27A1`    | Right Arrow ➡               | Direction modifier (facing right)        |
| `1F1E6`–`1F1FF` | Regional Indicators   | Pairs encode country flags               |

## Sequence Types

### 1. Simple Emoji (single codepoint)

One base codepoint, one file.

```
emoji-test.txt:   1F600 ; fully-qualified # 😀 E1.0 grinning face
filename:         emoji_u1f600.svg
```

### 2. Skin Tone Modifier Sequences

Base codepoint + skin tone modifier (1F3FB–1F3FF). The modifier immediately follows the base.

```
emoji-test.txt:   1F3C3        ; fully-qualified # 🏃   person running
                  1F3C3 1F3FB  ; fully-qualified # 🏃🏻 person running: light skin tone
                  1F3C3 1F3FC  ; fully-qualified # 🏃🏼 person running: medium-light skin tone
                  1F3C3 1F3FD  ; fully-qualified # 🏃🏽 person running: medium skin tone
                  1F3C3 1F3FE  ; fully-qualified # 🏃🏾 person running: medium-dark skin tone
                  1F3C3 1F3FF  ; fully-qualified # 🏃🏿 person running: dark skin tone

filenames:        emoji_u1f3c3.svg
                  emoji_u1f3c3_1f3fb.svg
                  emoji_u1f3c3_1f3fc.svg
                  emoji_u1f3c3_1f3fd.svg
                  emoji_u1f3c3_1f3fe.svg
                  emoji_u1f3c3_1f3ff.svg
```

One base emoji produces **6 files** (1 default + 5 skin tones).

### 3. ZWJ Gender Sequences

Base + ZWJ (`200D`) + gender sign (`2642` male / `2640` female). In `emoji-test.txt` the gender sign is followed by `FE0F`, but **FE0F is omitted from filenames**.

```
emoji-test.txt:   1F3C3 200D 2642 FE0F  ; fully-qualified     # 🏃‍♂️ man running
                  1F3C3 200D 2642       ; minimally-qualified # 🏃‍♂  man running
                  1F3C3 200D 2640 FE0F  ; fully-qualified     # 🏃‍♀️ woman running
                  1F3C3 200D 2640       ; minimally-qualified # 🏃‍♀  woman running

filenames:        emoji_u1f3c3_200d_2642.svg
                  emoji_u1f3c3_200d_2640.svg
```

The fully-qualified form has `FE0F`; the minimally-qualified form omits it. **Noto filenames match the minimally-qualified form** (no FE0F).

### 4. ZWJ Gender + Skin Tone Combinations

Skin tone goes right after the base, before the ZWJ+gender. Every person-emoji with gender variants generates a matrix:

```
Pattern:  {base}[_{skin}]_200d_{gender}

emoji-test.txt:   1F3C3 1F3FB 200D 2642 FE0F  ; man running: light skin tone
                  1F3C3 1F3FE 200D 2640 FE0F  ; woman running: medium-dark skin tone

filenames:        emoji_u1f3c3_1f3fb_200d_2642.svg
                  emoji_u1f3c3_1f3fe_200d_2640.svg
```

### 5. ZWJ Direction Sequences (E15.1+)

Added in Emoji 15.1. Base + ZWJ + direction arrow (e.g., `27A1` for right). Can combine with skin tone and gender.

```
Pattern:  {base}[_{skin}]_200d[_{gender}_200d]_{direction}

filenames:        emoji_u1f3c3_200d_27a1.svg             (person running facing right)
                  emoji_u1f3c3_200d_2642_200d_27a1.svg    (man running facing right)
                  emoji_u1f3c3_200d_2640_200d_27a1.svg    (woman running facing right)
                  emoji_u1f3c3_1f3fb_200d_2642_200d_27a1.svg  (man running facing right: light)
```

### 6. Full Variant Matrix Example

🏃 Person Running (U+1F3C3) has **36 files** in Noto:

| Variant                         | Count | Example filename                              |
|---------------------------------|-------|-----------------------------------------------|
| Default (no modifier)           | 1     | `emoji_u1f3c3.svg`                            |
| Skin tones                      | 5     | `emoji_u1f3c3_1f3fb.svg` … `_1f3ff.svg`      |
| Man (ZWJ+♂)                     | 1     | `emoji_u1f3c3_200d_2642.svg`                  |
| Man + skin tones                | 5     | `emoji_u1f3c3_1f3fb_200d_2642.svg` …          |
| Woman (ZWJ+♀)                   | 1     | `emoji_u1f3c3_200d_2640.svg`                  |
| Woman + skin tones              | 5     | `emoji_u1f3c3_1f3fb_200d_2640.svg` …          |
| Facing right (ZWJ+➡)            | 1     | `emoji_u1f3c3_200d_27a1.svg`                  |
| Facing right + skin tones       | 5     | `emoji_u1f3c3_1f3fb_200d_27a1.svg` …          |
| Man facing right                | 1     | `emoji_u1f3c3_200d_2642_200d_27a1.svg`        |
| Man facing right + skin tones   | 5     | `emoji_u1f3c3_1f3fb_200d_2642_200d_27a1.svg` …|
| Woman facing right              | 1     | `emoji_u1f3c3_200d_2640_200d_27a1.svg`        |
| Woman facing right + skin tones | 5     | `emoji_u1f3c3_1f3fb_200d_2640_200d_27a1.svg` …|
| **Total**                       | **36**|                                               |

### 7. ZWJ Profession Sequences

Person + ZWJ + object = profession. The object emoji after ZWJ represents the role.

```
emoji-test.txt:   1F469 200D 1F373  ; fully-qualified # 👩‍🍳 woman cook
                  1F469 200D 2695 FE0F ; fully-qualified # 👩‍⚕️ woman health worker

filenames:        emoji_u1f469_200d_1f373.svg     (👩 woman + 🍳 cooking = woman cook)
                  emoji_u1f469_200d_2695.svg      (👩 woman + ⚕ medical = woman health worker)
                  emoji_u1f469_200d_1f3eb.svg     (👩 woman + 🏫 school = woman teacher)
                  emoji_u1f469_200d_1f4bb.svg     (👩 woman + 💻 laptop = woman technologist)
                  emoji_u1f469_200d_1f680.svg     (👩 woman + 🚀 rocket = woman astronaut)
                  emoji_u1f469_200d_1f692.svg     (👩 woman + 🚒 fire engine = woman firefighter)
```

### 8. ZWJ Family Sequences

Multiple person/child emoji joined by ZWJ. These are the longest sequences.

```
emoji-test.txt:   1F469 200D 1F469 200D 1F466 200D 1F466
                  ; fully-qualified # 👩‍👩‍👦‍👦 family: woman, woman, boy, boy

filename:         emoji_u1f469_200d_1f469_200d_1f466_200d_1f466.svg
                  (4 people joined by 3 ZWJs = 7 codepoints)
```

### 9. ZWJ Compound Emoji (misc)

ZWJ combines existing emoji into new meanings:

```
emoji_u1f441_200d_1f5e8.svg     (👁‍🗨  eye + speech bubble = eye in speech bubble)
emoji_u1f62e_200d_1f4a8.svg     (😮‍💨  face + dash = face exhaling)
emoji_u1f408_200d_2b1b.svg      (🐈‍⬛  cat + black square = black cat)
emoji_u1f43b_200d_2744.svg      (🐻‍❄  bear + snowflake = polar bear)
emoji_u2764_200d_1f525.svg      (❤‍🔥  heart + fire = heart on fire)
emoji_u1f469_200d_1f9b0.svg     (👩‍🦰  woman + red hair component = woman: red hair)
```

### 10. Keycap Sequences

ASCII character + Combining Enclosing Keycap (`20E3`). In `emoji-test.txt` these include `FE0F` between the base and keycap, but **FE0F is omitted from filenames**.

```
emoji-test.txt:   0023 FE0F 20E3  ; fully-qualified # #️⃣ keycap: #
                  0023 20E3       ; unqualified     # #⃣  keycap: #

filename:         emoji_u0023_20e3.svg
```

All keycap emoji:

| Filename              | Emoji | Label      |
|-----------------------|-------|------------|
| `emoji_u0023_20e3.svg` | #️⃣   | keycap: #  |
| `emoji_u0030_20e3.svg` | 0️⃣   | keycap: 0  |
| `emoji_u0031_20e3.svg` | 1️⃣   | keycap: 1  |
| `emoji_u0032_20e3.svg` | 2️⃣   | keycap: 2  |
| `emoji_u0033_20e3.svg` | 3️⃣   | keycap: 3  |
| `emoji_u0034_20e3.svg` | 4️⃣   | keycap: 4  |
| `emoji_u0035_20e3.svg` | 5️⃣   | keycap: 5  |
| `emoji_u0036_20e3.svg` | 6️⃣   | keycap: 6  |
| `emoji_u0037_20e3.svg` | 7️⃣   | keycap: 7  |
| `emoji_u0038_20e3.svg` | 8️⃣   | keycap: 8  |
| `emoji_u0039_20e3.svg` | 9️⃣   | keycap: 9  |

Base characters are `0023` (#), `002A` (*), and `0030`–`0039` (0–9). Note: Noto does not include `*` keycap (`002a_20e3`).

### 11. Flag Sequences (Regional Indicators)

Country flags use pairs of Regional Indicator symbols (U+1F1E6–U+1F1FF). Each regional indicator corresponds to a Latin letter (1F1E6=A, 1F1E7=B, … 1F1FF=Z). The pair encodes an ISO 3166-1 alpha-2 country code.

```
emoji-test.txt:   1F1FA 1F1F8  ; fully-qualified # 🇺🇸 flag: United States

filename:         (would be emoji_u1f1fa_1f1f8.svg if present)
```

The `flags/` context contains 367 files in three groups:

**8 symbolic flags** (codepoint-named, from main Noto emoji source):

| Filename                                | Emoji | Description                |
|-----------------------------------------|-------|----------------------------|
| `emoji_u1f38c.svg`                      | 🎌    | crossed flags              |
| `emoji_u1f3c1.svg`                      | 🏁    | chequered flag             |
| `emoji_u1f3f3.svg`                      | 🏳    | white flag                 |
| `emoji_u1f3f3_200d_1f308.svg`           | 🏳‍🌈  | white flag + rainbow       |
| `emoji_u1f3f3_200d_26a7.svg`            | 🏳‍⚧  | white flag + transgender   |
| `emoji_u1f3f4.svg`                      | 🏴    | black flag                 |
| `emoji_u1f3f4_200d_2620.svg`            | 🏴‍☠  | black flag + skull = pirate|
| `emoji_u1f6a9.svg`                      | 🚩    | triangular flag            |

**259 country flags** (ISO 3166-1 alpha-2 named, from Noto `third_party/region-flags`):

```
US.svg    → 🇺🇸 United States
FR.svg    → 🇫🇷 France
JP.svg    → 🇯🇵 Japan
```

**100 subdivision flags** (ISO 3166-2 named, from Noto `third_party/region-flags`):

```
GB-ENG.svg  → 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England
GB-SCT.svg  → 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland
CA-ON.svg   → Ontario
MX-AGU.svg  → Aguascalientes
```

Country and subdivision flags use readable ISO names rather than codepoint encoding. These SVGs are vector source only — no pre-rendered PNGs are shipped.

### 12. Component Emoji

The `component` group contains modifier characters that are not standalone emoji — they modify other emoji when combined. These are the skin tone swatches and hair style components.

| Filename              | Codepoint | Description              |
|-----------------------|-----------|--------------------------|
| `emoji_u1f3fb.svg`    | U+1F3FB   | Light skin tone          |
| `emoji_u1f3fc.svg`    | U+1F3FC   | Medium-light skin tone   |
| `emoji_u1f3fd.svg`    | U+1F3FD   | Medium skin tone         |
| `emoji_u1f3fe.svg`    | U+1F3FE   | Medium-dark skin tone    |
| `emoji_u1f3ff.svg`    | U+1F3FF   | Dark skin tone           |
| `emoji_u1f9b0.svg`    | U+1F9B0   | Red hair                 |
| `emoji_u1f9b1.svg`    | U+1F9B1   | Curly hair               |
| `emoji_u1f9b2.svg`    | U+1F9B2   | Bald                     |
| `emoji_u1f9b3.svg`    | U+1F9B3   | White hair               |

## FE0F Handling

`FE0F` (Variation Selector 16) requests emoji presentation for characters that have both text and emoji forms. It is significant in `emoji-test.txt` for determining qualification level:

- **Fully-qualified**: all required FE0F present (e.g., `1F3C3 200D 2642 FE0F`)
- **Minimally-qualified**: some FE0F omitted (e.g., `1F3C3 200D 2642`)
- **Unqualified**: all FE0F omitted

**Noto filenames always omit FE0F.** The `emoji_import.py` script handles this with fuzzy lookup — trying sequences with and without FE0F to match files to their `emoji-test.txt` entries.

## Codepoint Order in Filenames

The codepoint order in filenames matches the canonical Unicode sequence:

```
{base}[_{skin_tone}][_200d_{gender}][_200d_{direction}]

Components in order:
1. Base emoji codepoint          (always first)
2. Skin tone modifier            (1F3FB–1F3FF, immediately after base)
3. ZWJ + gender sign             (200D + 2640 or 2642)
4. ZWJ + direction/object        (200D + additional codepoint)
```

For profession/compound sequences:
```
{person}_200d_{object}

1F469_200d_1F373  = woman + cook
```

For family sequences:
```
{person}_200d_{person}_200d_{child}[_200d_{child}]

1F469_200d_1F469_200d_1F466_200d_1F466 = woman+woman+boy+boy
```

## File Counts by Context

Full Noto source counts before filtering:

| Context          | Total | Base | With ZWJ | With Skin Tone |
|------------------|-------|------|----------|----------------|
| people-body      | 2261  | 157  | 1449     | 1875           |
| objects          | 264   | 263  | 1        | 0              |
| symbols          | 224   | 224  | 0        | 0              |
| travel-places    | 218   | 218  | 0        | 0              |
| smileys-emotion  | 169   | 161  | 8        | 0              |
| animals-nature   | 159   | 154  | 5        | 0              |
| food-drink       | 131   | 129  | 2        | 0              |
| activities       | 85    | 85   | 0        | 0              |
| component        | 9     | 4    | 0        | 5              |
| flags            | 8     | 5    | 3        | 0              |
| **Total**        |**3528**|**1400**|**1468**| **1880**       |

These counts reflect the main Noto emoji source only. The 359 region flags (from `third_party/region-flags`) are additional.

Base emoji have no skin tone modifiers (1F3FB–1F3FF) and no ZWJ (200D) sequences. The people-body context dominates the total because of the combinatorial explosion: each person emoji can have 5 skin tones × 2 genders × optional direction = up to 36 variants per base emoji.

### Filtered counts (shipped in this pack)

Removed: skin tone variants, gender sign variants (`200D 2642`/`2640`), direction variants (`200D 27A1`), component context. Non-human ZWJ compounds (black cat, polar bear, brown mushroom, etc.) are kept.

| Context          | Original | Shipped | Removed |
|------------------|----------|---------|---------|
| people-body      | 2261     | 266     | 1995    |
| objects          | 264      | 264     | 0       |
| symbols          | 224      | 224     | 0       |
| travel-places    | 218      | 218     | 0       |
| smileys-emotion  | 169      | 169     | 0       |
| animals-nature   | 159      | 159     | 0       |
| food-drink       | 131      | 131     | 0       |
| activities       | 85       | 85      | 0       |
| flags            | 8        | 8       | 0       |
| flags (region)   | —        | 359     | —       |
| **Total**        | **3519** | **1883**| **1995**|

## Reference

- Unicode Technical Standard #51 (UTS #51): https://unicode.org/reports/tr51/
- emoji-test.txt v16.0: https://unicode.org/Public/emoji/16.0/emoji-test.txt
- Noto Color Emoji source: https://github.com/googlefonts/noto-emoji
