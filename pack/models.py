#!/usr/bin/env python3
"""Voxel-sculpted 3D models for every Beyond the End item.

Every item is built on a 32x32x32 grid of half-unit voxels (the model spans the 16-unit
item box). The voxels are greedily merged into cuboids and written as a Minecraft model.
Tools stand upright in the grid and are turned 45 degrees about Z in the model, which lays
them along the same diagonal as a vanilla sword sprite, so vanilla's hand transforms work
unchanged. Everything else (ingots, relics, armour in the inventory) is built the way it
lies and shown slightly turned in the GUI so the depth reads.

Colours are painted as roles; each role is a dithered 16x16 swatch in a 64x64 texture and
every face maps onto its swatch. Detail comes from geometry, like vanilla's 3D trident.

The engine (Volume, mesh, texture, model_json) is the one from the CustomWeapons pack,
copied in so this folder stays self-contained.
"""
import math
import random

from PIL import Image

G = 32
SCALE = 16.0 / G
SWATCH = 16
C = 16
ZF, ZB = 15, 16   # the one-unit-thick main plane


class Volume:
    def __init__(self):
        self.v = {}

    def put(self, x, y, z, role):
        if 0 <= x < G and 0 <= y < G and 0 <= z < G:
            self.v[(x, y, z)] = role

    def box(self, x0, y0, x1, y1, role, z0=ZF, z1=ZB):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    self.put(x, y, z, role)

    def each(self, fn, role, z0=ZF, z1=ZB):
        for x in range(G):
            for y in range(G):
                if fn(x + 0.5, y + 0.5):
                    for z in range(z0, z1 + 1):
                        self.put(x, y, z, role)

    def taper(self, cx, y0, y1, w0, w1, role, z0=ZF, z1=ZB, skew=0.0):
        def f(x, y):
            if not (y0 <= y <= y1 + 1):
                return False
            t = (y - y0) / max(y1 + 1 - y0, 1e-6)
            w = w0 + (w1 - w0) * t
            c = cx + skew * t * t
            return abs(x - c) <= w
        self.each(f, role, z0, z1)

    def disc(self, cx, cy, r, role, z0=ZF, z1=ZB, ry=None):
        ry = r if ry is None else ry
        self.each(lambda x, y: ((x - cx) / r) ** 2 + ((y - cy) / ry) ** 2 <= 1.0, role, z0, z1)

    def line(self, x0, y0, x1, y1, role, z0=ZF, z1=ZB):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) * 2 + 1
        for i in range(n + 1):
            t = i / n
            px, py = int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))
            self.box(px, py, px, py, role, z0, z1)

    def edge(self, of, role):
        for (x, y, z), r in list(self.v.items()):
            if r == of and ((x - 1, y, z) not in self.v or (x + 1, y, z) not in self.v):
                self.v[(x, y, z)] = role

    def rim(self, of, role):
        """Recolour voxels of a role that touch empty space on any side in the plane."""
        for (x, y, z), r in list(self.v.items()):
            if r == of and any((x + dx, y + dy, z) not in self.v for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                self.v[(x, y, z)] = role

    def carve(self, fn):
        for k in [k for k in self.v if fn(k[0] + 0.5, k[1] + 0.5, k[2] + 0.5)]:
            del self.v[k]

    def rows(self, of, role, ys):
        for (x, y, z), r in list(self.v.items()):
            if r == of and y in ys:
                self.v[(x, y, z)] = role

    def mirror_x(self):
        for (x, y, z), r in list(self.v.items()):
            self.put(G - 1 - x, y, z, r)


def mesh(volume):
    v = volume.v
    done = set()
    boxes = []
    for key in sorted(v):
        if key in done:
            continue
        x, y, z = key
        role = v[key]

        def ok(px, py, pz):
            return (px, py, pz) in v and v[(px, py, pz)] == role and (px, py, pz) not in done

        x1 = x
        while ok(x1 + 1, y, z):
            x1 += 1
        z1 = z
        while all(ok(px, y, z1 + 1) for px in range(x, x1 + 1)):
            z1 += 1
        y1 = y
        while all(ok(px, y1 + 1, pz) for px in range(x, x1 + 1) for pz in range(z, z1 + 1)):
            y1 += 1
        for px in range(x, x1 + 1):
            for py in range(y, y1 + 1):
                for pz in range(z, z1 + 1):
                    done.add((px, py, pz))
        boxes.append(((x, y, z), (x1 + 1, y1 + 1, z1 + 1), role))
    return boxes


def texture(palette, seed):
    rng = random.Random(seed)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    px = img.load()
    for i, (role, base) in enumerate(palette.items()):
        ox, oy = (i % 4) * SWATCH, (i // 4) * SWATCH
        alpha = base[3] if len(base) == 4 else 255
        rgb = base[:3]
        tones = [tuple(int(c * f) for c in rgb) for f in (0.9, 0.96, 1.0, 1.0, 1.05)]
        for y in range(SWATCH):
            for x in range(SWATCH):
                t = rng.choice(tones)
                px[ox + x, oy + y] = tuple(min(255, c) for c in t) + (alpha,)
    return img


# Vanilla's handheld transforms, for the upright-then-leaned tools.
HANDHELD = {
    "thirdperson_righthand": {"rotation": [0, -90, 55], "translation": [0, 4.0, 0.5], "scale": [0.85, 0.85, 0.85]},
    "thirdperson_lefthand": {"rotation": [0, 90, -55], "translation": [0, 4.0, 0.5], "scale": [0.85, 0.85, 0.85]},
    "firstperson_righthand": {"rotation": [0, -90, 25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
    "firstperson_lefthand": {"rotation": [0, 90, -25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
}
# Vanilla's "generated" item transforms, with the GUI view turned a little so the depth shows.
THING = {
    "thirdperson_righthand": {"rotation": [0, 0, 0], "translation": [0, 3, 1], "scale": [0.55, 0.55, 0.55]},
    "thirdperson_lefthand": {"rotation": [0, 0, 0], "translation": [0, 3, 1], "scale": [0.55, 0.55, 0.55]},
    "firstperson_righthand": {"rotation": [0, -90, 25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
    "firstperson_lefthand": {"rotation": [0, 90, -25], "translation": [1.13, 3.2, 1.13], "scale": [0.68, 0.68, 0.68]},
    "gui": {"rotation": [22, 35, 0], "translation": [0, 0, 0], "scale": [0.9, 0.9, 0.9]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
    "fixed": {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]},
}


def model_json(boxes, palette, tex_ref, display, lean):
    order = list(palette)
    elements = []
    u = 16.0 / 64
    for (x0, y0, z0), (x1, y1, z1), role in boxes:
        i = order.index(role)
        ox, oy = (i % 4) * SWATCH, (i // 4) * SWATCH
        dx, dy, dz = (x1 - x0), (y1 - y0), (z1 - z0)
        faces = {}
        for side, (w, h) in {"north": (dx, dy), "south": (dx, dy), "east": (dz, dy), "west": (dz, dy),
                             "up": (dx, dz), "down": (dx, dz)}.items():
            faces[side] = {"uv": [ox * u, oy * u, (ox + min(SWATCH, w)) * u, (oy + min(SWATCH, h)) * u],
                           "texture": "#t"}
        el = {
            "from": [round(x0 * SCALE, 3), round(y0 * SCALE, 3), round(z0 * SCALE, 3)],
            "to": [round(x1 * SCALE, 3), round(y1 * SCALE, 3), round(z1 * SCALE, 3)],
            "faces": faces,
        }
        if lean:
            el["rotation"] = {"origin": [8, 8, 8], "axis": "z", "angle": lean}
        elements.append(el)
    return {
        "credit": "Beyond the End, pack/models.py",
        "texture_size": [64, 64],
        "textures": {"t": tex_ref, "particle": tex_ref},
        "gui_light": "front",
        "elements": elements,
        "display": display,
    }


# ------------------------------------------------------------------ tier palettes
TIERS = {
    "thallasium": {"metal": (104, 198, 214), "edge": (214, 244, 248), "dark": (52, 118, 134), "gem": (244, 250, 250),
                   "trim": (170, 226, 236)},
    "terminite": {"metal": (30, 132, 150), "edge": (132, 220, 228), "dark": (18, 70, 84), "gem": (206, 132, 255),
                  "trim": (86, 190, 204)},
    "aeternium": {"metal": (146, 88, 198), "edge": (234, 196, 255), "dark": (54, 30, 78), "gem": (255, 176, 255),
                  "trim": (196, 150, 236)},
}
GRIP = {"wood": (88, 64, 42), "wrap": (48, 36, 30), "band": (196, 168, 96)}


def tier_palette(tier):
    p = dict(TIERS[tier])
    p.update(GRIP)
    return p


# ------------------------------------------------------------------ tools
def sword(v, tier):
    v.box(14, 0, 17, 2, "dark", 14, 17)                   # pommel
    v.box(15, 0, 16, 1, "gem", 14, 17)
    v.box(15, 3, 16, 9, "wrap", 14, 17)                   # grip
    v.rows("wrap", "band", {4, 7})
    wide = {"thallasium": 20, "terminite": 21, "aeternium": 22}[tier]
    v.box(32 - wide, 10, wide - 1, 11, "dark", 14, 17)    # crossguard
    v.box(15, 10, 16, 12, "gem", 13, 18)                  # gem at the ricasso
    v.taper(C, 12, 31, 3.2 if tier != "thallasium" else 2.8, 0.6, "metal")
    v.edge("metal", "edge")
    v.box(15, 13, 16, 27, "trim")                         # fuller
    if tier == "aeternium":
        v.carve(lambda x, y, z: 25 <= y < 29 and x < 14.5)   # a notch at the tip's back edge


def pickaxe(v, tier):
    v.box(15, 0, 16, 23, "wood", 14, 17)                  # haft
    v.rows("wood", "wrap", set(range(1, 7)))
    v.box(14, 23, 17, 26, "dark", 14, 17)                 # socket
    v.box(6, 25, 25, 27, "metal", 14, 17)                 # head bar
    v.taper(7, 19, 25, 1.0, 1.5, "metal")                 # left tip curving down
    v.taper(25, 19, 25, 1.0, 1.5, "metal")
    v.rim("metal", "edge")
    v.box(15, 26, 16, 28, "gem", 14, 17)                  # jewel on top
    if tier != "thallasium":
        v.box(4, 24, 5, 26, "trim", 15, 16)                # wider bite
        v.box(26, 24, 27, 26, "trim", 15, 16)


def axe(v, tier):
    v.box(15, 0, 16, 27, "wood", 14, 17)
    v.rows("wood", "wrap", set(range(1, 7)))
    v.box(14, 20, 17, 28, "dark", 14, 17)                 # socket
    v.each(lambda x, y: 17 <= x <= 26 and 17 <= y <= 30 and (x - 17) <= (y - 17) * 0.9 + 3 and (x - 17) <= (30 - y) * 0.9 + 3, "metal", 14, 17)
    if tier == "aeternium":                               # double bit
        v.each(lambda x, y: 6 <= x <= 15 and 17 <= y <= 30 and (15 - x) <= (y - 17) * 0.9 + 3 and (15 - x) <= (30 - y) * 0.9 + 3, "metal", 14, 17)
    v.rim("metal", "edge")
    v.box(15, 22, 16, 25, "gem", 13, 18)


def shovel(v, tier):
    v.box(15, 0, 16, 21, "wood", 14, 17)
    v.rows("wood", "wrap", set(range(1, 7)))
    v.box(13, 0, 18, 1, "wood", 14, 17)                   # T handle end
    v.box(14, 20, 17, 23, "dark", 14, 17)
    v.each(lambda x, y: 22 <= y <= 31 and abs(x - 16) <= 4.5 - max(0, (y - 27)) * 1.2, "metal", 14, 17)
    v.rim("metal", "edge")
    v.box(15, 23, 16, 28, "trim")                         # ridge
    if tier != "thallasium":
        v.box(15, 24, 16, 25, "gem", 13, 18)


def hoe(v, tier):
    v.box(15, 0, 16, 27, "wood", 14, 17)
    v.rows("wood", "wrap", set(range(1, 7)))
    v.box(14, 26, 17, 29, "dark", 14, 17)
    v.box(17, 27, 26, 29, "metal", 14, 17)                # blade out to one side
    v.taper(25, 21, 27, 1.0, 1.5, "metal")                # and bent down
    v.rim("metal", "edge")
    v.box(15, 28, 16, 30, "gem", 14, 17)


# ------------------------------------------------------------------ armour (as held)
def helmet(v, tier):
    v.disc(16, 12, 10, "metal", 11, 20, ry=9)
    v.carve(lambda x, y, z: y < 6)                        # flat bottom
    v.carve(lambda x, y, z: 6 <= y < 13 and abs(x - 16) < 5 and z > 15.5)   # face opening
    v.rim("metal", "edge")
    v.box(15, 15, 16, 22, "trim", 10, 21)                 # crest ridge
    v.box(15, 19, 16, 20, "gem", 9, 22)
    v.box(6, 6, 25, 7, "dark", 11, 20)                    # rim


def chestplate(v, tier):
    v.box(9, 4, 22, 24, "metal", 12, 19)                  # torso
    v.carve(lambda x, y, z: y > 21 and abs(x - 16) < 3.5) # neck
    v.box(5, 18, 9, 24, "dark", 12, 19)                   # shoulders
    v.box(22, 18, 26, 24, "dark", 12, 19)
    v.box(9, 4, 22, 5, "dark", 12, 19)                    # hem
    v.rim("metal", "edge")
    v.box(15, 8, 16, 20, "trim", 11, 20)                  # centre line
    v.box(14, 14, 17, 16, "gem", 11, 20)


def leggings(v, tier):
    v.box(8, 22, 23, 26, "dark", 12, 19)                  # belt
    v.box(14, 23, 17, 25, "gem", 11, 20)
    v.box(8, 4, 14, 22, "metal", 12, 19)                  # legs
    v.box(17, 4, 23, 22, "metal", 12, 19)
    v.rim("metal", "edge")
    v.box(10, 12, 12, 13, "trim", 12, 19)                 # knee plates
    v.box(19, 12, 21, 13, "trim", 12, 19)


def boots(v, tier):
    for x0 in (5, 17):
        v.box(x0, 10, x0 + 9, 20, "metal", 12, 19)        # shaft
        v.box(x0, 6, x0 + 11, 10, "metal", 12, 19)        # foot, toe out
        v.box(x0, 5, x0 + 11, 5, "dark", 12, 19)          # sole
        v.box(x0, 19, x0 + 9, 20, "dark", 12, 19)         # cuff
    v.rim("metal", "edge")
    v.box(9, 14, 10, 15, "gem", 11, 20)
    v.box(21, 14, 22, 15, "gem", 11, 20)


# ------------------------------------------------------------------ materials
def dust(v, _):
    for (x, y, r) in ((11, 6, 3), (18, 5, 3.5), (24, 7, 2.5), (14, 10, 2), (21, 11, 2.5), (9, 11, 1.5)):
        v.disc(x, y, r, "metal", 13, 18, ry=r * 0.8)
    v.rim("metal", "edge")
    v.box(18, 7, 19, 8, "gem", 12, 19)


def ingot(v, _):
    v.each(lambda x, y: 8 <= y <= 15 and abs(x - 16) <= 9 - (y - 8) * 0.4, "metal", 11, 20)
    v.box(8, 15, 23, 15, "edge", 11, 20)                   # top face highlight
    v.rows("metal", "dark", {8, 9})
    v.box(16, 12, 20, 13, "trim", 11, 20)                  # stamp


def amber(v, _):
    v.disc(16, 11, 8, "metal", 12, 19, ry=7)
    v.rim("metal", "edge")
    v.disc(13, 13, 2, "gem", 12, 19)                       # inclusion (a trapped bubble)
    v.box(18, 8, 19, 9, "dark", 12, 19)


def silk_fibre(v, _):
    for i in range(6):                                     # a coiled skein
        y0 = 4 + i * 4
        v.box(9, y0, 22, y0 + 1, "metal", 13, 18)
        v.box(8, y0 + 2, 9, y0 + 3, "metal", 13, 18)
        v.box(22, y0 + 2, 23, y0 + 3, "metal", 13, 18)
    v.box(11, 12, 20, 15, "dark", 13, 18)                  # the tie around the middle
    v.rim("metal", "edge")


def gelatine(v, _):
    v.each(lambda x, y: 5 <= y <= 18 and 7 <= x <= 25 and not ((x < 9 or x > 23) and (y < 7 or y > 16)), "metal", 11, 20)
    v.rim("metal", "edge")
    v.disc(14, 13, 3, "gem", 11, 20)                       # a lighter core
    v.box(19, 9, 21, 10, "gem", 11, 20)


def shadow_essence(v, _):
    v.taper(16, 4, 26, 1.0, 4.0, "metal", 14, 17)          # a shard, wide at the top
    v.taper(16, 26, 31, 4.0, 0.5, "metal", 14, 17)
    v.rim("metal", "edge")
    v.box(15, 12, 16, 24, "gem", 13, 18)                   # the light inside
    for (x, y) in ((7, 10), (25, 14), (9, 22), (24, 25)):  # wisps of shadow
        v.box(x, y, x + 1, y + 2, "dark", 15, 16)


def end_fish(v, _):
    v.disc(15, 12, 9, "metal", 13, 18, ry=5)               # body
    v.each(lambda x, y: 24 <= x <= 30 and abs(y - 12) <= (x - 23) * 0.9, "dark", 14, 17)   # tail
    v.each(lambda x, y: 11 <= x <= 19 and 16 <= y <= 20 and abs(x - 15) <= (20 - y) * 1.2, "dark", 14, 17)  # dorsal fin
    v.rim("metal", "edge")
    v.box(9, 13, 10, 14, "gem", 12, 19)                    # eye
    v.box(6, 12, 6, 12, "dark", 13, 18)                    # mouth


# ------------------------------------------------------------------ relics
def chorus_lantern(v, _):
    v.box(10, 4, 21, 5, "dark", 11, 20)                    # base
    v.box(10, 21, 21, 22, "dark", 11, 20)                  # top
    for x in (10, 21):                                     # corner posts
        v.box(x, 5, x, 21, "dark", 11, 11)
        v.box(x, 5, x, 21, "dark", 20, 20)
    v.box(11, 6, 20, 20, "metal", 12, 19)                  # glass
    v.disc(16, 13, 4, "gem", 12, 19)                       # the light
    v.box(14, 23, 17, 26, "dark", 14, 17)                  # hanging ring
    v.carve(lambda x, y, z: 23.5 < y < 25.5 and 14.5 < x < 16.5 and 14 <= z <= 17)


def crystal_focus(v, _):
    v.taper(16, 4, 31, 3.5, 0.5, "metal", 13, 18)
    v.taper(9, 4, 22, 2.5, 0.4, "metal", 13, 18, skew=-2)
    v.taper(23, 4, 24, 2.5, 0.4, "metal", 13, 18, skew=2)
    v.rim("metal", "edge")
    v.box(15, 8, 16, 24, "gem", 12, 19)
    v.box(8, 2, 24, 4, "dark", 12, 19)                     # rock base


def amber_heart(v, _):
    v.disc(11, 18, 6, "metal", 12, 19)
    v.disc(21, 18, 6, "metal", 12, 19)
    v.each(lambda x, y: 4 <= y <= 18 and abs(x - 16) <= (y - 4) * 0.85, "metal", 12, 19)
    v.rim("metal", "edge")
    v.disc(16, 13, 2.5, "gem", 11, 20)                     # the glow at the centre
    v.box(9, 20, 10, 21, "edge", 12, 19)


def veil_of_shadows(v, _):
    v.each(lambda x, y: 4 <= y <= 28 and 5 + 2 * math.sin(y / 3.0) <= x <= 27 + 2 * math.sin(y / 3.0 + 1), "metal", 14, 17)
    v.carve(lambda x, y, z: y < 9 and ((x - 8) % 8) < 3)  # ragged hem
    v.rim("metal", "edge")
    v.box(8, 27, 24, 29, "dark", 13, 18)                   # clasp bar
    v.box(15, 26, 17, 29, "gem", 12, 19)


def tidal_lens(v, _):
    v.disc(16, 15, 11, "dark", 13, 18)                     # rim
    v.disc(16, 15, 8.5, "metal", 14, 17)                   # glass
    v.disc(13, 18, 2, "edge", 14, 17)                      # glint
    v.box(15, 2, 16, 5, "dark", 14, 17)                    # handle stub
    v.box(15, 15, 16, 16, "gem", 14, 17)


def starfall_shard(v, _):
    for a in range(5):
        ang = math.radians(90 + a * 72)
        v.line(16, 15, 16 + 13 * math.cos(ang), 15 + 13 * math.sin(ang), "metal", 14, 17)
        v.line(16, 15, 16 + 6 * math.cos(ang + 0.6), 15 + 6 * math.sin(ang + 0.6), "metal", 14, 17)
    v.each(lambda x, y: (x - 16) ** 2 + (y - 15) ** 2 <= 30, "metal", 14, 17)
    v.rim("metal", "edge")
    v.disc(16, 15, 2.5, "gem", 13, 18)


def eternal_crystal(v, _):
    v.each(lambda x, y: 3 <= y <= 27 and abs(x - 16) <= 5, "metal", 12, 19)
    v.taper(16, 27, 31, 5.0, 0.6, "metal", 12, 19)
    v.taper(16, 3, 0, 5.0, 2.0, "metal", 12, 19)
    v.rim("metal", "edge")
    v.box(15, 6, 16, 26, "gem", 11, 20)
    v.box(12, 10, 13, 20, "trim", 12, 19)


def gale_rod(v, _):
    v.box(14, 1, 17, 30, "metal", 14, 17)
    v.rows("metal", "trim", {5, 6, 12, 13, 19, 20, 26, 27})
    v.box(13, 29, 18, 31, "gem", 13, 18)
    v.box(13, 0, 18, 1, "dark", 13, 18)
    for y in (8, 16, 24):                                  # the wind curling round it
        v.box(11, y, 12, y + 1, "edge", 15, 16)
        v.box(19, y + 3, 20, y + 4, "edge", 15, 16)


def void_heart(v, _):
    for a in range(4):
        ang = math.radians(45 + a * 90)
        v.line(16, 15, 16 + 12 * math.cos(ang), 15 + 12 * math.sin(ang), "dark", 14, 17)
    v.disc(16, 15, 6, "dark", 12, 19)
    v.rim("dark", "metal")
    v.disc(16, 15, 3, "gem", 11, 20)
    for a in range(4):                                     # the long points
        ang = math.radians(a * 90)
        v.line(16, 15, 16 + 14 * math.cos(ang), 15 + 14 * math.sin(ang), "metal", 15, 16)


def tempest_horn(v, _):
    def horn(x, y):
        t = math.atan2(y - 6, x - 6)
        r = math.hypot(x - 6, y - 6)
        return 0 <= t <= math.pi / 2 and 14 <= r <= 24 and (r - 14) <= 10 * (1 - t / (math.pi / 2)) + 2
    v.each(horn, "metal", 13, 18)
    v.rim("metal", "edge")
    v.box(24, 4, 30, 7, "dark", 12, 19)                    # the mouthpiece band
    v.box(20, 5, 23, 8, "trim", 13, 18)


# ------------------------------------------------------------------ the table
GEAR = {"sword": sword, "pickaxe": pickaxe, "axe": axe, "shovel": shovel, "hoe": hoe,
        "helmet": helmet, "chestplate": chestplate, "leggings": leggings, "boots": boots}
TOOLS = {"sword", "pickaxe", "axe", "shovel", "hoe"}

MATERIALS = {
    "thallasium_dust": (dust, dict(tier_palette("thallasium"))),
    "thallasium_ingot": (ingot, dict(tier_palette("thallasium"))),
    "terminite_ingot": (ingot, dict(tier_palette("terminite"))),
    "aeternium_ingot": (ingot, dict(tier_palette("aeternium"))),
    "amber": (amber, {"metal": (232, 160, 40), "edge": (255, 214, 120), "gem": (255, 240, 200), "dark": (150, 90, 20)}),
    "silk_fibre": (silk_fibre, {"metal": (240, 240, 236), "edge": (255, 255, 255), "dark": (180, 176, 168)}),
    "gelatine": (gelatine, {"metal": (120, 220, 230, 220), "edge": (200, 248, 252), "gem": (230, 255, 255)}),
    "shadow_essence": (shadow_essence, {"metal": (60, 30, 90), "edge": (150, 90, 200), "gem": (216, 150, 255), "dark": (20, 10, 30, 200)}),
    "end_fish": (end_fish, {"metal": (110, 190, 210), "edge": (200, 240, 250), "dark": (60, 120, 140), "gem": (255, 255, 220)}),
}
RELICS = {
    "chorus_lantern": (chorus_lantern, {"metal": (150, 120, 200, 200), "gem": (220, 190, 255), "dark": (40, 30, 60), "edge": (200, 180, 230)}),
    "crystal_focus": (crystal_focus, {"metal": (120, 210, 230), "edge": (220, 250, 255), "gem": (255, 255, 255), "dark": (60, 70, 90)}),
    "amber_heart": (amber_heart, {"metal": (240, 140, 40), "edge": (255, 210, 120), "gem": (255, 250, 210)}),
    "veil_of_shadows": (veil_of_shadows, {"metal": (40, 30, 60, 230), "edge": (100, 80, 130), "dark": (90, 70, 40), "gem": (200, 60, 90)}),
    "tidal_lens": (tidal_lens, {"metal": (120, 200, 240, 200), "edge": (240, 252, 255), "dark": (200, 170, 110), "gem": (255, 255, 255)}),
    "starfall_shard": (starfall_shard, {"metal": (250, 240, 200), "edge": (255, 255, 240), "gem": (255, 200, 90)}),
    "eternal_crystal": (eternal_crystal, {"metal": (190, 130, 255), "edge": (240, 220, 255), "gem": (255, 255, 255), "trim": (220, 180, 255)}),
    "gale_rod": (gale_rod, {"metal": (170, 210, 230), "trim": (230, 245, 250), "gem": (255, 255, 255), "dark": (90, 120, 140), "edge": (255, 255, 255, 180)}),
    "void_heart": (void_heart, {"dark": (30, 14, 44), "metal": (140, 70, 210), "gem": (240, 200, 255)}),
    "tempest_horn": (tempest_horn, {"metal": (200, 190, 170), "edge": (240, 236, 224), "dark": (90, 80, 70), "trim": (150, 140, 120)}),
}


def build_all():
    """id -> (model dict, texture image, element count). One model per item."""
    out = {}
    for tier in TIERS:
        for kind, fn in GEAR.items():
            v = Volume()
            fn(v, tier)
            iid = f"{tier}_{kind}"
            palette = tier_palette(tier)
            display, lean = (HANDHELD, -45) if kind in TOOLS else (THING, 0)
            boxes = mesh(v)
            out[iid] = (model_json(boxes, palette, f"beyond:item/{iid}", display, lean), texture(palette, iid), len(boxes))
    for table in (MATERIALS, RELICS):
        for iid, (fn, palette) in table.items():
            v = Volume()
            fn(v, None)
            boxes = mesh(v)
            out[iid] = (model_json(boxes, palette, f"beyond:item/{iid}", THING, 0), texture(palette, iid), len(boxes))
    return out


if __name__ == "__main__":
    for iid, (m, t, n) in build_all().items():
        print(f"{iid:22s} {n:3d} boxes")
