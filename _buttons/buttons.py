#!/usr/bin/env python3
"""Lay out name-tag buttons from a design template and print-ready PDF.

Takes the mail-merge CSV from nametags.py plus an Inkscape design whose text
objects are named firstname / lastname / pronouns, fits every name into the
design's own text boxes, tiles the button N-up onto sheets and exports one PDF.

The design owns position, size, font and artwork; this script only substitutes
text and, where a name will not fit, wraps it and then shrinks it toward a
floor. Nothing about the layout is hardcoded here -- it is read from the SVG.

Usage:
    ./buttons.py                  # sheets + merged PDF + proofs
    ./buttons.py --report         # what would be wrapped or shrunk, no output
    ./buttons.py --proof          # just the 1:1 single-button and worst-case proofs
"""
import argparse
import copy
import csv
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

SYSTEM_PYTHON = '/usr/bin/python3'
try:
    ET.fromstring('<probe/>')
except Exception:  # pragma: no cover -- Homebrew 3.14 ships a broken pyexpat
    if sys.executable != SYSTEM_PYTHON and os.path.exists(SYSTEM_PYTHON):
        os.execv(SYSTEM_PYTHON, [SYSTEM_PYTHON] + sys.argv)
    raise

# ---------------------------------------------------------------------------
# CONFIG — edit this each year to match the new design and press.
# ---------------------------------------------------------------------------

CSV_PATH = './data/nametags-2026.csv'
TEMPLATE = './data/button-template.svg'
OUT_DIR = './data/print-2026'

# Sheet layout. make_template.py prints these for a given button and paper.
PAPER = 'letter'
MARGIN_MM = 10.0
COLS = 2
ROWS = 3

# How small a name may go before it is a problem rather than a solution,
# as a fraction of the size set in the design. Anything that would need to go
# below this is rendered AT the floor and flagged loudly for a human.
MIN_SCALE = 0.62

# Names are never broken across lines -- a long name shrinks until it fits.
# Set True to wrap multi-word names at their best break point instead.
WRAP_BEFORE_SHRINK = False
LINE_SPACING = 1.05          # multiple of font size between wrapped lines

INKSCAPE = '/Applications/Inkscape.app/Contents/MacOS/inkscape'
PDFUNITE = 'pdfunite'

# ---------------------------------------------------------------------------

PAPER_MM = {'letter': (215.9, 279.4), 'a4': (210.0, 297.0)}
SVG = 'http://www.w3.org/2000/svg'
INK_NS = 'http://www.inkscape.org/namespaces/inkscape'
MM_PER_PX = 25.4 / 96.0      # Inkscape reports query geometry in px
FIELDS = ('firstname', 'lastname', 'pronouns')

ET.register_namespace('', SVG)
ET.register_namespace('inkscape', INK_NS)
ET.register_namespace('sodipodi', 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd')


def die(msg):
    sys.exit(f"buttons.py: {msg}")


# ---------------------------------------------------------------------------
# Reading the design
# ---------------------------------------------------------------------------

def style_value(el, prop):
    """One property from a style="" attribute, or the same-named attribute."""
    style = el.get('style', '')
    m = re.search(rf'(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)', style)
    if m:
        return m.group(1).strip()
    return el.get(prop)


def to_units(value):
    """A length from the SVG as user units (the template makes 1 unit = 1mm)."""
    if value is None:
        return None
    m = re.match(r'^\s*(-?[\d.]+)\s*([a-z%]*)\s*$', str(value))
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2)
    # px and a bare number are user units. pt and mm are absolute; convert.
    return {'': n, 'px': n, 'pt': n * 25.4 / 72, 'mm': n, 'cm': n * 10}.get(unit)


def read_template(path):
    """(tree, {field: spec}, doc_w, doc_h) -- the design and its text contract."""
    if not os.path.exists(path):
        die(f"design not found: {path}\n  run ./make_template.py to generate a skeleton")
    tree = ET.parse(path)
    root = tree.getroot()

    doc_w = to_units(root.get('width')) or 0
    doc_h = to_units(root.get('height')) or 0
    if not doc_w or not doc_h:
        die(f"{path}: the svg needs width and height (the physical button size)")

    by_id = {el.get('id'): el for el in root.iter() if el.get('id')}
    spec = {}
    for field in FIELDS:
        text_el = by_id.get(field)
        if text_el is None:
            die(f"{path}: no text object with id={field!r}\n"
                f"  in Inkscape: select the text, Object Properties (Ctrl+Shift+O), set ID\n"
                f"  ids found: {', '.join(sorted(i for i in by_id if i)) or '(none)'}")
        size = to_units(style_value(text_el, 'font-size'))
        if not size:
            die(f"{path}: id={field!r} has no readable font-size")
        box = by_id.get(f'{field}-box')
        if box is not None:
            width = to_units(box.get('width'))
        else:
            # No explicit box: fall back to the widest chord of the button at
            # this text's height, minus a margin. Cruder, but it works.
            width = doc_w * 0.72
        spec[field] = {
            'el': text_el,
            'max_size': size,
            'box_w': width,
            'box_h': to_units(box.get('height')) if box is not None else None,
            'family': style_value(text_el, 'font-family') or 'sans-serif',
            'x': to_units(text_el.get('x')) or doc_w / 2,
            'y': to_units(text_el.get('y')) or doc_h / 2,
        }
    return tree, spec, doc_w, doc_h


# ---------------------------------------------------------------------------
# Measuring, via one Inkscape call for everything
# ---------------------------------------------------------------------------

def measure(strings_by_field, spec, workdir):
    """{(field, string): width_in_units} for every string, in one Inkscape call.

    Rendered width, not character count: in a proportional face 'Illiana' is
    about half the width of 'Wammmm' at equal length, so len() cannot decide
    whether a name fits.
    """
    items, parts = [], [
        '<svg xmlns="http://www.w3.org/2000/svg" width="4000mm" height="12000mm" '
        'viewBox="0 0 4000 12000">']
    for field, strings in strings_by_field.items():
        s = spec[field]
        for text in sorted(strings):
            if not text.strip():
                continue
            i = len(items)
            items.append((field, text))
            parts.append(
                f'<text id="m{i}" x="5" y="{(i + 1) * 20}" '
                f'font-family="{esc_attr(s["family"])}" font-size="{s["max_size"]}" '
                f'style="font-family:{esc_attr(s["family"])};font-size:{s["max_size"]}px">'
                f'{esc(text)}</text>')
    parts.append('</svg>')

    probe = os.path.join(workdir, 'measure.svg')
    with open(probe, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))

    out = run([INKSCAPE, '--query-all', probe], "measuring text")
    widths = {}
    for line in out.splitlines():
        f = line.strip().split(',')
        if len(f) >= 4 and f[0].startswith('m') and f[0][1:].isdigit():
            idx = int(f[0][1:])
            if idx < len(items):
                widths[items[idx]] = float(f[3]) * MM_PER_PX
    missing = [it for it in items if it not in widths]
    if missing:
        die(f"Inkscape did not measure {len(missing)} string(s), e.g. {missing[:3]}")
    return widths


def run(cmd, what):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"{what} failed\n  {' '.join(cmd)}\n  {proc.stderr.strip()[:400]}")
    return proc.stdout


# ---------------------------------------------------------------------------
# Deciding how each name is set
# ---------------------------------------------------------------------------

def fit(text, field, spec, widths):
    """(lines, size, note) -- how this string is set inside its box.

    Full size if it fits. Otherwise wrap a multi-word name at its widest space
    and retry, then fall back to scaling down, never below MIN_SCALE.
    """
    s = spec[field]
    max_size, box = s['max_size'], s['box_w']
    if not text.strip():
        return [], max_size, None

    w = widths[(field, text)]
    if w <= box:
        return [text], max_size, None

    if WRAP_BEFORE_SHRINK and len(text.split()) > 1:
        # Split at the break that minimises the wider of the two lines.
        words = text.split()
        best = min(
            ((max(widths[(field, ' '.join(words[:i]))], widths[(field, ' '.join(words[i:]))]), i)
             for i in range(1, len(words))), key=lambda t: t[0])
        widest, at = best
        lines = [' '.join(words[:at]), ' '.join(words[at:])]
        if widest <= box:
            note = f"wrapped to {len(lines)} lines"
            box_h = s.get('box_h')
            if box_h and len(lines) * max_size * LINE_SPACING > box_h:
                note += (f" -- but {len(lines)} lines need "
                         f"{len(lines) * max_size * LINE_SPACING:.1f}mm and the box is "
                         f"{box_h:.1f}mm; give the design headroom above the first name")
            return lines, max_size, note
        scale = max(box / widest, MIN_SCALE)
        note = f"wrapped and shrunk to {scale * 100:.0f}%"
        if box / widest < MIN_SCALE:
            note = (f"WOULD NOT FIT: wrapped, needs {box / widest * 100:.0f}% "
                    f"but floor is {MIN_SCALE * 100:.0f}% -- set at the floor, check it")
        return lines, max_size * scale, note

    scale = max(box / w, MIN_SCALE)
    note = f"shrunk to {scale * 100:.0f}%"
    if box / w < MIN_SCALE:
        note = (f"WOULD NOT FIT: needs {box / w * 100:.0f}% but floor is "
                f"{MIN_SCALE * 100:.0f}% -- set at the floor, check it")
    return [text], max_size * scale, note


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def esc_attr(t):
    return esc(t).replace('"', '&quot;')


# ---------------------------------------------------------------------------
# Building sheets
# ---------------------------------------------------------------------------

def strip_ids(el):
    """Cloned artwork must not carry duplicate ids onto the same sheet."""
    for node in el.iter():
        node.attrib.pop('id', None)
    return el


def button_group(tree, spec, layout):
    """One button as a <g>, with the design's placeholders replaced.

    Only the three named text objects are swapped out. Any other text in the
    design -- a year, an event name, decorative lettering -- is the designer's
    and is copied through untouched.
    """
    root = tree.getroot()
    g = ET.Element(f'{{{SVG}}}g')
    for layer in root:
        if not isinstance(layer.tag, str):
            continue
        if layer.get(f'{{{INK_NS}}}label') == 'guides':
            continue                      # press guides never print
        if layer.tag in (f'{{{SVG}}}defs', f'{{{SVG}}}metadata'):
            continue                      # hoisted to the sheet once
        if layer.tag.endswith('namedview'):
            continue
        if layer.tag == f'{{{SVG}}}text' and layer.get('id') in FIELDS:
            continue                      # a placeholder at the top level
        clone = copy.deepcopy(layer)
        # Drop just the placeholders, before stripping ids makes them
        # unidentifiable. Everything else in the layer survives.
        for parent in clone.iter():
            for child in list(parent):
                if child.tag == f'{{{SVG}}}text' and child.get('id') in FIELDS:
                    parent.remove(child)
        g.append(strip_ids(clone))

    # The fitted text goes in its own group appended last, so it draws on top
    # of the artwork whatever order the designer's layers are in.
    text_layer = ET.SubElement(g, f'{{{SVG}}}g')
    for field in FIELDS:
        lines, size, _ = layout[field]
        if not lines:
            continue
        s = spec[field]
        # Extra lines stack UPWARD from the design's baseline. Centring the
        # block instead would push the second line down into whatever the
        # designer put underneath -- for a first name, the last name.
        lead = size * LINE_SPACING
        y0 = s['y'] - lead * (len(lines) - 1)
        anchor = style_value(s['el'], 'text-anchor') or 'middle'
        fill = style_value(s['el'], 'fill') or '#000000'
        weight = style_value(s['el'], 'font-weight')
        for i, line in enumerate(lines):
            el = ET.SubElement(text_layer, f'{{{SVG}}}text')
            el.set('x', f"{s['x']:.4f}")
            el.set('y', f"{y0 + i * lead:.4f}")
            el.set('text-anchor', anchor)
            style = (f"font-family:{s['family']};font-size:{size:.4f}px;"
                     f"text-anchor:{anchor};fill:{fill}")
            if weight:
                style += f";font-weight:{weight}"
            el.set('style', style)
            el.text = line
    return g


def write_sheet(path, groups, tree, doc_w, doc_h):
    """A page of buttons, each translated into its grid cell."""
    pw, ph = PAPER_MM[PAPER]
    per_row = COLS
    root = ET.Element(f'{{{SVG}}}svg', {
        'width': f'{pw}mm', 'height': f'{ph}mm',
        'viewBox': f'0 0 {pw} {ph}', 'version': '1.1'})
    for defs in tree.getroot().iter(f'{{{SVG}}}defs'):
        root.append(copy.deepcopy(defs))
        break
    # Spread the slack evenly rather than crowding everything into a corner.
    gap_x = (pw - 2 * MARGIN_MM - COLS * doc_w) / max(COLS - 1, 1) if COLS > 1 else 0
    gap_y = (ph - 2 * MARGIN_MM - ROWS * doc_h) / max(ROWS - 1, 1) if ROWS > 1 else 0
    for i, g in enumerate(groups):
        col, row = i % per_row, i // per_row
        x = MARGIN_MM + col * (doc_w + gap_x)
        y = MARGIN_MM + row * (doc_h + gap_y)
        g.set('transform', f'translate({x:.4f},{y:.4f})')
        root.append(g)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def svg_to_pdf(svgs, out_pdf, workdir):
    """Each sheet to PDF, then stitched into one file."""
    pdfs = []
    for svg in svgs:
        pdf = os.path.splitext(svg)[0] + '.pdf'
        run([INKSCAPE, '--export-type=pdf', f'--export-filename={pdf}', svg],
            f"exporting {os.path.basename(svg)}")
        pdfs.append(pdf)
    if len(pdfs) == 1:
        os.replace(pdfs[0], out_pdf)
    else:
        run([PDFUNITE] + pdfs + [out_pdf], "merging PDFs")
        for p in pdfs:
            os.remove(p)
    return out_pdf


# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--csv', default=CSV_PATH)
    p.add_argument('--template', default=TEMPLATE)
    p.add_argument('--out-dir', default=OUT_DIR)
    p.add_argument('--report', action='store_true', help="what would change, write nothing")
    p.add_argument('--proof', action='store_true', help="only the 1:1 and worst-case proofs")
    args = p.parse_args()

    if not os.path.exists(INKSCAPE):
        die(f"Inkscape not found at {INKSCAPE}")
    if not os.path.exists(args.csv):
        die(f"CSV not found: {args.csv}\n  run ./nametags.py first")

    tree, spec, doc_w, doc_h = read_template(args.template)
    with open(args.csv, newline='', encoding='utf-8-sig') as f:
        people = list(csv.DictReader(f))
    if not people:
        die(f"no rows in {args.csv}")

    os.makedirs(args.out_dir, exist_ok=True)

    # Every string plus every prefix/suffix a wrap could produce, measured once.
    wanted = {field: set() for field in FIELDS}
    colmap = {'firstname': 'FirstName', 'lastname': 'LastName', 'pronouns': 'Pronouns'}
    for r in people:
        for field, col in colmap.items():
            text = r[col].strip()
            wanted[field].add(text)
            words = text.split()
            for i in range(1, len(words)):
                wanted[field].add(' '.join(words[:i]))
                wanted[field].add(' '.join(words[i:]))
    widths = measure(wanted, spec, args.out_dir)

    layouts, notes = [], []
    for r in people:
        layout, who = {}, f"{r['FirstName']} {r['LastName']}".strip()
        for field, col in colmap.items():
            lines, size, note = fit(r[col].strip(), field, spec, widths)
            layout[field] = (lines, size, note)
            if note:
                notes.append((note.startswith('WOULD NOT FIT'), f"{who}: {field} {note}"))
        layouts.append((r, layout))

    full = sum(1 for _, l in layouts if all(n is None for _, _, n in l.values()))
    how = 'wrapped or shrunk' if WRAP_BEFORE_SHRINK else 'shrunk to fit'
    print(f"{len(layouts)} buttons -- {full} at the design's size, "
          f"{len(layouts) - full} {how}.", file=sys.stderr)
    print(f"  {COLS}x{ROWS} = {COLS * ROWS} per sheet -> "
          f"{math.ceil(len(layouts) / (COLS * ROWS))} sheets", file=sys.stderr)
    if notes:
        print(f"\n{len(notes)} name(s) the design could not take as-is:", file=sys.stderr)
        for _, line in sorted(notes, reverse=True):
            print(f"  - {line}", file=sys.stderr)

    if args.report:
        return

    # Proofs: one button at 1:1 with the worst name, and a sheet of only the
    # names that needed intervention -- the two things worth eyeballing.
    touched = [rl for rl in layouts if any(n for _, _, n in rl[1].values())]
    proofs = []
    if touched:
        single = os.path.join(args.out_dir, 'proof-button.svg')
        write_sheet(single, [button_group(tree, spec, touched[0][1])], tree, doc_w, doc_h)
        proofs.append(single)
        sheet = os.path.join(args.out_dir, 'proof-worst.svg')
        write_sheet(sheet, [button_group(tree, spec, l) for _, l in touched[:COLS * ROWS]],
                    tree, doc_w, doc_h)
        proofs.append(sheet)
    for svg in proofs:
        svg_to_pdf([svg], os.path.splitext(svg)[0] + '.pdf', args.out_dir)
        os.remove(svg)
    if proofs:
        print(f"\nproofs: {', '.join(os.path.splitext(os.path.basename(s))[0] + '.pdf' for s in proofs)}",
              file=sys.stderr)
    if args.proof:
        return

    per = COLS * ROWS
    sheets = []
    for start in range(0, len(layouts), per):
        chunk = layouts[start:start + per]
        path = os.path.join(args.out_dir, f'sheet-{start // per + 1:02d}.svg')
        write_sheet(path, [button_group(tree, spec, l) for _, l in chunk], tree, doc_w, doc_h)
        sheets.append(path)

    out_pdf = os.path.join(args.out_dir, 'buttons-all.pdf')
    svg_to_pdf(sheets, out_pdf, args.out_dir)
    for s in sheets:
        os.remove(s)
    print(f"\nwrote {out_pdf} ({len(sheets)} sheets)", file=sys.stderr)
    print("print at 100% scale -- 'fit to page' will break registration with the punch",
          file=sys.stderr)


if __name__ == '__main__':
    main()
