"""Turn the drawings from art.py into Cricut layered SVGs:
black base silhouette at the bottom + one compound path per colour.
Small decorations sitting on a piece without a black line around them (sprinkles, a snowflake on a mug)
go on top of that piece: the piece underneath is cut whole, without holes."""
import io, re, sys, os, json, subprocess
import numpy as np, cv2, cairosvg
from PIL import Image
from scipy import ndimage as ndi
from svgpathtools import parse_path
from art import ITEMS, PALETTE, K

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
PX = 1600; SC = PX / 400            # raster px per canvas unit
BASE_R = 10                         # black margin around the design, px
MIN_PX = 60

pal = np.array([[int(c[i:i+2], 16) for i in (1, 3, 5)] for c in PALETTE], float)

def render(body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="{PX}" height="{PX}" '
           f'shape-rendering="crispEdges">{body}</svg>')
    return np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA'))

def potrace_d(bm):
    if bm.sum() < 30: return ''
    h, w = bm.shape
    pbm = b'P4\n%d %d\n' % (w, h) + np.packbits(bm.astype(np.uint8), axis=1).tobytes()
    r = subprocess.run(['potrace', '-s', '-o', '-', '-t', '30', '-a', '1.0', '-O', '0.4', '-u', '10', '--flat'],
                       input=pbm, capture_output=True, check=True).stdout.decode()
    ds = ' '.join(re.findall(r' d="([^"]+)"', r))
    if not ds.strip(): return ''
    tx, ty, sx, sy = map(float, re.search(r'translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)', r).groups())
    f = lambda z: complex((tx + sx*z.real)/SC, (ty + sy*z.imag)/SC)
    fmt = lambda z: f'{z.real:.2f},{z.imag:.2f}'
    out = []
    for sub in parse_path(ds).continuous_subpaths():
        segs = list(sub); out.append('M' + fmt(f(segs[0].start)))
        for s in segs:
            out.append(('C' + ' '.join(fmt(f(q)) for q in (s.control1, s.control2, s.end)))
                       if type(s).__name__ == 'CubicBezier' else 'L' + fmt(f(s.end)))
        out.append('Z')
    return ''.join(out)

def disk(r): return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*r+1, 2*r+1))

meta = []
for idx, (name, body) in enumerate(ITEMS.items()):
    rgba = render(body)
    fg = rgba[..., 3] > 127
    d2 = ((rgba[..., :3][:, :, None, :].astype(float) - pal[None, None]) ** 2).sum(-1)
    cls = np.where(fg, d2.argmin(-1), -1)
    black = cls == 0
    # pieces per colour (visible area)
    pieces, decor_of = {}, {}
    for c in range(1, len(PALETTE)):
        m = cls == c
        if m.sum() < MIN_PX: continue
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, disk(1)) > 0
        pieces[c] = m
    # a hole in a piece that holds only other colours (no black line, no background) -> piece goes under it
    order_edges = set()
    for c, m in pieces.items():
        holes, n = ndi.label(ndi.binary_fill_holes(m) & ~m)
        add = np.zeros_like(m)
        for i in range(1, n+1):
            h = holes == i
            inside = cls[h]
            if h.sum() < 400:                            # tiny pocket (e.g. between snowflake branches): just close it
                add |= h; continue
            if (inside <= 0).mean() < 0.02:            # no black / background inside (allow stray edge pixels)
                add |= h
                for d in np.unique(inside):
                    if d > 0 and d != c: order_edges.add((c, d))
        pieces[c] = m | add
    # stacking order: big pieces first, but a piece always below the decorations it carries
    cols = sorted(pieces, key=lambda c: -pieces[c].sum())
    order = []
    remaining = list(cols)
    while remaining:
        for c in remaining:
            if not any((p, c) in order_edges for p in remaining if p != c):
                order.append(c); remaining.remove(c); break
        else:
            print('  cycle in', name, sorted((PALETTE[a], PALETTE[b]) for a, b in order_edges), file=sys.stderr); order += remaining; break
    base = cv2.dilate(fg.astype(np.uint8), disk(BASE_R)) > 0
    layers = [('silhouette', K, potrace_d(base))]
    for j, c in enumerate(order):
        d = potrace_d(pieces[c])
        if d: layers.append((f'color-{j+1}', PALETTE[c], d))
    ys, xs = np.where(base)
    x0, y0 = xs.min()/SC - 2, ys.min()/SC - 2; x1, y1 = xs.max()/SC + 2, ys.max()/SC + 2
    w, h = x1 - x0, y1 - y0
    win, hin = 4.0*w/max(w, h), 4.0*h/max(w, h)
    els = [f'<path id="{n}" fill="{c}" d="{d}"/>' for n, c, d in layers]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" width="{win:.3f}in" height="{hin:.3f}in">\n'
           f'<title>{name}</title>\n' + '\n'.join(els) + '\n</svg>\n')
    fn = f'{OUT}/{idx+1:02d}-{name}.svg'; open(fn, 'w').write(svg)
    meta.append((fn, (x0, y0, w, h), [(n, c) for n, c, _ in layers], els))
    print(fn, len(layers)-1, 'colours', file=sys.stderr)
json.dump(meta, open('meta.json', 'w'))
