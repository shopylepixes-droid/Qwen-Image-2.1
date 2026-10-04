import json, sys, cairosvg
meta = json.load(open('meta.json')); CW, CH, COLS = 240, 260, 7
rows = (len(meta)+COLS-1)//COLS; W, H = CW*COLS + 40, CH*rows + 110
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, sans-serif"><rect width="100%" height="100%" fill="#fff"/>',
     f'<text x="{W/2}" y="48" text-anchor="middle" font-size="30">Frozen Silhouettes II — {len(meta)} SVG for Cricut</text>',
     f'<text x="{W/2}" y="80" text-anchor="middle" font-size="16" fill="#555">one black layer per design · single compound path</text>']
for i, (name, (x0, y0, w, h), d) in enumerate(meta):
    r, c = divmod(i, COLS); s = min((CW-30)/w, (CH-55)/h)
    cx, cy = 20 + c*CW + CW/2, 95 + r*CH + (CH-40)/2
    o.append(f'<path transform="translate({cx - w*s/2 - x0*s:.1f},{cy - h*s/2 - y0*s:.1f}) scale({s:.4f})" d="{d}"/>')
    o.append(f'<text x="{cx}" y="{95+r*CH+CH-12}" text-anchor="middle" font-size="13" fill="#555">{i+1:02d} {name}</text>')
o.append('</svg>'); open(sys.argv[1], 'w').write('\n'.join(o))
cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[1].replace('.svg', '.png'), output_width=1800)
