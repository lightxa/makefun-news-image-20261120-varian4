#!/usr/bin/env python3
"""news-image-20261120 variant 4: an evening TV news bulletin frame.

One image summing up the world news of Friday 20 November 2026, drawn
procedurally with pure stdlib Python. Writes /output/entry.png.
Concept: WORLD NEWS TONIGHT, red LIVE badge, a big date strip, one
dominant lead story (Russian missiles land in Poland), two side stories
(ICJ genocide ruling, markets slide), a three-story bottom row (Riyadh
PIF Tower strike, Peru earthquake, BepiColombo at Mercury) and a ticker.
Deterministic, no network at runtime.
"""
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
NAVY = (13, 27, 62)
NAVY2 = (24, 48, 96)
RED = (198, 28, 40)
RED_DK = (150, 18, 28)
WHITE = (255, 255, 255)
PAPER = (240, 241, 245)
INK = (16, 18, 24)
GREY = (96, 102, 116)
MIDGREY = (200, 205, 214)
GOLD = (232, 178, 32)
BLUE = (38, 92, 180)
SKY = (176, 208, 240)
GREEN = (28, 140, 70)
ORANGE = (228, 110, 20)
TEAL = (18, 130, 130)
SAND = (238, 222, 180)
DARK = (10, 12, 20)


class Canvas:
    """A plain RGB pixel buffer with small shape helpers."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)
        self.rect(0, 0, w, h, bg)

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i], self.buf[i + 1], self.buf[i + 2] = c

    def frame(self, x, y, w, h, c, t=2):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s // steps
            y = y0 + (y1 - y0) * s // steps
            for ox in range(-t // 2, t // 2 + 1):
                for oy in range(-t // 2, t // 2 + 1):
                    self.px(x + ox, y + oy, c)

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            span = int(math.sqrt(max(0, r * r - dy * dy)))
            for xx in range(cx - span, cx + span + 1):
                self.px(xx, yy, c)

    def ring(self, cx, cy, r, c, t=3):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d = math.hypot(xx - cx, yy - cy)
                if r - t <= d <= r + t * 0.5:
                    self.px(xx, yy, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for yy in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    xs.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for xx in range(int(math.ceil(xs[k])), int(xs[k + 1]) + 1):
                    self.px(xx, yy, c)

    def tri(self, x0, y0, x1, y1, x2, y2, c):
        self.poly([(x0, y0), (x1, y1), (x2, y2)], c)

    def arc(self, cx, cy, r, a0, a1, c, t=4):
        a = a0
        while a <= a1:
            rad = math.radians(a)
            x = int(cx + r * math.cos(rad))
            y = int(cy + r * math.sin(rad))
            for ox in range(-t // 2, t // 2 + 1):
                for oy in range(-t // 2, t // 2 + 1):
                    self.px(x + ox, y + oy, c)
            a += 3

    def star(self, cx, cy, r_out, r_in, c):
        pts = []
        for i in range(10):
            r = r_out if i % 2 == 0 else r_in
            ang = math.radians(-90 + i * 36)
            pts.append((int(cx + r * math.cos(ang)),
                        int(cy + r * math.sin(ang))))
        self.poly(pts, c)


# ------------------------------------------------------------- bitmap font
# 5x7 glyphs, each row a 5-bit integer (bit 4 = leftmost column).
G = {
    "A": (14, 17, 17, 31, 17, 17, 17), "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14), "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31), "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15), "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14), "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17), "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17), "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14), "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13), "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30), "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14), "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17), "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4), "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14), "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31), "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2), "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14), "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14), "9": (14, 17, 17, 15, 1, 2, 12),
    " ": (0, 0, 0, 0, 0, 0, 0), ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 4, 8), ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 12, 0, 12, 4, 8), "'": (4, 4, 8, 0, 0, 0, 0),
    '"': (10, 10, 0, 0, 0, 0, 0), "-": (0, 0, 0, 14, 0, 0, 0),
    "/": (1, 2, 2, 4, 8, 8, 16), "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8), "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 6, 4, 0, 4), "&": (12, 18, 20, 8, 21, 18, 13),
    "$": (4, 15, 20, 14, 5, 30, 4), "%": (25, 26, 2, 4, 8, 11, 19),
    "+": (0, 4, 4, 14, 4, 4, 0), "=": (0, 0, 31, 0, 31, 0, 0),
    "*": (0, 21, 14, 21, 0, 0, 0), "_": (0, 0, 0, 0, 0, 0, 31),
    "#": (10, 10, 31, 10, 31, 10, 10), "@": (14, 17, 23, 21, 22, 16, 14),
    "<": (2, 4, 8, 16, 8, 4, 2), ">": (8, 4, 2, 1, 2, 4, 8),
    "[": (14, 8, 8, 8, 8, 8, 14), "]": (14, 2, 2, 2, 2, 2, 14),
    "|": (4, 4, 4, 4, 4, 4, 4),
}


def text_w(s, sc):
    return len(s) * 6 * sc - sc


def draw_text(cv, s, x, y, sc, c):
    cx = x
    for ch in s.upper():
        rows = G.get(ch, G[" "])
        for r in range(7):
            bits = rows[r]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    cv.rect(cx + col * sc, y + r * sc, sc, sc, c)
        cx += 6 * sc
    return cx


def text_centred(cv, s, cx, y, sc, c):
    draw_text(cv, s, cx - text_w(s, sc) // 2, y, sc, c)


def wrap(s, sc, max_w):
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_w(trial, sc) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(cv, s, x, y, sc, c, max_w, gap=4):
    yy = y
    for ln in wrap(s, sc, max_w):
        draw_text(cv, ln, x, yy, sc, c)
        yy += 7 * sc + gap
    return yy


# ------------------------------------------------------------------ PNG out
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(cv, path):
    raw = bytearray()
    for yy in range(cv.h):
        raw.append(0)
        start = yy * cv.w * 3
        raw += cv.buf[start:start + cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += _chunk(b"IHDR", ihdr)
    data += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    data += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# -------------------------------------------------------------- pictograms
def pic_missile(cv, x, y):
    # A missile streaking down at an angle, NATO jets above, impact star.
    cv.rect(x, y, 260, 190, SKY)
    cv.rect(x, y + 150, 260, 40, (120, 160, 110))
    cv.line(x, y + 150, x + 260, y + 150, INK, 3)
    # Trail dashes.
    for i in range(6):
        cv.disc(x + 40 + i * 22, y + 30 + i * 14, 4, WHITE)
    # Missile body, nose pointing down-right.
    cv.poly([(x + 150, y + 78), (x + 176, y + 96), (x + 164, y + 118),
             (x + 138, y + 100)], RED)
    cv.tri(x + 176, y + 96, x + 192, y + 88, x + 188, y + 108, INK)
    cv.tri(x + 138, y + 100, x + 122, y + 92, x + 128, y + 112, RED_DK)
    # Impact star where it lands.
    cv.star(x + 205, y + 148, 26, 10, GOLD)
    cv.star(x + 205, y + 148, 12, 5, RED)
    # Two jets scrambled above.
    for jx in (x + 30, x + 78):
        cv.tri(jx, y + 168, jx + 34, y + 176, jx, y + 184, NAVY)
        cv.rect(jx + 30, y + 172, 14, 6, NAVY)


def pic_scales(cv, x, y):
    # Scales of justice: post, beam, two pans. Compact, ~90x84.
    cv.line(x + 45, y + 6, x + 45, y + 78, INK, 5)
    cv.line(x + 8, y + 14, x + 82, y + 14, INK, 5)
    cv.disc(x + 45, y + 6, 6, GOLD)
    for px in (x + 12, x + 78):
        cv.line(px, y + 14, px, y + 44, INK, 3)
        cv.tri(px - 20, y + 44, px + 20, y + 44, px, y + 68, GOLD)
        cv.line(px - 20, y + 44, px + 20, y + 44, INK, 3)
    cv.rect(x + 24, y + 78, 42, 7, INK)


def pic_chart(cv, x, y):
    # A market line falling hard, with a red down arrow. Compact, ~100x84.
    cv.line(x + 6, y + 6, x + 6, y + 78, GREY, 2)
    cv.line(x + 6, y + 78, x + 100, y + 78, GREY, 2)
    pts = [(x + 10, y + 14), (x + 28, y + 24), (x + 46, y + 20),
           (x + 62, y + 44), (x + 78, y + 60), (x + 96, y + 74)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 5)
    cv.tri(x + 96, y + 74, x + 82, y + 68, x + 90, y + 58, RED)
    for bx, bh in ((14, 18), (32, 12), (50, 24), (68, 36)):
        cv.rect(x + bx, y + 78 - bh, 12, bh, (190, 60, 70))


def pic_tower(cv, x, y):
    # Riyadh's PIF Tower: tall twisted tower, broken windows, smoke.
    cv.rect(x, y, 190, 150, (210, 222, 238))
    cv.poly([(x + 55, y + 6), (x + 95, y + 6), (x + 105, y + 150),
             (x + 45, y + 150)], NAVY2)
    cv.poly([(x + 95, y + 6), (x + 135, y + 6), (x + 145, y + 150),
             (x + 105, y + 150)], (120, 140, 180))
    for wy in range(24, 140, 18):
        for wx in (62, 82, 102, 122):
            cv.rect(x + wx, y + wy, 10, 8, INK)
    # Shattered band across the middle floors.
    cv.rect(x + 52, y + 66, 90, 14, RED)
    cv.disc(x + 30, y + 30, 12, GREY)
    cv.disc(x + 18, y + 48, 9, GREY)
    cv.disc(x + 160, y + 22, 10, GREY)


def pic_quake(cv, x, y):
    # Seismograph zigzag over cracked ground, big 6.7.
    cv.rect(x, y, 190, 150, SAND)
    cv.line(x, y + 118, x + 190, y + 118, INK, 3)
    cv.line(x + 30, y + 118, x + 52, y + 138, INK, 3)
    cv.line(x + 52, y + 138, x + 78, y + 126, INK, 3)
    cv.line(x + 120, y + 118, x + 140, y + 140, INK, 3)
    pts = [(x + 6, y + 72), (x + 30, y + 72), (x + 44, y + 42),
           (x + 58, y + 100), (x + 72, y + 54), (x + 86, y + 86),
           (x + 100, y + 72), (x + 124, y + 72), (x + 138, y + 38),
           (x + 152, y + 104), (x + 166, y + 72), (x + 186, y + 72)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 4)
    draw_text(cv, "6.7", x + 8, y + 8, 3, RED)


def pic_mercury(cv, x, y):
    # Cratered Mercury, a small probe, and its dashed orbit.
    cv.rect(x, y, 190, 150, (16, 16, 32))
    cv.disc(x + 60, y + 34, 12, GOLD)
    cv.arc(x + 95, y + 82, 62, 200, 340, WHITE, 3)
    cv.disc(x + 95, y + 82, 48, (176, 164, 148))
    cv.disc(x + 78, y + 66, 9, (140, 128, 112))
    cv.disc(x + 112, y + 78, 12, (140, 128, 112))
    cv.disc(x + 92, y + 102, 7, (140, 128, 112))
    cv.disc(x + 118, y + 52, 5, (140, 128, 112))
    # Probe with solar panels.
    cv.rect(x + 148, y + 30, 18, 14, GOLD)
    cv.rect(x + 130, y + 34, 16, 6, BLUE)
    cv.rect(x + 168, y + 34, 16, 6, BLUE)
    for sx, sy in ((30, 120), (170, 120), (150, 140), (60, 140)):
        cv.disc(x + sx, y + sy, 2, WHITE)


# ------------------------------------------------------------------ layout
def side_panel(cv, x, y, w, h, tag, headline, sub, pic, tint):
    cv.rect(x, y, w, h, tint)
    cv.frame(x, y, w, h, NAVY, 2)
    draw_text(cv, tag, x + 14, y + 12, 2, RED)
    pic(cv, x + 14, y + 34)
    tx = x + 122
    text_block(cv, headline, tx, y + 38, 2, INK, w - 136, gap=4)
    text_block(cv, sub, x + 14, y + 128, 2, GREY, w - 28, gap=3)


def bottom_panel(cv, x, y, w, h, tag, headline, sub, pic, tint):
    cv.rect(x, y, w, h, tint)
    cv.frame(x, y, w, h, NAVY, 2)
    draw_text(cv, tag, x + 14, y + 12, 2, RED)
    cv.rect(x + 14, y + 34, w - 28, 2, INK)
    pic(cv, x + (w - 190) // 2, y + 46)
    text_block(cv, headline, x + 14, y + 206, 2, INK, w - 28, gap=4)
    text_block(cv, sub, x + 14, y + 258, 2, GREY, w - 28, gap=3)


def main():
    cv = Canvas(W, H, PAPER)
    # Header: bulletin title + LIVE badge.
    cv.rect(0, 0, W, 92, NAVY)
    draw_text(cv, "WORLD NEWS TONIGHT", 24, 30, 5, WHITE)
    cv.rect(840, 24, 160, 44, RED)
    cv.disc(864, 46, 8, WHITE)
    draw_text(cv, "LIVE", 884, 30, 4, WHITE)
    # Date strip: the day, unmistakable.
    cv.rect(0, 92, W, 60, RED)
    text_centred(cv, "FRIDAY 20 NOVEMBER 2026", W // 2, 112, 5, WHITE)
    cv.rect(0, 152, W, 34, NAVY2)
    text_centred(cv, "SIX STORIES FROM AROUND THE WORLD",
                 W // 2, 162, 2, GOLD)
    # Lead story: missiles land in Poland.
    lx, ly, lw, lh = 24, 198, 600, 350
    cv.rect(lx, ly, lw, lh, WHITE)
    cv.frame(lx, ly, lw, lh, NAVY, 3)
    draw_text(cv, "LEAD STORY - EUROPE", lx + 16, ly + 14, 2, RED)
    draw_text(cv, "MISSILES LAND IN POLAND", lx + 16, ly + 42, 4, INK)
    text_block(cv, "NATO CALLS IT A GRAVE VIOLATION OF ITS AIRSPACE",
               lx + 16, ly + 82, 2, INK, lw - 32, gap=4)
    pic_missile(cv, lx + 16, ly + 128)
    fx = lx + 300
    draw_text(cv, "WHAT HAPPENED", fx, ly + 140, 2, RED)
    text_block(cv, "2 MISSILES AND A DRONE CAME DOWN IN POLAND. NO ONE WAS HURT. NATO JETS WERE SCRAMBLED.",
               fx, ly + 168, 2, INK, lw - 316, gap=5)
    draw_text(cv, "PM TUSK: AN INTENTIONAL", fx, ly + 288, 2, INK)
    draw_text(cv, "PROVOCATION", fx, ly + 308, 2, INK)
    # Side stories.
    side_panel(cv, 640, 198, 360, 169, "JUSTICE - THE HAGUE",
               "MYANMAR GUILTY OF GENOCIDE",
               "WORLD COURT RULES ON THE ROHINGYA",
               pic_scales, (232, 236, 222))
    side_panel(cv, 640, 379, 360, 169, "MARKETS - WORLDWIDE",
               "STOCKS SLIDE INTO CORRECTION",
               "S AND P DOWN 3.7%, NASDAQ DOWN 5.3%",
               pic_chart, (246, 220, 222))
    # Bottom row.
    by, bh = 564, 322
    bottom_panel(cv, 24, by, 314, bh, "MIDDLE EAST",
                 "MISSILE HITS RIYADH TOWER",
                 "PIF TOWER DAMAGED, NO ONE HURT",
                 pic_tower, (214, 228, 244))
    bottom_panel(cv, 355, by, 314, bh, "SOUTH AMERICA",
                 "QUAKE SHAKES CENTRAL PERU",
                 "MAGNITUDE 6.7 NEAR CARHUAMAYO",
                 pic_quake, (250, 238, 200))
    bottom_panel(cv, 686, by, 314, bh, "SPACE",
                 "PROBE REACHES MERCURY",
                 "8 YEARS, 6 BILLION MILES",
                 pic_mercury, (232, 232, 228))
    # Ticker + credit.
    cv.rect(0, 902, W, 122, NAVY)
    text_centred(cv, "MISSILES IN POLAND - MYANMAR GUILTY - MARKETS DOWN 3.7%",
                 W // 2, 916, 2, WHITE)
    text_centred(cv, "RIYADH TOWER HIT - PERU QUAKE 6.7 - MERCURY REACHED",
                 W // 2, 940, 2, GOLD)
    text_centred(cv, "ALL STORIES FIRST REPORTED FRIDAY 20 NOVEMBER 2026",
                 W // 2, 972, 2, WHITE)
    text_centred(cv, "SOURCES: AP - REUTERS - BBC - CNN - NPR",
                 W // 2, 996, 2, GREY)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(cv, path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
