# YDW Name Tags

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
