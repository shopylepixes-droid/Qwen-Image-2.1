"""Render the from-scratch drawings to one-layer SVGs on a 1080x1080 artboard + transparent PNGs."""
import io, re, sys, os, json, subprocess, glob
import numpy as np, cairosvg
from PIL import Image
from svgpathtools import parse_path
from art import ITEMS
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
PX = 3200; SC = PX/400; ART, MARGIN = 1080, 40
def potrace_d(bm, f):
    h, w = bm.shape
    pbm = b'P4\n%d %d\n' % (w, h) + np.packbits(bm.astype(np.uint8), axis=1).tobytes()
    r = subprocess.run(['potrace', '-s', '-o', '-', '-t', '20', '-a', '1.0', '-O', '0.8', '-u', '10', '--flat'], input=pbm, capture_output=True, check=True).stdout.decode()
    ds = ' '.join(re.findall(r' d="([^"]+)"', r))
    tx, ty, sx, sy = map(float, re.search(r'translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)', r).groups())
    g = lambda z: f(complex(tx + sx*z.real, ty + sy*z.imag)); fmt = lambda z: f'{z.real:.2f},{z.imag:.2f}'
    out = []
    for sub in parse_path(ds).continuous_subpaths():
        segs = list(sub); out.append('M' + fmt(g(segs[0].start)))
        for s in segs:
            out.append(('C' + ' '.join(fmt(g(q)) for q in (s.control1, s.control2, s.end))) if type(s).__name__ == 'CubicBezier' else 'L' + fmt(g(s.end)))
        out.append('Z')
    return ''.join(out)
meta = []
for i, (name, body) in enumerate(ITEMS.items()):
    fn = f'{OUT}/{i+1:02d}-{name}.svg'
    if body is None:
        svg = open(glob.glob(f'scratchpad/sil3/traced/{i+1:02d}-*.svg')[0]).read()
        d = re.search(r' d="([^"]+)"', svg).group(1)
    else:
        src = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="{PX}" height="{PX}">{body}</svg>'
        a = np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=src.encode()))).convert('RGBA')).astype(float)
        ink = (a[..., 3]/255) * (1 - a[..., :3].mean(-1)/255)       # anti-aliased coverage of black
        bm = ink > 0.5
        ys, xs = np.where(bm); bx0, bx1, by0, by1 = xs.min(), xs.max()+1, ys.min(), ys.max()+1
        s = (ART - 2*MARGIN)/max(bx1 - bx0, by1 - by0)
        ox = (ART - (bx1 - bx0)*s)/2 - bx0*s; oy = (ART - (by1 - by0)*s)/2 - by0*s
        d = potrace_d(bm, lambda z: complex(ox + z.real*s, oy + z.imag*s))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ART} {ART}" width="{ART}" height="{ART}">\n'
           f'<title>{name}</title>\n<path id="silhouette" fill="#000000" d="{d}"/>\n</svg>\n')
    open(fn, 'w').write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=fn[:-4] + '.png', output_width=ART, output_height=ART)
    meta.append((fn, ART, ART, d))
json.dump(meta, open('scratchpad/sil3/meta.json', 'w'))
print(len(meta))
