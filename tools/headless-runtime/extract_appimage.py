#!/usr/bin/env python3
"""Extract the pinned AppImage's bounded filesystem without executing its stub."""
from pathlib import Path
import hashlib
import struct
import subprocess

p = Path('/opt/pcsx2.AppImage')
data = p.read_bytes()
if hashlib.sha256(data).hexdigest() != '0c46bb6a88aa2782b10853a7b07cf3387ba99cbef2b966372cd2315b8571abea':
    raise ValueError('official AppImage hash differs')
if data[:7] != b'\x7fELF\x02\x01\x01':
    raise ValueError('unexpected ELF class or encoding')
section_offset, = struct.unpack_from('<Q', data, 40)
section_size, section_count = struct.unpack_from('<HH', data, 58)
offset = section_offset + section_size * section_count
if data[offset:offset + 4] != b'hsqs':
    raise ValueError('filesystem magic missing after ELF section table')
if struct.unpack_from('<HH', data, offset + 28) != (4, 0):
    raise ValueError('unsupported SquashFS version')
filesystem_size, = struct.unpack_from('<Q', data, offset + 40)
if not 96 <= filesystem_size <= len(data) - offset:
    raise ValueError('filesystem exceeds AppImage bounds')
print({'appimage_sha256': hashlib.sha256(data).hexdigest(),
       'filesystem_offset': offset, 'filesystem_bytes': filesystem_size}, flush=True)
subprocess.run(['unsquashfs', '-o', str(offset), '-d', '/opt/squashfs-root', str(p)], check=True)
