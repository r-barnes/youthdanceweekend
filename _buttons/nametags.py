#!/usr/bin/env python3
"""YDW name-tag list.

Reads the master sheet, keeps everyone who is actually attending, and writes a
three-column CSV -- FirstName, LastName, Pronouns -- ready for a mail merge onto
name tags. Everything year-specific lives in the CONFIG block below; the
machinery underneath does not change year to year.

Usage:
    ./nametags.py               # write the CSV, print a validation report
    ./nametags.py --dry-run     # print the rows, write nothing
    ./nametags.py --report      # validation report only (no rows, no file)
"""
import argparse
import csv
import os
import re
import sys
import zipfile

import xml.etree.ElementTree as ET

# xml.etree needs pyexpat, which is broken in some Homebrew Python builds (3.14
# links against a libexpat missing a symbol it wants). Importing the module
# still succeeds there -- it only blows up later, when a parser is actually
# constructed -- so probe it with a real parse. The system Python is always
# fine, so re-exec into it rather than making the reader's `python3` a thing
# they have to remember.
SYSTEM_PYTHON = '/usr/bin/python3'
try:
    ET.fromstring('<probe/>')
except Exception:  # pragma: no cover -- depends on the local Python build
    if sys.executable != SYSTEM_PYTHON and os.path.exists(SYSTEM_PYTHON):
        os.execv(SYSTEM_PYTHON, [SYSTEM_PYTHON] + sys.argv)
    raise

# ---------------------------------------------------------------------------
# CONFIG — edit this each year to match the new sheet.
# ---------------------------------------------------------------------------

# The master sheet. Either an .ods/.xlsx-renamed-.ods workbook (read directly,
# no export step) or a plain .csv of the one sheet.
SOURCE = '~/Documents/YDW Master Sheet 2026.xlsx.ods'

# Which sheet inside the workbook holds the roster. Ignored for a .csv source.
SHEET = 'YDW all spreadsheets'

# Where the mail-merge file lands. Kept in data/, which is gitignored -- this
# repo's published branch is gh-pages, so a roster of real names must not be
# committed. The directory is created if it does not exist.
OUTPUT = './data/nametags-2026.csv'

# Columns. Every one of these must exist in the sheet or the run aborts.
COL_ROLE = 'Role Status'
COL_FIRST = 'First name'
COL_LAST = 'Last name'
COL_TAG = 'Different Name for Tag'
COL_PRONOUNS = 'Pronouns?'

# Attendance. Anyone whose Role Status is in this set is NOT coming and is left
# off the list; every other status (Attending, Staff, Supervolunteer, Staff
# guest, Spot Offered, ...) gets a tag. Add next year's dead statuses here.
NOT_ATTENDING = {'Waitlist', 'Z Removed'}

# A "Different Name for Tag" longer than this many words is almost certainly a
# sentence rather than a name (people use the box to ask questions). Those fall
# back to First/Last name and are flagged in the report, never printed blind.
MAX_TAG_WORDS = 4

# Lowercase pronouns and join them with slashes ("She her" -> "she/her") so the
# tags read consistently. Only rearranges recognised pronoun words; anything
# unusual is passed through untouched and flagged. Set False to print as typed.
NORMALIZE_PRONOUNS = True

# Words normalize_pronouns() is willing to treat as pronouns when it decides
# whether a space-separated entry is a pronoun set or free text.
PRONOUN_WORDS = {
    'he', 'him', 'his', 'she', 'her', 'hers', 'they', 'them', 'their',
    'theirs', 'ze', 'zir', 'zirs', 'xe', 'xem', 'xyr', 'ey', 'em', 'eir',
    'fae', 'faer', 'it', 'its', 'any', 'all', 'none', 'ask',
}

# Collapse rows that are the same person entered twice (same name + email).
DROP_DUPLICATE_ROWS = True

# ---------------------------------------------------------------------------
# Reading the sheet
# ---------------------------------------------------------------------------

ODS_TABLE = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
ODS_TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'

# ODS compresses runs of identical cells/rows with number-*-repeated. A trailing
# empty run can claim to repeat thousands of times, so cap expansion; no real
# sheet has 200 identical adjacent columns or rows of data.
MAX_REPEAT = 200


def _cell_text(cell):
    """The visible text of one ODS cell (a cell holds <text:p> per line)."""
    return ' '.join(''.join(p.itertext()) for p in cell.findall(ODS_TEXT + 'p')).strip()


def read_ods(path, sheet_name):
    """Rows of the named sheet as lists of strings, header row first."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('content.xml'))

    tables = {t.get(ODS_TABLE + 'name'): t for t in root.iter(ODS_TABLE + 'table')}
    if sheet_name not in tables:
        sys.exit(
            f"sheet {sheet_name!r} not found in {path}\n"
            f"  sheets present: {', '.join(repr(n) for n in tables)}"
        )

    rows = []
    for row in tables[sheet_name].iter(ODS_TABLE + 'table-row'):
        cells = []
        for cell in row.findall(ODS_TABLE + 'table-cell'):
            repeat = min(int(cell.get(ODS_TABLE + 'number-columns-repeated', 1)), MAX_REPEAT)
            cells.extend([_cell_text(cell)] * repeat)
        while cells and not cells[-1]:
            cells.pop()
        repeat = min(int(row.get(ODS_TABLE + 'number-rows-repeated', 1)), MAX_REPEAT)
        rows.extend([cells] * repeat)
    return rows


def load_rows(path):
    """The sheet as a list of dicts keyed by column header."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        sys.exit(f"source sheet not found: {path}")

    if path.lower().endswith('.csv'):
        with open(path, newline='', encoding='utf-8-sig') as f:
            table = [list(r) for r in csv.reader(f)]
    else:
        table = read_ods(path, SHEET)

    if not table:
        sys.exit(f"no rows in {path}")

    header = [h.strip() for h in table[0]]
    required = (COL_ROLE, COL_FIRST, COL_LAST, COL_TAG, COL_PRONOUNS)
    missing = [c for c in required if c not in header]
    if missing:
        sys.exit(
            "these configured columns are not in the sheet:\n"
            + ''.join(f"  {c!r}\n" for c in missing)
            + "  columns found: " + ', '.join(repr(h) for h in header)
        )

    rows = []
    for raw in table[1:]:
        row = {h: (raw[i].strip() if i < len(raw) else '') for i, h in enumerate(header)}
        # A sheet is mostly empty padding below the last real entry, and the
        # roster picks up blank filler rows in the middle too. Neither is a
        # person; dropping them here keeps the run's counts honest.
        if any(row.values()):
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Deciding who gets a tag, and what it says
# ---------------------------------------------------------------------------

def is_attending(row):
    """A tag is printed for every named person not in a NOT_ATTENDING status.

    The name check matters as much as the status one: the sheet accumulates
    blank filler rows that have neither a name nor a status, and those must not
    become blank name tags.
    """
    if not row[COL_FIRST] and not row[COL_LAST]:
        return False
    return row[COL_ROLE] not in NOT_ATTENDING


def tag_name(row):
    """(first, last, note) for the tag.

    "Different Name for Tag" supersedes both name columns. It is one free-text
    box, so it is split at the first space -- "Robin Alvarez" becomes Robin /
    Alvarez, and a bare "Robin" becomes Robin with no last name, which is what a tag
    should say anyway. An over-long entry is prose, not a name: fall back to the
    real name and let the report raise it.
    """
    tag = row[COL_TAG]
    if not tag:
        return row[COL_FIRST], row[COL_LAST], None

    if len(tag.split()) > MAX_TAG_WORDS:
        return row[COL_FIRST], row[COL_LAST], f"tag-name box holds prose, using real name: {tag!r}"

    parts = tag.split(None, 1)
    return parts[0], (parts[1] if len(parts) > 1 else ''), None


def normalize_pronouns(value):
    """(pronouns, note) -- tidy the common spellings, pass anything odd through.

    The sheet collects a free-text answer, so the same pronouns arrive as
    "she/her", "She/Her", "(They/she)" and "She her". Lowercasing and joining on
    slashes makes the tags match each other. Only done when every word is a
    recognised pronoun, so "any pronouns" or a sentence survives as typed.
    """
    value = value.strip()
    if not value or not NORMALIZE_PRONOUNS:
        return value, None

    cleaned = value.strip('()[] ').strip()
    words = [w for w in re.split(r'[\s/,]+', cleaned.lower()) if w]
    if words and all(w.strip('.') in PRONOUN_WORDS for w in words):
        return '/'.join(w.strip('.') for w in words), None
    return cleaned, f"unrecognised pronouns, left as typed: {value!r}"


def build(rows):
    """(records, notes) -- the tag list plus everything a human should eyeball."""
    notes = []
    people = [r for r in rows if is_attending(r)]

    if DROP_DUPLICATE_ROWS:
        seen, deduped = set(), []
        for row in people:
            key = (row[COL_FIRST].lower(), row[COL_LAST].lower(), row['Email Address'].lower()
                   if 'Email Address' in row else '')
            if key in seen:
                notes.append(f"duplicate row dropped: {row[COL_FIRST]} {row[COL_LAST]}")
                continue
            seen.add(key)
            deduped.append(row)
        people = deduped

    records = []
    for row in people:
        first, last, note = tag_name(row)
        real = f"{row[COL_FIRST]} {row[COL_LAST]}".strip()
        if note:
            notes.append(f"{real}: {note}")

        pronouns, note = normalize_pronouns(row[COL_PRONOUNS])
        if note:
            notes.append(f"{real}: {note}")
        if not pronouns:
            notes.append(f"{real}: no pronouns given -- tag will have a blank line")

        records.append({'FirstName': first, 'LastName': last, 'Pronouns': pronouns})

    # Two identical tags in a stack of 160 are invisible until they are printed.
    printed = {}
    for rec in records:
        printed.setdefault(f"{rec['FirstName']} {rec['LastName']}".strip().lower(), []).append(rec)
    for label, group in printed.items():
        if len(group) > 1:
            notes.append(f"{len(group)} people share the tag {label!r} -- give them something to tell apart")

    return records, notes


# ---------------------------------------------------------------------------

FIELDS = ('FirstName', 'LastName', 'Pronouns')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('source', nargs='?', default=SOURCE,
                        help=f"master sheet to read (default: {SOURCE})")
    parser.add_argument('-o', '--output', default=OUTPUT,
                        help=f"where to write the CSV (default: {OUTPUT})")
    parser.add_argument('--dry-run', action='store_true',
                        help="print the rows instead of writing the file")
    parser.add_argument('--report', action='store_true',
                        help="print only the validation report")
    args = parser.parse_args()

    rows = load_rows(args.source)
    records, notes = build(rows)

    if args.dry_run:
        width = max((len(f"{r['FirstName']} {r['LastName']}".strip()) for r in records), default=0)
        for rec in records:
            label = f"{rec['FirstName']} {rec['LastName']}".strip()
            print(f"{label:<{width}}  {rec['Pronouns']}")
    elif not args.report:
        out = os.path.expanduser(args.output)
        parent = os.path.dirname(out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(records)
        print(f"wrote {out}", file=sys.stderr)

    named = [r for r in rows if r[COL_FIRST] or r[COL_LAST]]
    not_coming = len(named) - len([r for r in named if is_attending(r)])
    print(
        f"{len(records)} name tags "
        f"-- {len(named)} people on the sheet, {not_coming} not attending, "
        f"{len(named) - not_coming - len(records)} duplicate.",
        file=sys.stderr,
    )
    if notes:
        print(f"\n{len(notes)} thing(s) to check before printing:", file=sys.stderr)
        for note in notes:
            print(f"  - {note}", file=sys.stderr)


if __name__ == '__main__':
    main()
