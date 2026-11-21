#!/usr/bin/env python3
"""Velmara — a travel poster for a place that isn't there.

Pure Python 3.13 standard library, no network, no third-party packages.
Draws a 1024x1024 travel poster for Velmara, a floating archipelago
above a sea of clouds, and writes it to /output/entry.png.

The poster's invented place: VELMARA, the Floating Isles — a chain of
islands that drift above the clouds, reached only by sky-ferry, where a
lighthouse keeps watch over waterfalls that fall into the sky.
"""
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def _idx(x, y):
    return (y * W + x) * 3


def put(x, y, rgb):
    if 0 <= x < W and 0 <= y < H:
        i = _idx(x, y)
        buf[i], buf[i + 1], buf[i + 2] = rgb


def get(x, y):
    x = min(max(x, 0), W - 1)
    y = min(max(y, 0), H - 1)
    i = _idx(x, y)
    return buf[i], buf[i + 1], buf[i + 2]


def blend(x, y, rgb, a):
    """Blend rgb over the pixel at (x, y) with alpha a (0..1)."""
    if 0 <= x < W and 0 <= y < H and a > 0:
        i = _idx(x, y)
        buf[i] = int(buf[i] + (rgb[0] - buf[i]) * a)
        buf[i + 1] = int(buf[i + 1] + (rgb[1] - buf[i + 1]) * a)
        buf[i + 2] = int(buf[i + 2] + (rgb[2] - buf[i + 2]) * a)


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def fill_rect(x0, y0, x1, y1, rgb):
    x0 = max(x0, 0); y0 = max(y0, 0)
    x1 = min(x1, W); y1 = min(y1, H)
    for y in range(y0, y1):
        base = y * W * 3
        for x in range(x0, x1):
            i = base + x * 3
            buf[i], buf[i + 1], buf[i + 2] = rgb


def disc(cx, cy, r, rgb, a=1.0):
    """Filled disc, optionally translucent, with a 1px soft edge."""
    r2 = r * r
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= r2:
                blend(x, y, rgb, a)
            elif d2 <= (r + 1) ** 2:
                blend(x, y, rgb, a * 0.4)


def ellipse(cx, cy, rx, ry, rgb, a=1.0):
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            v = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if v <= 1.0:
                blend(x, y, rgb, a)


def thick_line(x0, y0, x1, y1, w, rgb):
    """A line drawn as a chain of discs (round caps)."""
    dist = math.hypot(x1 - x0, y1 - y0)
    steps = max(int(dist / max(w * 0.4, 1)), 1)
    r = w / 2.0
    for s in range(steps + 1):
        t = s / steps
        disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r, rgb)


def fill_poly(points, rgb, a=1.0):
    """Scanline fill of a simple polygon (list of (x, y))."""
    ys = [p[1] for p in points]
    y0, y1 = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(max(y0, 0), min(y1, H - 1) + 1):
        xs = []
        for i in range(n):
            x0, ya = points[i]
            x1, yb = points[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                t = (y - ya) / (yb - ya)
                xs.append(x0 + (x1 - x0) * t)
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                if a >= 1.0:
                    put(x, y, rgb)
                else:
                    blend(x, y, rgb, a)


def vgrad(stops):
    """Vertical gradient; stops = [(y_fraction, rgb), ...] sorted by y."""
    for y in range(H):
        t = y / (H - 1)
        for i in range(len(stops) - 1):
            y0, c0 = stops[i]
            y1, c1 = stops[i + 1]
            if y0 <= t <= y1:
                f = 0.0 if y1 == y0 else (t - y0) / (y1 - y0)
                rgb = mix(c0, c1, f)
                break
        else:
            rgb = stops[-1][1]
        for x in range(W):
            i = _idx(x, y)
            buf[i], buf[i + 1], buf[i + 2] = rgb


# ---------------------------------------------------------------- PNG out
def write_png(path, width, height, data):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(data[y * stride:(y + 1) * stride])

    def chunk(tag, payload):
        c = struct.pack(">I", len(payload)) + tag + payload
        return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------------------------ type
# Single-stroke vector capitals on a 4-wide x 7-tall grid, y down.
GLYPHS = {
    "A": [[(0, 7), (2, 0), (4, 7)], [(1, 4.5), (3, 4.5)]],
    "E": [[(4, 0), (0, 0), (0, 7), (4, 7)], [(0, 3.5), (3, 3.5)]],
    "F": [[(0, 7), (0, 0), (4, 0)], [(0, 3.5), (3, 3.5)]],
    "G": [[(4, 1.5), (3, 0), (1, 0), (0, 1.5), (0, 5.5), (1, 7),
           (3, 7), (4, 5.5), (4, 3.5), (2.5, 3.5)]],
    "H": [[(0, 0), (0, 7)], [(4, 0), (4, 7)], [(0, 3.5), (4, 3.5)]],
    "I": [[(2, 0), (2, 7)], [(0.5, 0), (3.5, 0)], [(0.5, 7), (3.5, 7)]],
    "L": [[(0, 0), (0, 7), (4, 7)]],
    "M": [[(0, 7), (0, 0), (2, 3.5), (4, 0), (4, 7)]],
    "N": [[(0, 7), (0, 0), (4, 7), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1.5), (4, 5.5), (3, 7), (1, 7),
           (0, 5.5), (0, 1.5), (1, 0)]],
    "R": [[(0, 7), (0, 0), (3, 0), (4, 1), (4, 2.5), (3, 3.5), (0, 3.5)],
          [(2.5, 3.5), (4, 7)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2.5), (1, 3.5),
           (3, 3.5), (4, 4.5), (4, 6), (3, 7), (1, 7), (0, 6)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 7)]],
    "V": [[(0, 0), (2, 7), (4, 0)]],
}


def text_width(text, height, gap_ratio=0.35):
    sc = height / 7.0
    cw = 4 * sc
    gap = cw * gap_ratio
    return len(text) * cw + (len(text) - 1) * gap


def draw_text(text, cx, top, height, rgb, stroke):
    """Draw centred text; returns (left, top, width, height)."""
    sc = height / 7.0
    cw = 4 * sc
    gap = cw * 0.35
    total = text_width(text, height)
    x = cx - total / 2.0
    for ch in text:
        for stroke_pts in GLYPHS.get(ch, []):
            for i in range(len(stroke_pts) - 1):
                x0, y0 = stroke_pts[i]
                x1, y1 = stroke_pts[i + 1]
                thick_line(x + x0 * sc, top + y0 * sc,
                           x + x1 * sc, top + y1 * sc, stroke, rgb)
        x += cw + gap
    return cx - total / 2.0, top, total, height

# ------------------------------------------------------------------ scene
INK = (42, 18, 48)          # deep plum, for type shadow and birds
CREAM = (255, 243, 214)
GOLD = (247, 183, 51)


def cloud(x, y, rx, ry, light, shade):
    ellipse(x, y + ry * 0.35, rx, ry * 0.7, shade, 0.9)
    ellipse(x, y, rx, ry, light, 1.0)
    ellipse(x - rx * 0.45, y - ry * 0.25, rx * 0.55, ry * 0.6, light, 1.0)
    ellipse(x + rx * 0.45, y - ry * 0.2, rx * 0.5, ry * 0.55, light, 1.0)


def pine(x, y, s, rgb):
    fill_poly([(x, y - 3.2 * s), (x - 1.6 * s, y), (x + 1.6 * s, y)], rgb)
    fill_poly([(x, y - 2.2 * s), (x - 1.4 * s, y + 1.2 * s),
               (x + 1.4 * s, y + 1.2 * s)], rgb)
    fill_poly([(x, y - 1.2 * s), (x - 1.2 * s, y + 2.2 * s),
               (x + 1.2 * s, y + 2.2 * s)], rgb)
    fill_rect(int(x - 0.25 * s), int(y + 2.2 * s), int(x + 0.25 * s),
              int(y + 3.2 * s), (90, 55, 40))


def house(x, y, s):
    fill_rect(int(x - 1.6 * s), int(y), int(x + 1.6 * s), int(y + 2.2 * s),
              (245, 234, 214))
    fill_poly([(x - 2.0 * s, y), (x, y - 1.6 * s), (x + 2.0 * s, y)],
              (192, 57, 43))
    fill_rect(int(x - 0.7 * s), int(y + 0.9 * s), int(x + 0.7 * s),
              int(y + 2.2 * s), (60, 35, 55))
    disc(x - 0.9 * s, y + 0.7 * s, 0.28 * s, (255, 215, 106))
    disc(x + 0.9 * s, y + 0.7 * s, 0.28 * s, (255, 215, 106))


def waterfall(x0, y0, x1, y1, w):
    steps = 24
    pts = []
    for s in range(steps + 1):
        t = s / steps
        pts.append((x0 + (x1 - x0) * t + math.sin(t * 9.0) * 4,
                    y0 + (y1 - y0) * t))
    for i in range(len(pts) - 1):
        thick_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                   w, (207, 232, 255))
        thick_line(pts[i][0] - w * 0.22, pts[i][1],
                   pts[i + 1][0] - w * 0.22, pts[i + 1][1],
                   w * 0.3, (255, 255, 255))


def island(cx, top_y, half_w, depth, grass, rock, dark):
    """Floating island: grassy plateau on top, rocky cone below."""
    fill_poly([(cx - half_w, top_y), (cx - half_w * 0.82, top_y - 26),
               (cx + half_w * 0.82, top_y - 26), (cx + half_w, top_y),
               (cx + half_w * 0.55, top_y + depth * 0.55),
               (cx, top_y + depth),
               (cx - half_w * 0.55, top_y + depth * 0.55)], rock)
    # cliff shading on the right half
    fill_poly([(cx, top_y - 10), (cx + half_w * 0.82, top_y - 26),
               (cx + half_w, top_y), (cx + half_w * 0.55, top_y + depth * 0.55),
               (cx, top_y + depth)], dark)
    ellipse(cx, top_y - 22, half_w * 0.86, 30, grass, 1.0)
    ellipse(cx - half_w * 0.3, top_y - 26, half_w * 0.4, 22, (87, 167, 115), 1.0)


def bird(x, y, s):
    thick_line(x - s, y, x, y - s * 0.55, 4, INK)
    thick_line(x, y - s * 0.55, x + s, y, 4, INK)


def draw():
    # --- sky: dusk gradient, indigo to gold
    vgrad([(0.00, (36, 20, 69)), (0.30, (94, 42, 102)),
           (0.52, (198, 90, 74)), (0.68, (240, 138, 60)),
           (0.82, (247, 183, 51)), (1.00, (250, 205, 110))])
    # --- stars fading into the dusk
    for i in range(46):
        sx = int((math.sin(i * 12.9898) * 43758.5453 % 1.0) * W)
        sy = int((math.sin(i * 78.233) * 12543.1234 % 1.0) * 300) + 20
        a = 0.25 + 0.55 * ((i * 37) % 10) / 10.0
        disc(sx, sy, 2 if i % 5 else 3, (255, 240, 200), a)
    # --- sun and its glow, low over the cloud sea, left of the main isle.
    # Forty fine steps (~0.25% brightness each) so the falloff is smooth
    # with no visible ring edges against the gradient.
    for i in range(40):
        disc(300, 640, 260 - i * 4, (255, 180, 110), 0.0025)
    disc(300, 640, 92, (255, 226, 158), 1.0)
    disc(300, 640, 76, (255, 240, 190), 1.0)
    # --- distant islets, hazy in the sunset
    island(185, 470, 95, 95, (122, 90, 130), (110, 70, 118), (88, 55, 98))
    island(845, 430, 78, 80, (122, 90, 130), (110, 70, 118), (88, 55, 98))
    # --- sea of clouds, back layer
    for (cx, cy, rx, ry) in [(120, 850, 200, 70), (420, 880, 260, 80),
                             (760, 860, 240, 75), (980, 900, 200, 70)]:
        cloud(cx, cy, rx, ry, (255, 233, 196), (232, 176, 107))
    # --- main island
    island(512, 560, 212, 175, (63, 143, 102), (110, 58, 86), (74, 38, 66))
    # --- waterfalls spilling off the main island into the clouds
    waterfall(348, 575, 338, 830, 16)
    waterfall(676, 575, 688, 830, 14)
    waterfall(185, 480, 180, 700, 10)
    # --- lighthouse on the main island, beam sweeping right
    fill_poly([(620, 470), (652, 470), (656, 545), (616, 545)], CREAM)
    fill_rect(614, 452, 658, 472, (192, 57, 43))
    disc(636, 448, 12, (192, 57, 43))
    disc(636, 462, 7, (255, 220, 120))
    # translucent beam so the islet and sky behind it stay visible
    fill_poly([(636, 462), (920, 428), (920, 496)], (255, 220, 120), 0.38)
    for (bx, by, br, ba) in [(700, 452, 60, 0.08), (790, 450, 45, 0.06)]:
        disc(bx, by, br, (255, 220, 120), ba)
    # --- cottages and pines on the main island
    house(430, 505, 11)
    house(500, 498, 9)
    pine(360, 520, 9, (30, 92, 67))
    pine(585, 512, 8, (30, 92, 67))
    pine(700, 522, 9, (30, 92, 67))
    pine(185, 440, 8, (74, 58, 86))
    pine(845, 400, 7, (74, 58, 86))
    # --- cloud sea, front layer, lapping at the island bases.
    # Two passes: all shade ellipses first, then all light ones, so no
    # dark shade sliver can peek through a gap between the puffs.
    banks = [(60, 960, 220, 80), (330, 990, 280, 85),
             (640, 970, 260, 80), (930, 990, 240, 85),
             (512, 1010, 320, 70),
             # mid bank: plugs the gap where a back cloud's shade sliver
             # showed between the back layer's bottom and this layer's top
             (540, 940, 180, 60)]
    for (cx, cy, rx, ry) in banks:
        ellipse(cx, cy + ry * 0.35, rx, ry * 0.7, (226, 164, 96), 0.9)
    for (cx, cy, rx, ry) in banks:
        ellipse(cx, cy, rx, ry, (255, 240, 210), 1.0)
        ellipse(cx - rx * 0.45, cy - ry * 0.25, rx * 0.55, ry * 0.6,
                (255, 240, 210), 1.0)
        ellipse(cx + rx * 0.45, cy - ry * 0.2, rx * 0.5, ry * 0.55,
                (255, 240, 210), 1.0)
        for k in range(-2, 3):
            disc(cx + k * rx * 0.32, cy - ry * 0.5 + (k % 2) * 6,
                 ry * 0.55, (255, 244, 218), 1.0)
    # --- birds
    bird(300, 300, 14)
    bird(360, 258, 11)
    bird(712, 282, 12)
    bird(760, 240, 9)
    # --- the place name, set large into the picture
    draw_text("VELMARA", 512 + 5, 96 + 6, 112, INK, 13)
    draw_text("VELMARA", 512, 96, 112, CREAM, 13)
    draw_text("THE FLOATING ISLES", 512 + 2, 228 + 3, 34, INK, 5)
    draw_text("THE FLOATING ISLES", 512, 228, 34, (255, 233, 196), 5)
    # --- poster frame
    for (inset, w, a) in [(26, 6, 0.85), (42, 2, 0.5)]:
        c = CREAM
        for x in range(inset, W - inset):
            blend(x, inset, c, a)
            blend(x, H - 1 - inset, c, a)
        for y in range(inset, H - inset):
            blend(inset, y, c, a)
            blend(W - 1 - inset, y, c, a)


def main():
    draw()
    os.makedirs("/output", exist_ok=True)
    n = write_png("/output/entry.png", W, H, buf)
    print(f"wrote /output/entry.png: {n} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
