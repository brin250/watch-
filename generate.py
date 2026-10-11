#!/usr/bin/env python3
"""Generate watch-face layers for HUAWEI WATCH FIT 2 (336 x 480 AMOLED).

Recreates the "Phantom Blue" style: silver dial, large radiating blue Roman
numerals, a central capsule with steps arc, date window and a moon window,
and slim blue leaf-shaped hands.

Everything is drawn at SS x resolution and downsampled for anti-aliasing.
Run:  python3 generate.py      -> writes PNGs to ./output
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 336, 480          # Watch Fit 2 screen
SS = 4                   # supersampling factor
CX, CY = W / 2, H / 2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

BLUE = (30, 74, 138)
BLUE_DARK = (18, 46, 92)
BLUE_LIGHT = (86, 132, 196)
SILVER = (196, 202, 210)
GOLD = (232, 182, 76)
NAVY = (20, 36, 78)

FONT_SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

DIAL_RADIUS = 34                          # screen corner radius
CAPSULE = (CX - 62, CY - 148, CX + 62, CY + 148)  # central pill
ROMAN = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def s(v):
    """Scale a coordinate (or tuple) to supersampled space."""
    if isinstance(v, (tuple, list)):
        return type(v)(x * SS for x in v)
    return v * SS


def canvas(w=W, h=H, color=(0, 0, 0, 0)):
    return Image.new("RGBA", (w * SS, h * SS), color)


def finish(img, w=W, h=H):
    return img.resize((w, h), Image.LANCZOS)


def rounded_mask(w, h, r):
    m = Image.new("L", (int(s(w)), int(s(h))), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, s(w) - 1, s(h) - 1), s(r), fill=255)
    return m


def radial_gradient(w, h, inner, outer, cx=None, cy=None, scale=1.0):
    cx = s(w / 2 if cx is None else cx)
    cy = s(h / 2 if cy is None else cy)
    img = Image.new("RGBA", (s(w), s(h)))
    px = img.load()
    maxd = math.hypot(s(w) / 2, s(h) / 2) * scale
    for y in range(s(h)):
        for x in range(s(w)):
            t = min(1.0, math.hypot(x - cx, y - cy) / maxd)
            t = t * t
            px[x, y] = tuple(int(inner[i] + (outer[i] - inner[i]) * t) for i in range(3)) + (255,)
    return img


def edge_hit(theta, inset):
    """Distance from centre to the inset dial rectangle along angle theta (0 = 12 o'clock, clockwise)."""
    dx, dy = math.sin(theta), -math.cos(theta)
    a, b = W / 2 - inset, H / 2 - inset
    t = min(a / abs(dx) if abs(dx) > 1e-9 else 1e9, b / abs(dy) if abs(dy) > 1e-9 else 1e9)
    return dx, dy, t


def numeral_sprite(text, color, outline=None, stretch=2.45, size=44):
    """Render a Roman numeral, stretched vertically like the original's tall serif numerals."""
    font = ImageFont.truetype(FONT_SERIF, s(size))
    l, t, r, b = font.getbbox(text)
    pad = s(4)
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if outline:
        d.text((pad - l, pad - t), text, font=font, fill=(0, 0, 0, 0),
               stroke_width=s(1), stroke_fill=outline)
    else:
        d.text((pad - l, pad - t), text, font=font, fill=color)
    return img.resize((img.width, int(img.height * stretch)), Image.LANCZOS)


def draw_numerals(img, color, outline=None):
    for h, text in enumerate(ROMAN):
        theta = math.radians(h * 30)
        dx, dy, t = edge_hit(theta, 16)
        spr = numeral_sprite(text, color, outline)
        rot = spr.rotate(-h * 30, resample=Image.BICUBIC, expand=True)
        # place so the outer tip of the numeral sits at the rim
        half_len = spr.height / 2 / SS
        dist = t - half_len + 4
        px, py = CX + dx * dist, CY + dy * dist
        img.alpha_composite(rot, (int(s(px) - rot.width / 2), int(s(py) - rot.height / 2)))


def draw_ticks(d, color, minor=True):
    for m in range(60):
        theta = math.radians(m * 6)
        dx, dy, t = edge_hit(theta, 5)
        major = m % 5 == 0
        if not major and not minor:
            continue
        ln = 9 if major else 5
        wd = 2.2 if major else 1.0
        d.line([s((CX + dx * t, CY + dy * t)), s((CX + dx * (t - ln), CY + dy * (t - ln)))],
               fill=color, width=int(s(wd)))


def capsule_layer(dark=False):
    x0, y0, x1, y1 = (int(v) for v in CAPSULE)
    cw, ch = x1 - x0, y1 - y0
    r = cw / 2
    layer = canvas()
    # soft drop shadow
    sh = canvas()
    ImageDraw.Draw(sh).rounded_rectangle(s((x0, y0 + 3, x1, y1 + 3)), s(r), fill=(0, 0, 0, 70 if not dark else 0))
    layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(s(5))))
    if dark:
        fill = Image.new("RGBA", (s(cw), s(ch)), (0, 0, 0, 255))
    else:
        fill = radial_gradient(cw, ch, (252, 252, 253), (226, 230, 236), cy=ch * 0.35, scale=0.9)
    mask = rounded_mask(cw, ch, r)
    layer.paste(fill, (s(x0), s(y0)), mask)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(s((x0, y0, x1, y1)), s(r), outline=SILVER if not dark else (60, 70, 90),
                        width=s(2))
    d.rounded_rectangle(s((x0 + 3, y0 + 3, x1 - 3, y1 - 3)), s(r - 3),
                        outline=(255, 255, 255, 200) if not dark else (0, 0, 0, 0), width=s(1))
    return layer


STEPS_ARC = dict(box=(CX - 44, CY - 128, CX + 44, CY - 40), start=215, end=325)  # PIL degrees
DATE_BOX = (CX - 26, CY - 100, CX + 26, CY - 80)
MOON_BOX = (CX - 44, CY + 30, CX + 44, CY + 118)  # full circle box; upper half visible


def draw_steps_track(d, color, width=4):
    a = STEPS_ARC
    d.arc(s(a["box"]), a["start"], a["end"], fill=color, width=s(width))


def draw_moon_window(img):
    x0, y0, x1, y1 = MOON_BOX
    r = (x1 - x0) / 2
    mcx, mcy = (x0 + x1) / 2, (y0 + y1) / 2
    w = canvas()
    d = ImageDraw.Draw(w)
    # navy half-disc aperture (upper half)
    d.pieslice(s(MOON_BOX), 180, 360, fill=NAVY + (255,))
    # gold moon peeking from the left, shaded into a crescent by a navy disc
    moon_r = 15
    mx, my = mcx - 22, mcy - 13
    d.ellipse(s((mx - moon_r, my - moon_r, mx + moon_r, my + moon_r)), fill=GOLD + (255,))
    d.ellipse(s((mx - moon_r + 9, my - moon_r - 4, mx + moon_r + 9, my + moon_r - 4)), fill=NAVY + (255,))
    # stars
    for sx, sy, sr in [(mcx + 12, mcy - 26, 4.2), (mcx + 26, mcy - 12, 2.6), (mcx + 2, mcy - 36, 1.8),
                       (mcx - 4, mcy - 16, 1.5), (mcx + 32, mcy - 28, 1.4)]:
        pts = []
        for k in range(8):
            ang = math.radians(k * 45)
            rr = sr if k % 2 == 0 else sr * 0.35
            pts.append(s((sx + rr * math.sin(ang), sy - rr * math.cos(ang))))
        d.polygon(pts, fill=(245, 245, 255, 255))
    # clip to the half disc
    mask = Image.new("L", w.size, 0)
    ImageDraw.Draw(mask).pieslice(s(MOON_BOX), 180, 360, fill=255)
    clipped = Image.new("RGBA", w.size, (0, 0, 0, 0))
    clipped.paste(w, (0, 0), mask)
    img.alpha_composite(clipped)
    # bezel + two small "humps" like the original's moon-phase cut-out
    d2 = ImageDraw.Draw(img)
    d2.arc(s(MOON_BOX), 180, 360, fill=SILVER, width=s(2))
    d2.line(s((x0 - 6, mcy, x1 + 6, mcy)), fill=SILVER, width=s(2))
    for hx in (mcx - r / 2, mcx + r / 2):
        hr = r / 2
        d2.pieslice(s((hx - hr, mcy - hr * 0.45, hx + hr, mcy + hr * 0.45)), 180, 360,
                    fill=(240, 242, 246, 255), outline=SILVER, width=s(1))


def background():
    img = radial_gradient(W, H, (255, 255, 255), (214, 219, 226), cy=H * 0.42, scale=0.95)
    # brushed/sunray texture: faint radial lines
    rays = canvas()
    rd = ImageDraw.Draw(rays)
    for k in range(180):
        ang = math.radians(k * 2)
        rd.line(s((CX, CY, CX + 400 * math.sin(ang), CY - 400 * math.cos(ang))),
                fill=(255, 255, 255, 22 if k % 2 else 0), width=s(1))
    img.alpha_composite(rays)
    d = ImageDraw.Draw(img)
    # inner chapter ring
    d.rounded_rectangle(s((3, 3, W - 3, H - 3)), s(DIAL_RADIUS - 3), outline=(180, 188, 198), width=s(1))
    draw_ticks(d, (120, 132, 150))
    draw_numerals(img, BLUE + (255,))
    img.alpha_composite(capsule_layer())
    d = ImageDraw.Draw(img)
    # steps track + label
    draw_steps_track(d, (205, 212, 222))
    font = ImageFont.truetype(FONT_SANS, s(7))
    d.text(s((CX, CY - 112)), "STEPS", font=font, fill=BLUE_DARK, anchor="mm")
    # date window frame (date text is a live widget on top)
    d.rounded_rectangle(s(DATE_BOX), s(3), fill=(246, 248, 251), outline=(150, 160, 175), width=s(1))
    draw_moon_window(img)
    # round the dial corners (screen shape)
    out = Image.new("RGBA", img.size, (0, 0, 0, 255))
    out.paste(img, (0, 0), rounded_mask(W, H, DIAL_RADIUS))
    return finish(out)


def aod_background():
    img = canvas(color=(0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    draw_ticks(d, (60, 72, 96), minor=False)
    draw_numerals(img, None, outline=(52, 84, 136, 255))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = CAPSULE
    # black out the capsule so numerals don't run under it, then a thin outline
    d.rounded_rectangle(s((x0, y0, x1, y1)), s((x1 - x0) / 2), fill=(0, 0, 0, 255),
                        outline=(50, 60, 80), width=s(1))
    return finish(img)


def steps_progress():
    """Full blue arc for a progress/arc widget (clip by progress in Theme Studio)."""
    img = canvas()
    draw_steps_track(ImageDraw.Draw(img), BLUE + (255,))
    return finish(img)


def hand(length, tail, max_w, kind):
    """Leaf (dauphine-skeleton) hand pointing up; returns (image, pivot_x, pivot_y)."""
    pad = 4
    w = int(max_w + 2 * pad)
    h = int(length + tail + 2 * pad)
    px, py = w / 2, pad + length
    img = canvas(w, h)
    d = ImageDraw.Draw(img)
    if kind == "second":
        d.line(s((px, py + tail, px, py - length)), fill=BLUE_LIGHT, width=int(s(1.4)))
        d.ellipse(s((px - 3.5, py + tail - 10, px + 3.5, py + tail - 3)), fill=BLUE_LIGHT)
        d.ellipse(s((px - 4, py - 4, px + 4, py + 4)), fill=BLUE_LIGHT)
        d.ellipse(s((px - 1.6, py - 1.6, px + 1.6, py + 1.6)), fill=(240, 240, 245))
    else:
        hw = max_w / 2
        bulge = py - length * 0.42
        outer = [(px, py - length), (px + hw, bulge), (px + 1.6, py - 8), (px - 1.6, py - 8), (px - hw, bulge)]
        d.polygon([s(p) for p in outer], fill=BLUE_DARK)
        inner_hw = hw - 2.2
        inner = [(px, py - length + 9), (px + inner_hw, bulge), (px, py - 16), (px - inner_hw, bulge)]
        d.polygon([s(p) for p in inner], fill=BLUE_LIGHT)
        d.line(s((px, py + tail, px, py - 8)), fill=BLUE_DARK, width=int(s(2.4)))
        d.ellipse(s((px - 6, py - 6, px + 6, py + 6)), fill=BLUE_DARK)
        d.ellipse(s((px - 3, py - 3, px + 3, py + 3)), fill=BLUE_LIGHT)
    return finish(img, w, h), px, py


def text_sprites(items, size, color, prefix):
    font = ImageFont.truetype(FONT_SANS, s(size))
    out = {}
    hgt = int(size * 1.4)
    for it in items:
        l, t, r, b = font.getbbox(it)
        wd = int((r - l) / SS) + 2
        img = canvas(wd, hgt)
        ImageDraw.Draw(img).text((s(wd / 2), s(hgt / 2)), it, font=font, fill=color, anchor="mm")
        out[f"{prefix}{it}"] = finish(img, wd, hgt)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "digits"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "weekdays"), exist_ok=True)

    bg = background()
    bg.save(os.path.join(OUT, "background.png"))
    aod = aod_background()
    aod.save(os.path.join(OUT, "aod_background.png"))
    steps_progress().save(os.path.join(OUT, "steps_progress.png"))

    meta = {"screen": [W, H], "dial_center": [CX, CY], "hands": {}}
    hands = {"hour": hand(70, 14, 14, "hour"), "minute": hand(112, 16, 12, "minute"),
             "second": hand(124, 26, 10, "second")}
    for name, (img, px, py) in hands.items():
        img.save(os.path.join(OUT, f"hand_{name}.png"))
        meta["hands"][name] = {"file": f"hand_{name}.png", "size": list(img.size),
                               "pivot": [px, py], "place_at": [CX - px, CY - py]}

    for name, img in text_sprites([str(i) for i in range(10)], 9, BLUE_DARK, "").items():
        img.save(os.path.join(OUT, "digits", f"{name}.png"))
    for name, img in text_sprites(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"], 9, BLUE_DARK, "").items():
        img.save(os.path.join(OUT, "weekdays", f"{name}.png"))

    meta["widgets"] = {
        "date_window": {"box": list(DATE_BOX), "text": "WEEK + DAY, e.g. 'FRI 18'", "color": "#122E5C"},
        "steps_arc": {"file": "steps_progress.png", "pil_box": list(STEPS_ARC["box"]),
                      "start_deg_from_12": STEPS_ARC["start"] + 90 - 360,
                      "end_deg_from_12": STEPS_ARC["end"] + 90 - 360},
    }
    with open(os.path.join(OUT, "layout.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # composite previews at 10:09:30, steps 60 %
    def compose(base, hour, minute, second, with_second=True, progress=0.6):
        img = base.copy().convert("RGBA")
        if progress:
            prog = Image.open(os.path.join(OUT, "steps_progress.png"))
            a = STEPS_ARC
            m = Image.new("L", (W * SS, H * SS), 0)
            ImageDraw.Draw(m).pieslice(s((CX - 80, CY - 160, CX + 80, CY)), a["start"],
                                       a["start"] + (a["end"] - a["start"]) * progress, fill=255)
            img.paste(prog, (0, 0), Image.composite(prog.getchannel("A"), Image.new("L", (W, H), 0),
                                                    m.resize((W, H))))
        if base is bg:
            d = ImageDraw.Draw(img)
            d.text((CX, (DATE_BOX[1] + DATE_BOX[3]) / 2), "FRI 18",
                   font=ImageFont.truetype(FONT_SANS, 9), fill=BLUE_DARK, anchor="mm")
        angles = {"hour": (hour % 12 + minute / 60) * 30, "minute": minute * 6 + second / 10,
                  "second": second * 6}
        for name in ("hour", "minute", "second"):
            if name == "second" and not with_second:
                continue
            himg, px, py = hands[name]
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            layer.alpha_composite(himg, (int(round(CX - px)), int(round(CY - py))))
            layer = layer.rotate(-angles[name], resample=Image.BICUBIC, center=(CX, CY))
            img.alpha_composite(layer)
        return img

    compose(bg, 10, 9, 30).save(os.path.join(OUT, "preview.png"))
    compose(aod, 10, 9, 30, with_second=False, progress=0).save(os.path.join(OUT, "preview_aod.png"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
