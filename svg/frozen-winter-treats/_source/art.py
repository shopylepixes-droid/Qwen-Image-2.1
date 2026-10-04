"""Frozen-themed winter treats, drawn as plain SVG on a 400x400 canvas (black outlines + flat fills)."""
import math

K, W, G = '#000000', '#ffffff', '#e3f3fc'
IB, SB, RB = '#a8dcf5', '#5aa9e6', '#2e6fc0'
LV, PU, MG = '#c7b6f0', '#8b6fd1', '#c8378a'
GD, OR, PK = '#f5c542', '#f08a3c', '#f6a7c8'
BR, DB, GB, CR = '#8b5a3c', '#4a2e1e', '#c98a4b', '#f3d9b1'
SL, DG = '#c5ccd6', '#3d8b5a'
PALETTE = [K, W, G, IB, SB, RB, LV, PU, MG, GD, OR, PK, BR, DB, GB, CR, SL, DG]
SW = 8


def P(d, fill, sw=SW, extra=''):
    st = f' stroke="#000" stroke-width="{sw}" stroke-linejoin="round"' if sw else ''
    return f'<path d="{d}" fill="{fill}"{st} {extra}/>'

def Cc(cx, cy, r, fill, sw=SW):
    st = f' stroke="#000" stroke-width="{sw}"' if sw else ''
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{st}/>'

def E(cx, cy, rx, ry, fill, sw=SW):
    st = f' stroke="#000" stroke-width="{sw}"' if sw else ''
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"{st}/>'

def R(x, y, w, h, rx, fill, sw=SW, rot=None):
    st = f' stroke="#000" stroke-width="{sw}" stroke-linejoin="round"' if sw else ''
    tr = f' transform="rotate({rot} {x + w/2} {y + h/2})"' if rot else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}{tr}/>'

def line(d, col, w, ow=6, cap='round'):
    """coloured band with a black edge"""
    return (f'<path d="{d}" fill="none" stroke="#000" stroke-width="{w + 2*ow}" stroke-linecap="{cap}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="{cap}" stroke-linejoin="round"/>')

def ink(d, w=7):
    return f'<path d="{d}" fill="none" stroke="#000" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'

def snowflake(cx, cy, r, col, w=None, rot=0):
    w = w or max(3.5, r * 0.15)
    segs = []
    for i in range(6):
        a = math.radians(rot + 90 + 60*i)
        ux, uy = math.cos(a), -math.sin(a)
        segs.append(f'M{cx},{cy} L{cx + ux*r:.1f},{cy + uy*r:.1f}')
        for t, L in ((0.5, 0.32), (0.78, 0.2)):
            bx, by = cx + ux*r*t, cy + uy*r*t
            for s in (-1, 1):
                b = a + s*math.radians(45)
                segs.append(f'M{bx:.1f},{by:.1f} L{bx + math.cos(b)*r*L:.1f},{by - math.sin(b)*r*L:.1f}')
    return (f'<path d="{" ".join(segs)}" fill="none" stroke="{col}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
            + Cc(cx, cy, w*0.9, col, 0))

def sparkle(cx, cy, r, col, sw=0):
    q = r*0.28
    d = f'M{cx},{cy-r} Q{cx+q*0.4},{cy-q*0.4} {cx+r},{cy} Q{cx+q*0.4},{cy+q*0.4} {cx},{cy+r} Q{cx-q*0.4},{cy+q*0.4} {cx-r},{cy} Q{cx-q*0.4},{cy-q*0.4} {cx},{cy-r} Z'
    return P(d, col, sw)

def sprinkles(items):
    return ''.join(R(x-7, y-2.6, 14, 5.2, 2.6, c, 0, rot=a) for x, y, c, a in items)

def dots(items, r=5.5):
    return ''.join(Cc(x, y, r, c, 0) for x, y, c in items)

def ring(cx, cy, Ro, Ri):
    c = lambda r: f'M{cx-r},{cy} a{r},{r} 0 1,0 {2*r},0 a{r},{r} 0 1,0 {-2*r},0 Z'
    return c(Ro) + ' ' + c(Ri)

def scallop(cx, cy, R0, amp, n, steps=240):
    pts = []
    for i in range(steps):
        t = 2*math.pi*i/steps
        r = R0 + amp*math.cos(n*t)
        pts.append(f'{cx + r*math.cos(t):.1f},{cy + r*math.sin(t):.1f}')
    return 'M' + ' L'.join(pts) + ' Z'

def swirl_candy(cx, cy, r, c1, c2, n=8):
    ri = r - SW/2
    out = [Cc(cx, cy, r, c2)]
    pt = lambda a, rr: (cx + rr*math.cos(math.radians(a)), cy + rr*math.sin(math.radians(a)))
    for i in range(0, n, 2):
        a0, a1 = 360*i/n, 360*(i+1)/n
        c0, c1_ = pt(a0 - 40, ri*0.55), pt(a1 - 40, ri*0.55)
        p0, p1 = pt(a0, ri), pt(a1, ri)
        out.append(f'<path d="M{cx},{cy} Q{c0[0]:.1f},{c0[1]:.1f} {p0[0]:.1f},{p0[1]:.1f} A{ri},{ri} 0 0 1 {p1[0]:.1f},{p1[1]:.1f} '
                   f'Q{c1_[0]:.1f},{c1_[1]:.1f} {cx},{cy} Z" fill="{c1}"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#000" stroke-width="{SW}"/>')
    return ''.join(out)

def bow(cx, cy, s, col, knot=None):
    L = (f'M{cx},{cy} C{cx-30*s},{cy-30*s} {cx-62*s},{cy-14*s} {cx-52*s},{cy+10*s} '
         f'C{cx-44*s},{cy+30*s} {cx-16*s},{cy+18*s} {cx},{cy} Z')
    Rr = (f'M{cx},{cy} C{cx+30*s},{cy-30*s} {cx+62*s},{cy-14*s} {cx+52*s},{cy+10*s} '
          f'C{cx+44*s},{cy+30*s} {cx+16*s},{cy+18*s} {cx},{cy} Z')
    tl = f'M{cx-4*s},{cy+2*s} L{cx-26*s},{cy+44*s} L{cx-12*s},{cy+40*s} L{cx},{cy+8*s} Z'
    tr = f'M{cx+4*s},{cy+2*s} L{cx+26*s},{cy+44*s} L{cx+12*s},{cy+40*s} L{cx},{cy+8*s} Z'
    return P(tl, col, 6) + P(tr, col, 6) + P(L, col, 6) + P(Rr, col, 6) + Cc(cx, cy, 9*s, knot or col, 6)

def tiara(cx, by, s, gold=GD, gem=IB):
    d = (f'M{cx-46*s},{by} L{cx-40*s},{by-30*s} L{cx-24*s},{by-14*s} L{cx-12*s},{by-38*s} L{cx},{by-18*s} L{cx},{by-50*s} '
         f'L{cx},{by-18*s} L{cx+12*s},{by-38*s} L{cx+24*s},{by-14*s} L{cx+40*s},{by-30*s} L{cx+46*s},{by} Q{cx},{by-12*s} {cx-46*s},{by} Z')
    d = (f'M{cx-46*s},{by} L{cx-40*s},{by-30*s} L{cx-24*s},{by-16*s} L{cx-12*s},{by-38*s} L{cx},{by-20*s} '
         f'L{cx+12*s},{by-38*s} L{cx+24*s},{by-16*s} L{cx+40*s},{by-30*s} L{cx+46*s},{by} Q{cx},{by-12*s} {cx-46*s},{by} Z')
    top = P(f'M{cx-9*s},{by-22*s} L{cx},{by-56*s} L{cx+9*s},{by-22*s} Z', gold, 6)
    return top + P(d, gold, 6) + Cc(cx, by-14*s, 7*s, gem, 5) + Cc(cx-28*s, by-10*s, 4.5*s, LV, 4) + Cc(cx+28*s, by-10*s, 4.5*s, LV, 4)

def cream(x0, x1, yb, h, fill=W, sw=SW):
    """bumpy whipped-cream cloud sitting on y = yb"""
    w = x1 - x0
    d = (f'M{x0},{yb} C{x0-14},{yb-28} {x0+10},{yb-52} {x0+0.16*w},{yb-0.62*h} C{x0+0.15*w},{yb-1.0*h} {x0+0.38*w},{yb-1.1*h} {x0+0.45*w},{yb-0.86*h} '
         f'C{x0+0.5*w},{yb-1.3*h} {x0+0.78*w},{yb-1.2*h} {x0+0.76*w},{yb-0.84*h} C{x0+0.92*w},{yb-0.98*h} {x1+18},{yb-0.62*h} {x1},{yb-0.18*h} '
         f'C{x1+8},{yb} {x1-4},{yb+8} {x1-20},{yb+6} L{x0+20},{yb+6} C{x0+4},{yb+8} {x0-6},{yb+2} {x0},{yb} Z')
    return P(d, fill, sw)


ITEMS = {}
def item(name):
    def deco(f): ITEMS[name] = f(); return f
    return deco


@item('cocoa-mug')
def _():
    return (line('M292,214 C364,204 368,302 286,306', SB, 22)
            + P('M88,190 L312,190 L298,332 Q295,352 272,352 L128,352 Q105,352 102,332 Z', SB)
            + cream(92, 306, 196, 92)
            + sprinkles([(140, 160, LV, 30), (180, 132, PU, -20), (225, 150, IB, 60), (262, 175, LV, -40), (205, 178, RB, 10), (160, 182, IB, -60), (240, 120, PU, 20)])
            + snowflake(200, 272, 46, W) + sparkle(318, 120, 14, W, 5) + sparkle(76, 128, 10, W, 5))

@item('soft-serve')
def _():
    t3 = 'M150,158 C136,134 160,120 178,124 C186,104 196,86 216,70 C210,92 222,106 224,124 C244,122 264,136 252,158 Z'
    t2 = 'M124,194 C110,168 138,150 162,156 C182,142 218,142 238,156 C262,150 290,168 276,194 Z'
    t1 = 'M102,232 C88,202 118,184 150,190 C175,176 225,176 250,190 C282,184 312,202 298,232 Z'
    return (P(t3, W) + P(t2, W) + P(t1, W)
            + P('M110,240 L290,240 L272,354 L128,354 Z', PU) + R(98, 222, 204, 30, 13, LV)
            + sprinkles([(160, 206, LV, 20), (205, 198, SB, -30), (245, 212, PU, 45), (180, 168, IB, -15), (225, 160, LV, 30), (196, 128, SB, 70), (140, 222, IB, -45), (262, 222, LV, 0)])
            + snowflake(200, 298, 34, W))

@item('blue-lemonade')
def _():
    cubes = R(150, 190, 40, 40, 8, W, 5, rot=15) + R(210, 200, 38, 38, 8, W, 5, rot=-12) + R(176, 248, 40, 40, 8, W, 5, rot=8)
    return (line('M178,186 L150,58', PU, 14) + line('M214,186 L240,70', LV, 14)
            + P('M118,135 L282,135 L268,352 L132,352 Z', G)
            + P('M130,176 L270,176 L261,338 L139,338 Z', SB, 6)
            + cubes + dots([(160, 300, W), (240, 280, W), (220, 318, W), (152, 252, W)], 5)
            + Cc(278, 140, 32, LV) + snowflake(278, 140, 22, W))

@item('snowman-mug')
def _():
    twigs = line('M186,150 L172,96 M176,112 L154,100 M214,150 L230,92 M226,108 L248,98', BR, 8, 5)
    return (line('M292,190 C362,184 364,286 290,292', W, 22) + twigs
            + P('M96,152 L304,152 L294,336 Q290,356 268,356 L132,356 Q110,356 106,336 Z', W)
            + E(200, 152, 104, 18, BR)
            + R(132, 124, 34, 28, 8, W, 6, rot=-12) + R(238, 126, 32, 26, 8, PK, 6, rot=14) + R(256, 140, 26, 20, 6, W, 6, rot=-8) + R(146, 140, 26, 22, 6, IB, 6, rot=10)
            + Cc(166, 212, 11, K, 0) + Cc(234, 212, 11, K, 0)
            + P('M196,232 L262,244 L198,256 Z', OR, 6)
            + ink('M160,280 Q200,306 240,280') + Cc(144, 258, 10, PK, 0) + Cc(256, 258, 10, PK, 0)
            + snowflake(140, 320, 13, IB) + snowflake(262, 318, 11, IB))

@item('snowflake-lollipop')
def _():
    return (R(191, 250, 18, 140, 8, W)
            + swirl_candy(200, 165, 100, SB, W, 8)
            + bow(200, 268, 0.85, LV, PU)
            + sparkle(142, 108, 14, W, 0) + snowflake(312, 70, 20, IB))

@item('snowflake-cookie')
def _():
    ds = [(200 + 104*math.cos(math.radians(a)), 200 + 104*math.sin(math.radians(a)), IB) for a in range(15, 360, 30)]
    return (P(scallop(200, 200, 150, 12, 10), GB)
            + P(scallop(200, 200, 124, 10, 10), W, 0)
            + snowflake(200, 200, 82, SB, 14) + dots(ds, 7))

@item('cocoa-to-go')
def _():
    return (P('M122,125 L278,125 L260,360 L140,360 Z', LV)
            + P('M129,196 L271,196 L264,296 L136,296 Z', PU)
            + snowflake(200, 246, 38, W)
            + P('M126,100 L274,100 L262,72 L138,72 Z', W) + R(106, 98, 188, 30, 10, W)
            + sparkle(304, 150, 12, IB, 5) + sparkle(96, 210, 9, IB, 5))

@item('ice-soda-can')
def _():
    drip = ('M130,112 L270,112 L270,140 Q262,172 252,142 Q242,192 230,142 Q216,164 202,142 '
            'Q188,184 174,142 Q162,162 150,142 Q140,176 130,142 Z')
    return (R(128, 92, 144, 266, 20, SB) + P(drip, W, 6)
            + R(134, 74, 132, 26, 10, SL) + R(134, 348, 132, 22, 10, SL)
            + snowflake(200, 246, 40, W) + snowflake(160, 316, 13, IB) + snowflake(244, 304, 15, IB))

@item('frozen-martini')
def _():
    return (P('M193,244 L207,244 L207,346 L193,346 Z', G) + E(200, 352, 62, 13, G)
            + P('M92,118 L308,118 L200,246 Z', G)
            + P('M114,132 L286,132 L200,230 Z', SB, 6)
            + dots([(186, 170, W), (214, 196, W), (230, 152, W)], 5)
            + Cc(112, 112, 28, LV) + snowflake(112, 112, 20, W)
            + sparkle(300, 76, 14, IB, 5))

@item('anna-lollipop')
def _():
    return (R(191, 250, 18, 140, 8, W)
            + swirl_candy(200, 165, 100, MG, W, 10)
            + bow(200, 268, 0.85, DG, DG)
            + sparkle(140, 108, 14, W, 0))

@item('ice-cream-cone')
def _():
    cone = 'M140,206 L260,206 L200,382 Z'
    waffle = ''.join(f'<path d="M{x},200 L{x+120},390" stroke="#000" stroke-width="5"/><path d="M{x+120},200 L{x},390" stroke="#000" stroke-width="5"/>' for x in range(60, 260, 32))
    scoop2 = 'M140,152 C128,112 160,84 200,86 C240,84 272,112 260,152 C230,168 170,168 140,152 Z'
    scoop1 = ('M120,216 C100,172 140,142 170,152 C185,130 225,130 240,152 C270,142 304,174 282,216 '
              'C268,234 250,214 236,230 C222,242 208,218 194,232 C178,246 166,216 150,230 C136,240 126,230 120,216 Z')
    return (f'<defs><clipPath id="cone"><path d="{cone}"/></clipPath></defs>' + P(cone, GB)
            + f'<g clip-path="url(#cone)">{waffle}</g>' + P(cone, 'none')
            + P(scoop2, IB) + P(scoop1, LV)
            + sprinkles([(170, 120, W, 30), (220, 110, PU, -30), (236, 136, W, 50), (160, 182, W, -20), (210, 178, PU, 40), (250, 190, W, 0), (186, 200, IB, 70)])
            + snowflake(200, 70, 24, W))

@item('gingerbread-snowman')
def _():
    return (Cc(200, 284, 80, GB) + Cc(200, 160, 58, GB) + Cc(200, 284, 76, GB, 0) + Cc(200, 160, 54, GB, 0)
            + f'<path d="M150,330 Q165,345 180,330 Q195,345 210,330 Q225,345 240,330 Q250,322 256,312" fill="none" stroke="{W}" stroke-width="6" stroke-linecap="round"/>'
            + P('M140,206 Q200,228 260,206 L264,232 Q200,256 136,232 Z', PU, 6) + P('M226,234 L250,232 L258,290 L236,292 Z', PU, 6)
            + Cc(180, 150, 8, K, 0) + Cc(220, 150, 8, K, 0) + P('M198,162 L236,170 L199,176 Z', OR, 5)
            + dots([(180, 186, K), (192, 191, K), (208, 191, K), (220, 186, K)], 3.5)
            + Cc(200, 270, 10, IB, 5) + Cc(200, 302, 10, IB, 5)
            + f'<path d="M156,118 Q200,96 244,118" fill="none" stroke="{W}" stroke-width="6" stroke-linecap="round"/>')

@item('sparkling-soda')
def _():
    glass = 'M140,150 L260,150 C262,206 246,252 248,300 L252,352 L148,352 L152,300 C154,252 138,206 140,150 Z'
    foam = 'M128,160 C110,138 134,112 160,120 C170,94 230,94 240,120 C266,112 290,138 272,160 C240,172 160,172 128,160 Z'
    return (P(glass, SB) + dots([(170, 210, W), (220, 226, W), (196, 260, W), (174, 300, W), (226, 300, W), (200, 330, W), (232, 190, W)], 7)
            + P(foam, W) + tiara(200, 116, 1.35))

@item('frosted-donut')
def _():
    sp = [(200 + r*math.cos(math.radians(a)), 200 + r*math.sin(math.radians(a)), c, a*1.7)
          for (r, a0, c) in ((72, 0, W), (72, 22, PU), (88, 11, MG), (88, 33, W)) for a in range(a0, 360, 45)]
    return (P(ring(200, 200, 114, 36), GB, SW, 'fill-rule="evenodd"')
            + P(scallop(200, 200, 98, 8, 9) + ' ' + ring(200, 200, 46, 46).split(' M')[0], IB, 6, 'fill-rule="evenodd"')
            + sprinkles(sp))

@item('crystal-cupcake')
def _():
    ridges = ''.join(ink(f'M{x},{246} L{x + (x-200)*0.12:.1f},{356}', 4) for x in range(146, 260, 22))
    t2 = 'M124,206 C112,178 140,164 164,170 C184,156 216,156 236,170 C260,164 288,178 276,206 Z'
    t1 = 'M100,250 C86,218 116,198 146,204 C170,188 230,188 254,204 C284,198 314,218 300,250 Z'
    return (P('M198,70 L222,112 L212,172 L188,172 L176,112 Z', IB, 6) + P('M162,104 L178,136 L174,174 L156,174 L148,136 Z', LV, 6)
            + P('M240,98 L254,132 L246,174 L226,174 L222,130 Z', W, 6)
            + P(t2, LV) + P(t1, LV)
            + P('M118,244 L282,244 L264,362 L136,362 Z', SB) + ridges
            + sprinkles([(150, 220, W, 30), (196, 214, IB, -20), (240, 224, W, 50), (176, 236, IB, 0), (226, 238, W, -40), (262, 238, IB, 20)]))

@item('frappe')
def _():
    return (line('M230,172 L262,48', PU, 14)
            + P('M128,178 L272,178 L256,362 L144,362 Z', IB)
            + P('M134,244 L266,244 L262,292 L138,292 Z', PU, 6) + snowflake(200, 326, 24, W)
            + P('M122,176 A78,78 0 0 1 278,176 Z', G)
            + P('M144,172 C132,152 152,138 172,142 C180,120 222,120 230,142 C250,138 270,152 258,172 Z', W, 6)
            + R(110, 170, 180, 20, 9, W) + sprinkles([(176, 150, LV, 20), (210, 140, SB, -30), (232, 158, LV, 60)]))

@item('reindeer-cookie')
def _():
    antlers = line('M168,146 C150,104 138,84 118,62 M146,102 L110,100 M134,80 L140,48 '
                   'M232,146 C250,104 262,84 282,62 M254,102 L290,100 M266,80 L260,48', BR, 13, 6)
    head = 'M200,136 C262,136 282,182 272,232 C264,288 242,348 200,352 C158,348 136,288 128,232 C118,182 138,136 200,136 Z'
    return (antlers + P('M140,172 C100,150 84,178 122,196 Z', GB) + P('M260,172 C300,150 316,178 278,196 Z', GB)
            + P(head, GB) + E(200, 302, 50, 40, CR, 6) + E(200, 284, 22, 15, DB, 5)
            + Cc(170, 226, 10, K, 0) + Cc(230, 226, 10, K, 0) + ink('M186,318 Q200,330 214,318', 5)
            + Cc(152, 262, 9, PK, 0) + Cc(248, 262, 9, PK, 0) + snowflake(200, 182, 20, W))

@item('candy-cane-heart')
def _():
    left = 'M200,346 C150,300 92,246 92,176 C92,124 128,98 160,98 C186,98 200,118 200,142'
    right = 'M200,346 C250,300 308,246 308,176 C308,124 272,98 240,98 C214,98 200,118 200,142'
    out = ''
    for d in (left, right):
        out += (f'<path d="{d}" fill="none" stroke="#000" stroke-width="36" stroke-linecap="round"/>'
                f'<path d="{d}" fill="none" stroke="{W}" stroke-width="22" stroke-linecap="round"/>'
                f'<path d="{d}" fill="none" stroke="{SB}" stroke-width="22" stroke-dasharray="15 15"/>')
    return out + bow(200, 322, 1.0, LV, W) + snowflake(200, 322, 7, SB, 3)

@item('peppermint-trio')
def _():
    return swirl_candy(300, 120, 62, SB, W, 8) + swirl_candy(300, 288, 58, PU, W, 8) + swirl_candy(168, 204, 108, RB, W, 10)

@item('macaron-tower')
def _():
    def mac(y, c, x=200):
        top = f'M{x-82},{y-6} C{x-84},{y-50} {x+84},{y-50} {x+82},{y-6} Z'
        bot = f'M{x-82},{y+8} C{x-80},{y+40} {x+80},{y+40} {x+82},{y+8} Z'
        return P(bot, c) + P(top, c) + R(x-74, y-9, 148, 20, 10, W, 6)
    return (mac(322, SB, 196) + mac(234, LV, 206) + mac(146, IB, 198) + snowflake(200, 78, 24, W)
            + dots([(160, 124, W), (236, 118, W), (184, 206, W), (240, 212, W), (150, 296, W), (236, 300, W)], 4.5))

@item('drip-cake')
def _():
    drip = ('M88,176 L312,176 L312,214 Q304,252 294,216 Q282,268 268,216 Q252,244 236,216 Q222,278 206,216 '
            'Q190,248 176,216 Q160,264 146,216 Q132,242 118,216 Q104,260 88,216 Z')
    return (E(200, 344, 142, 18, SL) + R(90, 178, 220, 162, 14, LV) + P(drip, IB, 6)
            + snowflake(150, 290, 18, W) + snowflake(250, 284, 22, W) + snowflake(200, 310, 12, W)
            + snowflake(200, 112, 52, W, 11) + sparkle(120, 140, 12, W, 5) + sparkle(282, 132, 14, W, 5))

@item('tiara-cupcake')
def _():
    ridges = ''.join(ink(f'M{x},{246} L{x + (x-200)*0.12:.1f},{356}', 4) for x in range(146, 260, 22))
    t2 = 'M124,206 C112,178 140,164 164,170 C184,156 216,156 236,170 C260,164 288,178 276,206 Z'
    t1 = 'M100,250 C86,218 116,198 146,204 C170,188 230,188 254,204 C284,198 314,218 300,250 Z'
    return (tiara(200, 176, 1.15) + P(t2, W) + P(t1, W)
            + P('M118,244 L282,244 L264,362 L136,362 Z', PU) + ridges
            + sprinkles([(150, 222, IB, 30), (196, 214, LV, -20), (240, 226, IB, 50), (176, 238, LV, 0), (226, 238, IB, -40), (262, 238, LV, 20), (200, 186, IB, 10)]))

@item('mitten-cookie')
def _():
    mitten = ('M142,150 L262,150 L268,290 C270,346 232,372 202,372 C160,372 136,346 136,300 L136,256 '
              'C100,268 82,236 100,212 C112,196 128,198 136,208 Z')
    cuff = ('M126,108 Q140,88 156,104 Q172,86 188,104 Q204,86 220,104 Q236,86 252,104 Q270,90 276,110 '
            'L276,150 Q260,170 244,154 Q228,172 212,154 Q196,172 180,154 Q164,172 148,154 Q132,168 126,150 Z')
    return (P(mitten, SB) + P(cuff, W) + snowflake(204, 268, 44, W)
            + dots([(160, 210, IB), (248, 214, IB), (160, 330, IB), (246, 332, IB)], 6))

@item('ice-castle-cookie')
def _():
    body = ('M100,330 L100,250 L112,250 L112,202 L150,202 L150,250 L165,250 L165,142 L235,142 L235,250 '
            'L250,250 L250,202 L288,202 L288,250 L300,250 L300,330 Z')
    win = R(190, 176, 20, 30, 10, W, 5) + R(122, 220, 16, 22, 8, W, 5) + R(262, 220, 16, 22, 8, W, 5)
    return (P(body, IB) + P('M158,144 L200,58 L242,144 Z', PU) + P('M106,204 L131,150 L156,204 Z', PU) + P('M244,204 L269,150 L294,204 Z', PU)
            + P('M182,332 L182,292 A18,18 0 0 1 218,292 L218,332 Z', PU, 6) + win
            + P('M78,336 C110,312 150,326 180,320 C220,310 262,326 322,320 L324,352 L76,352 Z', W)
            + sparkle(84, 150, 12, W, 5) + sparkle(318, 120, 14, W, 5))
