#!/usr/bin/env python3
"""Lay out name-tag buttons from a design template and print-ready PDF.

Takes the mail-merge CSV from roster.py plus an Inkscape design whose text
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
import base64
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

CSV_PATH = './data/roster-2026.csv'

# Which object in the design holds each field. Rename the objects in Inkscape
# (Object Properties, Ctrl+Shift+O) or just point these at the ids the design
# already has -- whichever is less work when the design changes.
FIELD_IDS = {
    'firstname': 'firstname',
    'lastname': 'lastname',
    'pronouns': 'pronouns',
}

# Set True if the design sets names in capitals. The roster is mixed case, so
# this is a property of the design, not of the data. Capitals are noticeably
# wider, so turning this on means more names get shrunk.
UPPERCASE = True

TEMPLATE = './data/2026-button-reference-inkscape.svg'
OUT_DIR = './data/print-2026'

# Sheet layout. make_template.py prints these for a given button and paper.
# 3x3 on Letter, laid out for a hand-cranked rotary circle cutter rather than
# for maximum density. Three 68mm circles use 204mm of the 215.9mm width, so
# the columns end up touching whatever we do -- but only three rows leaves
# ~32mm between them, which is room to trim the sheet into strips first. A
# strip is far easier to align a centering template on than a whole sheet, and
# it stays rigid as circles come out of it.
#
# 3x4 = 12 also fits (badge template makers quote 12 per A4 for this circle)
# and saves four sheets, but the rows touch, so there is nowhere to cut strips.
PAPER = 'letter'
MARGIN_MM = 5.9
COLS = 3
ROWS = 3

# The press's safe zone. When the design has no <field>-box rect, text is fitted
# to the chord of this circle at the text's own height, so a plain design --
# just a circle and three named text objects -- works with no extra setup.
SAFE_DIAMETER_MM = 58.0

# How small a name may go before it is a problem rather than a solution,
# as a fraction of the size set in the design. Anything that would need to go
# below this is rendered AT the floor and flagged loudly for a human.
MIN_SCALE = 0.62

# Names are never broken across lines -- a long name shrinks until it fits.
# Set True to wrap multi-word names at their best break point instead.
WRAP_BEFORE_SHRINK = False
LINE_SPACING = 1.05          # multiple of font size between wrapped lines

# Inkscape's PDF backend flattens a masked object at PDF user-space resolution
# -- 72 dpi -- no matter what --export-dpi says, which leaves raster artwork
# visibly stair-stepped. Masked images are pre-rendered at this resolution
# instead, with the mask baked into the alpha channel, so the PDF carries a
# plain high-resolution image and no mask. 0 disables the whole step.
FLATTEN_MASKS_DPI = 300

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
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


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


FONT_ATTRS = ('font-family', 'font-size', 'font-weight', 'font-stretch', 'font-style')


def _collect_style(el, into):
    """Presentation attributes first, then style="" -- style wins, as in CSS."""
    for attr in FONT_ATTRS:
        if el.get(attr):
            into[attr] = el.get(attr)
    for part in (el.get('style') or '').split(';'):
        if ':' in part:
            key, value = part.split(':', 1)
            into[key.strip()] = value.strip()


def effective_style(el):
    """The style a text object actually renders with.

    Inkscape writes the chosen face on the <tspan>, not the <text>: a heading
    can say font-weight:900 on the element while its tspan says 600, and the
    tspan is what you see. Reading only the <text> picks the wrong face.
    """
    merged = {}
    _collect_style(el, merged)
    for child in el:
        if child.tag == f'{{{SVG}}}tspan':
            _collect_style(child, merged)
            break
    return merged


def mm_length(value):
    """A document width/height in mm. A bare number means px, not mm."""
    if value is None:
        return 0.0
    m = re.match(r'^\s*(-?[\d.]+)\s*([a-z%]*)\s*$', str(value))
    if not m:
        return 0.0
    n, unit = float(m.group(1)), m.group(2)
    return {'': n * MM_PER_PX, 'px': n * MM_PER_PX, 'mm': n, 'cm': n * 10,
            'in': n * 25.4, 'pt': n * 25.4 / 72}.get(unit, n * MM_PER_PX)


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


def template_geometry(path):
    """{id: (x, y, w, h)} in mm, as rendered.

    Read from Inkscape rather than from the attributes, because a designer's
    objects usually sit inside a layer with its own transform -- the attribute
    values are in the layer's coordinate system, not the button's.
    """
    geom = {}
    for line in run([INKSCAPE, '--query-all', path], "reading design geometry").splitlines():
        f = line.strip().split(',')
        if len(f) >= 5:
            try:
                geom[f[0]] = tuple(float(v) * MM_PER_PX for v in f[1:5])
            except ValueError:
                continue
    return geom


def parse_transform(text):
    """An SVG transform list as a 2x3 affine (a, b, c, d, e, f)."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', text or ''):
        v = [float(x) for x in re.split(r'[,\s]+', args.strip()) if x]
        if name == 'matrix' and len(v) == 6:
            t = tuple(v)
        elif name == 'translate':
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale':
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate' and len(v) == 1:
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
        else:
            continue                       # skew/rotate-about-point: rare here
        m = mat_mul(m, t)
    return m


def mat_mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a*A + c*B, b*A + d*B, a*C + c*D, b*C + d*D, a*E + c*F + e, b*E + d*F + f)


def mat_inv(m):
    a, b, c, d, e, f = m
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    return (d/det, -b/det, -c/det, a/det, (c*f - d*e)/det, (b*e - a*f)/det)


def flatten_masked_images(tree, path, dpi, workdir):
    """Replace every masked <image> with a pre-rendered one, mask baked in.

    Returns how many were replaced. Each is rendered on its own, over the full
    page, so the result drops straight back in at page coordinates -- no
    guessing where a clipped bounding box ended up.
    """
    if not dpi:
        return 0
    root = tree.getroot()
    parent_of = {child: parent for parent in root.iter() for child in parent}
    targets = [el for el in root.iter(f'{{{SVG}}}image')
               if el.get('mask') or el.get('clip-path')]
    if not targets:
        return 0

    vb = (root.get('viewBox') or '').replace(',', ' ').split()
    page_w, page_h = (float(vb[2]), float(vb[3])) if len(vb) == 4 else (0, 0)
    if not page_w:
        return 0

    done = 0
    for n, target in enumerate(targets):
        chain = []                         # root -> ... -> target
        node = target
        while node in parent_of:
            chain.append(node)
            node = parent_of[node]
        chain.reverse()

        # A copy of the document holding only this image and its ancestors, so
        # the render is the image alone, masked, with every transform applied.
        solo = ET.Element(root.tag, dict(root.attrib))
        for defs in root.iter(f'{{{SVG}}}defs'):
            solo.append(copy.deepcopy(defs))
        cursor = solo
        for link in chain[:-1]:
            shell = ET.SubElement(cursor, link.tag, dict(link.attrib))
            cursor = shell
        cursor.append(copy.deepcopy(target))

        solo_path = os.path.join(workdir, f'_mask{n}.svg')
        png_path = os.path.join(workdir, f'_mask{n}.png')
        ET.ElementTree(solo).write(solo_path, encoding='utf-8', xml_declaration=True)
        run([INKSCAPE, solo_path, '--export-area-page', '--export-type=png',
             f'--export-dpi={dpi}', f'--export-filename={png_path}'],
            "pre-rendering masked artwork")
        if not os.path.exists(png_path):
            continue

        with open(png_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')

        # Put it back exactly where it was in the stacking order, undoing the
        # ancestors' transforms so page coordinates land on the page.
        accum = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        for link in chain[:-1]:
            accum = mat_mul(accum, parse_transform(link.get('transform')))
        inv = mat_inv(accum)
        if inv is None:
            continue

        flat = ET.Element(f'{{{SVG}}}image', {
            'x': '0', 'y': '0',
            'width': f'{page_w:.6f}', 'height': f'{page_h:.6f}',
            'preserveAspectRatio': 'none',
            'style': 'image-rendering:optimizeQuality',
            'transform': 'matrix({:.9f},{:.9f},{:.9f},{:.9f},{:.9f},{:.9f})'.format(*inv),
            '{http://www.w3.org/1999/xlink}href': f'data:image/png;base64,{data}',
        })
        holder = parent_of[target]
        holder.insert(list(holder).index(target), flat)
        holder.remove(target)
        os.remove(solo_path)
        os.remove(png_path)
        done += 1
    return done


def read_template(path):
    """(tree, {field: spec}, doc_w, doc_h) -- the design and its text contract."""
    if not os.path.exists(path):
        die(f"design not found: {path}\n  run ./make_template.py to generate a skeleton")
    tree = ET.parse(path)
    root = tree.getroot()

    doc_w = mm_length(root.get('width'))
    doc_h = mm_length(root.get('height'))
    if not doc_w or not doc_h:
        die(f"{path}: the svg needs width and height (the physical button size)")

    # An Inkscape file's user units are whatever its viewBox says, commonly px
    # rather than mm. Everything below works in mm and converts back on write,
    # so the design's own unit choice stops mattering.
    vb = (root.get('viewBox') or '').replace(',', ' ').split()
    scale = doc_w / float(vb[2]) if len(vb) == 4 and float(vb[2]) else 1.0

    # Object Properties in Inkscape offers both ID and Label, and typing into
    # Label is the natural thing to do, so honour either.
    by_id = {}
    for el in root.iter():
        for key in (el.get(f'{{{INK_NS}}}label'), el.get('id')):
            if key and key not in by_id:
                by_id[key] = el
    geom = template_geometry(path)
    spec = {}
    for field in FIELDS:
        oid = FIELD_IDS[field]
        text_el = by_id.get(oid)
        if text_el is None:
            texts = []
            for e in root.iter(f'{{{SVG}}}text'):
                label = e.get(f'{{{INK_NS}}}label')
                content = (' '.join(''.join(n.itertext()) for n in e).strip()
                           or (e.text or '').strip())[:24]
                texts.append(f"{e.get('id') or '?'}"
                             + (f" (label {label})" if label else '')
                             + (f" = {content!r}" if content else ''))
            die(f"{path}: nothing has id or label {oid!r} (for {field})\n"
                f"  set it in Inkscape: select the text, Object Properties "
                f"(Ctrl+Shift+O), fill in ID or Label, then SAVE\n"
                f"  or point FIELD_IDS[{field!r}] at one of these:\n    "
                + '\n    '.join(texts or ['(no text objects)']))
        eff = effective_style(text_el)
        size = to_units(eff.get('font-size'))
        if not size:
            die(f"{path}: id={oid!r} has no readable font-size")
        size *= scale                     # user units -> mm
        oid = text_el.get('id') or oid    # geometry is keyed by real id
        if f'{oid}-box' in geom:
            width = geom[f'{oid}-box'][2]
        elif oid in geom:
            # No explicit box. Fit to the safe circle's chord at this text's
            # own height, measured at whichever edge sits further off centre.
            gx, gy, gw, gh = geom[oid]
            r = SAFE_DIAMETER_MM / 2
            cy = doc_h / 2
            dy = max(abs(gy - cy), abs(gy + gh - cy))
            width = 2 * math.sqrt(max(r ** 2 - dy ** 2, 0.0))
            if width < 1:
                die(f"{path}: id={oid!r} sits outside the {SAFE_DIAMETER_MM}mm "
                    f"safe zone; move it in or add a {oid}-box rect")
        else:
            width = doc_w * 0.72
        spec[field] = {
            'id': oid,
            'el': text_el,
            'max_size': size,
            'box_w': width,
            'box_h': geom[f'{oid}-box'][3] if f'{oid}-box' in geom else None,
            'family': eff.get('font-family', 'sans-serif'),
            'weight': eff.get('font-weight'),
            'stretch': eff.get('font-stretch'),
            'style': eff.get('font-style'),
        }
    return tree, spec, doc_w, doc_h, scale


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
            css = f'font-family:{s["family"]};font-size:{s["max_size"]}px'
            for prop in ('weight', 'stretch', 'style'):
                if s.get(prop):
                    css += f';font-{prop}:{s[prop]}'
            parts.append(
                f'<text id="m{i}" x="5" y="{(i + 1) * 20}" '
                f'style="{esc_attr(css)}">{esc(text)}</text>')
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


def set_style_prop(el, prop, value):
    """Set one property in a style="" attribute, leaving the rest alone."""
    style = el.get('style', '')
    if re.search(rf'(?:^|;)\s*{re.escape(prop)}\s*:', style):
        style = re.sub(rf'((?:^|;)\s*{re.escape(prop)}\s*:)[^;]*', rf'\g<1>{value}', style)
    else:
        style = f"{style};{prop}:{value}" if style else f"{prop}:{value}"
    el.set('style', style)


def set_text(el, lines, size_user):
    """Replace a placeholder's content and size, in place.

    In place matters: the design nests its text inside groups that carry their
    own transforms, so a rebuilt element appended elsewhere would land in the
    wrong coordinate system entirely.
    """
    set_style_prop(el, 'font-size', f'{size_user:.4f}px')
    if el.get('font-size') is not None:
        el.set('font-size', f'{size_user:.4f}')

    x, y, proto = el.get('x'), el.get('y'), None
    for child in el:                       # Inkscape often keeps x/y on the tspan
        if x is None:
            x = child.get('x')
        if y is None:
            y = child.get('y')
        if proto is None and child.tag == f'{{{SVG}}}tspan':
            proto = child.get('style')     # the face actually being rendered
    lead = size_user * LINE_SPACING
    y0 = float(y) - lead * (len(lines) - 1) if y is not None else None

    for child in list(el):
        el.remove(child)
    el.text = None
    for i, line in enumerate(lines):
        ts = ET.SubElement(el, f'{{{SVG}}}tspan')
        if proto:
            # Carry the original tspan's styling onto the replacement, or the
            # text drops back to the <text> element's weight -- which is not
            # the one the designer picked.
            ts.set('style', proto)
            set_style_prop(ts, 'font-size', f'{size_user:.4f}px')
        if x is not None:
            ts.set('x', x)
        if y0 is not None:
            ts.set('y', f'{y0 + i * lead:.4f}')
        ts.text = line


def find_by_key(root, key):
    for el in root.iter():
        if el.get('id') == key or el.get(f'{{{INK_NS}}}label') == key:
            return el
    return None


def button_group(tree, spec, layout, scale):
    """One button as a <g>, with only the named placeholders rewritten.

    Everything else in the design -- artwork, embedded images, curved text,
    nested transforms -- is copied through exactly as the designer left it.
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
        g.append(copy.deepcopy(layer))

    for image in g.iter(f'{{{SVG}}}image'):
        # A design that came through a PDF or AI import carries
        # image-rendering:optimizeSpeed, which tells the renderer to skip
        # interpolation -- the artwork prints visibly jagged. Nothing is lost
        # by asking for quality instead, and it is the single biggest
        # difference in how the embedded artwork comes out.
        set_style_prop(image, 'image-rendering', 'optimizeQuality')

    for field in FIELDS:
        el = find_by_key(g, spec[field]['id'])
        if el is None:
            continue
        lines, size_mm, _ = layout[field]
        if not lines:
            for parent in g.iter():       # nothing to print: drop the object
                if el in list(parent):
                    parent.remove(el)
                    break
            continue
        set_text(el, lines, size_mm / scale)
    return g


def write_sheet(path, groups, tree, doc_w, doc_h, scale):
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
    slack_x = pw - 2 * MARGIN_MM - COLS * doc_w
    slack_y = ph - 2 * MARGIN_MM - ROWS * doc_h
    if slack_x < -0.01 or slack_y < -0.01:
        die(f"{COLS}x{ROWS} buttons of {doc_w:.1f}mm do not fit {PAPER} at "
            f"{MARGIN_MM}mm margins (short by "
            f"{max(-slack_x, 0):.1f}mm across, {max(-slack_y, 0):.1f}mm down)")
    gap_x = slack_x / max(COLS - 1, 1) if COLS > 1 else 0
    gap_y = slack_y / max(ROWS - 1, 1) if ROWS > 1 else 0
    for i, g in enumerate(groups):
        col, row = i % per_row, i // per_row
        x = MARGIN_MM + col * (doc_w + gap_x)
        y = MARGIN_MM + row * (doc_h + gap_y)
        # The button's contents are in the design's user units; scale them
        # into the sheet's millimetres.
        g.set('transform', f'translate({x:.4f},{y:.4f}) scale({scale:.6f})')
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
        die(f"CSV not found: {args.csv}\n  run ./roster.py first")

    tree, spec, doc_w, doc_h, scale = read_template(args.template)
    with open(args.csv, newline='', encoding='utf-8-sig') as f:
        people = list(csv.DictReader(f))
    if not people:
        die(f"no rows in {args.csv}")

    os.makedirs(args.out_dir, exist_ok=True)

    flattened = flatten_masked_images(tree, args.template, FLATTEN_MASKS_DPI, args.out_dir)
    if flattened:
        print(f"pre-rendered {flattened} masked image(s) at {FLATTEN_MASKS_DPI}dpi "
              f"so the PDF keeps them sharp", file=sys.stderr)

    # Every string plus every prefix/suffix a wrap could produce, measured once.
    wanted = {field: set() for field in FIELDS}
    colmap = {'firstname': 'FirstName', 'lastname': 'LastName', 'pronouns': 'Pronouns'}
    for r in people:
        for field, col in colmap.items():
            text = r[col].strip()
            if UPPERCASE:
                text = text.upper()
            wanted[field].add(text)
            words = text.split()
            for i in range(1, len(words)):
                wanted[field].add(' '.join(words[:i]))
                wanted[field].add(' '.join(words[i:]))
    widths = measure(wanted, spec, args.out_dir)
    probe = os.path.join(args.out_dir, 'measure.svg')
    if os.path.exists(probe):
        os.remove(probe)                  # scratch file from the measuring pass

    layouts, notes = [], []
    for r in people:
        layout, who = {}, f"{r['FirstName']} {r['LastName']}".strip()
        for field, col in colmap.items():
            value = r[col].strip().upper() if UPPERCASE else r[col].strip()
            lines, size, note = fit(value, field, spec, widths)
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
        write_sheet(single, [button_group(tree, spec, touched[0][1], scale)],
                    tree, doc_w, doc_h, scale)
        proofs.append(single)
        sheet = os.path.join(args.out_dir, 'proof-worst.svg')
        write_sheet(sheet, [button_group(tree, spec, l, scale)
                            for _, l in touched[:COLS * ROWS]], tree, doc_w, doc_h, scale)
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
        write_sheet(path, [button_group(tree, spec, l, scale) for _, l in chunk],
                    tree, doc_w, doc_h, scale)
        sheets.append(path)

    out_pdf = os.path.join(args.out_dir, 'buttons-all.pdf')
    svg_to_pdf(sheets, out_pdf, args.out_dir)
    for s in sheets:
        os.remove(s)
    print(f"\nwrote {out_pdf} ({len(sheets)} sheets)", file=sys.stderr)
    print("print at 100% scale -- 'fit to page' rescales the circles and the cutter will not line up",
          file=sys.stderr)


if __name__ == '__main__':
    main()
