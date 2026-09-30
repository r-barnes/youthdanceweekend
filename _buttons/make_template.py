#!/usr/bin/env python3
"""Generate a skeleton button template for Inkscape.

Writes a single button at true physical size, with the three named text
placeholders buttons.py looks for, guide circles for the press, and an empty
layer to drop artwork into. Run it once per design; after that the SVG is
yours to redesign freely -- only the object ids matter.

The grid is computed from the button and paper size, so the number per sheet
falls out of the geometry rather than being guessed.

Usage:
    ./make_template.py                          # 2.25in button on Letter
    ./make_template.py --diameter 44.45 --cut 54
    ./make_template.py --paper a4 --margin 8
"""
import argparse
import math
import os

PAPER = {'letter': (215.9, 279.4), 'a4': (210.0, 297.0)}

# Layer and object names buttons.py relies on. Renaming these means editing
# both files, so they live here as the single statement of the contract.
FIELDS = ('firstname', 'lastname', 'pronouns')


def build_svg(d_visible, d_cut, d_safe, sizes):
    """One button, at physical size, in mm user units."""
    c = d_cut / 2                       # centre of the paper circle
    r_vis = d_visible / 2               # what stays visible once pressed
    r_safe = d_safe / 2                 # the press's stated safe zone

    def half_width(dy):
        """Half the chord of the safe circle at vertical offset dy from centre.

        A round button narrows towards the top and bottom, so a text box's
        usable width depends on how far off centre it sits.
        """
        dy = min(abs(dy), r_safe)
        return math.sqrt(max(r_safe ** 2 - dy ** 2, 0))

    # Stacked first name / last name / pronouns, first name slightly above
    # centre so the block as a whole reads centred.
    # (name, vertical offset from centre, size, lines the box must accommodate).
    # The first name gets room for two, because two-word first names are common
    # and buttons.py wraps them upward before it shrinks them.
    rows = [('firstname', -4.0, sizes['firstname'], 1),
            ('lastname', 6.0, sizes['lastname'], 1),
            ('pronouns', 13.5, sizes['pronouns'], 1)]

    text, boxes = [], []
    # Invented names, deliberately long, so the skeleton shows the worst case.
    # Never a real attendee: this file is committed to a public branch.
    dummy = {'firstname': 'Marisol Wren', 'lastname': 'Vasterling', 'pronouns': 'they/them'}
    for name, dy, size, lines in rows:
        y = c + dy
        # A multi-line box grows upward, so measure the chord at its top line.
        hw = min(half_width(dy), half_width(dy - (lines - 1) * size * 1.05))
        # The box is what buttons.py fits text into; the text object supplies
        # the styling and the maximum size.
        top = y - size - (lines - 1) * size * 1.05
        boxes.append(
            f'      <rect id="{name}-box" x="{c - hw:.3f}" y="{top:.3f}" '
            f'width="{hw * 2:.3f}" height="{(y + size * 0.35) - top:.3f}" '
            f'fill="none" stroke="#00a0ff" stroke-width="0.2" stroke-dasharray="1,1"/>'
        )
        text.append(
            f'      <text id="{name}" x="{c:.3f}" y="{y:.3f}" font-family="Helvetica" '
            f'font-size="{size}" text-anchor="middle" fill="#000000" '
            f'style="font-family:Helvetica;font-size:{size}px;text-anchor:middle;fill:#000000">'
            f'{dummy[name]}</text>'
        )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- YDW button template. Physical size {d_cut}mm paper circle,
     {d_visible}mm visible once pressed. 1 user unit = 1mm.

     buttons.py finds text by id: {', '.join(FIELDS)}.
     Keep those ids and keep them as live text. Everything else (artwork,
     fonts, colours, position, size) is yours to change.

     The first name's font-size here is treated as the MAXIMUM; long names are
     wrapped, then shrunk toward the floor set in buttons.py. -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
     width="{d_cut}mm" height="{d_cut}mm"
     viewBox="0 0 {d_cut} {d_cut}" version="1.1">
  <sodipodi:namedview inkscape:document-units="mm" units="mm"/>
  <defs/>

  <g inkscape:groupmode="layer" inkscape:label="artwork" id="layer-artwork">
    <!-- Drop the design in here. Behind the text, so it can be anything. -->
    <circle cx="{c}" cy="{c}" r="{d_visible / 2:.3f}" fill="#f2f2f2"/>
  </g>

  <g inkscape:groupmode="layer" inkscape:label="text" id="layer-text">
{chr(10).join(text)}
  </g>

  <g inkscape:groupmode="layer" inkscape:label="guides" id="layer-guides"
     sodipodi:insensitive="true">
    <!-- Dropped from the printed output: cut line, visible edge, text boxes. -->
    <circle cx="{c}" cy="{c}" r="{d_cut / 2:.3f}" fill="none" stroke="#ff0000"
            stroke-width="0.2" stroke-dasharray="2,1"/>
    <circle cx="{c}" cy="{c}" r="{d_visible / 2:.3f}" fill="none" stroke="#00c000"
            stroke-width="0.2" stroke-dasharray="2,1"/>
    <circle cx="{c}" cy="{c}" r="{d_safe / 2:.3f}" fill="none" stroke="#c000c0"
            stroke-width="0.2" stroke-dasharray="1,1"/>
{chr(10).join(boxes)}
  </g>
</svg>
'''


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--diameter', type=float, default=68.0,
                   help="visible button diameter in mm (default 68)")
    p.add_argument('--cut', type=float, default=68.0,
                   help="paper footprint in mm, what the grid tiles (default 68)")
    p.add_argument('--safe', type=float, default=58.0,
                   help="safe zone in mm; text is fitted inside this (default 58)")
    p.add_argument('--paper', choices=sorted(PAPER), default='letter')
    p.add_argument('--margin', type=float, default=10.0, help="sheet margin in mm")
    p.add_argument('--first-size', type=float, default=11.0, help="first-name size in mm")
    p.add_argument('--last-size', type=float, default=6.0)
    p.add_argument('--pronoun-size', type=float, default=4.5)
    p.add_argument('-o', '--output', default='./button-template.svg')
    args = p.parse_args()

    if args.cut < args.diameter:
        p.error(f"--cut ({args.cut}) must be at least --diameter ({args.diameter})")
    if args.safe > args.diameter:
        p.error(f"--safe ({args.safe}) must fit inside --diameter ({args.diameter})")

    sizes = {'firstname': args.first_size, 'lastname': args.last_size,
             'pronouns': args.pronoun_size}
    out = os.path.expanduser(args.output)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(build_svg(args.diameter, args.cut, args.safe, sizes))

    pw, ph = PAPER[args.paper]
    cols = int((pw - 2 * args.margin) // args.cut)
    rows = int((ph - 2 * args.margin) // args.cut)
    per = cols * rows
    print(f"wrote {out}")
    print(f"  button    {args.diameter}mm visible, {args.cut}mm footprint, "
          f"{args.safe}mm safe zone")
    print(f"  {args.paper} @ {args.margin}mm margin -> {cols} x {rows} = {per} per sheet")
    if per == 0:
        print("  WARNING: the button does not fit this paper at this margin")
    else:
        print(f"  161 buttons -> {math.ceil(161 / per)} sheets")
    print(f"\n  put these in buttons.py CONFIG:  COLS = {cols}   ROWS = {rows}"
          f"   PAPER = {args.paper!r}   MARGIN_MM = {args.margin}")


if __name__ == '__main__':
    main()
