"""The canvas an End city is drawn on - the same sparse block box the Overworld mod
uses, without its material sets, which are all grass and sandstone and no use here.
"""
import nbt

DATA_VERSION = 4671


class Piece:
    """A sparse box of blocks. Anything not set is left as the terrain found it."""

    def __init__(self):
        self.blocks = {}

    def set(self, x, y, z, name, props=None, entity=None):
        if y < 0:
            return
        self.blocks[(x, y, z)] = ('minecraft:' + name, props or {}, entity)

    def air(self, x, y, z):
        self.set(x, y, z, 'air')

    def fill(self, x0, y0, z0, x1, y1, z1, name, props=None):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name, props)

    def hollow(self, x0, y0, z0, x1, y1, z1, name, props=None):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    edge = x in (x0, x1) or z in (z0, z1) or y in (y0, y1)
                    if edge:
                        self.set(x, y, z, name, props)
                    else:
                        self.air(x, y, z)

    def column(self, x, z, y0, y1, name, props=None):
        for y in range(y0, y1 + 1):
            self.set(x, y, z, name, props)

    def chest(self, x, y, z, loot, facing='north'):
        self.set(x, y, z, 'chest', {'facing': facing, 'type': 'single',
                                    'waterlogged': 'false'},
                 {'id': 'minecraft:chest', 'LootTable': loot})

    def to_nbt(self):
        palette, index = [], {}
        blocks = []
        mx = my = mz = 0
        for (x, y, z), (name, props, entity) in sorted(self.blocks.items()):
            key = (name, tuple(sorted(props.items())))
            if key not in index:
                index[key] = len(palette)
                p = {'Name': name}
                if props:
                    p['Properties'] = dict(props)
                palette.append(p)
            b = {'pos': nbt.ints([x, y, z]), 'state': nbt.i(index[key])}
            if entity:
                b['nbt'] = dict(entity)
            blocks.append(b)
            mx, my, mz = max(mx, x), max(my, y), max(mz, z)
        return {'size': nbt.ints([mx + 1, my + 1, mz + 1]),
                'palette': palette, 'blocks': blocks, 'entities': [],
                'DataVersion': nbt.i(DATA_VERSION)}
