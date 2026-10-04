"""Render art.py drawings and trace each into a one-layer SVG (single black compound path)."""
import io, re, sys, os, json, subprocess
import numpy as np, cairosvg
from PIL import Image
from svgpathtools import parse_path
from art import ITEMS
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
PX = 1600; SC = PX/400
def potrace_d(bm):
    h, w = bm.shape
    pbm = b'P4\n%d %d\n' % (w, h) + np.packbits(bm.astype(np.uint8), axis=1).tobytes()
    r = subprocess.run(['potrace', '-s', '-o', '-', '-t', '30', '-a', '1.0', '-O', '0.4', '-u', '10', '--flat'], input=pbm, capture_output=True, check=True).stdout.decode()
    ds = ' '.join(re.findall(r' d="([^"]+)"', r))
    tx, ty, sx, sy = map(float, re.search(r'translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)', r).groups())
    f = lambda z: complex((tx + sx*z.real)/SC, (ty + sy*z.imag)/SC); fmt = lambda z: f'{z.real:.2f},{z.imag:.2f}'
    out = []
    for sub in parse_path(ds).continuous_subpaths():
        segs = list(sub); out.append('M' + fmt(f(segs[0].start)))
        for s in segs:
            out.append(('C' + ' '.join(fmt(f(q)) for q in (s.control1, s.control2, s.end))) if type(s).__name__ == 'CubicBezier' else 'L' + fmt(f(s.end)))
        out.append('Z')
    return ''.join(out)
meta = []
for i, (name, body) in enumerate(ITEMS.items()):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="{PX}" height="{PX}" shape-rendering="crispEdges">{body}</svg>'
    a = np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA'))
    bm = (a[..., 3] > 127) & (a[..., :3].mean(-1) < 128)
    d = potrace_d(bm)
    ys, xs = np.where(bm); x0, y0 = xs.min()/SC - 4, ys.min()/SC - 4; w, h = (xs.max() - xs.min())/SC + 8, (ys.max() - ys.min())/SC + 8
    win, hin = 4*w/max(w, h), 4*h/max(w, h)
    open(f'{OUT}/{i+1:02d}-{name}.svg', 'w').write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" width="{win:.3f}in" height="{hin:.3f}in">\n<title>{name}</title>\n<path id="silhouette" fill="#000000" d="{d}"/>\n</svg>\n')
    meta.append((name, (x0, y0, w, h), d))
json.dump(meta, open('meta.json', 'w'))
