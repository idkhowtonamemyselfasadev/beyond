"""Ten more End cities, and the throne the boss sits on.

Vanilla has one city: purpur towers, a sail, a ship if you are lucky. These are ten
more shapes for the same idea - a spire, a bridge run, a wreck, a library, a hollowed
crystal, a drowned hall - built from the same purpur-and-end-stone vocabulary so they
read as the same civilisation, and placed on their own structure set alongside the
vanilla one.

Everything is a single-piece jigsaw template, the same approach as the Overworld mod:
no jigsaw blocks, size 1, so the shape is exactly what is drawn here.
"""
import math
import os
import random
import zlib

import nbt
from piece import Piece

# The End builds out of a small palette, which is most of why it reads as one place.
PURPUR = 'purpur_block'
PILLAR = 'purpur_pillar'
SLAB = 'purpur_slab'
STAIRS = 'purpur_stairs'
END = 'end_stone'
BRICK = 'end_stone_bricks'
GLOW = 'end_rod'
LAMP = 'sea_lantern'
MAGENTA = 'magenta_stained_glass'


def _tower(p, cx, cz, height, rad, hollow=True, bands=True):
    for y in range(height + 1):
        block = PILLAR if (bands and y % 5 == 0) else PURPUR
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                d = max(abs(x), abs(z))
                if d == rad:
                    p.set(cx + x, y, cz + z, block)
                elif hollow:
                    p.air(cx + x, y, cz + z)
        if y % 6 == 0 and y > 0:
            for x in range(-rad + 1, rad):
                for z in range(-rad + 1, rad):
                    p.set(cx + x, y, cz + z, SLAB)
            p.air(cx + 1, y, cz)
    for y in range(1, height):
        p.set(cx + 1, y, cz, 'ladder', {'facing': 'west'})


def _rim(p, cx, cz, y, rad, block=SLAB):
    for x in range(-rad - 1, rad + 2):
        for z in range(-rad - 1, rad + 2):
            if max(abs(x), abs(z)) > rad - 1:
                p.set(cx + x, y, cz + z, block)


def _sail(p, x, y, z, height, length):
    for i in range(height):
        for j in range(length):
            p.set(x, y + i, z + j, MAGENTA if (i + j) % 4 else 'purpur_block')


def _loot(p, x, y, z, table='beyond:chests/end_city'):
    p.chest(x, y, z, table)


def _shulker(p, x, y, z):
    p.set(x, y, z, 'purpur_block')


# --------------------------------------------------------------------------- cities

def spire_city(r):
    p = Piece()
    h = r.choice([34, 42, 50])
    rad = 4
    c = rad + 2
    _tower(p, c, c, h, rad)
    for y in range(8, h - 4, 8):
        _rim(p, c, c, y, rad + 2)
        p.set(c + rad + 1, y + 1, c, GLOW, {'facing': 'up'})
        p.set(c - rad - 1, y + 1, c, GLOW, {'facing': 'up'})
    _rim(p, c, c, h + 1, rad + 2)
    p.set(c, h + 2, c, LAMP)
    _loot(p, c + 1, 2, c + 1)
    _loot(p, c - 1, h - 6, c - 1, 'beyond:chests/end_city_treasure')
    return p


def bridge_city(r):
    p = Piece()
    towers = r.choice([3, 4])
    gap = 16
    heights = [r.choice([20, 26, 32]) for _ in range(towers)]
    for i, h in enumerate(heights):
        _tower(p, 6, 6 + i * gap, h, 3)
        _rim(p, 6, 6 + i * gap, h + 1, 5)
        p.set(6, h + 2, 6 + i * gap, LAMP)
        if i:
            y = min(heights[i - 1], h) - 4
            for z in range(6 + (i - 1) * gap + 3, 6 + i * gap - 2):
                for x in (5, 6, 7):
                    p.set(x, y, z, PURPUR)
                p.set(4, y + 1, z, 'purpur_slab')
                p.set(8, y + 1, z, 'purpur_slab')
    _loot(p, 6, 2, 6)
    _loot(p, 6, heights[-1] - 5, 6 + (towers - 1) * gap,
          'beyond:chests/end_city_treasure')
    return p


def hanging_city(r):
    p = Piece()
    c, top = 9, 30
    _tower(p, c, c, 10, 4)
    for tier, drop in enumerate(range(10, 0, -3)):
        rad = 4 + tier
        _rim(p, c, drop, c, 0)          # placeholder, replaced below
    # platforms hanging under the tower on chains
    for tier in range(r.choice([3, 4])):
        y = 8 - tier * 3
        rad = 3 + tier
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                if abs(x) + abs(z) <= rad:
                    p.set(c + x, y, c + z, PURPUR if (x + z) % 3 else BRICK)
        for dx, dz in ((-rad, 0), (rad, 0), (0, -rad), (0, rad)):
            for yy in range(y + 1, y + 3):
                p.set(c + dx, yy, c + dz, 'chain')
        p.set(c + rad - 1, y + 1, c, GLOW, {'facing': 'up'})
    _loot(p, c, 9, c)
    _loot(p, c, 2, c + 2, 'beyond:chests/end_city_treasure')
    return p


def wreck_city(r):
    p = Piece()
    h = r.choice([18, 24])
    c = 6
    for y in range(h):
        rad = 4
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                if max(abs(x), abs(z)) == rad and r.random() < 0.72 - y * 0.012:
                    p.set(c + x, y, c + z, PURPUR if r.random() < 0.7 else BRICK)
                elif max(abs(x), abs(z)) < rad:
                    p.air(c + x, y, c + z)
    for _ in range(r.choice([12, 18])):          # rubble at the foot
        p.set(c + r.randrange(-7, 8), 0, c + r.randrange(-7, 8),
              r.choice([PURPUR, BRICK, END, SLAB]))
    p.set(c, h, c, GLOW, {'facing': 'up'})
    _loot(p, c + 2, 1, c - 2)
    return p


def crystal_city(r):
    p = Piece()
    c, h = 8, r.choice([24, 30])
    _tower(p, c, c, h, 5)
    for y in range(3, h - 2, 4):                 # a geode growing through it
        rad = 2 + (y // 7) % 3
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                if abs(x) + abs(z) == rad:
                    p.set(c + x, y, c + z, 'amethyst_block')
    p.set(c, h - 2, c, 'budding_amethyst')
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        p.set(c + dx, h - 2, c + dz, 'amethyst_cluster', {'facing': 'up'})
    _rim(p, c, c, h + 1, 6)
    _loot(p, c + 2, 2, c, 'beyond:chests/end_city_treasure')
    return p


def library_city(r):
    p = Piece()
    c, h = 8, r.choice([22, 28])
    _tower(p, c, c, h, 5)
    for y in range(2, h - 3, 6):
        for x in range(-4, 5):
            for z in (-4, 4):
                p.set(c + x, y + 1, c + z, 'bookshelf')
                p.set(c + x, y + 2, c + z, 'bookshelf')
        p.set(c, y + 1, c, 'lectern', {'facing': 'north'})
        p.set(c + 3, y + 1, c + 3, GLOW, {'facing': 'up'})
    p.set(c, h - 3, c, 'enchanting_table')
    _rim(p, c, c, h + 1, 6)
    _loot(p, c - 2, 2, c + 2)
    _loot(p, c + 2, h - 4, c, 'beyond:chests/end_city_treasure')
    return p


def drowned_city(r):
    p = Piece()
    w = r.choice([21, 27])
    for x in range(w):
        for z in range(w):
            if (x + z) % 7 == 0 or max(abs(x - w // 2), abs(z - w // 2)) == w // 2:
                p.set(x, 0, z, BRICK)
            else:
                p.set(x, 0, z, PURPUR)
    for i in range(r.choice([5, 7, 9])):         # stumps of towers
        x, z = r.randrange(2, w - 2), r.randrange(2, w - 2)
        hh = r.choice([3, 5, 8, 12])
        _tower(p, x, z, hh, 2)
        p.set(x, hh + 1, z, GLOW, {'facing': 'up'})
    c = w // 2
    p.fill(c - 2, 1, c - 2, c + 2, 1, c + 2, 'water', {'level': '0'})
    _loot(p, c, 1, c - 3)
    return p


def beacon_city(r):
    p = Piece()
    c, h = 8, r.choice([26, 32])
    _tower(p, c, c, h, 5)
    p.fill(c - 2, h - 3, c - 2, c + 2, h - 3, c + 2, 'iron_block')
    p.set(c, h - 2, c, 'beacon')
    for x in range(-1, 2):
        for z in range(-1, 2):
            p.set(c + x, h - 1, c + z, 'glass')
    for y in range(4, h - 6, 5):                 # shulker alcoves
        for dx, dz in ((-4, 0), (4, 0), (0, -4), (0, 4)):
            p.air(c + dx, y, c + dz)
            p.set(c + dx, y - 1, c + dz, SLAB)
    _rim(p, c, c, h + 1, 6)
    _loot(p, c + 2, 2, c + 2)
    _loot(p, c, h - 6, c + 3, 'beyond:chests/end_city_treasure')
    return p


def sail_city(r):
    p = Piece()
    c, h = 7, r.choice([28, 34])
    _tower(p, c, c, h, 4)
    for y in range(6, h - 6, 9):                 # sails on booms
        length = r.choice([7, 9])
        p.fill(c + 5, y, c, c + 5, y, c + length, PILLAR)
        _sail(p, c + 5, y + 1, c, 6, length)
        for i in range(1, 5):
            p.set(c + i, y, c, PILLAR)
    _rim(p, c, c, h + 1, 5)
    p.set(c, h + 2, c, LAMP)
    _loot(p, c, 2, c)
    return p


def gate_city(r):
    p = Piece()
    span, h = 18, r.choice([20, 26])
    for side in (0, span):
        _tower(p, 5, 5 + side, h, 4)
        p.set(5, h + 1, 5 + side, GLOW, {'facing': 'up'})
    for z in range(6, span + 4):                 # the arch over the road
        for x in range(2, 9):
            p.set(x, h - 3, z, PURPUR if (x + z) % 5 else BRICK)
        p.set(1, h - 2, z, SLAB)
        p.set(9, h - 2, z, SLAB)
    for z in range(4, span + 6):                 # the road under it
        for x in range(3, 8):
            p.set(x, 0, z, BRICK if (x + z) % 6 == 0 else PURPUR)
    _loot(p, 5, 2, 5)
    _loot(p, 5, 2, 5 + span, 'beyond:chests/end_city_treasure')
    return p


def throne_city(r):
    """Where the boss waits. Bigger than the rest, and open enough to fight in."""
    p = Piece()
    w = 31
    c = w // 2
    for x in range(w):
        for z in range(w):
            d = max(abs(x - c), abs(z - c))
            if d <= c:
                p.set(x, 0, z, BRICK if (x + z) % 8 == 0 else PURPUR)
    for i in range(0, w, 6):                     # colonnade
        for x, z in ((i, 0), (i, w - 1), (0, i), (w - 1, i)):
            for y in range(1, 13):
                p.set(x, y, z, PILLAR if y % 4 else PURPUR)
            p.set(x, 13, z, GLOW, {'facing': 'up'})
    for step in range(4):                        # the dais
        lo, hi = c - 5 + step, c + 5 - step
        for x in range(lo, hi + 1):
            for z in range(lo, hi + 1):
                p.set(x, 1 + step, z, PURPUR)
    p.set(c, 5, c, 'dragon_egg')
    p.set(c - 1, 5, c, LAMP)
    p.set(c + 1, 5, c, LAMP)
    _loot(p, c - 3, 5, c - 3, 'beyond:chests/end_city_treasure')
    _loot(p, c + 3, 5, c + 3, 'beyond:chests/end_city_treasure')
    return p


CITIES = {
    'spire_city': spire_city, 'bridge_city': bridge_city,
    'hanging_city': hanging_city, 'wreck_city': wreck_city,
    'crystal_city': crystal_city, 'library_city': library_city,
    'drowned_city': drowned_city, 'beacon_city': beacon_city,
    'sail_city': sail_city, 'gate_city': gate_city,
    'throne_city': throne_city,
}
VARIANTS = 3


def emit(write, ns, biome_tag):
    """Templates, pools, structures, one shared set, and a tag of where they go."""
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'src', 'main', 'resources', 'data', ns, 'structure')
    made = 0
    for name, builder in CITIES.items():
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

    # One set for all of them, so ten cities cost one placement check per chunk.
    write(f'{ns}/worldgen/structure_set/cities.json', {
        'structures': [{'structure': f'{ns}:{n}', 'weight': 3 if n != 'throne_city'
                        else 1} for n in CITIES],
        'placement': {'type': 'minecraft:random_spread', 'spacing': 14,
                      'separation': 6, 'salt': 5512377}})

    # And vanilla's own cities, closer together than they were.
    write('minecraft/worldgen/structure_set/end_cities.json', {
        'structures': [{'structure': 'minecraft:end_city', 'weight': 1}],
        'placement': {'type': 'minecraft:random_spread', 'spacing': 11,
                      'separation': 5, 'salt': 10387313}})
    return made
