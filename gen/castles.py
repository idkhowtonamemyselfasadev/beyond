"""Three castles: the big places, walled complexes you can walk through for ten minutes.

The monuments are single tall shapes you steer towards. These are the opposite - wide,
low, and full of rooms: a fortress of obsidian behind a moat, a hill-fort of purpur
climbing through three terraces to a domed palace, and a bastion of prismarine built
round a pool with a lighthouse in the middle of it.

Same construction as the monuments: shared parts, one builder per kind, a single-piece
jigsaw template for each of three seeded variants, and their own structure set spaced far
enough apart that finding one is an event. The one difference is the foundation. A
template cannot reach below its own origin, so every castle is drawn with its courtyard
at y = G and the structure sunk G blocks into the ground, which puts six rows of solid
stone under the whole footprint and the courtyard exactly on the surface.
"""
import math
import os
import random
import zlib

import nbt
from piece import Piece

G = 6            # the row the surface sits on inside a template
F = G + 1        # where your feet are in the courtyard

END = 'end_stone'
BRICK = 'end_stone_bricks'
PURPUR = 'purpur_block'
PILLAR = 'purpur_pillar'
OBS = 'obsidian'
CRY = 'crying_obsidian'
BLACK = 'blackstone'
PB = 'polished_blackstone'
PBB = 'polished_blackstone_bricks'
TILES = 'deepslate_tiles'
PRIS = 'prismarine'
PBR = 'prismarine_bricks'
DARK = 'dark_prismarine'
ROD = 'end_rod'
LAMP = 'sea_lantern'
SOUL = 'soul_lantern'
WATER = 'water'
BARS = 'iron_bars'

SIDES = {'east': (1, 0), 'west': (-1, 0), 'south': (0, 1), 'north': (0, -1)}
NAMES = {v: k for k, v in SIDES.items()}


# ------------------------------------------------------------------------- parts

def _b(block, x, z, y):
    return block(x, z, y) if callable(block) else block


def dname(dx, dz):
    return NAMES[(dx, dz)]


def frame(side):
    """A local frame for one side of a square: `at(u, v)` is u blocks out from the
    centre along that side's axis and v blocks along the wall. Returns it with the
    unit vector of +v, which is the way stairs on that side climb."""
    ox, oz = SIDES[side]
    ax, az = -oz, ox
    return (lambda u, v: (ox * u + ax * v, oz * u + az * v)), (ax, az)


def band(p, cx, cz, r0, r1, y0, y1, block):
    """A square band r0 <= max(|dx|,|dz|) <= r1, rows y0..y1."""
    for x in range(-r1, r1 + 1):
        for z in range(-r1, r1 + 1):
            if r0 <= max(abs(x), abs(z)) <= r1:
                for y in range(y0, y1 + 1):
                    p.set(cx + x, y, cz + z, _b(block, x, z, y))


def merlons(p, cx, cz, r, y, block, height=1, rods=0):
    """Crenellations round a square ring, every other block, with an end rod on every
    `rods`-th one so the wall reads at night."""
    for x in range(-r, r + 1):
        for z in range(-r, r + 1):
            if max(abs(x), abs(z)) != r:
                continue
            lit = rods and ((abs(z) == r and x % rods == 0) or (abs(x) == r and z % rods == 0))
            if (x + z) % 2 == 0 or lit:
                p.fill(cx + x, y, cz + z, cx + x, y + height - 1, cz + z, block)
                if lit:
                    p.set(cx + x, y + height, cz + z, ROD, {'facing': 'up'})


def round_tower(p, cx, cz, rad, y0, y1, block, floors=(), floor_block=None,
                ladder=True, cap=True, base=False):
    """A hollow cylinder: a shell, floors with a hatch, a ladder up the inside against
    the east wall, a roof you can stand on and merlons round its edge."""
    floor_block = floor_block or block
    for y in range(y0, y1 + 1):
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                d = math.hypot(x, z)
                if rad - 1 < d <= rad:
                    p.set(cx + x, y, cz + z, _b(block, x, z, y))
                elif d <= rad - 1:
                    p.air(cx + x, y, cz + z)
    for y in ([y0] if base else []) + list(floors) + ([y1] if cap else []):
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                if math.hypot(x, z) <= rad - 1 and not (x == rad - 1 and z == 0 and y != y0):
                    p.set(cx + x, y, cz + z, _b(floor_block, x, z, y))
    if ladder:
        for y in range(y0 + 1, y1 + 1):
            p.set(cx + rad - 1, y, cz, 'ladder', {'facing': 'west'})
    if cap:
        for x in range(-rad, rad + 1):
            for z in range(-rad, rad + 1):
                if rad - 1 < math.hypot(x, z) <= rad and (x + z) % 2 == 0:
                    p.set(cx + x, y1 + 1, cz + z, _b(block, x, z, y1 + 1))


def diag_door(p, tx, tz, rad, sx, sz, y, height=3):
    """Open a round tower towards the centre of the castle it stands at the corner of:
    the shell cells nearest the inward diagonal."""
    for x in range(-rad, rad + 1):
        for z in range(-rad, rad + 1):
            if x * sx < 0 and z * sz < 0 and abs(abs(x) - abs(z)) <= 1 \
                    and rad - 1 < math.hypot(x, z) <= rad:
                for k in range(height):
                    p.air(tx + x, y + k, tz + z)


def stair_run(p, x, y, z, n, dx, dz, block, under=None, headroom=2):
    """n+1 stairs climbing one block a step towards (dx, dz), solid underneath, and the
    air a player needs above each step - which is also what cuts the hole through
    whatever floor the run arrives at."""
    for i in range(n + 1):
        sx, sz = x + dx * i, z + dz * i
        if under:
            for yy in range(y, y + i):
                p.set(sx, yy, sz, under)
        p.set(sx, y + i, sz, block, {'facing': dname(dx, dz)})
        for yy in range(y + i + 1, y + i + 1 + headroom):
            p.air(sx, yy, sz)


def loot(p, x, y, z, table='beyond:chests/monument', facing='north'):
    p.chest(x, y, z, table, facing)


def bed(p, x, y, z, dx, dz, colour='purple'):
    """Foot at (x, z), head one block along (dx, dz)."""
    f = dname(dx, dz)
    p.set(x, y, z, colour + '_bed', {'facing': f, 'part': 'foot', 'occupied': 'false'})
    p.set(x + dx, y, z + dz, colour + '_bed', {'facing': f, 'part': 'head', 'occupied': 'false'})


def hanging_lantern(p, x, y, z, block=SOUL):
    """A lantern on a chain under the block at y+2."""
    p.set(x, y + 1, z, 'chain')
    p.set(x, y, z, block, {'hanging': 'true'})


# ------------------------------------------------------------ 1. obsidian fortress

def obsidian_fortress(r):
    """Curtain walls behind a moat, four corner towers, a gatehouse and bridge, and a
    three-floor keep in the middle of a courtyard with a well and a market."""
    W = r.choice([26, 27, 28])          # outer half-width of the curtain wall
    T = r.choice([5, 6])                # corner tower radius
    K = r.choice([10, 11])              # keep half-width
    WH = G + r.choice([10, 11, 12])     # walkway floor on top of the wall
    TH = WH + r.choice([9, 11, 13])     # corner tower roof
    M = W + 10                          # outer lining of the moat
    c = M + 1
    p = Piece()
    STAIR = 'polished_blackstone_brick_stairs'
    RAIL = 'polished_blackstone_brick_wall'
    awning = r.choice([('purple_wool', 'black_wool'), ('magenta_wool', 'black_wool'),
                       ('purple_wool', 'white_wool')])

    # foundation, courtyard paving, and the air the courtyard needs above it
    p.fill(c - M, 0, c - M, c + M, G - 1, c + M, BLACK)
    for x in range(-(W - 4), W - 3):
        for z in range(-(W - 4), W - 3):
            p.set(c + x, G, c + z, PB if (x % 6 == 0 or z % 6 == 0) else PBB)
            for y in range(F, F + 9):
                p.air(c + x, y, c + z)

    # curtain walls: skins of polished blackstone brick with a course of obsidian every
    # fourth row, blackstone inside, a two-wide walkway on top behind merlons
    def curtain(x, z, y):
        d = max(abs(x), abs(z))
        if d in (W - 3, W):
            return OBS if y % 4 == 0 else PBB
        return BLACK
    band(p, c, c, W - 3, W, G, WH, curtain)
    band(p, c, c, W - 2, W - 1, WH + 1, WH + 3, 'air')
    band(p, c, c, W, W, WH + 1, WH + 1, OBS)
    merlons(p, c, c, W, WH + 2, PBB, rods=8)
    band(p, c, c, W - 3, W - 3, WH + 1, WH + 1, RAIL)

    # berm, then the moat: deepslate-tiled walls and floor, water to the brim
    band(p, c, c, W + 1, W + 2, G, G, BLACK)
    band(p, c, c, W + 3, W + 3, 0, G, TILES)
    band(p, c, c, M, M, 0, G, TILES)
    band(p, c, c, W + 4, W + 9, 1, 1, TILES)
    band(p, c, c, W + 4, W + 9, 2, G, WATER)

    # stairs from the courtyard up to the walkway, one on the north wall, one south
    n = WH - F
    stair_run(p, c - 13, F, c - W + 4, n, 1, 0, STAIR, PBB)
    stair_run(p, c + 13, F, c + W - 4, n, -1, 0, STAIR, PBB)
    p.air(c - 13 + n, WH + 1, c - W + 3)
    p.air(c + 13 - n, WH + 1, c + W - 3)

    # corner towers: banded crying obsidian, floors at the walkway level, the walkway
    # carried straight through them, a door onto the courtyard
    def tower_block(x, z, y):
        return CRY if y % 6 == 0 else (OBS if y % 6 == 3 else PBB)
    towers = [(sx, sz) for sx in (-1, 1) for sz in (-1, 1)]
    for i, (sx, sz) in enumerate(towers):
        tx, tz = c + sx * W, c + sz * W
        fl = [G + 5, WH] + ([WH + 6] if WH + 6 < TH - 1 else [])
        round_tower(p, tx, tz, T, G, TH, tower_block, floors=fl, floor_block=PB, base=True)
        for x in range(-T, T + 1):
            for z in range(-T, T + 1):
                if math.hypot(x, z) > T:
                    continue
                ax, az = abs(sx * W + x), abs(sz * W + z)
                if W - 2 <= max(ax, az) <= W - 1:
                    p.set(tx + x, WH, tz + z, PB)
                    for y in range(WH + 1, WH + 4):
                        p.air(tx + x, y, tz + z)
        diag_door(p, tx, tz, T, sx, sz, F)
        p.set(tx - sx * (T - 3), G + 6, tz - sz * (T - 3), SOUL)
        if i % 2 == 0:
            loot(p, tx - sx, G + 6, tz + sz * (T - 2))
        p.set(tx, TH + 1, tz, CRY)
        p.set(tx, TH + 2, tz, ROD, {'facing': 'up'})

    # gatehouse on the south wall: a block straddling the wall, rooms either side of
    # the passage, a raised portcullis of iron bars, the walkway through its top room
    gz = c + W
    p.fill(c - 6, G, gz - 5, c + 6, WH + 5, gz, PBB)
    p.fill(c - 5, F, gz - 4, c + 5, WH + 4, gz - 1, 'air')
    p.fill(c - 5, G + 6, gz - 4, c + 5, G + 6, gz - 1, PB)
    p.fill(c - 5, WH, gz - 4, c + 5, WH, gz - 1, PB)
    p.fill(c - 2, F, gz - 4, c + 2, F + 4, gz - 1, PBB)        # passage walls and roof
    p.fill(c - 1, F, gz - 6, c + 1, F + 3, gz + 1, 'air')      # the passage
    p.fill(c - 1, F + 2, gz, c + 1, F + 3, gz, BARS)           # portcullis, raised
    p.set(c - 2, F + 4, gz, CRY)
    p.set(c + 2, F + 4, gz, CRY)
    hanging_lantern(p, c, F + 2, gz - 2)
    for y in range(F, WH + 6):
        p.set(c + 5, y, gz - 2, 'ladder', {'facing': 'west'})
    for x in (-6, 6):
        p.fill(c + x, WH + 1, gz - 2, c + x, WH + 3, gz - 1, 'air')
    for x in range(-6, 7):
        for z in range(-5, 1):
            if (x in (-6, 6) or z in (-5, 0)) and (x + z) % 2 == 0:
                p.set(c + x, WH + 6, gz + z, PBB)
    for x in (-3, 3):
        p.set(c + x, WH + 6, gz, PBB)
        p.set(c + x, WH + 7, gz, ROD, {'facing': 'up'})
    for x in (-4, -3, 3, 4):
        p.set(c + x, F + 2, gz, BARS)
        p.set(c + x, G + 8, gz, BARS)
    loot(p, c - 4, G + 7, gz - 3, 'beyond:chests/end_city', 'east')
    p.set(c + 4, G + 7, gz - 3, 'barrel', {'facing': 'up'})

    # the bridge: twelve blocks of blackstone over the moat on deepslate piers
    p.fill(c - 3, G, gz + 1, c + 3, G, gz + 12, BLACK)
    for x in (-3, 3):
        p.fill(c + x, G, gz + 1, c + x, G, gz + 12, PBB)
        p.fill(c + x, G + 1, gz + 1, c + x, G + 1, gz + 12, RAIL)
        for z in (1, 6, 12):
            p.set(c + x, G + 2, gz + z, ROD, {'facing': 'up'})
        for z in (5, 9):
            p.fill(c + x, 1, gz + z, c + x, G - 1, gz + z, TILES)

    # the keep: three floors, obsidian corners, a crying-obsidian course every seventh row
    FL2, FL3, ROOF = G + 7, G + 14, G + 21

    def keep_block(x, z, y):
        if abs(x) == K and abs(z) == K:
            return OBS
        return CRY if y % 7 == 6 else PBB
    band(p, c, c, K - 1, K, G, ROOF, keep_block)
    for x in range(-(K - 2), K - 1):
        for z in range(-(K - 2), K - 1):
            p.set(c + x, G, c + z, PB)
            p.set(c + x, FL2, c + z, PB)
            p.set(c + x, FL3, c + z, PB)
            p.set(c + x, ROOF, c + z, PB)
            for y in list(range(F, FL2)) + list(range(FL2 + 1, FL3)) + list(range(FL3 + 1, ROOF)):
                p.air(c + x, y, c + z)
    merlons(p, c, c, K, ROOF + 1, PBB, rods=5)
    for sz in (-1, 1):                                            # doors north and south
        p.fill(c - 1, F, c + sz * (K - 1), c + 1, F + 3, c + sz * K, 'air')
    for level in (F + 2, FL2 + 2, FL3 + 2):                        # iron-bar windows
        for k in (-K + 3, -K + 7, K - 7, K - 3):
            for s in (-1, 1):
                p.set(c + k, level, c + s * K, BARS)
                p.set(c + s * K, level, c + k, BARS)
    # stairs: west wall up to the treasury, east wall up to the chamber, ladder to the roof
    stair_run(p, c - K + 2, F, c - K + 3, FL2 - F, 0, 1, STAIR, PBB)
    stair_run(p, c + K - 2, FL2 + 1, c + K - 2, FL3 - FL2 - 1, 0, -1, STAIR, PBB)
    for y in range(FL3 + 1, ROOF + 1):
        p.set(c - K + 2, y, c - K + 2, 'ladder', {'facing': 'east'})
    p.air(c - K + 2, ROOF, c - K + 2)
    # great hall: a long table, chairs, banners on the walls, chandeliers, lit corners
    for z in range(-6, 7):
        p.set(c, F, c + z, 'polished_blackstone_brick_slab')
        if z % 2 == 0:
            p.set(c - 1, F, c + z, 'blackstone_stairs', {'facing': 'west'})
            p.set(c + 1, F, c + z, 'blackstone_stairs', {'facing': 'east'})
    for i, z in enumerate(range(-6, 7, 4)):
        colour = 'purple' if i % 2 == 0 else 'black'
        p.set(c + K - 2, F + 2, c + z, colour + '_wall_banner', {'facing': 'west'})
        if z > 2:
            p.set(c - K + 2, F + 2, c + z, colour + '_wall_banner', {'facing': 'east'})
        p.set(c + z, F + 2, c - K + 2, colour + '_wall_banner', {'facing': 'south'})
    for z in (-4, 0, 4):
        p.set(c, FL2 - 1, c + z, 'chain')
        p.set(c, FL2 - 2, c + z, ROD, {'facing': 'down'})
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.fill(c + sx * (K - 2), F, c + sz * (K - 2), c + sx * (K - 2), FL2 - 1, c + sz * (K - 2), CRY)
            hanging_lantern(p, c + sx * 5, FL2 - 2, c + sz * 5)
    # treasury: a vault wall with a doorway, three chests and two blocks of gold
    for x in range(-K + 3, K - 1):
        if x not in (0, 1):
            p.fill(c + x, FL2 + 1, c - K + 6, c + x, FL3 - 1, c - K + 6, PBB)
    for x in (-3, 3):
        p.set(c + x, FL2 + 2, c - K + 6, BARS)
    for x in (-2, 0, 2):
        loot(p, c + x, FL2 + 1, c - K + 3, facing='south')
    p.set(c - 4, FL2 + 1, c - K + 3, 'gold_block')
    p.set(c + 4, FL2 + 1, c - K + 3, 'gold_block')
    p.set(c, FL2 + 1, c + 4, LAMP)
    hanging_lantern(p, c, FL3 - 2, c - K + 4)
    # the lord's chamber: beds, an armoury, a chest of the city's own things
    for x in range(-4, 3, 2):
        bed(p, c + x, FL3 + 1, c - K + 3, 0, -1)
    p.set(c + K - 4, FL3 + 1, c - K + 3, 'smithing_table')
    p.set(c + K - 3, FL3 + 1, c - K + 3, 'anvil', {'facing': 'east'})
    p.set(c + K - 5, FL3 + 1, c - K + 3, 'grindstone', {'face': 'floor', 'facing': 'east'})
    loot(p, c - K + 3, FL3 + 1, c + K - 3, 'beyond:chests/end_city')
    for sx in (-1, 1):
        hanging_lantern(p, c + sx * 5, ROOF - 2, c + 5)
    # the keep tower above the roof, the tallest thing in the castle
    KT = ROOF + r.choice([14, 16, 18])
    round_tower(p, c, c, 4, ROOF, KT, tower_block, floors=(ROOF + 7,), floor_block=PB, base=True)
    p.fill(c, ROOF + 1, c + 4, c, ROOF + 3, c + 4, 'air')
    p.set(c, KT + 1, c, CRY)
    for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        p.set(c + dx, KT + 1, c + dz, ROD, {'facing': 'up'})
    p.set(c, KT + 2, c, ROD, {'facing': 'up'})

    # barracks against the west wall
    bx0, bx1 = c - W + 4, c - W + 12
    bz0, bz1 = c - 12, c + 12
    p.hollow(bx0, G, bz0, bx1, G + 6, bz1, PBB)
    p.fill(bx0, G, bz0, bx1, G, bz1, PB)
    p.fill(bx0, G + 6, bz0, bx1, G + 6, bz1, 'polished_blackstone_brick_slab')
    p.fill(bx1, F, c, bx1, F + 1, c + 1, 'air')
    for z in range(bz0 + 3, bz1 - 2, 4):
        p.set(bx1, F + 1, z, BARS)
    for z in range(bz0 + 2, bz1 - 1, 3):
        bed(p, bx0 + 2, F, z, -1, 0, 'black' if z % 2 else 'purple')
    for z in (bz0 + 6, c, bz1 - 6):
        hanging_lantern(p, bx1 - 3, G + 4, z)
    loot(p, bx1 - 2, F, bz1 - 1, facing='west')
    p.set(bx1 - 2, F, bz0 + 1, 'barrel', {'facing': 'up'})

    # the well
    wx, wz = c + 14, c - 14
    p.fill(wx - 1, 1, wz - 1, wx + 1, F, wz + 1, TILES)
    p.fill(wx, 2, wz, wx, G, wz, WATER)
    p.air(wx, F, wz)
    for dx, dz in ((-1, -1), (1, 1)):
        p.fill(wx + dx, F + 1, wz + dz, wx + dx, F + 2, wz + dz, 'dark_oak_fence')
    p.fill(wx - 1, F + 3, wz - 1, wx + 1, F + 3, wz + 1, 'polished_blackstone_brick_slab')
    hanging_lantern(p, wx, F + 1, wz)

    # the market: stalls along the gate road under striped awnings
    for i, x in enumerate(r.sample([-16, -9, 9, 16, -20, 20], r.choice([4, 5, 6]))):
        sx, sz = c + x, gz - 9
        for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            p.fill(sx + dx, F, sz + dz, sx + dx, F + 2, sz + dz, 'dark_oak_fence')
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                p.set(sx + dx, F + 3, sz + dz, awning[(dx + i) % 2])
        for dx in (-1, 0, 1):
            p.set(sx + dx, F, sz + 1, 'polished_blackstone_brick_slab')
        p.set(sx, F, sz - 1, 'barrel', {'facing': 'up'})
        p.set(sx + r.choice([-1, 1]), F, sz, r.choice(['soul_lantern', 'cake', 'flower_pot']))
    # lantern posts round the courtyard
    for dx, dz in ((-18, -18), (18, 0), (0, -18), (18, 18), (-18, 18)):
        p.fill(c + dx, F, c + dz, c + dx, F + 1, c + dz, 'dark_oak_fence')
        p.set(c + dx, F + 2, c + dz, SOUL)
    return p


# -------------------------------------------------------------- 2. purpur citadel

def _gate(p, c, rk, lo, hi, side, chest):
    """A gate through ring `rk` whose terrace top is `hi`, reached by a ramp up from the
    terrace below at `lo`: two square towers straddling the wall, a lintel bridge
    between them, and the stairs running along the wall face to a landing."""
    at, (ax, az) = frame(side)
    ox, oz = SIDES[side]

    def S(u, v, y, block, props=None):
        dx, dz = at(u, v)
        p.set(c + dx, y, c + dz, block, props)

    for sgn in (-1, 1):
        for u in range(rk - 4, rk + 1):
            for v in range(2, 7):
                edge = u in (rk - 4, rk) or v in (2, 6)
                for y in range(lo + 1, hi + 11):
                    if edge:
                        S(u, sgn * v, y, PILLAR if y % 5 == 0 else BRICK)
                    elif y < hi:
                        S(u, sgn * v, y, END)
                    elif y in (hi, hi + 7, hi + 10):
                        S(u, sgn * v, y, BRICK)
                    else:
                        S(u, sgn * v, y, 'air')
                if edge and (u + v) % 2 == 0:
                    S(u, sgn * v, hi + 11, PURPUR)
        for k in range(2):
            S(rk - 4, sgn * 4, hi + 1 + k, 'air')            # door from the terrace
            S(rk - 2, sgn * 2, hi + 8 + k, 'air')            # door onto the lintel
        for y in range(hi + 1, hi + 11):
            S(rk - 1, sgn * 4, y, 'ladder', {'facing': dname(-ox, -oz)})
        S(rk - 3, sgn * 5, hi + 1, LAMP)
        S(rk - 3, sgn * 5, hi + 9, LAMP)
    for u in range(rk - 4, rk + 1):                              # lintel over the gate
        for v in (-1, 0, 1):
            for y in range(hi + 5, hi + 8):
                S(u, v, y, PURPUR if y == hi + 7 else BRICK)
            if v and u != rk - 2:
                S(u, v, hi + 8, 'end_stone_brick_wall')
    S(rk - 2, 0, hi + 5, LAMP)
    S(rk, 0, hi + 8, ROD, {'facing': 'up'})
    for u in (rk - 1, rk):                                       # the opening
        for v in (-1, 0, 1):
            for y in range(hi + 1, hi + 5):
                S(u, v, y, 'air')
    if chest:
        dx, dz = at(rk - 3, 3)
        loot(p, c + dx, hi + 1, c + dz)

    n = hi - lo
    for u in (rk + 1, rk + 2):                                   # ramp and landing
        for i in range(n - 1):
            v, y = -8 - (n - 2) + i, lo + 1 + i
            for yy in range(lo + 1, y):
                S(u, v, yy, END)
            S(u, v, y, 'purpur_stairs', {'facing': dname(ax, az)})
        for v in range(-7, 2):
            for yy in range(lo + 1, hi):
                S(u, v, yy, END)
            S(u, v, hi, PURPUR if v % 2 else BRICK)
    for i in range(n - 1):
        S(rk + 3, -8 - (n - 2) + i, lo + 2 + i, 'end_stone_brick_wall')
    for v in range(-7, 2):
        S(rk + 3, v, hi + 1, 'end_stone_brick_wall')
    S(rk + 3, -7, hi + 2, ROD, {'facing': 'up'})
    S(rk + 3, 1, hi + 2, ROD, {'facing': 'up'})


def _garden(p, x, y, z, r):
    kind = r.choice(['chorus', 'chorus', 'crystal', 'lamp', 'pool', 'bench'])
    if kind == 'chorus':
        p.set(x, y, z, END)
        h = r.choice([1, 2, 3])
        for k in range(1, h + 1):
            p.set(x, y + k, z, 'chorus_plant')
        p.set(x, y + h + 1, z, 'chorus_flower', {'age': '5'})
    elif kind == 'crystal':
        p.set(x, y + 1, z, 'amethyst_block')
        p.set(x, y + 2, z, 'amethyst_cluster', {'facing': 'up'})
    elif kind == 'lamp':
        p.fill(x, y + 1, z, x, y + 2, z, PILLAR)
        p.set(x, y + 3, z, ROD, {'facing': 'up'})
    elif kind == 'pool':
        p.set(x, y, z, WATER)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.set(x + dx, y, z + dz, BRICK)
    else:
        p.set(x, y + 1, z, 'purpur_slab')


def purpur_citadel(r):
    """A stepped hill-fort: three terraces inside three rings of wall, a gate and a
    ramp into each, gardens on the terraces, corner towers joined by bridges in the
    air, and a domed palace on the top."""
    R = (r.choice([39, 40]), r.choice([27, 28]), r.choice([16, 17]))
    L = (G, G + 5, G + 11, G + 17)      # terrain, then the top of each terrace
    P = 11                              # palace half-width
    DR = r.choice([10, 11])             # dome radius
    c = R[0] + 4
    p = Piece()
    rot = r.randrange(4)
    order = ['south', 'east', 'north', 'west']
    sides = [order[(rot + k) % 4] for k in range(3)]

    def paving(x, z):
        return BRICK if (x % 5 == 0 or z % 5 == 0) else PURPUR

    def wall_block(x, z, y):
        return PURPUR if y % 3 == 0 else BRICK

    p.fill(c - R[0] - 3, 0, c - R[0] - 3, c + R[0] + 3, G, c + R[0] + 3, END)
    for k in range(1, 4):
        rk, lo, hi = R[k - 1], L[k - 1], L[k]
        inner = R[k] if k < 3 else P
        for x in range(-rk, rk + 1):
            for z in range(-rk, rk + 1):
                d = max(abs(x), abs(z))
                for y in range(lo + 1, hi):
                    p.set(c + x, y, c + z, END)
                p.set(c + x, hi, c + z, paving(x, z))
                if inner < d <= rk - 2:
                    for y in range(hi + 1, hi + 7):
                        p.air(c + x, y, c + z)
        band(p, c, c, rk - 1, rk, lo + 1, hi + 2, wall_block)
        merlons(p, c, c, rk, hi + 3, PURPUR, rods=8)
    for k in range(3):
        _gate(p, c, R[k], L[k], L[k + 1], sides[k], chest=k < 2)

    # gardens in the quiet corners of the two lower terraces
    for rk, hi, inner in ((R[0], L[1], R[1]), (R[1], L[2], R[2])):
        for x in range(-rk + 3, rk - 2):
            for z in range(-rk + 3, rk - 2):
                d = max(abs(x), abs(z))
                if not (inner + 3 <= d <= rk - 3) or min(abs(x), abs(z)) <= 13:
                    continue
                if x % 3 or z % 3 or r.random() > 0.55:
                    continue
                if math.hypot(abs(x) - inner, abs(z) - inner) <= 6:
                    continue
                _garden(p, c + x, hi, c + z, r)

    # corner towers on the second and third rings, bridged diagonally at the top
    TOP = L[3] + 8
    tblock = lambda x, z, y: PILLAR if y % 6 == 0 else PURPUR
    for sx in (-1, 1):
        for sz in (-1, 1):
            for rk, lo in ((R[1], L[1]), (R[2], L[2])):
                tx, tz = c + sx * rk, c + sz * rk
                round_tower(p, tx, tz, 4, lo + 1, TOP, tblock,
                            floors=(lo + 7,) if lo + 7 < TOP - 1 else (), floor_block=BRICK)
                diag_door(p, tx, tz, 4, -sx, -sz, lo + 1)
                p.set(tx - sx * 2, lo + 6, tz - sz * 2, ROD, {'facing': 'down'})
            for i in range(R[1] - R[2] + 1):
                for ex, ez in ((0, 0), (1, 0), (0, 1)):
                    x, z = c + sx * (R[2] + i + ex), c + sz * (R[2] + i + ez)
                    p.set(x, TOP, z, PURPUR if (i + ex + ez) % 4 else BRICK)
                    p.air(x, TOP + 1, z)
                    p.air(x, TOP + 2, z)
                if i % 5 == 2 and 0 < i < R[1] - R[2]:
                    p.set(c + sx * (R[2] + i + 1), TOP + 1, c + sz * (R[2] + i), ROD, {'facing': 'up'})
                    p.set(c + sx * (R[2] + i), TOP + 1, c + sz * (R[2] + i + 1), ROD, {'facing': 'up'})

    # the palace: a square hall under a dome of purpur stairs, ribbed with pillars
    lo = L[3]
    band(p, c, c, P - 1, P, lo + 1, lo + 9,
         lambda x, z, y: PILLAR if abs(x) == P and abs(z) == P else wall_block(x, z, y))
    for x in range(-(P - 2), P - 1):
        for z in range(-(P - 2), P - 1):
            p.set(c + x, lo, c + z, LAMP if (abs(x) == 5 and abs(z) == 5) else paving(x, z))
            for y in range(lo + 1, lo + 10):
                p.air(c + x, y, c + z)
    for side in order:
        at, _ = frame(side)
        for u in (P - 1, P):
            for v in (-1, 0, 1):
                dx, dz = at(u, v)
                for y in range(lo + 1, lo + 5):
                    p.air(c + dx, y, c + dz)
        dx, dz = at(P, 2)
        p.set(c + dx, lo + 5, c + dz, ROD, {'facing': 'up'})
        dx, dz = at(P, -2)
        p.set(c + dx, lo + 5, c + dz, ROD, {'facing': 'up'})
    for x in range(-P, P + 1):
        for z in range(-P, P + 1):
            p.set(c + x, lo + 10, c + z, 'purpur_slab')
    merlons(p, c, c, P, lo + 11, PURPUR)
    y0 = lo + 9
    for y in range(lo + 10, y0 + DR + 1):
        dy = y - y0
        rad = math.sqrt(max(0.0, DR * DR - dy * dy))
        for x in range(-DR, DR + 1):
            for z in range(-DR, DR + 1):
                d = math.hypot(x, z)
                if d <= rad - 1:
                    p.air(c + x, y, c + z)
                elif d <= rad:
                    if x == 0 or z == 0 or abs(x) == abs(z):
                        p.set(c + x, y, c + z, PILLAR)
                    elif dy >= DR - 2 or dy == 1:
                        p.set(c + x, y, c + z, PURPUR if dy == 1 else 'purpur_slab')
                    else:
                        if abs(x) >= abs(z):
                            facing = 'west' if x > 0 else 'east'
                        else:
                            facing = 'north' if z > 0 else 'south'
                        p.set(c + x, y, c + z, 'purpur_stairs', {'facing': facing})
    p.set(c, y0 + DR, c, PURPUR)
    p.set(c, y0 + DR + 1, c, 'amethyst_block')
    p.set(c, y0 + DR + 2, c, ROD, {'facing': 'up'})
    # the council chamber: a round table, eight seats, lecterns, banners, and the loot
    for x in range(-3, 4):
        for z in range(-3, 4):
            d = math.hypot(x, z)
            if d <= 1.5:
                p.set(c + x, lo + 1, c + z, BRICK)
            elif d <= 3:
                p.set(c + x, lo + 1, c + z, 'purpur_slab')
    p.set(c, lo + 2, c, LAMP)
    for i in range(8):
        a = i * math.pi / 4
        x, z = round(5 * math.cos(a)), round(5 * math.sin(a))
        if abs(x) >= abs(z):
            facing = 'east' if x > 0 else 'west'
        else:
            facing = 'south' if z > 0 else 'north'
        p.set(c + x, lo + 1, c + z, 'purpur_stairs', {'facing': facing})
    for x in (-7, 7):
        p.set(c + x, lo + 1, c + 4, 'lectern', {'facing': 'west' if x > 0 else 'east'})
    for z in (-6, -2, 2, 6):
        p.set(c - P + 2, lo + 3, c + z, 'magenta_wall_banner', {'facing': 'east'})
        p.set(c + P - 2, lo + 3, c + z, 'purple_wall_banner', {'facing': 'west'})
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.fill(c + sx * (P - 2), lo + 1, c + sz * (P - 2), c + sx * (P - 2), lo + 8, c + sz * (P - 2), PILLAR)
            p.set(c + sx * (P - 2), lo + 9, c + sz * (P - 2), ROD, {'facing': 'up'})
    loot(p, c - 3, lo + 1, c - P + 2, facing='south')
    loot(p, c + 3, lo + 1, c - P + 2, facing='south')
    loot(p, c + 6, lo + 1, c + P - 2, 'beyond:chests/end_city')
    p.set(c - 6, lo + 1, c + P - 2, 'amethyst_block')
    p.set(c - 6, lo + 2, c + P - 2, 'amethyst_cluster', {'facing': 'up'})
    return p


# ---------------------------------------------------------------- 3. tide bastion

def tide_bastion(r):
    """A castle round a pool: an arcaded outer wall with corner towers, a lighthouse on
    an islet, flooded halls under the courtyard, warehouses and docks."""
    R = r.choice([37, 38])              # outer wall
    PR = r.choice([12, 13, 14])         # pool radius
    H0, H1 = PR + 4, R - 8              # the flooded halls, under the courtyard
    LH = G + r.choice([34, 36, 38])     # lighthouse lantern floor
    c = R + 2
    p = Piece()
    STAIR = 'prismarine_brick_stairs'
    hall_rad = r.choice([4, 5])

    def wall_block(x, z, y):
        return DARK if y % 4 == 0 else PBR

    def paving(x, z):
        return DARK if (x % 7 == 0 or z % 7 == 0) else PBR

    # foundation, courtyard, air
    p.fill(c - R, 0, c - R, c + R, G - 1, c + R, PRIS)
    for x in range(-(R - 3), R - 2):
        for z in range(-(R - 3), R - 2):
            p.set(c + x, G, c + z, paving(x, z))
            for y in range(F, F + 7):
                p.air(c + x, y, c + z)

    # the outer wall: three thick, an arcade of arches along its foot, a walkway on top
    WH = G + 9
    band(p, c, c, R - 2, R, G, WH, wall_block)
    band(p, c, c, R - 2, R - 1, WH + 1, WH + 3, 'air')
    band(p, c, c, R, R, WH + 1, WH + 1, DARK)
    merlons(p, c, c, R, WH + 2, PBR, rods=8)
    band(p, c, c, R - 2, R - 2, WH + 1, WH + 1, 'prismarine_wall')
    for side in SIDES:
        at, (ax, az) = frame(side)
        for v in range(-R + 8, R - 8, 6):
            if side == 'south' and abs(v) < 6:
                continue
            for u in range(R - 2, R + 1):
                for k in (0, 1):
                    dx, dz = at(u, v + k)
                    for y in range(F, F + 4):
                        p.air(c + dx, y, c + dz)
                    p.set(c + dx, F + 3, c + dz, 'dark_prismarine_stairs',
                          {'facing': dname(-ax, -az) if k == 0 else dname(ax, az), 'half': 'top'})
            dx, dz = at(R - 1, v)
            p.set(c + dx, F + 3, c + dz, LAMP)

    # corner towers, the walkway carried through them
    for sx in (-1, 1):
        for sz in (-1, 1):
            tx, tz = c + sx * (R - 2), c + sz * (R - 2)
            round_tower(p, tx, tz, 5, G, WH + 9, wall_block, floors=(G + 5, WH), floor_block=DARK, base=True)
            for x in range(-5, 6):
                for z in range(-5, 6):
                    if math.hypot(x, z) > 5:
                        continue
                    ax_, az_ = abs(sx * (R - 2) + x), abs(sz * (R - 2) + z)
                    if R - 2 <= max(ax_, az_) <= R - 1:
                        p.set(tx + x, WH, tz + z, DARK)
                        for y in range(WH + 1, WH + 4):
                            p.air(tx + x, y, tz + z)
            diag_door(p, tx, tz, 5, sx, sz, F)
            p.set(tx, WH + 10, tz, LAMP)
            if sx == sz:
                loot(p, tx - sx, G + 6, tz + sz * 3)

    # the gate: a tall arch on the south wall between two round towers
    gz = c + R
    p.fill(c - 2, F, gz - 2, c + 2, F + 5, gz + 1, 'air')
    for x in (-2, 2):
        for z in range(-2, 1):
            p.set(c + x, F + 5, gz + z, 'dark_prismarine_stairs',
                  {'facing': 'east' if x < 0 else 'west', 'half': 'top'})
    p.set(c, F + 6, gz, LAMP)
    for sx in (-1, 1):
        tx = c + sx * 7
        round_tower(p, tx, gz - 1, 4, G, WH + 11, wall_block, floors=(G + 6, WH), floor_block=DARK, base=True)
        for x in range(-4, 5):
            for z in range(-4, 5):
                if math.hypot(x, z) <= 4 and R - 2 <= abs(gz - 1 + z - c) <= R - 1 \
                        and not (x == 3 and z == 0):
                    p.set(tx + x, WH, gz - 1 + z, DARK)
                    for y in range(WH + 1, WH + 4):
                        p.air(tx + x, y, gz - 1 + z)
        for y in range(F, F + 3):
            p.air(tx, y, gz - 5)
        p.set(tx, WH + 12, gz - 1, LAMP)

    # the pool: dark prismarine lining, sea lanterns in the floor, a rim you can sit on
    for x in range(-PR - 2, PR + 3):
        for z in range(-PR - 2, PR + 3):
            d = math.hypot(x, z)
            if d <= PR:
                p.set(c + x, 1, c + z, LAMP if (x % 4 == 0 and z % 4 == 0) else DARK)
                for y in range(2, G + 1):
                    p.set(c + x, y, c + z, WATER)
            elif d <= PR + 1:
                p.fill(c + x, 1, c + z, c + x, G, c + z, DARK)
            elif d <= PR + 2:
                p.set(c + x, G, c + z, DARK)
                if (x + z) % 2 == 0 and abs(x) > 1 and abs(z) > 1:
                    p.set(c + x, F, c + z, 'dark_prismarine_slab')
    # the islet and the lighthouse
    for x in range(-4, 5):
        for z in range(-4, 5):
            if math.hypot(x, z) <= 4:
                p.fill(c + x, 1, c + z, c + x, G, c + z, PBR)
                p.set(c + x, G, c + z, DARK)
    for sz in (-1, 1):                                            # causeways north and south
        for z in range(4, PR + 2):
            for x in (-1, 0, 1):
                p.set(c + x, G, c + sz * z, LAMP if (x == 0 and z % 5 == 0) else DARK)
    lb = lambda x, z, y: DARK if y % 4 == 0 else PBR
    round_tower(p, c, c, 3, G, LH, lb, floors=tuple(range(G + 8, LH - 2, 8)), floor_block=DARK, base=True)
    p.fill(c, F, c - 3, c, F + 2, c - 3, 'air')
    p.fill(c, F, c + 3, c, F + 2, c + 3, 'air')
    for y in range(G + 8, LH - 2, 8):
        for dx, dz in ((-3, 0), (0, 3), (0, -3)):
            p.set(c + dx, y + 2, c + dz, BARS)
    for y in range(LH + 1, LH + 4):                               # the lantern room
        for x in range(-3, 4):
            for z in range(-3, 4):
                d = math.hypot(x, z)
                if 2 < d <= 3:
                    p.set(c + x, y, c + z, 'glass')
                elif d <= 2:
                    p.air(c + x, y, c + z)
    p.fill(c, LH + 1, c, c, LH + 3, c, LAMP)
    for x in range(-3, 4):
        for z in range(-3, 4):
            if math.hypot(x, z) <= 3:
                p.set(c + x, LH + 4, c + z, DARK)
    p.set(c, LH + 5, c, LAMP)
    p.set(c, LH + 6, c, ROD, {'facing': 'up'})
    loot(p, c - 1, LH + 1, c + 1, 'beyond:chests/monument_deep')

    # flooded halls under the courtyard: two rows of water, three of air, pillars with
    # sea lanterns in them, two stairwells down from the courtyard, chests on plinths
    for x in range(-H1, H1 + 1):
        for z in range(-H1, H1 + 1):
            d = max(abs(x), abs(z))
            if d < H0 or d > H1:
                continue
            if d in (H0, H1):
                p.fill(c + x, 0, c + z, c + x, G - 1, c + z, PBR)
                continue
            p.set(c + x, 0, c + z, LAMP if (x % 5 == 0 and z % 5 == 0) else DARK)
            if x % 6 == 0 and z % 6 == 0:
                p.fill(c + x, 1, c + z, c + x, G - 1, c + z, DARK)
                p.set(c + x, G - 2, c + z, LAMP)
                continue
            p.set(c + x, 1, c + z, WATER)
            p.set(c + x, 2, c + z, WATER)
            for y in range(3, G):
                p.air(c + x, y, c + z)
    for sx in (-1, 1):
        x0 = c + sx * (H0 + 2)
        for k in range(3):
            for z in (c, c + 1):
                p.air(x0 + sx * k, G, z)
                for y in range(G - k, G + 1):
                    p.air(x0 + sx * k, y, z)
                for y in range(3, G - 1 - k):
                    p.set(x0 + sx * k, y, z, PBR)
                p.set(x0 + sx * k, G - 1 - k, z, STAIR, {'facing': dname(-sx, 0)})
        for z in (c - 1, c + 2):
            p.set(x0, F, z, 'prismarine_wall')
            p.set(x0 + sx * 2, F, z, 'prismarine_wall')
        p.set(x0 + sx, F, c - 1, LAMP)
    for sx, sz in ((1, 1), (-1, -1), (1, -1)):
        px, pz = c + sx * (H1 - 3), c + sz * (H1 - 3)
        p.fill(px, 1, pz, px, 2, pz, DARK)
        loot(p, px, 3, pz)
        p.air(px, 4, pz)
        p.set(px, G - 1, pz, LAMP)

    # warehouses in the four corners of the courtyard
    for i, (sx, sz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        wx, wz = c + sx * 26, c + sz * 25
        x0, x1 = wx - 4, wx + 4
        z0, z1 = wz - 3, wz + 3
        p.hollow(x0, G, z0, x1, G + 6, z1, PBR)
        for x, z in ((x0, z0), (x0, z1), (x1, z0), (x1, z1)):
            p.fill(x, G, z, x, G + 6, z, DARK)
        p.fill(x0, G, z0, x1, G, z1, DARK)
        p.fill(x0, G + 6, z0, x1, G + 6, z1, DARK)
        p.fill(x0 - 1, G + 7, z0 - 1, x1 + 1, G + 7, z1 + 1, 'dark_prismarine_slab')
        p.set(wx, G + 8, wz, LAMP)
        dz_ = -sz
        p.fill(wx - 1, F, wz + dz_ * 3, wx + 1, F + 1, wz + dz_ * 3, 'air')
        for k in (-2, 2):
            p.set(wx + k, F + 1, wz + dz_ * 3, BARS)
        for x in range(x0 + 1, x1, 2):
            p.set(x, F, wz - dz_ * 2, 'barrel', {'facing': 'up'})
            if x % 2:
                p.set(x, F + 1, wz - dz_ * 2, 'barrel', {'facing': 'up'})
        p.set(wx, G + 5, wz, LAMP)
        if i < 2:
            loot(p, x0 + 1, F, wz, facing='east')
        elif i == 2:
            loot(p, x0 + 1, F, wz, 'beyond:chests/end_city', 'east')
        else:
            p.set(x0 + 1, F, wz, 'barrel', {'facing': 'up'})

    # docks: two timber piers out over the water, east and west
    for sx in (-1, 1):
        for k in range(PR - 5, PR + 3):
            for z in (-1, 0, 1):
                p.set(c + sx * k, G, c + z, 'dark_oak_planks')
        for k in (PR - 5, PR - 1):
            for z in (-2, 2):
                p.fill(c + sx * k, 2, c + z, c + sx * k, F, c + z, 'dark_oak_fence')
        p.set(c + sx * (PR - 5), F + 1, c - 2, LAMP)
        p.set(c + sx * (PR - 5), F + 1, c + 2, LAMP)
        p.set(c + sx * (PR - 3), F, c, 'barrel', {'facing': 'up'})
    # lamp posts round the courtyard
    for dx, dz in ((-20, -8), (20, 8), (-8, 20), (8, -20), (20, -20), (-20, 20)):
        p.fill(c + dx, F, c + dz, c + dx, F + 2, c + dz, 'prismarine_wall')
        p.set(c + dx, F + 3, c + dz, LAMP)
    return p


CASTLES = {
    'obsidian_fortress': obsidian_fortress,
    'purpur_citadel': purpur_citadel,
    'tide_bastion': tide_bastion,
}
VARIANTS = 3


def emit(write, ns, biome_tag):
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'src', 'main', 'resources', 'data', ns, 'structure')
    made = 0
    for name, builder in CASTLES.items():
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
    # No jigsaw structure or structure set: a jigsaw start over the void is silently
    # dropped, and half the End is void. The mod places these itself (world/Castles.java)
    # on islands it has measured, sunk by G so the foundation is underground.
    return made
