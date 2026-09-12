"""Can you actually walk round a castle? A player two blocks tall who can jump one block,
climb ladders and swim is flood-filled through each template from outside its gate, and
every chest, walkway, roof and tower top must be somewhere it got to.

    python3 gen/walkcheck.py

Unset cells count as air above the surface row and as ground below it, which is what
the world does to them.
"""
import collections
import random
import zlib

import castles
from castles import G, F

NONSOLID = {'air', 'ladder', 'water', 'chain', 'chorus_flower', 'chorus_plant'}


def free(p, x, y, z):
    v = p.blocks.get((x, y, z))
    if v is None:
        return y > G
    n = v[0][10:]
    return n in NONSOLID or n.endswith('_banner')


def stair(p, x, y, z):
    v = p.blocks.get((x, y, z))
    return bool(v) and v[0].endswith('_stairs')


def climbable(p, x, y, z):
    v = p.blocks.get((x, y, z))
    return bool(v) and v[0][10:] in ('ladder', 'water')


def reach(p, start):
    seen = set()
    q = collections.deque([start])
    xs = [k[0] for k in p.blocks]
    zs = [k[2] for k in p.blocks]
    x0, x1, z0, z1 = min(xs) - 2, max(xs) + 2, min(zs) - 2, max(zs) + 2
    while q:
        x, y, z = q.popleft()
        if (x, y, z) in seen or not (x0 <= x <= x1 and z0 <= z <= z1) or y > 60:
            continue
        seen.add((x, y, z))
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (1, 0):
                nx, ny, nz = x + dx, y + dy, z + dz
                if dy == 1 and not free(p, x, y + 2, z) and not stair(p, nx, ny - 1, nz):
                    continue                      # a jump needs headroom; a stair is a step
                if not (free(p, nx, ny, nz) and free(p, nx, ny + 1, nz)):
                    continue
                while ny > 1 and free(p, nx, ny - 1, nz) and not climbable(p, nx, ny - 1, nz) \
                        and not climbable(p, nx, ny, nz):
                    ny -= 1
                q.append((nx, ny, nz))
        if climbable(p, x, y, z) or climbable(p, x, y + 1, z):
            if free(p, x, y + 2, z):
                q.append((x, y + 1, z))
            if free(p, x, y - 1, z):
                q.append((x, y - 1, z))
    return seen


def check(name, k, start, targets):
    r = random.Random(zlib.crc32(f'{name}/{k}'.encode()))
    p = castles.CASTLES[name](r)
    seen = reach(p, start)
    chests = [(x, y, z) for (x, y, z), v in p.blocks.items() if v[0].endswith('chest')]
    bad = []
    for cx, cy, cz in chests:
        ok = any((cx + dx, cy + dy, cz + dz) in seen
                 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)) for dy in (-1, 0, 1))
        if not ok:
            bad.append(('chest', cx, cy, cz, p.blocks[(cx, cy, cz)][2]['LootTable']))
    for label, (x, y, z) in targets.items():
        if not any((x, yy, z) in seen for yy in range(y - 3, y + 4)):
            bad.append((label, x, y, z))
    top = max(y for (_, y, _) in seen)
    print(f"{name}/{k}: reached {len(seen)} cells, highest y {top}, chests {len(chests)}, "
          + ("OK" if not bad else f"UNREACHED {bad}"))
    return not bad


def main():
    ok = True
    for k in range(3):
        r = random.Random(zlib.crc32(f'obsidian_fortress/{k}'.encode()))
        W, T, K = r.choice([26, 27, 28]), r.choice([5, 6]), r.choice([10, 11])
        WH = G + r.choice([10, 11, 12])
        TH = WH + r.choice([9, 11, 13])
        c = W + 11
        ROOF = G + 21
        ok &= check('obsidian_fortress', k, (c, F, c + W + 13), {
            'walkway_north': (c, WH + 1, c - W + 2), 'walkway_east': (c + W - 2, WH + 1, c),
            'tower_top': (c + W + 1, TH + 1, c + W + 1), 'keep_roof': (c + 3, ROOF + 1, c),
            'keep_tower_top': (c + 1, ROOF + 17, c + 1),
            'gatehouse_top': (c, WH + 5, c + W - 2), 'barracks': (c - W + 8, F, c)})
    for k in range(3):
        r = random.Random(zlib.crc32(f'purpur_citadel/{k}'.encode()))
        R = (r.choice([39, 40]), r.choice([27, 28]), r.choice([16, 17]))
        r.choice([10, 11])
        rot = r.randrange(4)
        order = ['south', 'east', 'north', 'west']
        at, _ = castles.frame(order[rot])
        c = R[0] + 4
        L = (G, G + 5, G + 11, G + 17)
        dx, dz = at(R[0] + 1, -14)
        ok &= check('purpur_citadel', k, (c + dx, F, c + dz), {
            'terrace1': (c + R[1] + 4, L[1] + 1, c + 20), 'terrace2': (c + R[2] + 4, L[2] + 1, c + 12),
            'terrace3': (c, L[3] + 1, c + 13), 'palace': (c, L[3] + 1, c + 5),
            'bridge': (c + R[2] + 6, L[3] + 9, c + R[2] + 6),
            'ring2_tower_top': (c + R[1], L[3] + 9, c - R[1]),
            'ring3_tower_top': (c - R[2], L[3] + 9, c - R[2])})
    for k in range(3):
        r = random.Random(zlib.crc32(f'tide_bastion/{k}'.encode()))
        R = r.choice([37, 38])
        PR = r.choice([12, 13, 14])
        LH = G + r.choice([34, 36, 38])
        c = R + 2
        WH = G + 9
        ok &= check('tide_bastion', k, (c, F, c + R + 2), {
            'walkway_north': (c, WH + 1, c - R + 2), 'walkway_east': (c + R - 2, WH + 1, c),
            'corner_tower_top': (c + R - 2, WH + 10, c + R - 2), 'lighthouse_top': (c - 1, LH + 1, c - 1),
            'hall_east': (c + PR + 8, 3, c + 5), 'hall_west': (c - PR - 8, 3, c - 5),
            'warehouse': (c + 26, F, c + 25), 'pier': (c + PR, F, c),
            'gate_tower_top': (c + 7, WH + 12, c + R - 1)})
    print('all reachable' if ok else 'SOMETHING IS NOT REACHABLE')
    return ok


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
