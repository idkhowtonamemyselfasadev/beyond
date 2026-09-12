"""Just enough NBT to read a vanilla structure file and write our own.

Structure templates are gzipped NBT: a size, a block-state palette, a list of blocks
that index into it, and the data version they were saved at. Nothing here is a general
NBT library - it is the subset those files use.
"""
import gzip
import struct

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE = 0, 1, 2, 3, 4, 5, 6
BYTES, STRING, LIST, COMPOUND, INTS, LONGS = 7, 8, 9, 10, 11, 12


class Tag:
    """A value plus the NBT type it must be written as."""

    def __init__(self, kind, value):
        self.kind = kind
        self.value = value


def i(v):
    return Tag(INT, v)


def s(v):
    return Tag(STRING, v)


def b(v):
    return Tag(BYTE, v)


def ints(v):
    return Tag(LIST, [Tag(INT, x) for x in v])


# ------------------------------------------------------------------------ reading

class _R:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def take(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def num(self, fmt, n):
        return struct.unpack('>' + fmt, self.take(n))[0]

    def string(self):
        return self.take(self.num('H', 2)).decode('utf-8')

    def payload(self, t):
        if t == BYTE:
            return self.num('b', 1)
        if t == SHORT:
            return self.num('h', 2)
        if t == INT:
            return self.num('i', 4)
        if t == LONG:
            return self.num('q', 8)
        if t == FLOAT:
            return self.num('f', 4)
        if t == DOUBLE:
            return self.num('d', 8)
        if t == BYTES:
            return self.take(self.num('i', 4))
        if t == STRING:
            return self.string()
        if t == LIST:
            it = self.num('b', 1)
            n = self.num('i', 4)
            return [] if it == END else [self.payload(it) for _ in range(n)]
        if t == COMPOUND:
            out = {}
            while True:
                tt = self.num('b', 1)
                if tt == END:
                    return out
                name = self.string()          # name first: Python would
                out[name] = self.payload(tt)  # evaluate the value before the key
        if t == INTS:
            return [self.num('i', 4) for _ in range(self.num('i', 4))]
        if t == LONGS:
            return [self.num('q', 8) for _ in range(self.num('i', 4))]
        raise ValueError(t)


def read(path):
    with gzip.open(path, 'rb') as f:
        data = f.read()
    r = _R(data)
    r.num('b', 1)
    r.string()
    return r.payload(COMPOUND)


# ------------------------------------------------------------------------ writing

def _kind(v):
    if isinstance(v, Tag):
        return v.kind
    if isinstance(v, bool):
        return BYTE
    if isinstance(v, int):
        return INT
    if isinstance(v, float):
        return DOUBLE
    if isinstance(v, str):
        return STRING
    if isinstance(v, dict):
        return COMPOUND
    if isinstance(v, list):
        return LIST
    raise ValueError(type(v))


def _write(out, v):
    t = _kind(v)
    if isinstance(v, Tag):
        v = v.value
    if t == BYTE:
        out += struct.pack('>b', int(v))
    elif t == SHORT:
        out += struct.pack('>h', v)
    elif t == INT:
        out += struct.pack('>i', v)
    elif t == LONG:
        out += struct.pack('>q', v)
    elif t == FLOAT:
        out += struct.pack('>f', v)
    elif t == DOUBLE:
        out += struct.pack('>d', v)
    elif t == STRING:
        e = v.encode('utf-8')
        out += struct.pack('>H', len(e)) + e
    elif t == LIST:
        it = _kind(v[0]) if v else END
        out += struct.pack('>bi', it, len(v))
        for x in v:
            _write(out, x)
    elif t == COMPOUND:
        for k, x in v.items():
            e = k.encode('utf-8')
            out += struct.pack('>b', _kind(x)) + struct.pack('>H', len(e)) + e
            _write(out, x)
        out += b'\x00'
    else:
        raise ValueError(t)


def write(path, root):
    out = bytearray(b'\x0a\x00\x00')
    _write(out, root)
    with open(path, 'wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=9, mtime=0) as f:
            f.write(bytes(out))
