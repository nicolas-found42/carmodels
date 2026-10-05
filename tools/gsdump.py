"""Minimal PCSX2 GSDump reader shared by the retained-packet scripts (transfer events only)."""
import hashlib
import struct
import subprocess

ZSTD = '/opt/homebrew/bin/zstd'


def load_transfers(path, compressed_sha256=None):
    """Return the list of GIF transfer payloads in event order; header and event stream are bounds-checked."""
    if compressed_sha256 is not None:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == compressed_sha256, 'GSDump compressed hash differs from pin'
    d = subprocess.check_output([ZSTD, '-d', '-c', str(path)])
    marker, hs = struct.unpack_from('<II', d, 0)
    assert marker == 0xffffffff
    state_size = struct.unpack_from('<9I', d, 8)[1]
    pos = 8 + hs + state_size + 0x2000
    transfers = []
    while pos < len(d):
        kind = d[pos]; pos += 1
        if kind == 0:
            size = struct.unpack_from('<I', d, pos + 1)[0]; pos += 5
            assert pos + size <= len(d)
            transfers.append(d[pos:pos + size]); pos += size
        elif kind == 1:
            pos += 1
        elif kind == 2:
            pos += 4
        elif kind == 3:
            pos += 0x2000
        else:
            raise ValueError(f'unknown GSDump record {kind}')
    assert pos == len(d)
    return transfers, hashlib.sha256(d).hexdigest()


def iter_tags(data):
    """Yield (offset, lo, hi, nloop, flg, nreg, payload_bytes) for each GIF tag in one transfer."""
    off = 0
    while off < len(data):
        lo, hi = struct.unpack_from('<QQ', data, off)
        nloop = lo & 0x7fff; flg = (lo >> 58) & 3; nreg = (lo >> 60) & 15 or 16
        pl = nloop * nreg * 16 if flg == 0 else (((nloop * nreg + 1) // 2) * 16 if flg == 1 else (nloop * 16 if flg == 2 else 0))
        assert off + 16 + pl <= len(data)
        yield off, lo, hi, nloop, flg, nreg, pl
        off += 16 + pl
