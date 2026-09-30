# YDW Lottery

`lottery.py` runs the Youth Dance Weekend participant lottery: it reads a CSV
export of the sign-up sheet, gives each applicant a **weighted-random**
waitlist position, and prints a column of numbers you paste back into the sheet.

It is standalone — **not** part of the Jekyll site build. Pure Python 3 standard
library, no dependencies, no `pip install`.

**`data/` is gitignored; this script is not.** `gh-pages` is the published
branch, so participant data must not be committed. Keep every spreadsheet and
CSV export under `data/`.

```bash
./lottery.py --explain            # sanity-check the weighting logic (no randomness)
./lottery.py --seed 1234075561    # the real draw: one waitlist number per row
./lottery.py --groups             # a parallel column showing who's linked
```

---

## How a run works, start to finish

1. **Load** the CSV (path from `CSV_PATH`, or pass one as an argument).
2. **Validate loudly** — every configured column must exist; plus-ones must point
   at real staff; ambiguous linked names abort. Better to stop than draw wrong.
3. **Decide eligibility** — staff and staff plus-ones are guaranteed in, so they
   are *excluded from the draw* and get a blank line.
4. **Weight** each eligible person: start at `1.0`, multiply by every matching
   rule in `RULES` (age band, flying in, first-timer, …).
5. **Group** linked applicants into one lottery entry at their *average* weight.
6. **Draw** — weighted-random ordering; then expand each group into a block of
   consecutive waitlist numbers, members adjacent, shuffled within the block.
7. **Print** one line per sheet row, in sheet order, so it pastes as a column.

The output always has exactly as many lines as the sheet has data rows, in the
same order. Paste it starting at the first data row (row 2). Blank lines fall on
staff / plus-ones automatically, keeping everything aligned.

---

## CLI

```
./lottery.py [csv_path] [--dry-run | --explain | --groups] [--seed N]
```

| Invocation | What it prints | Uses randomness? |
|---|---|---|
| `./lottery.py` | One **waitlist number** per sheet row (blank = not in draw) | **Yes** |
| `./lottery.py --seed N` | Same, but reproducible for seed `N` | Yes (seeded) |
| `./lottery.py --explain` | Full per-person decision trail: eligibility, every rule, group | **No** |
| `./lottery.py --dry-run` | Each lottery entry with its (averaged) weight, high→low | No |
| `./lottery.py --groups` | `G1`, `G2`, … per row for linked people, blank otherwise | **No** |

- `csv_path` is optional; without it, `CSV_PATH` from the config is used. `~` is expanded.
- **All output goes to stdout; warnings and counts go to stderr.** So piping/copying
  stdout gives you a clean column with no warning text mixed in.
- `--explain` is the audit surface — deterministic, safe to publish to the team.
- `--groups` is deterministic and **seed-independent**; run it once, it never changes.

### Two-column paste workflow

The draw and the group label are two separate columns:

```bash
./lottery.py --seed <N>   > waitlist_numbers.txt   # the numbers
./lottery.py --groups     > group_labels.txt       # the G1/G2 labels
```

Waitlist numbers are **distinct consecutive integers** — no decimals — so they
drop straight into Email Octopus with no `floor`/rounding needed.

---

## Configuration (the `CONFIG` block at the top of `lottery.py`)

Everything year-specific lives here; the machinery below the `CONFIG` banner does
not change year to year.

| Setting | Meaning |
|---|---|
| `CSV_PATH` | Default CSV to read, under `data/`. Export the master sheet tab to CSV each year. |
| `NAME_COLUMNS` | Columns joined to form a person's display name (`First name`, `Last name`). |
| `ELIGIBLE_COLUMN` | The `Staff?` column; `Yes` = staff = excluded from the draw. |
| `PLUS_ONE_COLUMN` | Names the staff host a person is a guest of; guests are guaranteed in. `None` to disable. |
| `LINK_COLUMN` | Free-text column of comma-separated names to group with. `None` to disable. |
| `RULES` | The weighting rules — see below. |

### Writing rules

Each rule is a 4-tuple: `(column, predicate, multiplier, label)`.

```python
RULES = [
    ('Plane?', lambda v: v.strip() == 'Yes', 2.25, 'plane'),
    ('How old will you be in October 2026?', age_at_most(24), 1.75, 'under 25'),
    ('How old will you be in October 2026?', age_between(25, 39), 1.5, '25-39'),
    ('Is this your first time at YDW?', lambda v: v.strip() == 'Yes', 2.0, 'first-timer'),
]
```

- **Multipliers stack multiplicatively.** Someone matching plane (×2.25) and
  first-timer (×2.0) has weight `4.5`. A weight `> 1` helps, `< 1` hurts.
- **Two rules can share a column** (e.g. the two age bands). They're mutually
  exclusive here, so at most one fires — no accidental stacking. The `label` is
  what disambiguates them in `--explain`.
- Helpers `age_at_most(n)` and `age_between(lo, hi)` safely parse the age cell;
  blank/non-numeric values match nothing (→ no boost), never crash.

---

## Key decisions (and why)

- **Weighted-random ordering, not a score sort.** Uses the Efraimidis–Spirakis
  method (`random() ** (1/weight)`, sort descending). Higher weight means *more
  likely* near the front — it biases luck, it doesn't hand-pick. A lottery, not a
  ranking.

- **Weights are multiplicative from a base of 1.0.** Independent factors (age,
  travel, first-timer) compose naturally. Neutral = 1.0.

- **Staff and plus-ones are guaranteed in, so they're pulled out of the draw**
  (blank line), rather than given a huge weight. Cleaner and unambiguous.

- **Plus-ones are validated to a real staff host.** Only staff get plus-ones; a
  guest pointing at a non-staff or missing name is a hard error. Captures the
  pairing in the sheet via `Plus-one of`.

- **Linked groups draw at the AVERAGE of member weights, not the sum.** This is
  size-neutral: a group of friends is no more likely than one applicant, matching
  how group lotteries are normally run. Trade-off: a strong applicant who links
  with lower-weight friends is pulled down to the group average. (Sum would make
  bigger groups luckier — rejected as unfair to solo applicants. `max` is a
  one-line alternative in `group_weight` if you ever want "inherit the best
  member's weight".)

- **At admission, groups are split into consecutive numbers, not admitted as a
  block.** Because we let people off the waitlist one at a time. Each person gets
  a distinct integer; linked members sit in an adjacent block (e.g. 41, 42, 43),
  shuffled within the block (the group won its *slot* together, so internal order
  is random).

- **A link to someone who didn't apply is a warning, not an error.** People list
  friends who never sign up — expected, not corruption. The link is ignored, the
  person draws solo, and the skipped links print to stderr so you can eyeball
  them. The spreadsheet is never modified.

- **Fail loud on genuine problems.** Missing configured column, ambiguous linked
  name (matches two people), plus-one/host mismatch, mixed eligible+excluded
  group — all abort with a clear message. Silent wrong draws are the thing to
  avoid.

- **Determinism vs. randomness is explicit.** Everything except the final draw is
  deterministic and auditable via `--explain`. The draw's randomness is captured
  by `--seed`, so any specific result is reproducible.

### Choosing the seed

The seed *is* the outcome, so choose it defensibly:

- **Don't seed-shop.** Don't try seeds until you like the result — that's
  hand-picking. Decide the seed *before* seeing any outcome.
- **Use a public, uncontrollable, pre-committed source** — e.g. announce "the
  seed is the Mega Millions numbers from date X", or roll dice on a group call.
  Anyone can then rerun and verify.
- **The number's length doesn't matter.** Seed `7` is as random as a 12-digit
  number; the generator scrambles either thoroughly. What matters is *how* it was
  chosen, not how big it is.
- **Record all three: the seed, the exact CSV, and the git commit.** Same inputs
  reproduce the identical draw forever — that's the audit trail.

---

## Yearly checklist

Each year, working through the `CONFIG` block top to bottom:

1. **Export** the new master sheet to CSV and set `CSV_PATH` (or pass it as an
   argument).
2. **Check every configured column name against the new form's headers.** The
   form's wording changes year to year. In particular the **age column has the
   year baked into its name** (`How old will you be in October 2026?`) — it
   *will* change. `NAME_COLUMNS`, `ELIGIBLE_COLUMN`, `PLUS_ONE_COLUMN`, and
   `LINK_COLUMN` all need to match the new headers too. (If any are wrong, the
   run aborts and lists the sheet's actual headers — use that to fix them.)
3. **Update `RULES`** — the multipliers, the age thresholds, and each `label`.
   Decide the boost policy for the year and encode it.
4. **`./lottery.py --explain | less`** — read the decision trail. Confirm the
   right people are excluded (staff/plus-ones), age bands land correctly, and
   linked groups formed as expected.
5. **Read the dangling-link warnings** (stderr). Anything in that list that is
   actually an applicant (name typed differently) is worth reconciling.
6. **`./lottery.py --dry-run`** — eyeball the entry weights high→low for sanity.
7. **Pick a seed** by the rules above, then **`./lottery.py --seed <N>`** for the
   real draw. Save the seed, the CSV, and the commit.
8. **`./lottery.py --groups`** for the group-label column. Paste both columns.

---

## Gotchas

- **Name matching is case/whitespace-insensitive but otherwise exact on
  `First Last`.** Free-text link entries like `"Jane"` or `"my partner"` won't
  match and will show up as ignored links. Skim the warnings before the real draw.
- **The input must be CSV**, not `.xlsx`. Export the sheet/tab first.
- **`--groups` labels every multi-person link group**, including the rare
  all-excluded one (e.g. two staff who linked). One-line filter to change if
  wanted.
- **One plus-one per staff member is not enforced** — two people could both claim
  the same host. Add a check if that matters.
- **Weighting controls luck, not seat count.** A group still occupies as many
  waitlist slots as it has members; averaging only decides *where* the block
  lands, not how many seats it takes.
