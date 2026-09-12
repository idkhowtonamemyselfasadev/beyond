"""Twenty monuments: the big things in the End, the ones you see from another island.

The cities are places people lived. These are not - they are the leftovers of whatever
made the End: a needle you can see across the void, a ring of stone with nothing in the
middle, a hull the size of a hill, a well that goes down further than it should.

Same construction as everything else here: shared parts, a spec table, one single-piece
jigsaw template each, so twenty monuments are twenty sets of choices rather than twenty
hand-drawn boxes. They sit on their own structure set, spaced far apart, because a
landmark you meet every two minutes is scenery.
"""
import math
import os
import random
import zlib

import nbt
from piece import Piece

PURPUR = 'purpur_block'
PILLAR = 'purpur_pillar'
SLAB = 'purpur_slab'
END = 'end_stone'
BRICK = 'end_stone_bricks'
OBS = 'obsidian'
CRY = 'crying_obsidian'
AMETHYST = 'amethyst_block'
SCULK = 'sculk'
ROD = 'end_rod'
LAMP = 'sea_lantern'
GLASS = 'purple_stained_glass'
CHORUS = 'chorus_flower'


# ------------------------------------------------------------------------- parts

def shell(p, cx, cz, y0, y1, radius_at, block_at, square=False, holes=None):
    """A hollow body whose width is a function of height."""
    for y in range(y0, y1 + 1):
        rad = max(0, radius_at(y))
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                d = max(abs(x), abs(z)) if square else math.hypot(x, z)
                if rad - 1 < d <= rad:
                    if holes and holes(x, z, y):
                        p.air(cx + x, y, cz + z)
                    else:
                        p.set(cx + x, y, cz + z, block_at(x, z, y))
                elif d <= rad - 1:
                    p.air(cx + x, y, cz + z)


def banded(a, b, period=5):
    return lambda x, z, y: a if (y // period) % 2 == 0 else b


def floors(p, cx, cz, y0, y1, radius_at, every=8, block=SLAB):
    for y in range(y0 + every, y1, every):
        rad = radius_at(y)
        for x in range(-rad + 1, rad):
            for z in range(-rad + 1, rad):
                if math.hypot(x, z) < rad - 0.5:
                    p.set(cx + x, y, cz + z, block)
        p.air(cx + 1, y, cz)


def climb(p, cx, cz, y0, y1):
    for y in range(y0, y1):
        p.set(cx + 1, y, cz, 'ladder', {'facing': 'west'})


def lantern_ring(p, cx, cz, y, rad, block=ROD):
    for i in range(8):
        a = i * math.pi / 4
        p.set(cx + round(rad * math.cos(a)), y, cz + round(rad * math.sin(a)),
              block, {'facing': 'up'} if block == ROD else None)


def loot(p, x, y, z, table='beyond:chests/monument'):
    p.chest(x, y, z, table)


def plinth(p, cx, cz, rad, depth=3, block=BRICK):
    for i in range(depth):
        w = rad + depth - i
        for x in range(-w, w + 1):
            for z in range(-w, w + 1):
                if max(abs(x), abs(z)) >= w - 1:
                    p.set(cx + x, i, cz + z, block if i % 2 else END)


# ------------------------------------------------------------------- the twenty

def _tall(height, base, top, shape, blocks, crown, extra=None):
    def build(r):
        h = r.randrange(height[0], height[1] + 1)
        pad = base + 6
        c = pad
        p = Piece()

        def rad(y):
            t = y / max(1, h)
            if shape == 'straight':
                return base
            if shape == 'taper':
                return max(top, round(base - (base - top) * t))
            if shape == 'step':
                return max(top, base - int(t * (base - top) * 1.15))
            if shape == 'waist':
                return max(top, round(base - (base - top)
                                      * math.sin(t * math.pi) * 0.85))
            return base

        plinth(p, c, c, base)
        shell(p, c, c, 0, h, rad, banded(*blocks),
              holes=lambda x, z, y: y % 7 == 3 and 4 < y < h - 3
              and (x == 0 or z == 0) and max(abs(x), abs(z)) == rad(y))
        floors(p, c, c, 0, h, rad)
        climb(p, c, c, 1, h)
        loot(p, c + base - 2, 1, c)
        loot(p, c, h - 7, c + max(1, top - 1), 'beyond:chests/monument_deep')

        tip = rad(h)
        if crown == 'spire':
            for i in range(tip * 4):
                w = max(0, tip - i // 3)
                for x in range(-w, w + 1):
                    for z in range(-w, w + 1):
                        if max(abs(x), abs(z)) == w:
                            p.set(c + x, h + i, c + z, blocks[1])
            p.set(c, h + tip * 4, c, LAMP)
        elif crown == 'ring':
            lantern_ring(p, c, c, h + 2, tip + 3)
            for x in range(-tip - 3, tip + 4):
                for z in range(-tip - 3, tip + 4):
                    if tip + 1 < math.hypot(x, z) <= tip + 3:
                        p.set(c + x, h + 1, c + z, SLAB)
        elif crown == 'crystal':
            for i in range(7):
                w = max(0, 3 - i // 2)
                p.fill(c - w, h + i, c - w, c + w, h + i, c + w, AMETHYST)
            p.set(c, h + 7, c, 'budding_amethyst')
        elif crown == 'eye':
            p.fill(c - 2, h + 1, c - 2, c + 2, h + 3, c + 2, GLASS)
            p.set(c, h + 2, c, LAMP)
        if extra:
            extra(p, c, h, base, top, r)
        return p
    return build


def _wings(p, c, h, base, top, r):
    for d in (-1, 1):
        for i in range(1, base + 9):
            p.set(c + d * (base + i), h - 6 - i // 2, c, PURPUR)
            if i % 3 == 0:
                p.set(c + d * (base + i), h - 5 - i // 2, c, ROD, {'facing': 'up'})


def _buttress(p, c, h, base, top, r):
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        dx, dz = math.cos(a), math.sin(a)
        for step in range(base + 10):
            y = max(0, h // 2 - step * 2)
            p.set(c + round(dx * (base + step)), y, c + round(dz * (base + step)),
                  BRICK)
            if y == 0:
                break


def _hive(p, c, h, base, top, r):
    for tier in range(6, h - 4, 9):
        rad = max(2, base - tier // 12)
        for x in range(-rad - 2, rad + 3):
            for z in range(-rad - 2, rad + 3):
                if rad < math.hypot(x, z) <= rad + 2 and (x + z + tier) % 2 == 0:
                    p.set(c + x, tier, c + z, PURPUR)
                    p.air(c + x, tier + 1, c + z)


def _chorus(p, c, h, base, top, r):
    for tier in range(h // 3, h, 6):
        rad = 5 + (tier % 4)
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                d = math.hypot(x, z)
                if d <= rad and (x + z + tier) % 3 == 0:
                    p.set(c + x, tier, c + z, 'chorus_plant')
                    if r.random() < 0.2:
                        p.set(c + x, tier + 1, c + z, CHORUS)


def ring_monument(r):
    """A ring of stone standing on edge, with nothing in the middle."""
    p = Piece()
    rad = r.choice([16, 20, 24])
    c = rad + 3
    thick = 3
    for y in range(rad * 2 + 1):
        for z in range(rad * 2 + 1):
            d = math.hypot(y - rad, z - rad)
            if rad - thick < d <= rad:
                for x in range(3):
                    p.set(c - 1 + x, y + 2, c - rad + z,
                          PURPUR if (y + z) % 6 else BRICK)
    plinth(p, c, c, 4)
    for i in range(6):
        a = i * math.pi / 3
        p.set(c, 2 + rad + round(rad * 0.9 * math.sin(a)),
              c + round(rad * 0.9 * math.cos(a)), LAMP)
    loot(p, c, 3, c + 2)
    return p


def bridgeway(r):
    """A road to somewhere that is not there any more."""
    p = Piece()
    length = r.choice([60, 80, 100])
    for z in range(length):
        broken = 0.10 + 0.35 * abs(math.sin(z / 11.0))
        if r.random() < broken:
            continue
        for x in range(5):
            p.set(x, 1, z, BRICK if (x + z) % 7 == 0 else PURPUR)
        if z % 9 == 0:
            for x in (0, 4):
                for y in range(2, 6):
                    p.set(x, y, z, PILLAR)
                p.set(x, 6, z, ROD, {'facing': 'up'})
        if z % 17 == 0:
            loot(p, 2, 2, z)
    return p


def void_well(r):
    """A shaft cut straight down through the island, lit all the way."""
    p = Piece()
    depth = r.choice([30, 40])
    rad = 5
    c = rad + 3
    for y in range(depth):
        for x in range(-rad - 1, rad + 2):
            for z in range(-rad - 1, rad + 2):
                d = math.hypot(x, z)
                if rad < d <= rad + 1:
                    p.set(c + x, 20 - y, c + z, BRICK if y % 6 else PURPUR)
                elif d <= rad:
                    p.air(c + x, 20 - y, c + z)
        if y % 6 == 0:
            lantern_ring(p, c, 20 - y, c, rad)
    plinth(p, c, c, rad + 1, depth=2)
    for x in range(-rad, rad + 1):
        for z in range(-rad, rad + 1):
            if math.hypot(x, z) <= rad:
                p.air(c + x, 21, c + z)
    loot(p, c + rad - 1, 22, c)
    return p


def pillar_field(r):
    """Forty pillars of different heights, and one of them is hollow."""
    p = Piece()
    w = r.choice([40, 52])
    special = (r.randrange(6, w - 6), r.randrange(6, w - 6))
    for _ in range(r.choice([26, 34, 42])):
        x, z = r.randrange(2, w - 2), r.randrange(2, w - 2)
        h = r.choice([6, 10, 14, 20, 28])
        for y in range(h):
            p.set(x, y, z, PILLAR if y % 4 else PURPUR)
        p.set(x, h, z, ROD, {'facing': 'up'})
    sx, sz = special
    for y in range(24):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if abs(dx) + abs(dz) == 1:
                    p.set(sx + dx, y, sz + dz, BRICK)
                elif dx == 0 and dz == 0:
                    p.air(sx, y, sz)
    loot(p, sx, 1, sz, 'beyond:chests/monument_deep')
    return p


def shattered_hull(r):
    """A ship the size of a hill, broken over the rock."""
    p = Piece()
    length = r.choice([46, 58])
    half = 7
    for z in range(length):
        taper = max(0, 5 - min(z, length - 1 - z))
        w = max(1, half - taper)
        gone = 0.45 * max(0.0, math.sin((z / length) * math.pi * 2.5))
        for y in range(9):
            for x in range(half - w, half + w + 1):
                edge = x in (half - w, half + w) or y == 0
                if edge and r.random() > gone:
                    p.set(x, y + 2, z, PURPUR if (x + y) % 5 else BRICK)
                elif not edge:
                    p.air(x, y + 2, z)
    for z in range(6, length - 6, 14):        # broken masts
        for y in range(11, 11 + r.choice([4, 8, 14])):
            p.set(half, y, z, PILLAR)
        p.set(half, 11 + 3, z, ROD, {'facing': 'up'})
    loot(p, half, 3, length - 8, 'beyond:chests/monument_deep')
    loot(p, half - 2, 3, 8)
    return p


MONUMENTS = {
    'void_spire':        _tall((70, 96), 5, 3, 'taper',  (PURPUR, BRICK), 'spire'),
    'watchspire':        _tall((52, 68), 6, 4, 'taper',  (BRICK, END), 'ring', _buttress),
    'obsidian_gate':     _tall((44, 58), 7, 7, 'straight', (OBS, CRY), 'eye'),
    'crystal_cathedral': _tall((60, 82), 9, 4, 'step',   (PURPUR, AMETHYST), 'crystal',
                               _buttress),
    'starforge':         _tall((46, 60), 8, 6, 'straight', (BRICK, OBS), 'ring'),
    'shulker_hive':      _tall((48, 64), 7, 3, 'taper',  (PURPUR, PILLAR), 'ring', _hive),
    'chorus_titan':      _tall((54, 72), 6, 3, 'waist',  (PURPUR, BRICK), 'spire',
                               _chorus),
    'mausoleum_of_wings': _tall((40, 54), 8, 5, 'step',  (BRICK, PURPUR), 'eye', _wings),
    'shadow_keep':       _tall((44, 58), 9, 7, 'step',   (SCULK, OBS), 'ring'),
    'frozen_beacon':     _tall((50, 66), 6, 4, 'taper',  ('packed_ice', 'blue_ice'),
                               'crystal'),
    'amber_hall':        _tall((38, 50), 10, 8, 'straight', ('smooth_sandstone', BRICK),
                               'ring'),
    'dragon_shrine':     _tall((42, 56), 8, 5, 'step',   (OBS, BRICK), 'eye', _wings),
    'dust_throne':       _tall((36, 48), 11, 9, 'straight', ('sandstone', END), 'ring'),
    'sunken_vault':      _tall((34, 46), 9, 7, 'straight', ('prismarine_bricks',
                                                            'dark_prismarine'), 'eye'),
    'endermans_folly':   _tall((40, 52), 10, 4, 'step',  (PURPUR, END), 'spire', _hive),
    'ring_monument':     ring_monument,
    'bridgeway':         bridgeway,
    'void_well':         void_well,
    'pillar_field':      pillar_field,
    'shattered_hull':    shattered_hull,
}
VARIANTS = 2


def emit(write, ns, biome_tag):
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'src', 'main', 'resources', 'data', ns, 'structure')
    made = 0
    for name, builder in MONUMENTS.items():
        elements = []
        for k in range(VARIANTS):
            r = random.Random(zlib.crc32(f'{name}/{k}'.encode()))
            path = os.path.join(root, name, f'{k}.nbt')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            nbt.write(path, builder(r).to_nbt())
            made += 1
            elements.append({'weight': 1, 'element': {
                'element_type': 'minecraft:single_pool_element',
                'location': f'{ns}:{name}/{k}',
                'processors': 'minecraft:empty',
                'projection': 'rigid'}})
        write(f'{ns}/worldgen/template_pool/{name}.json',
              {'fallback': 'minecraft:empty', 'elements': elements})
        write(f'{ns}/worldgen/structure/{name}.json', {
            'type': 'minecraft:jigsaw',
            'biomes': biome_tag,
            'step': 'surface_structures',
            'spawn_overrides': {},
            'start_pool': f'{ns}:{name}',
            'size': 1,
            'max_distance_from_center': 116,
            'start_height': {'absolute': 0},
            'project_start_to_heightmap': 'WORLD_SURFACE_WG',
            'use_expansion_hack': False,
            'terrain_adaptation': 'beard_thin'})

    write(f'{ns}/worldgen/structure_set/monuments.json', {
        'structures': [{'structure': f'{ns}:{n}', 'weight': 1} for n in MONUMENTS],
        'placement': {'type': 'minecraft:random_spread', 'spacing': 26,
                      'separation': 11, 'salt': 7719431}})
    return made
