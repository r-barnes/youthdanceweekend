#!/usr/bin/env python3
"""Weighted YDW lottery.

Ranks applicants in a weighted-random order so the top N are winners and the
rest form the waitlist (in order). Everything year-specific lives in the CONFIG
block below; the machinery underneath does not change year to year.

Usage:
    ./lottery.py             # one rank per sheet row (1 = first picked), blank
                             #   for ineligible rows -> paste as waitlist column
    ./lottery.py --dry-run   # print each eligible person's computed weight
"""
import argparse
import csv
import os
import random
import sys

# ---------------------------------------------------------------------------
# CONFIG — edit this each year to match the new sheet.
# ---------------------------------------------------------------------------

# Input lives in data/, which is gitignored -- this repo's published branch is
# gh-pages, so participant data must not be committed.
#CSV_PATH = './data/ydw_master_sheet_2025/main.csv'
CSV_PATH = './data/ydw2026.csv'

# Columns used to build each person's display name.
NAME_COLUMNS = ('First name', 'Last name')

# Eligibility: everyone is entered into the draw EXCEPT staff. The 'Staff?'
# column marks staff with 'Yes'; blank / anything other than 'Yes' is a regular
# applicant and gets a rank.
ELIGIBLE_COLUMN = 'Staff?'

# Staff plus-ones: this column names the staff member a person is attending as a
# guest of. Anyone with a value here is guaranteed a spot -- excluded from the
# draw, like staff -- and gets a blank rank. Validated loudly: the named host
# must exist AND be staff (only staff get plus-ones). Set to None to disable.
PLUS_ONE_COLUMN = 'Plus-one of'


def is_staff(row):
    return row.get(ELIGIBLE_COLUMN, '').strip() == 'Yes'


def is_eligible(row):
    """In the lottery = not staff and not a (guaranteed) staff plus-one."""
    if is_staff(row):
        return False
    if PLUS_ONE_COLUMN and row.get(PLUS_ONE_COLUMN, '').strip():
        return False
    return True


# Linked applicants: a column holding a comma-separated list of other people's
# names (matching NAME_COLUMNS, e.g. "First Last"). Linked people are drawn as a
# single unit -- they share one waitlist number and rise/fall together, and the
# group draws at the AVERAGE of its members' weights (so group size doesn't buy
# better odds). Set to None to disable.
LINK_COLUMN = 'Would you like to group your lottery with others?'


def age_at_most(n):
    """Value-test: True when the cell parses to an integer <= n."""
    def test(value):
        try:
            return int(value) <= n
        except ValueError:
            return False
    return test


def age_between(lo, hi):
    """Value-test: True when the cell parses to an integer in [lo, hi]."""
    def test(value):
        try:
            return lo <= int(value) <= hi
        except ValueError:
            return False
    return test


# Weighting rules: (column, predicate(value) -> bool, multiplier, label).
# A person starts at weight 1.0; every rule whose predicate matches their value
# in that column multiplies their weight. Multipliers > 1 favor selection,
# multipliers < 1 weight against it. The label is a short name shown in --explain
# (handy when two rules share a column, like the two age bands below).
RULES = [
    ('Plane?', lambda v: v.strip() == 'Yes', 2.25, 'plane'),
    ('How old will you be in October 2026?', age_at_most(24), 1.75, 'under 25'),
    ('How old will you be in October 2026?', age_between(25, 39), 1.5, '25-39'),
    ('Is this your first time at YDW?', lambda v: v.strip() == 'Yes', 2.0, 'first-timer'),
]

# 2026:
# people who need to fly on plane x2.25
# people under 25 x1.75
# people who've never attended YDW + x2.0
# people under 40 x1.25
# VT + NH? we decided not.

# ---------------------------------------------------------------------------
# Machinery — stable from year to year.
# ---------------------------------------------------------------------------


def validate_columns(fieldnames):
    """Error loudly if any configured column is missing from the sheet."""
    headers = set(fieldnames or ())
    needed = set(NAME_COLUMNS) | {ELIGIBLE_COLUMN} | {col for col, _, _, _ in RULES}
    if LINK_COLUMN:
        needed.add(LINK_COLUMN)
    if PLUS_ONE_COLUMN:
        needed.add(PLUS_ONE_COLUMN)
    missing = sorted(col for col in needed if col not in headers)
    if missing:
        sys.exit(
            "ERROR: these configured columns are not in the CSV:\n"
            + "\n".join(f"  - {col!r}" for col in missing)
            + "\n\nColumns present in the sheet:\n"
            + "\n".join(f"  - {col!r}" for col in sorted(headers))
        )


def weight_for(row):
    """Compute a person's selection weight from the RULES."""
    weight = 1.0
    for col, test, mult, _ in RULES:
        if test(row.get(col, '')):
            weight *= mult
    return weight


def name_for(row):
    return ' '.join(row[col].strip() for col in NAME_COLUMNS)


def group_weight(group):
    """A linked group draws as one entry at the AVERAGE of its members' weights,
    so linking couples their outcomes without letting group size buy better odds.
    """
    return sum(weight_for(row) for row in group) / len(group)


def _norm(name):
    """Normalize a name for matching: lowercase, collapse whitespace."""
    return ' '.join(name.split()).lower()


def validate_plus_ones(rows):
    """Exit loudly if any plus-one names a host who is missing or not staff."""
    if not PLUS_ONE_COLUMN:
        return

    index = {}
    for row in rows:
        index.setdefault(_norm(name_for(row)), []).append(row)

    errors = []
    for i, row in enumerate(rows):
        host = row.get(PLUS_ONE_COLUMN, '').strip()
        if not host:
            continue
        who = f"row {i + 2}: {name_for(row)!r} is a plus-one of {host!r},"
        matches = index.get(_norm(host), [])
        if not matches:
            errors.append(f"{who} who is not in the sheet")
        elif len(matches) > 1:
            errors.append(f"{who} but {len(matches)} people share that name")
        elif not is_staff(matches[0]):
            errors.append(f"{who} who is not staff "
                          f"({ELIGIBLE_COLUMN} = {matches[0].get(ELIGIBLE_COLUMN, '')!r})")

    if errors:
        sys.exit("ERROR: problems with plus-ones:\n"
                 + "\n".join(f"  - {e}" for e in errors))


def build_groups(rows):
    """Union rows that reference each other via LINK_COLUMN into groups.

    Returns a list of groups (each a list of rows in sheet order); unlinked
    people form singleton groups. Links are undirected -- naming someone on
    either side links the pair.

    A link to a name that isn't in the sheet (e.g. a friend who never applied)
    is expected, not fatal: it's skipped with a warning to stderr and the person
    stays in the draw on their own. Genuinely unsafe cases -- a name matching two
    people, or a group mixing eligible and excluded people -- still exit loudly.
    """
    if not LINK_COLUMN:
        return [[row] for row in rows]

    index = {}
    for i, row in enumerate(rows):
        index.setdefault(_norm(name_for(row)), []).append(i)

    parent = list(range(len(rows)))

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:      # path compression
            parent[x], x = root, parent[x]
        return root

    errors = []
    warnings = []
    for i, row in enumerate(rows):
        for target in (n.strip() for n in row.get(LINK_COLUMN, '').split(',')):
            if not target:
                continue
            matches = index.get(_norm(target), [])
            if not matches:
                warnings.append(f"row {i + 2}: {name_for(row)!r} linked to {target!r}, "
                                "who is not in the sheet -- link ignored")
            elif len(matches) > 1:
                errors.append(f"row {i + 2}: {name_for(row)!r} links to {target!r}, "
                              f"but {len(matches)} people share that name")
            else:
                parent[find(i)] = find(matches[0])

    comps = {}
    for i, row in enumerate(rows):
        comps.setdefault(find(i), []).append(row)

    for members in comps.values():
        if len(members) > 1:
            excluded = [name_for(r) for r in members if not is_eligible(r)]
            if excluded and len(excluded) != len(members):
                names = ', '.join(name_for(r) for r in members)
                errors.append(f"linked group [{names}] mixes eligible and excluded "
                              f"people (excluded: {', '.join(excluded)})")

    if warnings:
        print("WARNING: some linked names were not found (those links ignored, "
              "spreadsheet unchanged):\n"
              + "\n".join(f"  - {w}" for w in warnings), file=sys.stderr)
    if errors:
        sys.exit("ERROR: problems with linked names:\n"
                 + "\n".join(f"  - {e}" for e in errors))

    return list(comps.values())


def load_rows(path):
    """Read every row in sheet order, validating configured columns."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        sys.exit(f"CSV not found: {path}\n  export the master sheet into data/, or pass a path")
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        validate_columns(reader.fieldnames)
        return list(reader)


def explain(rows, groups):
    """Print the full, deterministic decision trail for every person.

    Shows why each person is included/excluded, how every RULE affected their
    weight, and which linked group they draw with. Randomness is NOT involved
    here -- this is the auditable part. (The final rank is a weighted random
    draw of the group weights; use --seed to reproduce a specific draw.)
    """
    group_of = {id(row): g for g in groups for row in g}
    eligible = [row for row in rows if is_eligible(row)]
    entries = [g for g in groups if is_eligible(g[0])]
    print(f"{len(rows)} rows | {len(eligible)} eligible | "
          f"{len(rows) - len(eligible)} excluded | {len(entries)} lottery entries\n")

    for i, row in enumerate(rows, start=2):  # +1 header, +1 for 1-based sheet row
        name = name_for(row) or '(no name)'
        if not is_eligible(row):
            if is_staff(row):
                reason = f"staff, {ELIGIBLE_COLUMN} = {row.get(ELIGIBLE_COLUMN, '')!r}"
            else:
                reason = f"plus-one of {row.get(PLUS_ONE_COLUMN, '').strip()!r}"
            print(f"row {i:<4} EXCLUDED  {name}  ({reason})")
            continue

        weight = 1.0
        factors = ['1.0']
        for col, test, mult, _ in RULES:
            if test(row.get(col, '')):
                weight *= mult
                factors.append(f"x{mult}")

        group = group_of[id(row)]
        note = ""
        if len(group) > 1:
            others = ', '.join(name_for(r) for r in group if r is not row)
            note = f"  [linked with {others} -> group weight {group_weight(group):.3f}]"
        print(f"row {i:<4} weight {weight:6.3f}  {name}{note}")
        for col, test, mult, label in RULES:
            val = row.get(col, '')
            mark = f"x{mult}" if test(val) else "  . "
            print(f"           {mark:>6}  {label:<12} {col} = {val!r}")
        print(f"           = {' '.join(factors)} = {weight:.4f}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'csv_path', nargs='?', default=CSV_PATH,
        help=f"CSV to draw from (default: {CSV_PATH})",
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="print each eligible person's computed weight instead of drawing",
    )
    parser.add_argument(
        '--explain', action='store_true',
        help="print the full decision trail (eligibility + every rule) per person",
    )
    parser.add_argument(
        '--groups', action='store_true',
        help="print a group label (G1, G2, ...) per sheet row for linked people, "
             "blank otherwise -- a column to paste alongside the waitlist numbers",
    )
    parser.add_argument(
        '--seed', type=int, default=None,
        help="seed the draw so ranks are reproducible (for auditing/re-runs)",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    rows = load_rows(args.csv_path)
    validate_plus_ones(rows)
    groups = build_groups(rows)
    # Each group is entirely eligible or entirely excluded (build_groups checks
    # this), so the first member decides. Excluded groups get no rank.
    entries = [g for g in groups if is_eligible(g[0])]

    if args.explain:
        explain(rows, groups)
        return

    if args.dry_run:
        for group in sorted(entries, key=group_weight, reverse=True):
            label = ' + '.join(name_for(row) for row in group)
            print(f"{group_weight(group):6.3f}  {label}")
        people = sum(len(g) for g in entries)
        print(f"\n{len(entries)} lottery entries ({people} people).", file=sys.stderr)
        return

    if args.groups:
        # One line per sheet row: a shared label for each multi-person linked
        # group (numbered in sheet order), blank for everyone else. Deterministic
        # -- independent of the seed -- so it's stable across draws.
        label_by_row = {}
        n = 0
        for group in groups:
            if len(group) > 1:
                n += 1
                for row in group:
                    label_by_row[id(row)] = f"G{n}"
        for row in rows:
            print(label_by_row.get(id(row), ''))
        return

    # Efraimidis-Spirakis weighted random ordering without replacement:
    # key = random() ** (1 / weight); sort descending. Higher weight => more
    # likely to land near the top of the draw. Linked people draw as one entry on
    # their averaged weight to decide where their block lands.
    ranked = sorted(
        entries,
        key=lambda group: random.random() ** (1.0 / group_weight(group)),
        reverse=True,
    )
    # Expand each group into a block of consecutive positions so every person
    # gets a distinct waitlist number, with linked members kept adjacent. Order
    # within a block is shuffled (seeded) since the group won its spot together.
    position_by_row = {}
    position = 1
    for group in ranked:
        members = list(group)
        random.shuffle(members)
        for row in members:
            position_by_row[id(row)] = position
            position += 1

    # One line per sheet row, in sheet order: the person's waitlist number if
    # eligible, else blank -- so the whole column pastes straight into the sheet.
    for row in rows:
        print(position_by_row.get(id(row), ''))


if __name__ == '__main__':
    main()
