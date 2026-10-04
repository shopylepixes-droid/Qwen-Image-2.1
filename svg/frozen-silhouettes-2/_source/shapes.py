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


