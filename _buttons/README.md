# YDW Name Tags

Two steps. `nametags.py` turns the master sheet into a clean roster CSV;
`buttons.py` lays that roster onto a designed button and exports print-ready
PDF. `make_template.py` generates a skeleton design to start from.

```
master sheet (.ods)
      |  nametags.py          -> data/nametags-2026.csv   (FirstName, LastName, Pronouns)
      |
      +  button-template.svg  (your Inkscape design)
      |
      v  buttons.py           -> data/print-2026/buttons-all.pdf
```

---

`nametags.py` turns the master sheet into the mail-merge file for name-tag
buttons: it keeps everyone who is actually attending, applies each person's
preferred tag name, tidies the pronouns, and writes three columns —
**FirstName, LastName, Pronouns**.

It is standalone — **not** part of the Jekyll site build. Pure Python 3 standard
library, no dependencies, no `pip install`. It reads the `.ods` workbook
directly, so there is no export-to-CSV step.

```bash
./nametags.py              # write data/nametags-2026.csv, print the validation report
./nametags.py --dry-run    # print the tags to read through, write nothing
./nametags.py --report     # just the report: what to fix before printing
```

---

## How a run works, start to finish

1. **Load** the sheet named by `SHEET` out of `SOURCE`. An `.ods` workbook is
   read in place; a `.csv` export works too, if a future year's sheet lives
   somewhere else.
2. **Validate loudly** — every column in the CONFIG block must exist, or the run
   aborts and lists the columns it *did* find. Better to stop than to print 161
   wrong buttons.
3. **Decide who is coming** — everyone whose `Role Status` is *not* in
   `NOT_ATTENDING` (`Waitlist`, `Z Removed`). Every other status — `Attending`,
   `Staff`, `Supervolunteer`, `Staff guest`, `Spot Offered` — gets a tag.
   A row also needs a name: the sheet collects blank filler rows, and those must
   not become blank buttons.
4. **Drop duplicate rows** — same name and email entered twice.
5. **Pick the name.** `Different Name for Tag` supersedes both name columns,
   split at the first space. Most people write only a first name, so a blank
   `LastName` is normal and expected — see below.
6. **Tidy the pronouns** — lowercase, slash-separated, so the buttons match each
   other. Anything unrecognised is passed through exactly as typed and flagged.
7. **Report** — duplicates, blank pronouns, prose in the tag-name box, and any
   two people who would get identical buttons.

---

## The blank-LastName thing (read this before editing the merge template)

`Different Name for Tag` is one free-text box, and **most people put a single
word in it** — 24 of the 161 tags in 2026 have an empty `LastName` as a result.
That is correct, not a bug: someone who writes "Robin" wants a button that says
Robin.

So the mail-merge template has to look right with the last name missing. In
LibreOffice, put `FirstName` and `LastName` in separate frames or paragraphs
rather than on one line with a literal space between them, or the short tags
come out with a trailing gap.

---

## CONFIG — what to change next year

Everything year-specific is in one block at the top of the script.

| Setting | What it does |
| --- | --- |
| `SOURCE` | Path to the master sheet (`.ods` or `.csv`). |
| `SHEET` | Which sheet inside the workbook holds the roster. |
| `OUTPUT` | Where the CSV lands, under `data/` — **bump the year**. |
| `COL_*` | The five column headings. Update if the form's wording changes. |
| `NOT_ATTENDING` | Role statuses that mean "no button". Add new dead statuses here. |
| `MAX_TAG_WORDS` | Longer than this in the tag-name box is prose, not a name. |
| `NORMALIZE_PRONOUNS` | `False` prints pronouns exactly as typed. |
| `PRONOUN_WORDS` | Words the tidier recognises when reading a space-separated answer. |
| `DROP_DUPLICATE_ROWS` | `False` keeps double-entered people. |

A typical year is three edits: `SOURCE`, `OUTPUT`, and whatever the role-status
vocabulary turned into.

---

## The report is the point

The script never silently guesses. Anything ambiguous is printed to stderr and
left for a human:

```
161 name tags -- 262 people on the sheet, 100 not attending, 1 duplicate.

15 thing(s) to check before printing:
  - duplicate row dropped: Marisol Ferreira
  - Quillon Vasterling: tag-name box holds prose, using real name: "whatever is easiest, I don't mind ..."
  - Wren Baptiste: unrecognised pronouns, left as typed: 'they/any/whatever fits'
  - Tobias Nkemdirim: no pronouns given -- tag will have a blank line
  - 2 people share the tag 'robin' -- give them something to tell apart
```

The last two categories are the ones that actually matter at the printer.
**Blank pronouns** (11 people in 2026) leave an empty line on the button — decide
whether that is fine or worth an email. **Shared tags** are invisible in a stack
of 161 until two people pick up the same button.

---

## Notes

- **`data/` is gitignored; the script is not.** `gh-pages` is the published
  branch, so a roster of real names and pronouns must not be committed — but the
  script and this README should be. Keep every input and output under `data/`
  and that stays true by default. `_lottery/` follows the same split.
- **Interpreter:** the script re-execs itself into `/usr/bin/python3` if the
  default `python3` cannot parse XML. Homebrew's Python 3.14 currently ships a
  broken `pyexpat`, and `.ods` files are zipped XML. Nothing to do about it —
  just don't be surprised that the script hops interpreters.
- **`Button Name Updates` sheet:** the workbook has a second, empty sheet with
  its own "different name for tag" column, left over from a previous year. The
  script ignores it. Delete it or wire it in, but don't let it sit there looking
  authoritative.


---

# Buttons

## The design is an SVG you own

`buttons.py` never hardcodes a position, size or font. It reads them off your
Inkscape file. The entire contract is three named text objects:

| id | what it is |
| --- | --- |
| `firstname` | styled how you want it; its font-size is the **maximum** |
| `lastname` | same |
| `pronouns` | same |
| `firstname-box` *(optional)* | a rect marking the area the first name may fill |

In Inkscape: select the text, **Object Properties** (`Ctrl+Shift+O`), and fill
in **ID** *or* **Label** — either works.

> **Save as "Inkscape SVG", or use the ID field.** Exporting as *Plain SVG* or
> *Optimized SVG* strips the entire `inkscape:` namespace, and **Label** lives
> there — it is silently deleted, while **ID** survives every format. If the
> script says nothing has that id or label, this is almost always why.

A layer labelled `guides` is dropped from the output, so put cut lines and box
outlines there. Everything else — artwork, embedded images, curved text on a
path, nested groups with their own transforms — is copied through untouched.

Don't want to rename anything? Point `FIELD_IDS` at whatever ids the design
already has:

```python
FIELD_IDS = {'firstname': 'text42', 'lastname': 'text42-9', 'pronouns': 'text42-9-6'}
```

**Units take care of themselves.** Inkscape files are usually in px even when the
document is sized in mm; the script reads the real scale from the `viewBox` and
converts, so the design's unit choice does not matter.

**If the design sets names in capitals**, set `UPPERCASE = True`. The roster is
mixed case, so this is a property of the design, not the data. Capitals are
wider, so expect more names to shrink.

To start from scratch:

```bash
./make_template.py                                # 68mm button, 58mm safe zone
./make_template.py --first-size 11 --paper a4
```

The defaults match the press: **68mm footprint, 58mm safe zone**, which should
hold year to year. Text is fitted inside the safe zone, not the full circle.

It prints the grid that falls out of the geometry, which you paste into
`buttons.py`'s CONFIG:

```
  button    68.0mm visible, 68.0mm footprint, 58.0mm safe zone
  letter @ 10.0mm margin -> 2 x 3 = 6 per sheet
  161 buttons -> 27 sheets
```

**Margin is worth a moment.** Three 68mm circles need 204mm of a 215.9mm page,
so the column count falls off a cliff at 5.95mm:

| Margin | Per sheet | Sheets for 161 |
| --- | --- | --- |
| 6mm and up | 6 | 27 |
| 5.9mm or less | 9 | **18** |

A third fewer sheets, but 5mm margins are inside some printers' unprintable
area and would clip the artwork. Worth a single test page before committing.

## How a name is fitted

1. **Measure**, don't count characters. One Inkscape `--query-all` call returns
   the true rendered width of every name in the real font. In a proportional
   face a 12-character name can be narrower than a 9-character one.
2. **Full size** if it fits the box. For 2026 that is 155 of 161 buttons.
3. **Shrink** to the largest size that fits, never below `MIN_SCALE`. Names are
   not broken across lines.
4. Anything that would need to go below the floor is set **at** the floor and
   flagged loudly — it prints, but you were told.

How many get shrunk depends entirely on the design's first-name size. On the
2026 design, set in capitals, that is **148 of 161 at full size** and 13 shrunk,
the worst around 62%. If too many are shrinking, the lever is the design: lower
the first name's font size a little and more names clear it untouched.

`WRAP_BEFORE_SHRINK = True` switches to breaking multi-word names across two
lines instead, keeping one uniform size. If you use it, give the design headroom
*above* the first name: extra lines stack upward, and the script warns when a
wrapped block is taller than its box.

## Proofs

Every run writes two PDFs worth looking at before committing 27 sheets to paper:

- `proof-button.pdf` — one button at 1:1, to hold against a physical blank
- `proof-worst.pdf` — a sheet of only the names that needed wrapping or shrinking

These exist because the failure mode is subtle. An early version centred wrapped
names on their baseline, which pushed the second line straight through the last
name; nothing in the report said so, and the proof made it obvious at a glance.

## Image quality

If the design's artwork is a raster image with transparency — which is what a
PDF or Illustrator import produces — two things quietly wreck it on the way to
PDF, and both are handled automatically:

1. **`image-rendering:optimizeSpeed`.** Imports carry this, and it tells the
   renderer to skip interpolation. The artwork prints visibly jagged. It is
   rewritten to `optimizeQuality`.
2. **Masked images flatten at 72 dpi.** Inkscape's PDF backend rasterises a
   masked object at PDF user-space resolution regardless of `--export-dpi`
   (tested: the flag, the actions API, and rewriting the image geometry all
   change nothing). So masked images are pre-rendered at `FLATTEN_MASKS_DPI`
   with the mask baked into the alpha channel, and the PDF gets a plain
   high-resolution image with no mask at all.

The difference is not subtle — before, artwork edges were stair-stepped at
roughly 72 dpi while the vector text beside them was perfectly smooth.

`pdfimages -list data/print-2026/buttons-all.pdf` is the way to check: every
image should report 300 ppi or better. The cost is file size, since each button
carries its own copy — about 7 MB at 300 dpi, 18 MB at 600.

## Printing

**100% scale, "fit to page" OFF.** Any scaling breaks registration with the
punch and ruins the run.

## CONFIG

| Setting | What it does |
| --- | --- |
| `CSV_PATH` | Roster from `nametags.py`. |
| `TEMPLATE` | Your design SVG. |
| `OUT_DIR` | Where sheets and proofs land — **bump the year**. |
| `PAPER`, `MARGIN_MM`, `COLS`, `ROWS` | Sheet grid; `make_template.py` prints these. |
| `FIELD_IDS` | Which object in the design holds each field. |
| `UPPERCASE` | `True` if the design sets names in capitals. |
| `SAFE_DIAMETER_MM` | The press's safe zone, used when there is no `-box` rect. |
| `FLATTEN_MASKS_DPI` | Resolution for pre-rendering masked artwork; `0` disables. |
| `MIN_SCALE` | How far a name may shrink before it is a problem. |
| `WRAP_BEFORE_SHRINK` | `False` (default) shrinks; `True` breaks names across lines. |
| `LINE_SPACING` | Leading between wrapped lines. |

## Notes

- **Fonts must be installed on the rendering machine.** If the design uses a font
  you do not have, Inkscape substitutes silently and every measurement and line
  break shifts. Get the font file along with the SVG.
- **Requires** Inkscape (measurement + PDF export) and `pdfunite` from poppler
  (stitching sheets). Both were already on this machine.
- **Buttons come out in roster order**, which is the master sheet's order and only
  partly alphabetical. If you want them sorted for check-in, that is a small
  change to `nametags.py`.
