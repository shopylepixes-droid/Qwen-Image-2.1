import json, sys, cairosvg
meta = json.load(open('meta.json'))
CW, CH, COLS = 240, 270, 8
rows = (len(meta)+COLS-1)//COLS
EXH = 280
W, H = CW*COLS + 40, CH*rows + 110 + EXH
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, sans-serif">',
       '<rect width="100%" height="100%" fill="#ffffff"/>',
       f'<text x="{W/2}" y="48" text-anchor="middle" font-size="30" fill="#23395d">Frozen Winter Treats — {len(meta)} layered SVG for Cricut</text>',
       f'<text x="{W/2}" y="80" text-anchor="middle" font-size="16" fill="#555">black base layer + flat colour layers, each colour one compound path</text>']
def place(els, box, cx, cy, maxw, maxh):
    x0, y0, w, h = box; s = min(maxw/w, maxh/h)
    return f'<g transform="translate({cx - w*s/2 - x0*s:.1f},{cy - h*s/2 - y0*s:.1f}) scale({s:.4f})">' + ''.join(els) + '</g>'
for i, (fn, box, layers, els) in enumerate(meta):
    r, c = divmod(i, COLS)
    out.append(place(els, box, 20 + c*CW + CW/2, 95 + r*CH + (CH-40)/2, CW-30, CH-60))
    name = fn.split('/')[-1][3:-4]
    out.append(f'<text x="{20+c*CW+CW/2}" y="{95+r*CH+CH-14}" text-anchor="middle" font-size="13" fill="#555">{i+1:02d} {name} · {len(layers)-1}+black</text>')
k = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
fn, box, layers, els = meta[k]
ey = 95 + rows*CH + 20
out.append(f'<text x="{W/2}" y="{ey}" text-anchor="middle" font-size="20" fill="#23395d">Layers of {k+1:02d} (bottom → top) — each colour is one compound path</text>')
n = len(els); ew = (W-40)/n
for j, (el, (ln, col)) in enumerate(zip(els, layers)):
    out.append(f'<rect x="{20+j*ew+4:.1f}" y="{ey+16}" width="{ew-8:.1f}" height="200" rx="10" fill="#eef1f5"/>')
    out.append(place([el], box, 20+j*ew+ew/2, ey+116, ew-30, 170))
    out.append(f'<text x="{20+j*ew+ew/2:.1f}" y="{ey+238}" text-anchor="middle" font-size="13" fill="#444">{j+1}. {ln} {col}</text>')
out.append('</svg>')
open(sys.argv[1], 'w').write('\n'.join(out))
cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[1].replace('.svg', '.png'), output_width=2000)
