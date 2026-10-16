"""Original display/RT/default-state setup around a bounded authored draw.

The display profile is an explicit 512-square inherited context, followed by
an original 256-square color/depth target. It is not a stock garage frame.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import _read_elf, encode_ee_job
import mc3_vehicle_authored_draw as authored

DISPLAY = 0x1040000
COLOR = 0x1020000
DEPTH = 0x1020100
HEAP = 0x1030000
EVIDENCE = Path(__file__).resolve().parents[1]/"research/evidence/midnight-club-3-remix/previews/vehicle-target.json"
PROOF_SHA = "d2d300b34da542265bba103a4218054898d0cb8eee88325351c7e7fefcd88034"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_contract(executable=None, receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    if sha(json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()) != PROOF_SHA:
        raise ValueError("target source receipt differs")
    if proof["authored_receipt_sha256"] != authored.PROOF_SHA:
        raise ValueError("authored source dependency differs")
    if executable is not None:
        authored.from_executable(executable)
        for pin in proof["source_intervals"]:
            if sha(_read_elf(executable, pin["start"], pin["end"]-pin["start"])) != pin["sha256"]:
                raise ValueError("target source instructions differ")
    return proof


def _call(words, address, args=()):
    for register, value in args:
        authored._li(words, register, value)
    words.extend((0x0c000000 | address >> 2, 0))


def target_job(executable, model, context, pass_limit=1):
    """Execute the original constructors/defaults; retain source binder bytes."""
    source_contract(executable)
    patches = authored.caller(executable, model, context, pass_limit)
    code = next(data for address, data in patches if address == authored.CODE)
    words = list(struct.unpack('<'+'I'*(len(code)//4), code))
    location = words.index(0x0c000000 | 0x3b4800 >> 2) + 2
    setup = []
    _call(setup, 0x5453b0, [(4, DISPLAY), (5, 0), (6, 512), (7, 512),
                          (8, 2), (9, 0x3a), (10, 0)])
    _call(setup, 0x2b7018)
    _call(setup, 0x2b5d40)
    _call(setup, 0x2a4e30, [(4, 0), (5, 0)])
    _call(setup, 0x2a4f40)
    for address, name, kind, bpp in [(COLOR, 0x673fb5, 3, 32), (DEPTH, 0x673fc2, 2, 16)]:
        _call(setup, 0x2b90c0, [(4, address), (5, name), (6, kind), (7, 256),
                              (8, 256), (9, bpp), (10, 0)])
    _call(setup, 0x2b9e48, [(4, authored.MANAGER), (5, COLOR), (6, DEPTH), (7, 0)])
    words[location:location] = setup
    heap = bytearray(0x124)
    heap[0x2a] = 1
    struct.pack_into('<3I', heap, 4, 0x1800000, 0x200000, 0)
    patches = [(address, struct.pack('<'+'I'*len(words), *words) if address == authored.CODE else data)
               for address, data in patches]
    patches += [(COLOR, bytes(0x200)), (DISPLAY, bytes(0x240)), (HEAP, bytes(heap)),
                (0x70e500, struct.pack('<I', HEAP)), (0x711db4, struct.pack('<I', HEAP))]
    return encode_ee_job(authored.CODE, {}, patches)


def initial_gif(executable, ram):
    """Use the actual SDK-produced draw environment and original common ADs."""
    source_contract(executable)
    if len(ram) != 33554432:
        raise ValueError('complete original EE memory required')
    packet = ram[DISPLAY+0x50:DISPLAY+0xe0]
    if struct.unpack_from('<QQ', packet) != (0x1000000000008008, 14):
        raise ValueError('original SDK draw environment tag differs')
    # All eight native AD destinations, including original XYOFFSET and CLAMP.
    if [struct.unpack_from('<Q', packet, i+8)[0] for i in range(16, 144, 16)] != [
            0x4c, 0x4e, 0x18, 0x40, 0x1a, 0x46, 0x45, 0x47]:
        raise ValueError('original SDK draw environment registers differ')
    return [packet, _read_elf(executable, 0x61c3c0, 64)]


def execute_reference(executable, model, output):
    """Fresh original EE→VIF/VU execution with literal SDK output packets."""
    from mc3_reference_runtime import run_job
    from mc3_vehicle_transfer_reference import run_job as transfer
    executable, model, output = Path(executable), Path(model), Path(output)
    source, original = executable.read_bytes(), model.read_bytes()
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in authored.source_contract()['cases']:
        directory = output/case['name']
        directory.mkdir()
        path = directory/'input.job'
        path.write_bytes(target_job(source, original, case['context'], case['pass_limit']))
        ee = run_job(path, directory/'ee', mode='ee', executable=executable)
        ram = (directory/'ee/ee-ram.bin').read_bytes()
        job, dma = authored.coupled_job(source, ram)
        coupled = transfer(job, directory/'coupled')
        packets = initial_gif(source, ram)
        rows.append(dict(name=case['name'], ee=ee, coupled=coupled, dma=dma,
                         initial_gif_sha256=[sha(packet) for packet in packets]))
    (output/'comparison.json').write_text(json.dumps(rows, indent=2)+'\n')
    return rows


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute_reference(args.executable, args.model, args.output)
