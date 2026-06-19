#!/usr/bin/env python3
"""Generate Google Play store graphics for FreeAndroidDoctor (brand: navy + coral)."""
import math
from PIL import Image, ImageDraw, ImageFont

import os
OUT = os.path.dirname(os.path.abspath(__file__))
FREG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FBOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

NAVY_DEEP = (10, 19, 32)
NAVY = (15, 27, 45)
NAVY_SURF = (22, 38, 61)
SURFACE = (30, 51, 80)
CORAL = (255, 111, 97)
CORAL_LT = (255, 144, 128)
SKY = (79, 195, 247)
VIOLET = (156, 123, 255)
GREEN = (76, 175, 80)
AMBER = (255, 179, 0)
TEXT = (236, 239, 244)
TEXT2 = (167, 180, 199)
SS = 3  # supersample factor


def font(bold, size):
    return ImageFont.truetype(FBOLD if bold else FREG, size)


def vgrad(w, h, top, bottom):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def gauge(draw, cx, cy, r, width, frac, color, track=(40, 60, 88)):
    box = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(box, 135, 135 + 270, fill=track, width=width)
    if frac > 0:
        draw.arc(box, 135, 135 + int(270 * frac), fill=color, width=width)
        # rounded end caps
        for ang in (135, 135 + 270 * frac):
            a = math.radians(ang)
            ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
            draw.ellipse([ex - width / 2, ey - width / 2, ex + width / 2, ey + width / 2], fill=color)


def ctext(draw, cx, y, text, fnt, fill, anchor="ma"):
    draw.text((cx, y), text, font=fnt, fill=fill, anchor=anchor)


def rrect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


# ---------- 1. App icon 512x512 ----------
def make_icon():
    s = 512 * SS
    img = vgrad(s, s, (18, 30, 52), (10, 17, 30))
    # rounded mask
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s, s], radius=int(s * 0.23), fill=255)
    d = ImageDraw.Draw(img)
    cx = cy = s // 2
    gauge(d, cx, cy, int(s * 0.30), int(s * 0.075), 0.78, CORAL)
    # checkmark
    w = int(s * 0.055)
    p1 = (cx - int(s * 0.13), cy + int(s * 0.01))
    p2 = (cx - int(s * 0.03), cy + int(s * 0.11))
    p3 = (cx + int(s * 0.16), cy - int(s * 0.12))
    d.line([p1, p2], fill=TEXT, width=w, joint="curve")
    d.line([p2, p3], fill=TEXT, width=w, joint="curve")
    img.putalpha(mask)
    img = img.resize((512, 512), Image.LANCZOS)
    img.save(f"{OUT}/play_icon_512.png")


# ---------- 2. Feature graphic 1024x500 ----------
def make_feature():
    w, h = 1024 * SS, 500 * SS
    img = vgrad(w, h, (16, 28, 50), (9, 16, 28))
    d = ImageDraw.Draw(img)
    # soft accent blobs
    for (bx, by, br, col) in [(int(w*0.12), int(h*0.2), int(h*0.5), CORAL), (int(w*0.2), int(h*0.95), int(h*0.45), VIOLET)]:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([bx-br, by-br, bx+br, by+br], fill=col + (38,))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    cy = h // 2
    gx = int(w * 0.17)
    gauge(d, gx, cy, int(h * 0.30), int(h * 0.07), 0.82, GREEN)
    ctext(d, gx, cy - int(h * 0.12), "92", font(True, int(h * 0.20)), TEXT, anchor="mm")
    tx = int(w * 0.36)
    d.text((tx, int(h * 0.30)), "FreeAndroidDoctor", font=font(True, int(h * 0.135)), fill=TEXT)
    d.text((tx, int(h * 0.50)), "Czyść • Optymalizuj • Bez roota", font=font(False, int(h * 0.072)), fill=CORAL_LT)
    d.text((tx, int(h * 0.63)), "30+ narzędzi: śmieci, duplikaty, zdjęcia, bateria, backup", font=font(False, int(h * 0.052)), fill=TEXT2)
    img = img.resize((1024, 500), Image.LANCZOS)
    img.save(f"{OUT}/play_feature_1024x500.png")


# ---------- phone screenshot base ----------
def screen_base(caption, sub):
    w, h = 1080 * SS, 1920 * SS
    img = vgrad(w, h, (12, 22, 38), (8, 14, 26))
    d = ImageDraw.Draw(img)
    ctext(d, w // 2, int(h * 0.045), caption, font(True, int(h * 0.030)), TEXT, anchor="ma")
    ctext(d, w // 2, int(h * 0.082), sub, font(False, int(h * 0.020)), CORAL_LT, anchor="ma")
    return img, d, w, h


def card(d, box, fill=SURFACE, radius=None):
    if radius is None:
        radius = int((box[2] - box[0]) * 0.06)
    rrect(d, box, radius, fill)


def finish(img, name):
    img.resize((1080, 1920), Image.LANCZOS).save(f"{OUT}/{name}")


# ---------- 3. Screenshot: Dashboard ----------
def shot_dashboard():
    img, d, w, h = screen_base("Stan telefonu w jednym spojrzeniu", "Pamięć, RAM i bateria w czasie rzeczywistym")
    cx = w // 2
    card(d, [int(w*0.08), int(h*0.13), int(w*0.92), int(h*0.40)], NAVY_SURF, int(w*0.05))
    gauge(d, cx, int(h*0.255), int(h*0.10), int(h*0.022), 0.92, GREEN)
    ctext(d, cx, int(h*0.232), "92", font(True, int(h*0.060)), GREEN, anchor="mm")
    ctext(d, cx, int(h*0.30), "Kondycja urządzenia", font(False, int(h*0.020)), TEXT2, anchor="ma")
    rows = [("Pamięć", "47,2 GB / 128 GB", 0.37, SKY), ("RAM", "3,1 GB / 8 GB", 0.39, VIOLET), ("Bateria", "84% · 29,5°C", 0.84, GREEN)]
    y = int(h*0.44)
    for title, val, frac, col in rows:
        box = [int(w*0.08), y, int(w*0.92), y + int(h*0.10)]
        card(d, box, SURFACE, int(w*0.045))
        d.text((int(w*0.13), y + int(h*0.018)), title, font=font(False, int(h*0.021)), fill=TEXT2)
        d.text((int(w*0.13), y + int(h*0.044)), val, font=font(True, int(h*0.030)), fill=col)
        bx0, bx1 = int(w*0.13), int(w*0.87)
        by = y + int(h*0.082)
        rrect(d, [bx0, by, bx1, by + int(h*0.010)], int(h*0.005), (40, 60, 88))
        rrect(d, [bx0, by, bx0 + int((bx1-bx0)*frac), by + int(h*0.010)], int(h*0.005), col)
        y += int(h*0.115)
    finish(img, "shot_1_dashboard.png")


# ---------- 4. Screenshot: Tools grid ----------
def shot_tools():
    img, d, w, h = screen_base("30+ narzędzi w jednym miejscu", "Pliki, zdjęcia, aplikacje, sieć i system")
    labels = ["Duplikaty", "Duże pliki", "Wg typu", "Podobne", "Rozmyte", "Kompresja",
              "Czas ekranu", "Uprawnienia", "Backup APK", "Dane", "WiFi", "Bateria"]
    cols, rows = 3, 4
    gx0, gy0 = int(w*0.07), int(h*0.13)
    gw = int(w*0.86); gap = int(w*0.03)
    cw = (gw - gap*(cols-1)) // cols
    ch = int(h*0.135); gapy = int(h*0.022)
    accents = [CORAL, SKY, VIOLET, GREEN, AMBER, CORAL_LT]
    for i, lab in enumerate(labels):
        r, c = divmod(i, cols)
        x = gx0 + c*(cw+gap); y = gy0 + r*(ch+gapy)
        card(d, [x, y, x+cw, y+ch], SURFACE, int(cw*0.14))
        col = accents[i % len(accents)]
        rrect(d, [x+int(cw*0.12), y+int(ch*0.16), x+int(cw*0.12)+int(cw*0.26), y+int(ch*0.16)+int(cw*0.26)], int(cw*0.07), lerp(col, NAVY, 0.55))
        d.ellipse([x+int(cw*0.17), y+int(ch*0.21), x+int(cw*0.31), y+int(ch*0.21)+int(cw*0.14)], outline=col, width=SS*3)
        d.text((x+int(cw*0.12), y+int(ch*0.62)), lab, font=font(True, int(h*0.0185)), fill=TEXT)
    finish(img, "shot_2_tools.png")


# ---------- 5. Screenshot: Cleaner / space ----------
def shot_cleaner():
    img, d, w, h = screen_base("Odzyskaj miejsce jednym ruchem", "Śmieci, duplikaty i duże pliki")
    cx = w // 2
    card(d, [int(w*0.08), int(h*0.13), int(w*0.92), int(h*0.335)], NAVY_SURF, int(w*0.05))
    ctext(d, cx, int(h*0.150), "Możliwe do odzyskania", font(False, int(h*0.021)), TEXT2, anchor="ma")
    ctext(d, cx, int(h*0.215), "6,8 GB", font(True, int(h*0.072)), CORAL, anchor="mm")
    btn = [int(w*0.28), int(h*0.270), int(w*0.72), int(h*0.315)]
    rrect(d, btn, int(h*0.022), CORAL)
    ctext(d, cx, int(h*0.279), "Wyczyść teraz", font(True, int(h*0.024)), NAVY_DEEP, anchor="ma")
    items = [("Cache aplikacji", "2,1 GB", SKY), ("Duplikaty plików", "1,9 GB", VIOLET),
             ("Stare pliki APK", "1,2 GB", AMBER), ("Pliki .tmp / .log", "0,9 GB", GREEN),
             ("Puste foldery", "0,7 GB", CORAL_LT)]
    y = int(h*0.355)
    for name, sz, col in items:
        box = [int(w*0.08), y, int(w*0.92), y+int(h*0.075)]
        card(d, box, SURFACE, int(w*0.04))
        d.ellipse([int(w*0.12), y+int(h*0.024), int(w*0.12)+int(h*0.028), y+int(h*0.024)+int(h*0.028)], fill=col)
        d.text((int(w*0.20), y+int(h*0.023)), name, font=font(False, int(h*0.024)), fill=TEXT)
        d.text((int(w*0.74), y+int(h*0.023)), sz, font=font(True, int(h*0.024)), fill=col)
        y += int(h*0.088)
    finish(img, "shot_3_cleaner.png")


# ---------- 6. Screenshot: Pro ----------
def shot_pro():
    img, d, w, h = screen_base("FreeAndroidDoctor Pro", "Bez reklam. Wszystkie narzędzia zaawansowane.")
    cx = w // 2
    gauge(d, cx, int(h*0.235), int(h*0.085), int(h*0.020), 1.0, CORAL)
    ctext(d, cx, int(h*0.215), "PRO", font(True, int(h*0.040)), CORAL, anchor="mm")
    benefits = ["Usuń wszystkie reklamy", "Wszystkie narzędzia zaawansowane",
                "Automatyczne czyszczenie", "Monitor na pasku stanu", "Wsparcie rozwoju"]
    y = int(h*0.36)
    for b in benefits:
        box = [int(w*0.10), y, int(w*0.90), y+int(h*0.072)]
        card(d, box, SURFACE, int(w*0.04))
        d.ellipse([int(w*0.14), y+int(h*0.022), int(w*0.14)+int(h*0.030), y+int(h*0.022)+int(h*0.030)], fill=GREEN)
        # check
        cxk = int(w*0.155); cyk = y+int(h*0.037)
        d.line([(cxk-int(h*0.006), cyk), (cxk, cyk+int(h*0.008)), (cxk+int(h*0.010), cyk-int(h*0.009))], fill=NAVY_DEEP, width=SS*3, joint="curve")
        d.text((int(w*0.21), y+int(h*0.021)), b, font=font(True, int(h*0.024)), fill=TEXT)
        y += int(h*0.085)
    plan = [int(w*0.10), int(h*0.81), int(w*0.90), int(h*0.86)]
    rrect(d, plan, int(h*0.022), CORAL)
    ctext(d, cx, int(h*0.818), "Subskrybuj / kup dożywotnio", font(True, int(h*0.024)), NAVY_DEEP, anchor="ma")
    finish(img, "shot_4_pro.png")


make_icon()
make_feature()
shot_dashboard()
shot_tools()
shot_cleaner()
shot_pro()
print("done")
