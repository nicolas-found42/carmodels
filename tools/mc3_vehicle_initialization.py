"""Original VIF initialization streams, separate from raw VU microcode.

The special bank supplies native GIF templates and constants. Loading only
the extracted microprogram does not initialize these VU data-memory slots.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job
from mc3_reference_runtime import run_job
from mc3_vehicle_transfer_reference import encode_job, run_job as run_coupled

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'research/evidence/midnight-club-3-remix/previews/vehicle-initialization.json'
INTERVALS = [
    (0x526d08, 352, '6bbbc6cddcba351112ab7b2dabe01d530684178c2f7ccbffdf6be5205eb9088a'),
    (0x61c2b8, 16, '03ad324556087e7190be44b0fcc217450fc9b41d7d123e96f789504b786b41d3'),
    (0x612010, 8096, '648af94a1d02c21d53208a341bc57a6dfff2592303af2643534fcfc1c280ab38'),
    (0x610a60, 5552, 'd69719e77592f8c1490a2547a972b2bdc127718b53379082af0def038d6ccec9'),
    (0x5ec4f0, 13488, '9d30b140652bb9400499dd7e450f17618de7ca45d52237b58add56274ec11f71')]
DMA = bytes.fromhex('fa0100301020610000000000000000005b010030600a61000000001100000000')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build_pack(executable):
    if sha(executable) != EXECUTABLE_SHA:
        raise ValueError('initialization executable differs')
    for address, size, digest in INTERVALS:
        if sha(_read_elf(executable, address, size)) != digest:
            raise ValueError('initialization source interval differs')
    if struct.unpack('<4I', _read_elf(executable, 0x61c2b8, 16)) != (0x612010, 0x613fb0, 0, 0):
        raise ValueError('initialization special descriptor differs')
    stream = (DMA[8:16]+_read_elf(executable, 0x612010, 8096)
              +DMA[24:32]+_read_elf(executable, 0x610a60, 5552)
              +_read_elf(executable, 0x5ec4f8, 13480))
    return dict(schema=1, source_executable_sha256=EXECUTABLE_SHA,
                source_intervals=[dict(address=a, bytes=n, sha256=h) for a, n, h in INTERVALS],
                special_dma_hex=DMA.hex(), vif_bytes=len(stream), vif_sha256=sha(stream),
                vif_base64=base64.b64encode(stream).decode(),
                claim_limits=['Special descriptor selected explicitly with previous bank null; original normal bank follows.',
                              'Original VIF initialization, not a complete material draw or actor context.'])


def initialization_job():
    def li(register, value):
        return [0x3c000000 | register << 16 | value >> 16,
                0x34000000 | register << 21 | register << 16 | value & 65535]
    words = [0x03e0b82d, *li(8, 0x70000000), *li(9, 0x1100000), 0xad0905ac,
             *li(9, 0x1110000), 0xad0905b0, *li(4, 0x61c2b8),
             0x0c000000 | 0x526d08 >> 2, 0, *li(8, 0x70000000), 0x8d0905ac,
             *li(8, 0x1001000), 0xad090000, 0x02e00008, 0]
    return encode_ee_job(0x1000000, {}, [(0x1000000, struct.pack('<'+'I'*len(words), *words)),
                                            (0x70e5e8, bytes(4))])


def reference(executable, output):
    executable, output = Path(executable), Path(output)
    pack = build_pack(executable.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    job = output/'input.job';job.write_bytes(initialization_job())
    ee = run_job(job, output/'ee', mode='ee', executable=executable)
    ram = (output/'ee/ee-ram.bin').read_bytes()
    end = struct.unpack_from('<I', ram, 0x1001000)[0]
    if end != 0x1100020 or ram[0x1100000:end] != DMA:
        raise ValueError('original initialization DMA differs')
    stream = base64.b64decode(pack['vif_base64'])
    coupled = run_coupled(encode_job(bytes(16384), bytes(16384), stream), output/'coupled')
    result = dict(pack=pack, ee=ee, coupled=coupled)
    (output/'reference.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--write-fixture', action='store_true')
    args = p.parse_args()
    if args.output:
        result = reference(args.executable, args.output)
        if args.write_fixture:
            FIXTURE.write_text(json.dumps(result, indent=2)+'\n')
    elif args.write_fixture:
        p.error('--write-fixture requires --output')
    else:
        print(json.dumps(build_pack(args.executable.read_bytes())))
