#!/usr/bin/env python3
"""Tiny RCON client, so the build can ask the running server what it actually made."""
import socket
import struct
import sys


class Rcon:
    def __init__(self, host='127.0.0.1', port=25651, password='beyond'):
        self.s = socket.create_connection((host, port), timeout=300)
        self.i = 0
        if self._send(3, password) is None:
            raise SystemExit('rcon auth failed')

    def _pack(self, i, t, body):
        p = struct.pack('<ii', i, t) + body.encode() + b'\x00\x00'
        return struct.pack('<i', len(p)) + p

    def _read(self, n):
        buf = b''
        while len(buf) < n:
            c = self.s.recv(n - len(buf))
            if not c:
                raise EOFError
            buf += c
        return buf

    def _send(self, t, body):
        self.i += 1
        self.s.sendall(self._pack(self.i, t, body))
        ln = struct.unpack('<i', self._read(4))[0]
        rid, _ = struct.unpack('<ii', self._read(8))
        payload = self._read(ln - 8)[:-2].decode('utf-8', 'replace')
        return None if rid == -1 else payload

    def cmd(self, c):
        return self._send(2, c)


if __name__ == '__main__':
    r = Rcon()
    for c in sys.argv[1:]:
        print(r.cmd(c))
