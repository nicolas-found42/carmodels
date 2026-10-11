#!/usr/bin/env python3
"""Bounded reader for Redline R3Dl1n3 native packages.

The LZRW3-A dictionary/cursor operations reproduce the shipped i386 decoder
(sub_716ec). This is static reconstruction, not execution of the game. Some observed table slots contain unreadable bytes. They are omitted only
when all named, bounded members still partition the complete payload with no
missing bytes. The native loader does not prove these slots are deleted.
"""

import hashlib
import os
from pathlib import Path
import struct
import unicodedata

MAGIC = b'R3Dl1n3\0'
HEADER_BYTES = 24
ENTRY_BYTES = 268
MAX_PACKAGE_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_MEMBERS = 100000
SEED = b'123456789012345678'


def decompress(data, expected_bytes, *, max_bytes=MAX_MEMBER_BYTES):
    """Decode one complete native LZRW3-A or raw member, with exact lengths."""
    if not isinstance(expected_bytes, int) or not 0 <= expected_bytes <= max_bytes:
        raise ValueError('decoded member size exceeds bound')
    if len(data) < 4:
        raise ValueError('truncated compression flag')
    flag = data[:4]
    if flag == b'\1\0\0\0':
        if len(data) != expected_bytes + 4:
            raise ValueError('raw member length mismatch')
        return bytes(data[4:])
    if flag != b'\0\0\0\0':
        raise ValueError('unsupported compression flag')
    if expected_bytes > 9 * max(0, len(data) - 4):
        raise ValueError('compressed member expansion exceeds LZRW bound')
    output = bytearray()
    dictionary = [None] * 4096
    cursor = 0
    literals = 0
    control = 1
    position = 4

    def bucket(start):
        value = (output[start] << 8) ^ (output[start + 1] << 4) ^ output[start + 2]
        return ((40543 * value >> 4) & 511) * 8

    while position < len(data):
        if control == 1:
            if position + 2 >= len(data):
                raise ValueError('truncated or empty control group')
            control = 65536 | data[position] | (data[position + 1] << 8)
            position += 2
        start = len(output)
        if control & 1:
            if position + 2 > len(data):
                raise ValueError('truncated copy token')
            first, second = data[position:position + 2]
            position += 2
            index = ((first & 240) << 4) | second
            length = (first & 15) + 3
            if start + length > expected_bytes:
                raise ValueError('decoded member exceeds declared size')
            source = dictionary[index]
            if source is None:
                output.extend(SEED[:length])
            elif source + length <= start:
                output.extend(output[source:source + length])
            else:
                # Bytewise copying preserves native overlapping history copies.
                for offset in range(length):
                    output.append(output[source + offset])
            if literals:
                pending = start - literals
                dictionary[bucket(pending) + cursor] = pending
                cursor = (cursor + 1) & 7
                if literals == 2:
                    pending += 1
                    dictionary[bucket(pending) + cursor] = pending
                    cursor = (cursor + 1) & 7
                literals = 0
            dictionary[(index & ~7) + cursor] = start
            cursor = (cursor + 1) & 7
        else:
            if start >= expected_bytes:
                raise ValueError('decoded member exceeds declared size')
            output.append(data[position])
            position += 1
            literals += 1
            if literals == 3:
                pending = len(output) - 3
                dictionary[bucket(pending) + cursor] = pending
                cursor = (cursor + 1) & 7
                literals = 2
        control >>= 1
    if len(output) != expected_bytes:
        raise ValueError('decoded member length mismatch')
    return bytes(output)


def safe_name(name):
    """Validate a flat native filename without discarding the Finder Icon CR."""
    controls = any(ord(c) < 32 or ord(c) == 127 for c in name)
    if (not name or name in ('.', '..') or any(c in name for c in '/\\:\0')
            or (controls and name != 'Icon\r')):
        raise ValueError('unsafe package member name')
    return name


def read_package(path_or_bytes, *, max_member_bytes=MAX_MEMBER_BYTES,
                 max_total_bytes=MAX_TOTAL_BYTES):
    """Return native named members with exact bytes, offsets and SHA-256 pins.

    Each record has name, offset, stored_bytes, bytes, data, sha256, compression
    and slot. Names use reversible Mac Roman decoding. No files are written.
    Unknown unreadable table bytes remain in the original container; complete
    payload coverage is required even when such slots exist.
    """
    if isinstance(path_or_bytes, (str, os.PathLike)):
        path = Path(path_or_bytes)
        if path.stat().st_size > MAX_PACKAGE_BYTES:
            raise ValueError('package size exceeds bound')
        with path.open('rb') as stream:
            data = stream.read(MAX_PACKAGE_BYTES + 1)
    else:
        if not isinstance(path_or_bytes, (bytes, bytearray, memoryview)):
            raise TypeError('package input must be a path or bytes')
        input_size = (path_or_bytes.nbytes if isinstance(path_or_bytes, memoryview)
                      else len(path_or_bytes))
        if input_size > MAX_PACKAGE_BYTES:
            raise ValueError('package size exceeds bound')
        data = bytes(path_or_bytes)
    if len(data) > MAX_PACKAGE_BYTES:
        raise ValueError('package size exceeds bound')
    if len(data) < HEADER_BYTES or data[:8] != MAGIC:
        raise ValueError('invalid native package header')
    count = struct.unpack_from('>I', data, 8)[0]
    table_end = HEADER_BYTES + count * ENTRY_BYTES
    if count > MAX_MEMBERS or table_end > len(data):
        raise ValueError('truncated or excessive package table')
    members = []
    names = set()
    total = 0
    for slot in range(count):
        start = HEADER_BYTES + slot * ENTRY_BYTES
        offset, size, stored = struct.unpack_from('>III', data, start)
        raw_name = data[start + 12:start + ENTRY_BYTES]
        name_bytes, separator, _ = raw_name.partition(b'\0')
        if not name_bytes:
            continue
        # Uninitialized nonempty slots are distinguishable from members only
        # through the complete payload-coverage check below, not by prose/name.
        if offset < table_end or stored < 4 or offset + stored > len(data):
            continue
        if not separator:
            raise ValueError('unterminated package member name')
        name = safe_name(name_bytes.decode('mac_roman'))
        key = unicodedata.normalize('NFC', name).casefold()
        if key in names:
            raise ValueError('duplicate or case-colliding package member name')
        names.add(key)
        if size > max_member_bytes or total + size > max_total_bytes:
            raise ValueError('decoded package size exceeds bound')
        total += size
        members.append({'name': name, 'offset': offset, 'stored_bytes': stored,
                        'bytes': size, 'slot': slot})
    end = table_end
    for member in sorted(members, key=lambda item: item['offset']):
        if member['offset'] != end:
            raise ValueError('payload gap or overlapping package members')
        end += member['stored_bytes']
    if end != len(data):
        raise ValueError('payload gap or trailing package bytes')
    for member in members:
        start = member['offset']
        packed = data[start:start + member['stored_bytes']]
        content = decompress(packed, member['bytes'], max_bytes=max_member_bytes)
        member.update(data=content, sha256=hashlib.sha256(content).hexdigest(),
                      compression='raw' if packed[0] == 1 else 'lzrw3-a')
    return members


def extract_package(path_or_bytes, output):
    """Write all members into a new flat directory; existing outputs fail."""
    members = read_package(path_or_bytes)
    output = Path(output)
    # A native Finder Icon filename's carriage return is encoded in the output.
    filenames = [member['name'].replace('%', '%25').replace('\r', '%0D')
                 for member in members]
    keys = [unicodedata.normalize('NFC', name).casefold() for name in filenames]
    if len(set(keys)) != len(keys):
        raise ValueError('encoded output filename collision')
    output.mkdir(parents=False, exist_ok=False)
    for filename, member in zip(filenames, members):
        target = output / filename
        with target.open('xb') as stream:
            stream.write(member['data'])
    return members
