"""MAATRUBHUMI: MAY WAR REST IN PEACE. A fan-made Hindi tribute trailer, about 90 s.

Everything on screen is drawn in code: no footage, stills or posters from the film. The soldiers,
helicopters, convoy, map, flag and letter are symbolic and stand for no real person, unit or event.

One camera travels left to right over one dark world with a mountain ridge running under all of it:
  S1 the opening (smoke, a lone soldier, flashes on the horizon)   lines 1-3
  S2 the title                                                      lines 4-5
  S3 the world of war (tactical map, convoy, the three cards)       lines 6-8
  S4 the cast                                                       lines 9-10
  S5 the cost (empty frame, a letter from home)                     lines 11-13
  S6 the climax (soldiers advancing, flashes, the flag)             lines 14-15
  S7 the title card and release date                                lines 16-18
Times come from the voice: doc.L(i) line start, doc.E(i) line end, doc.W(i, "word") a spoken word.
World units are 4K pixels at zoom 1.
"""
import math

import numpy as np
import skia

from engine import (HILITE, LOOKS, BigText, Card, Film, Item, PaperDoc, PenMark, Route, Stamp, draw_text,
                    ease_in_out, ease_out_cubic, paint, ramp, text_width)

# ---------------------------------------------------------------- palette
STEEL = (196, 202, 206)
BONE = (238, 232, 220)
SAFFRON = (255, 153, 51)
GREEN = (19, 136, 8)
NAVY = (0, 0, 128)
EMBER = (255, 142, 52)
BLOOD = (176, 34, 26)
OLIVE = (104, 112, 82)
NIGHT = (11, 12, 14)

LOOK = dict(LOOKS["charcoal"], bg=(6, 6, 7), grade=(1.04, 1.0, 0.93), grain=0.034, glow=0.34, vignette=0.9, curve=0.34,
            dim=(3, 3, 3))

X1, X2, X3, X4, X5, X6, X7 = 0, 13000, 27000, 41000, 53000, 65000, 78000
GROUND = 2400                    # y of the ridge line under the whole world


def noise1(x, seed=0):
    """Smooth 1-D value noise in [-1, 1]."""
    i = math.floor(x); f = x - i
    def h(n):
        n = (n * 374761393 + seed * 668265263) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 32767.5 - 1
    u = f * f * (3 - 2 * f)
    return h(i) * (1 - u) + h(i + 1) * u


# ---------------------------------------------------------------- items drawn in code
LAYERS = ((1700, GROUND - 900, (44, 40, 38)), (1250, GROUND - 350, (28, 26, 26)), (520, GROUND + 260, (12, 12, 13)))


def ridge_y(x, k=2):
    amp, base, _ = LAYERS[k]
    return base - amp * (0.55 + 0.45 * noise1(x / (2600 - k * 500), 11 + k) + 0.18 * noise1(x / 610, 31 + k))


def ground(x):
    """y of the front ridge (where soldiers and trucks stand) at world x."""
    return ridge_y(x, 2)


class Ridge(Item):
    """Layered mountain silhouettes along the whole world, with a warm horizon glow behind."""
    z = -60

    def __init__(self, x0, x1):
        super().__init__(-1)
        self.paths = []
        for k, (_, _, col) in enumerate(LAYERS):
            p = skia.Path(); p.moveTo(x0, GROUND + 6000)
            x = x0
            while x <= x1:
                p.lineTo(x, ridge_y(x, k)); x += 100
            p.lineTo(x1, GROUND + 6000); p.close()
            self.paths.append((p, col))

    def draw(self, c, res, t):
        v = res.view
        g = skia.GradientShader.MakeLinear([skia.Point(0, GROUND - 4200), skia.Point(0, GROUND - 600)],
                                           [skia.Color(0, 0, 0, 0), skia.Color(150, 70, 26, 150)])
        gp = skia.Paint(); gp.setShader(g)
        c.drawRect(skia.Rect.MakeLTRB(v.left(), GROUND - 4200, v.right(), GROUND + 400), gp)
        for p, col in self.paths:
            c.drawPath(p, paint(col, 1))


class Smoke(Item):
    """Drifting smoke over a stretch of the world. front=True puts thin wisps in front of everything."""

    def __init__(self, x0, x1, y0, y1, n=26, seed=3, front=False, alpha=0.22, rgb=(70, 66, 62), t_in=-1, t_out=None):
        super().__init__(t_in, t_out)
        self.z = 95 if front else -30
        rng = np.random.default_rng(seed)
        self.p = [(rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(700, 2200), rng.uniform(-90, 90), rng.uniform(-30, 10),
                   rng.uniform(0.4, 1.0)) for _ in range(n)]
        self.alpha, self.rgb = alpha, rgb
        self.box = skia.Rect.MakeLTRB(x0 - 3000, y0 - 3000, x1 + 3000, y1 + 3000)

    def bounds(self, res):
        return self.box

    def draw(self, c, res, t):
        a = self.alpha * self.fade(t) * ramp(t, self.t_in, 1.5)
        for (x, y, r, vx, vy, w) in self.p:
            xx, yy = x + vx * t, y + vy * t
            rr = r * (1 + 0.04 * math.sin(t * 0.3 + x))
            c.drawCircle(xx, yy, rr, paint(self.rgb, a * w, blur=rr * 0.45))


class Flash(Item):
    """An explosion on the horizon: a hot core and a wide warm glow that flares and dies away."""
    z = -45

    def __init__(self, x, y, t_in, size=1800, gain=0.8, shake=18):
        super().__init__(t_in)
        self.x, self.y, self.size, self.gain, self.sh = x, y, size, gain, shake

    def bounds(self, res):
        r = self.size * 3
        return skia.Rect.MakeLTRB(self.x - r, self.y - r, self.x + r, self.y + r)

    def visible(self, t):
        return self.t_in - 0.01 <= t < self.t_in + 4

    def cues(self):
        return [("boom", self.t_in, self.gain, {})]

    def shakes(self):
        return [(self.t_in + 0.05, self.sh, 0.6)] if self.sh else []

    def draw(self, c, res, t):
        u = t - self.t_in
        if u < 0:
            return
        e = min(1, u / 0.08) * math.exp(-u * 1.6)
        r = self.size * (0.6 + 0.5 * ease_out_cubic(min(1, u / 0.8)))
        g = skia.GradientShader.MakeRadial(skia.Point(self.x, self.y), r * 2.4,
                                           [skia.Color(255, 236, 190, int(255 * e)), skia.Color(*EMBER, int(200 * e)),
                                            skia.Color(150, 50, 16, int(90 * e)), skia.Color(0, 0, 0, 0)], [0, 0.12, 0.45, 1])
        p = skia.Paint(); p.setShader(g); p.setBlendMode(skia.BlendMode.kScreen)
        c.drawCircle(self.x, self.y, r * 2.4, p)


def _capsule(path, p0, p1, r0, r1):
    """A tapered limb from p0 (radius r0) to p1 (radius r1), round at both ends."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / d, dx / d
    pts = [(x0 + nx * r0, y0 + ny * r0), (x1 + nx * r1, y1 + ny * r1), (x1 - nx * r1, y1 - ny * r1), (x0 - nx * r0, y0 - ny * r0)]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) < 0:
        pts.reverse()                     # same winding as addCircle/addRect (clockwise), so overlaps fill, never cancel
    q = skia.Path(); q.moveTo(*pts[0]); [q.lineTo(*pt) for pt in pts[1:]]; q.close()
    path.addPath(q); path.addCircle(x0, y0, r0); path.addCircle(x1, y1, r1)


def soldier_path(pose="stand", phase=0.0):
    """One filled path: a soldier with helmet, pack and rifle, 1 unit tall, feet at y=0, facing right."""
    lean = {"stand": 0.0, "walk": 0.035, "run": 0.11}[pose]
    swing = {"stand": 0.0, "walk": 0.38, "run": 0.7}[pose]
    bob = {"stand": 0.0, "walk": 0.012, "run": 0.03}[pose] * abs(math.sin(phase))
    p = skia.Path()
    hip = (0.0, -0.47 - bob)
    neck = (0.02 + lean, -0.79 - bob)
    for s in (1, -1):                                         # legs: thigh, shin, boot
        a = swing * math.sin(phase + (0 if s > 0 else math.pi)) + (0.06 * s if pose == "stand" else 0)
        knee = (hip[0] + 0.235 * math.sin(a), hip[1] + 0.235 * math.cos(a))
        bend = 0.55 * swing * max(0.0, -math.sin(phase + (0 if s > 0 else math.pi)))
        ankle = (knee[0] + 0.22 * math.sin(a - bend), min(-0.035, knee[1] + 0.22 * math.cos(a - bend)))
        _capsule(p, hip, knee, 0.062, 0.05)
        _capsule(p, knee, ankle, 0.046, 0.036)
        p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(ankle[0] - 0.045, ankle[1] - 0.03, ankle[0] + 0.085, ankle[1] + 0.035), 0.02, 0.02))
    _capsule(p, hip, neck, 0.085, 0.105)                      # torso, chest wider
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(neck[0] - 0.2, neck[1] + 0.0, neck[0] - 0.07, neck[1] + 0.25), 0.03, 0.03))  # pack
    head = (neck[0] + 0.012, neck[1] - 0.075)
    p.addCircle(head[0], head[1], 0.052)
    p.addOval(skia.Rect.MakeLTRB(head[0] - 0.078, head[1] - 0.085, head[0] + 0.07, head[1] + 0.02))      # helmet dome
    p.addRect(skia.Rect.MakeLTRB(head[0] - 0.09, head[1] - 0.012, head[0] + 0.085, head[1] + 0.008))      # brim
    sh = (neck[0] + 0.01, neck[1] + 0.03)
    elbow = (sh[0] + 0.07, sh[1] + 0.15)
    hand = (sh[0] + 0.21, sh[1] + 0.1)
    _capsule(p, sh, elbow, 0.042, 0.036); _capsule(p, elbow, hand, 0.034, 0.03)
    _capsule(p, (sh[0] - 0.1, sh[1] + 0.14), (sh[0] + 0.36, sh[1] + 0.06), 0.018, 0.014)                 # rifle
    p.addRect(skia.Rect.MakeLTRB(sh[0] + 0.08, sh[1] + 0.11, sh[0] + 0.11, sh[1] + 0.19))                # magazine
    return p


class Soldier(Item):
    """A soldier silhouette, standing or moving along the ground, with a warm rim from the fires."""
    z = 20

    def __init__(self, x, h, t_in, pose="stand", vx=0.0, t_out=None, flip=False, rgb=NIGHT, rim=EMBER, rim_a=0.55, z=None, lift=0.0):
        super().__init__(t_in, t_out, z)
        self.x, self.h, self.pose, self.vx, self.flip, self.rgb, self.rim, self.rim_a, self.lift = x, h, pose, vx, flip, rgb, rim, rim_a, lift

    def pos(self, t):
        x = self.x + self.vx * max(0, t - self.t_in)
        return x, ground(x) + 40 - self.lift

    def bounds(self, res):
        return skia.Rect.MakeLTRB(-1e9, GROUND - 2000 - self.h * 1.5, 1e9, GROUND + 2000)

    def draw(self, c, res, t):
        a = ramp(t, self.t_in, 0.6) * self.fade(t)
        if a <= 0:
            return
        x, y = self.pos(t)
        speed = {"stand": 0, "walk": 5.2, "run": 10.5}[self.pose]
        body = soldier_path(self.pose, t * speed + self.x * 0.001)
        c.save(); c.translate(x, y); c.scale(-self.h if self.flip else self.h, self.h)
        c.save(); c.translate(-0.014, -0.008); c.drawPath(body, paint(self.rim, self.rim_a * a, blur=0.004)); c.restore()
        c.drawPath(body, paint(self.rgb, a))
        c.restore()


class Helicopter(Item):
    """Helicopter silhouette flying from (x0, y) to (x1, y) between t_in and t_in + dur, rotor spinning."""
    z = 30

    def __init__(self, x0, x1, y, size, t_in, dur, rgb=(14, 15, 17)):
        super().__init__(t_in)
        self.x0, self.x1, self.y, self.size, self.dur, self.rgb = x0, x1, y, size, dur, rgb

    def visible(self, t):
        return self.t_in - 0.01 <= t <= self.t_in + self.dur

    def cues(self):
        return [("whoosh", self.t_in + self.dur * 0.4, 0.5, {})]

    def draw(self, c, res, t):
        u = ramp(t, self.t_in, self.dur)
        x = self.x0 + (self.x1 - self.x0) * u
        y = self.y + 60 * math.sin(t * 1.4)
        s = self.size; d = 1 if self.x1 > self.x0 else -1
        c.save(); c.translate(x, y); c.scale(s * d, s); c.rotate(4)
        p = paint(self.rgb, 1)
        c.drawOval(skia.Rect.MakeLTRB(-0.45, -0.22, 0.25, 0.14), p)                    # cabin
        c.drawRect(skia.Rect.MakeLTRB(-1.05, -0.09, -0.35, -0.02), p)                  # tail boom
        c.drawRect(skia.Rect.MakeLTRB(-1.1, -0.26, -1.0, -0.02), p)                    # fin
        c.drawRect(skia.Rect.MakeLTRB(-0.06, -0.3, 0.02, -0.2), p)                     # mast
        c.drawLine(-0.38, 0.24, 0.2, 0.24, paint(self.rgb, 1, stroke=0.03))             # skid
        for k in (-0.22, 0.08):
            c.drawLine(k, 0.12, k - 0.02, 0.24, paint(self.rgb, 1, stroke=0.025))
        blade = abs(math.sin(t * 22))
        c.drawLine(-0.02 - 0.95 * blade, -0.31, -0.02 + 0.95 * blade, -0.31, paint(self.rgb, 0.85, stroke=0.025))
        c.drawOval(skia.Rect.MakeLTRB(-0.97, -0.34, 0.93, -0.28), paint(self.rgb, 0.18))   # rotor blur disc
        c.restore()


class Convoy(Item):
    """A line of army trucks rolling along the ridge."""
    z = 15

    def __init__(self, x, y, n, size, t_in, vx=260):
        super().__init__(t_in)
        self.x, self.y, self.n, self.size, self.vx = x, y, n, size, vx

    def bounds(self, res):
        return skia.Rect.MakeLTRB(-1e9, self.y - self.size * 2, 1e9, self.y + self.size)

    def draw(self, c, res, t):
        a = ramp(t, self.t_in, 0.8) * self.fade(t)
        if a <= 0:
            return
        for k in range(self.n):
            x = self.x + (t - self.t_in) * self.vx - k * self.size * 2.6
            c.save(); c.translate(x, ground(x) + 30 + 10 * math.sin(t * 3 + k)); c.scale(self.size, self.size)
            p = paint((12, 13, 14), a)
            c.drawRect(skia.Rect.MakeLTRB(-1.0, -0.85, 0.35, -0.2), p)                  # canvas back
            c.drawRect(skia.Rect.MakeLTRB(0.38, -0.62, 0.85, -0.2), p)                  # cab
            for wx in (-0.7, -0.3, 0.62):
                c.drawCircle(wx, -0.12, 0.13, p)
            c.drawCircle(0.86, -0.42, 0.05, paint((255, 220, 160), 0.7 * a, blur=0.06))  # headlamp
            c.restore()


class TacticalMap(Item):
    """A dark terrain sheet: grid, contour rings and range lines. Symbolic, no real place or border."""
    z = -20

    def __init__(self, x, y, w, h, t_in, seed=5):
        super().__init__(t_in)
        self.x, self.y, self.w, self.h = x, y, w, h
        rng = np.random.default_rng(seed)
        self.rings = []
        for _ in range(4):
            cx, cy = rng.uniform(-0.35, 0.35) * w, rng.uniform(-0.3, 0.3) * h
            base = rng.uniform(500, 900)
            for k in range(7):
                r = base + k * 260
                p = skia.Path()
                for j in range(73):
                    ang = j / 72 * 2 * math.pi
                    rr = r * (1 + 0.18 * noise1(ang * 2 + k * 0.3, 7 + int(cx) % 50) + 0.07 * math.sin(3 * ang + k))
                    pt = (cx + rr * math.cos(ang), cy + rr * math.sin(ang) * 0.75)
                    p.moveTo(*pt) if j == 0 else p.lineTo(*pt)
                p.close(); self.rings.append((p, k))

    def bounds(self, res):
        return skia.Rect.MakeXYWH(self.x - self.w, self.y - self.h, self.w * 2, self.h * 2)

    def draw(self, c, res, t):
        u = ease_out_cubic(ramp(t, self.t_in, 1.2)); a = u * self.fade(t)
        if a <= 0:
            return
        W, H = self.w, self.h
        c.save(); c.translate(self.x, self.y)
        rect = skia.Rect.MakeXYWH(-W / 2, -H / 2, W, H)
        c.drawRect(rect, paint((14, 20, 18), 0.92 * a))
        c.save(); c.clipRect(rect)
        gp = paint((80, 120, 96), 0.18 * a, stroke=6)
        for gx in np.arange(-W / 2, W / 2, 600):
            c.drawLine(gx, -H / 2, gx, -H / 2 + H * u, gp)
        for gy in np.arange(-H / 2, H / 2, 600):
            c.drawLine(-W / 2, gy, -W / 2 + W * u, gy, gp)
        for p, k in self.rings:
            c.drawPath(p, paint((132, 170, 120), (0.42 - 0.04 * k) * a, stroke=10 if k % 3 else 16))
        c.restore()
        c.drawRect(rect, paint((150, 170, 140), 0.5 * a, stroke=14))
        for i in range(0, int(W // 600) + 1):
            draw_text(c, res, f"{i:02d}", -W / 2 + i * 600 + 20, -H / 2 - 40, 90, "mono", (150, 170, 140), 0.6 * a)
        c.restore()


class Frame(Item):
    """An empty photo frame, pinned: the person who is missing from it."""
    z = 25

    def __init__(self, x, y, w, h, t_in, rot=-3):
        super().__init__(t_in)
        self.x, self.y, self.w, self.h, self.rot = x, y, w, h, rot

    def cues(self):
        return [("pop", self.t_in, 0.5, {})]

    def draw(self, c, res, t):
        u = ease_out_cubic(ramp(t, self.t_in, 0.6)); a = ramp(t, self.t_in, 0.3) * self.fade(t)
        if a <= 0:
            return
        W, H = self.w, self.h
        c.save(); c.translate(self.x, self.y + (1 - u) * 150); c.rotate(self.rot)
        c.save(); c.translate(30, 50); c.drawRect(skia.Rect.MakeXYWH(-W / 2, -H / 2, W, H), paint((0, 0, 0), 0.5 * a, blur=50)); c.restore()
        c.drawRect(skia.Rect.MakeXYWH(-W / 2, -H / 2, W, H), paint((92, 64, 40), a))
        b = W * 0.09
        inner = skia.Rect.MakeXYWH(-W / 2 + b, -H / 2 + b, W - 2 * b, H - 2 * b)
        g = skia.GradientShader.MakeRadial(skia.Point(0, -H * 0.05), W * 0.6, [skia.Color(58, 54, 50), skia.Color(18, 17, 16)])
        gp = skia.Paint(); gp.setShader(g); gp.setAlphaf(a); c.drawRect(inner, gp)
        # faint pale outline where a portrait was: shoulders and head, no face
        op = paint((210, 200, 180), 0.16 * a, stroke=10)
        c.drawCircle(0, -H * 0.12, W * 0.13, op)
        sh = skia.Path(); sh.moveTo(-W * 0.3, H / 2 - b); sh.cubicTo(-W * 0.28, H * 0.12, W * 0.28, H * 0.12, W * 0.3, H / 2 - b); c.drawPath(sh, op)
        sheen = skia.Path(); sheen.moveTo(-W / 2 + b, -H / 2 + b); sheen.lineTo(-W / 2 + b + W * 0.25, -H / 2 + b); sheen.lineTo(-W / 2 + b, -H / 2 + b + H * 0.3); sheen.close()
        c.drawPath(sheen, paint((255, 255, 255), 0.06 * a))
        c.restore()


class Tricolour(Item):
    """The Indian flag (3:2, Ashoka Chakra with 24 spokes) rising up a pole and waving."""
    z = 40

    def __init__(self, x, y, w, t_in, rise=3.0, pole_h=None):
        super().__init__(t_in)
        self.x, self.y, self.w, self.rise = x, y, w, rise
        self.pole_h = pole_h or w * 2.2

    def bounds(self, res):
        return skia.Rect.MakeLTRB(self.x - self.w, self.y - self.pole_h - self.w, self.x + self.w * 2, self.y + 200)

    def cues(self):
        return [("riser", self.t_in, 0.5, {"dur": self.rise})]

    def draw(self, c, res, t):
        a = ramp(t, self.t_in - 0.5, 0.8) * self.fade(t)
        if a <= 0:
            return
        W = self.w; H = W * 2 / 3
        c.drawRect(skia.Rect.MakeLTRB(self.x - 22, self.y - self.pole_h, self.x + 22, self.y), paint((150, 150, 150), a))
        c.drawCircle(self.x, self.y - self.pole_h - 30, 40, paint((200, 180, 120), a))
        u = ease_in_out(ramp(t, self.t_in, self.rise))
        top = self.y - H - 60 - (self.pole_h - H - 160) * u
        n = 48
        bands = (SAFFRON, (255, 255, 255), GREEN)
        for k in range(n):
            x0 = k / n; x1 = (k + 1) / n
            def wave(xf):
                return 0.06 * H * xf * math.sin(xf * 7 - t * 4.2), 1 - 0.05 * xf * (0.5 + 0.5 * math.sin(xf * 7 - t * 4.2 + 1.3))
            (d0, s0), (d1, s1) = wave(x0), wave(x1)
            shade = 0.86 + 0.14 * math.cos(x0 * 7 - t * 4.2)
            for b, col in enumerate(bands):
                q = skia.Path()
                ya0, yb0 = top + d0 + H * s0 * b / 3, top + d0 + H * s0 * (b + 1) / 3
                ya1, yb1 = top + d1 + H * s1 * b / 3, top + d1 + H * s1 * (b + 1) / 3
                xa, xb = self.x + 22 + W * x0, self.x + 22 + W * x1 + 1.5
                q.moveTo(xa, ya0); q.lineTo(xb, ya1); q.lineTo(xb, yb1); q.lineTo(xa, yb0); q.close()
                c.drawPath(q, paint(tuple(int(v * shade) for v in col), a))
        # chakra at the flag's centre, following the wave
        d, s = wave(0.5)
        cx, cy = self.x + 22 + W * 0.5, top + d + H * s * 0.5
        r = H * s / 3 * 0.43
        cp = paint(NAVY, a, stroke=r * 0.1)
        c.drawCircle(cx, cy, r, cp)
        for k in range(24):
            ang = k / 24 * 2 * math.pi
            c.drawLine(cx, cy, cx + r * math.cos(ang), cy + r * math.sin(ang), paint(NAVY, a, stroke=r * 0.045))
        c.drawCircle(cx, cy, r * 0.16, paint(NAVY, a))


class Embers(Item):
    """Sparks rising through the climax."""
    z = 90

    def __init__(self, x0, x1, y0, y1, t_in, t_out=None, n=90, seed=9):
        super().__init__(t_in, t_out)
        rng = np.random.default_rng(seed)
        self.p = [(rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(80, 260), rng.uniform(6, 16), rng.uniform(0, 6)) for _ in range(n)]
        self.span = y1 - y0 + 3000

    def draw(self, c, res, t):
        a = ramp(t, self.t_in, 1.0) * self.fade(t)
        if a <= 0:
            return
        for (x, y, vy, r, ph) in self.p:
            yy = y - ((t * vy + ph * 400) % self.span)
            xx = x + 120 * math.sin(t * 0.8 + ph)
            fl = 0.5 + 0.5 * math.sin(t * 9 + ph * 3)
            c.drawCircle(xx, yy, r, paint(EMBER, a * (0.35 + 0.65 * fl), blur=r * 0.8))


class SplitLine(Item):
    """A red line cutting down between two words (life | death)."""
    z = 75

    def __init__(self, x, y, h, t_in, t_out=None):
        super().__init__(t_in, t_out)
        self.x, self.y, self.h = x, y, h

    def cues(self):
        return [("snip", self.t_in, 0.6, {})]

    def draw(self, c, res, t):
        u = ease_out_cubic(ramp(t, self.t_in, 0.35)); a = self.fade(t)
        if u <= 0:
            return
        c.drawLine(self.x, self.y - self.h / 2, self.x, self.y - self.h / 2 + self.h * u, paint(BLOOD, a, stroke=26))


# ---------------------------------------------------------------- the film
def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look=LOOK)
    cue, shot, cam, foc = film.cue, film.shot, film.cam, film.focus

    film.add(Ridge(X1 - 14000, X7 + 14000))
    film.add(Smoke(X1 - 9000, X7 + 9000, GROUND - 3600, GROUND + 400, n=90, seed=2, alpha=0.18))
    film.add(Smoke(X1 - 6000, X1 + 7000, -2500, 2600, n=22, seed=4, front=True, alpha=0.10, t_out=L(4)))
    film.add(Smoke(X6 - 7000, X6 + 8000, -2400, 2600, n=26, seed=6, front=True, alpha=0.12, t_in=L(14) - 1, t_out=L(16)))
    film.room_tone = [[0.0, film.duration]]

    # ============================================================ S1 OPENING (1-3)
    cue("boom", 0.6, 0.35)
    film.add(Flash(X1 - 4200, GROUND - 1500, 0.9, size=1300, gain=0.45, shake=6))
    film.add(Soldier(X1 + 400, 2100, L(1) + 0.2, "stand", rim_a=0.8))
    film.add(Flash(X1 + 3600, GROUND - 1300, W(1, "गोलियां") - 0.05, size=1900, gain=0.7, shake=14))
    PX = X1 - 4300                                                       # a patrol walks the ridge: boots in the dust
    for k in range(5):
        film.add(Soldier(PX - k * 1000, 1500, L(2) - 1.0, "walk", vx=360, t_out=E(3), rim_a=0.5))
    film.add(Smoke(PX - 4000, PX + 3000, GROUND - 900, GROUND + 300, n=26, seed=12, front=True, alpha=0.16, rgb=(120, 104, 86),
                   t_in=L(2) - 1.5, t_out=L(3) + 0.5))
    film.add(Flash(X1 - 2400, GROUND - 1700, W(2, "टूटता") - 0.1, size=1500, gain=0.55, shake=10))
    one = W(3, "देश") - 0.05
    film.add(BigText("ONE NATION.", X1 - 2600, -1700, 620, W(3, "कोई") - 0.1, rgb=BONE, hit=0.8, t_out=L(4) + 0.3))
    film.add(BigText("ONE WAR.", X1 + 2700, -1700, 620, one, rgb=BONE, hit=0.8, t_out=L(4) + 0.3))
    film.add(BigText("COUNTLESS SACRIFICES.", X1, -900, 520, W(3, "नाम") - 0.05, rgb=EMBER, hit=1.0, t_out=L(4) + 0.3))

    g0 = ground(X1 + 400)
    cam(0.0, X1 + 900, g0 - 1500, 0.4, -0.8)                              # black, then the ridge and the lone soldier
    cam(L(1) + 2.0, X1 + 600, g0 - 1300, 0.5, -0.4)
    cam(E(1) + 0.3, X1 + 450, g0 - 1200, 0.6, 0.0)
    bx = PX + 360 * (L(2) + 1.5 - (L(2) - 1.0)) - 1200                      # where the boots are mid-line
    cam(L(2) + 0.4, bx, ground(bx) - 600, 0.82, 0.8)                       # low on the ridge: the patrol marching in the dust
    cam(E(2) - 0.2, bx + 900, ground(bx + 900) - 650, 0.74, 0.4)
    cam(L(3) + 0.7, X1, -800, 0.42, 0.0)
    cam(E(3) + 0.6, X1, -1000, 0.4, -0.3)
    foc(0.0, X1 + 450, g0 - 1200, 3000, 0.4)
    foc(L(2) + 0.3, bx + 400, ground(bx) - 400, 2400, 0.3)
    foc(L(3) + 0.5, X1, -1100, 6500, 0.3)

    # ============================================================ S2 TITLE (4-5)
    cue("riser", L(4) - 1.0, 0.45, dur=0.9)
    film.add(BigText("SALMAN KHAN", X2, -1300, 520, W(4, "सलमान") - 0.1, rgb=STEEL, rules=True, type_on=0.5, hit=0.6, t_out=E(5)))
    film.add(BigText("MAATRUBHUMI", X2, 300, 1250, W(5, "बलिदान") - 0.15, rgb=BONE, hit=1.0))
    film.add(BigText("मातृभूमि", X2, 1300, 700, W(5, "परीक्षा") - 0.1, rgb=EMBER, grunge=True, shadow=True))
    film.add(BigText("MAY WAR REST IN PEACE", X2, 2100, 330, E(5) - 0.4, rgb=STEEL, type_on=0.9, track=0.12))
    film.add(Flash(X2, GROUND - 1200, W(5, "बलिदान") - 0.1, size=2600, gain=0.9, shake=22))

    cam(L(4) + 0.3, X2 - 300, -1200, 0.62, 0.4)
    cam(E(4), X2, -1100, 0.6, 0.0)
    cam(W(5, "बलिदान") + 0.1, X2, 500, 0.5, 0.0)
    cam(E(5) + 0.8, X2, 900, 0.44, -0.3)
    foc(L(4) + 0.2, X2, -1300, 3000, 0.5)
    foc(W(5, "बलिदान"), X2, 700, 4300, 0.42)

    # ============================================================ S3 THE WORLD OF WAR (6-8)
    MAPX, MAPY = X3, -900
    film.add(TacticalMap(MAPX, MAPY, 9800, 5600, L(6) - 0.2))
    a, b, cc = (MAPX - 3800, MAPY + 1800), (MAPX - 300, MAPY - 600), (MAPX + 3600, MAPY - 1700)
    film.add(Route(a, b, t_in=W(6, "रक्षा") - 0.2, dur=1.1, bend=0.2, width=40, rgb=(214, 196, 120)))
    film.add(Route(b, cc, t_in=W(6, "जवान"), dur=1.0, bend=-0.25, width=40, rgb=(214, 196, 120)))
    film.add(Convoy(MAPX - 5200, GROUND - 60, 5, 520, L(6), vx=380))
    film.add(Helicopter(MAPX - 9000, MAPX + 9000, -4200, 900, L(6) + 0.6, 7.5))
    cards = []
    for k, (word, hindi) in enumerate((("बेटे", "बेटा"), ("भाई", "भाई"), ("पति", "पति"))):
        x = MAPX - 3300 + k * 3300
        cards.append(film.add(Stamp(hindi, x, MAPY + 600, size=560, rot=(-6, 4, -3)[k], t_in=W(7, word) - 0.1, rgb=BONE)))
    film.add(PenMark("ellipse", MAPX, MAPY + 600, 10600, 2600, t_in=W(8, "परिवार") - 0.2, dur=0.7, width=30, seed=8, rgb=EMBER))
    film.add(BigText("उम्मीद", MAPX, MAPY + 2700, 600, W(8, "उम्मीद") - 0.1, rgb=EMBER, hit=0.5))

    cam(L(6) - 0.4, MAPX - 3000, MAPY + 300, 0.3, 0.0)                     # fly in over the map
    cam(W(6, "जवान") + 0.3, MAPX - 500, MAPY - 300, 0.36, 0.3)
    cam(E(6), MAPX, MAPY + 200, 0.34, 0.0)
    cam(W(7, "बेटे") + 0.2, MAPX - 3300, MAPY + 600, 0.66, -0.4)
    cam(W(7, "भाई") + 0.2, MAPX, MAPY + 600, 0.66, 0.3)
    cam(W(7, "पति") + 0.2, MAPX + 3300, MAPY + 600, 0.66, -0.2)
    cam(L(8) + 0.3, MAPX, MAPY + 1200, 0.38, 0.0)
    cam(E(8) + 0.5, MAPX, MAPY + 1500, 0.36, 0.0)
    foc(L(6) - 0.3, MAPX, MAPY, 9000, 0.25)
    foc(W(7, "बेटे"), MAPX - 3300, MAPY + 600, 1700, 0.55)
    foc(W(7, "भाई"), MAPX, MAPY + 600, 1700, 0.55)
    foc(W(7, "पति"), MAPX + 3300, MAPY + 600, 1700, 0.55)
    foc(L(8) + 0.2, MAPX, MAPY + 1200, 6500, 0.35)

    # ============================================================ S4 CAST (9-10)
    cue("riser", L(9) - 1.0, 0.4, dur=0.9)
    film.add(BigText("SALMAN KHAN", X4, -1500, 560, W(9, "सलमान") - 0.1, rgb=BONE, rules=True, hit=0.7, t_out=E(10) + 0.5))
    film.add(BigText("&", X4, -800, 300, W(9, "साथ") - 0.1, rgb=STEEL, grunge=False, t_out=E(10) + 0.5))
    film.add(BigText("CHITRANGDA SINGH", X4, -100, 560, W(9, "चित्रांगदा") - 0.1, rgb=BONE, rules=True, hit=0.7, t_out=E(10) + 0.5))
    film.add(Helicopter(X4 + 9000, X4 - 9000, 1100, 1300, L(10) - 0.2, 6.0))
    film.add(Helicopter(X4 + 11000, X4 - 7000, 600, 800, L(10) + 0.4, 6.2))
    film.add(BigText("ज़िंदगी", X4 - 1700, 1800, 620, W(10, "ज़िंदगी") - 0.1, rgb=BONE, hit=0.5))
    film.add(SplitLine(X4, 1550, 1400, W(10, "और") - 0.05))
    film.add(BigText("मौत", X4 + 1500, 1800, 620, W(10, "मौत") - 0.1, rgb=BLOOD, hit=0.7))

    cam(L(9) + 0.3, X4, -1100, 0.5, 0.3)
    cam(E(9) + 0.2, X4, -900, 0.47, 0.0)
    cam(L(10) + 0.8, X4, 700, 0.42, 0.0)
    cam(W(10, "ज़िंदगी") + 0.2, X4 - 300, 1500, 0.55, -0.3)
    cam(E(10) + 0.4, X4, 1500, 0.52, 0.0)
    foc(L(9) + 0.2, X4, -900, 4200, 0.45)
    foc(W(10, "ज़िंदगी"), X4, 1600, 3200, 0.5)

    # ============================================================ S5 THE COST (11-13)
    film.add(Frame(X5 - 2300, -400, 2300, 2900, L(11) + 0.15))
    letter = film.add(PaperDoc(X5 + 1700, -300, 2500, 3200, rot=2.0, t_in=L(12) + 0.1, rows=15,
                               header=(("घर से चिट्ठी", 170, "cond"), ("· · ·", 70, "mono"))))
    film.add(BigText("असली वीरता", X5, 2350, 720, W(13, "वीरता") - 0.15, rgb=BONE, bar=HILITE, bar_h=0.5, hit=0.6))
    film.add(Soldier(X5 + 5200, 1900, L(11), "stand", flip=True, rim_a=0.45))
    cue("heartbeat", L(11) + 0.2, 0.45); cue("heartbeat", L(11) + 1.15, 0.4)

    cam(L(11) + 0.2, X5 - 2300, -400, 0.62, -0.5)
    cam(E(11) + 0.1, X5 - 2200, -300, 0.68, -0.2)
    cam(L(12) + 0.6, X5 + 1600, -300, 0.66, 0.6)
    cam(E(12), X5 + 1700, -100, 0.7, 0.8)
    cam(W(13, "वीरता") + 0.2, X5, 1900, 0.5, 0.0)
    cam(E(13) + 0.6, X5, 1300, 0.4, 0.0)
    foc(L(11), X5 - 2300, -400, 1900, 0.62)
    foc(L(12) + 0.5, X5 + 1700, -300, 2000, 0.6)
    foc(W(13, "वीरता"), X5, 1700, 4200, 0.4)

    # ============================================================ S6 CLIMAX (14-15)
    cue("riser", L(14) - 1.3, 0.7, dur=1.2)
    film.add(Embers(X6 - 8000, X6 + 9000, -2500, GROUND, L(14) - 0.5, t_out=L(16) + 1))
    for k in range(8):
        film.add(Soldier(X6 - 4200 - k * 950, 1750 - (k % 3) * 180, L(14) - 0.6, "run", vx=950, t_out=E(15) - 0.3, rim_a=0.8))
    for k, (dx, w) in enumerate(((-3000, "बात"), (2500, "मातृभूमि"), (-500, "हौसले"), (3800, "पीछे"))):
        film.add(Flash(X6 + dx, GROUND - 1400 - 300 * (k % 2), W(14, w) - 0.1, size=2000 + 300 * k, gain=0.8, shake=20))
    film.add(BigText("मातृभूमि", X6, -1200, 1050, W(14, "मातृभूमि") - 0.1, rgb=EMBER, hit=1.0, t_out=L(15) + 1.2))
    film.add(Helicopter(X6 - 9000, X6 + 9000, -3200, 1100, L(14) + 0.5, 4.5))
    flag = film.add(Tricolour(X6 + 5200, GROUND - 400, 2400, L(15) + 0.2, rise=3.2, pole_h=5200))

    cam(L(14) - 0.6, X6 - 4500, GROUND - 1300, 0.42, 1.0)                  # fast in with the runners
    cam(W(14, "मातृभूमि") - 0.1, X6 - 600, -600, 0.4, -0.6)
    cam(W(14, "हौसले"), X6 - 400, GROUND - 1300, 0.46, 0.8)
    cam(E(14) + 0.1, X6 + 1500, -200, 0.38, 0.0)
    cam(L(15) + 0.8, X6 + 6100, -900, 0.34, 0.0)                            # the flag
    cam(E(15) + 0.4, X6 + 6400, -1500, 0.4, -0.3)
    foc(L(14) - 0.5, X6 - 3000, GROUND - 1200, 5000, 0.3)
    foc(L(15) + 0.6, X6 + 6400, -1400, 4500, 0.35)

    # ============================================================ S7 TITLE CARD (16-18)
    cue("boom", W(16, "मातृभूमि") - 0.1, 1.0)
    film.add(BigText("MAATRUBHUMI", X7, -900, 1050, W(16, "मातृभूमि") - 0.1, rgb=BONE, hit=1.0))
    film.add(BigText("MAY WAR REST IN PEACE", X7, 0, 380, W(16, "मातृभूमि") + 0.6, rgb=EMBER, type_on=0.8, track=0.12, grunge=False))
    film.add(Stamp("IN CINEMAS · 4 DECEMBER 2026", X7, 1100, size=300, rot=-3, t_in=W(17, "चार") - 0.05, rgb=BONE))
    film.add(BigText("JAI HIND!", X7, 2500, 700, W(18, "देश") - 0.1, rgb=SAFFRON, hit=1.0))
    film.add(Flash(X7, GROUND - 900, W(18, "देश") - 0.1, size=3000, gain=1.0, shake=26))

    cam(L(16) - 0.5, X7 - 300, -600, 0.46, 0.6)
    cam(E(16) + 0.4, X7, -500, 0.52, 0.0)
    cam(W(17, "चार") + 0.3, X7, 600, 0.48, 0.0)
    cam(W(18, "देश"), X7, 900, 0.4, 0.0)
    cam(film.duration, X7, 700, 0.36, 0.0)
    foc(L(16) - 0.4, X7, -600, 5000, 0.4)
    foc(W(18, "देश"), X7, 800, 7000, 0.3)

    film.fade_in, film.fade_out = 1.4, 2.4
    return film
