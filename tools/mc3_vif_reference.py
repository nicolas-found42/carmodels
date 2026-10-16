"""Independent original PCSX2 VIF1 dynamic-unpack execution, not a Python unpacker.

Only code-reserve/VU-data transport is adapted. The original dynamic compiler,
mask/mode logic and memory-wrap fallback execute inside the pinned binary.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_reference_runtime import (ROOT, DEFAULT_IMAGE, BINARY_SHA, Cursor,
                                   command, identity)

ADAPTER = ROOT / 'tools/reference-runtime/mc3_vif_reference.cpp'
EVIDENCE = ROOT / 'research/evidence/midnight-club-3-remix/previews/vehicle-vif-reference.json'
RECEIPT_SHA = 'db9411a48c997c7075a45963e56b0cee13e3842ae202c831e459b60af239def9'
OUTPUT_SIZE = 144+384+16384
SIZES = (4, 2, 1, 0, 8, 4, 2, 0, 12, 6, 3, 0, 16, 8, 4, 2)


def sha(data):
    return hashlib.sha256(data).hexdigest()


SYMBOLS = {
    'vif1': 'vif1', 'ee_hardware': 'eeHw', 'vu_registers': 'vuRegs',
    'unpack_dynamic': '_Z10dVifUnpackILi1EEvPKhb',
    'unpack_interpreter': '_Z11_nVifUnpackiPKhjb',
    'reset': '_Z11resetNewVifi', 'reset_dynamic': '_Z9dVifReseti',
    'initialize_sse': '_Z17VifUnpackSSE_Initv',
    'code_reserve': '_ZN9SysMemoryL13s_code_memoryE.llvm.8852152464508194628',
}


def binary_symbols(data):
    if sha(data) != BINARY_SHA:
        raise ValueError('VIF reference binary identity differs')
    offset = struct.unpack_from('<Q', data, 40)[0]
    width, count = struct.unpack_from('<HH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset+i*width) for i in range(count)]
    names = {name: role for role, name in SYMBOLS.items()}
    result = {}
    for section in sections:
        if section[1] != 2:
            continue
        strings = sections[section[6]]
        table = data[strings[4]:strings[4]+strings[5]]
        for start in range(section[4], section[4]+section[5], section[9]):
            name, info, _, index, address, size = struct.unpack_from('<IBBHQQ', data, start)
            name = table[name:table.index(b'\0', name)].decode()
            if name not in names:
                continue
            value = dict(symbol=name, address=hex(address), bytes=size)
            if info & 15 == 2:
                segment = sections[index]
                source = segment[4]+address-segment[3]
                value['instruction_sha256'] = sha(data[source:source+size])
            result[names[name]] = value
    if result.keys() != SYMBOLS.keys():
        raise ValueError('VIF reference symbols missing')
    return result


def contract():
    raw = EVIDENCE.read_bytes()
    if sha(raw) != RECEIPT_SHA:
        raise ValueError('VIF reference receipt differs')
    proof = json.loads(raw)
    if proof['adapter_sha256'] != sha(ADAPTER.read_bytes()):
        raise ValueError('VIF reference adapter differs')
    return proof


def from_binary(data):
    proof = contract()
    if binary_symbols(data) != proof['symbols']:
        raise ValueError('VIF reference source symbols differ')
    return proof


def unpack_case(*, kind, alignment, data, memory=None, row=(0, 0, 0, 0),
                col=(0, 0, 0, 0), count=8, cl=1, wl=1, mode=0, mask=0,
                masked=False, unsigned=False, start=0):
    """Explicit raw state carrier; no source geometry is reconstructed here."""
    vif, regs = bytearray(144), bytearray(384)
    struct.pack_into('<4I', vif, 0, *row)
    struct.pack_into('<4I', vif, 16, *col)
    struct.pack_into('<I', vif, 32, start*16)
    struct.pack_into('<I', vif, 48, 0x60+kind+(16 if masked else 0))
    vif[60:62] = bytes((unsigned, alignment))
    regs[64:66] = bytes((cl, wl))
    struct.pack_into('<I', regs, 80, mode)
    struct.pack_into('<I', regs, 96, count)
    struct.pack_into('<I', regs, 112, mask)
    return bytes(vif+regs)+(bytes(16384) if memory is None else memory)+struct.pack('<I', len(data))+data


def build_job(cases):
    result = b'MC3VIF02'+struct.pack('<I', len(cases))+b''.join(cases)
    validate_job(result)
    return result


def validate_job(data):
    cur = Cursor(data)
    if cur.take(8) != b'MC3VIF02':
        raise ValueError('VIF reference job magic differs')
    count = cur.u32()
    if not 1 <= count <= 100000:
        raise ValueError('VIF reference case count differs')
    for _ in range(count):
        vif, regs = cur.take(144), cur.take(384)
        cmd = struct.unpack_from('<I', vif, 48)[0]
        mode = struct.unpack_from('<I', regs, 80)[0]
        num = struct.unpack_from('<I', regs, 96)[0]
        addr = struct.unpack_from('<I', vif, 32)[0]
        if (cmd >> 5 != 3 or not SIZES[cmd & 15] or mode > 3 or not 1 <= num <= 256
                or addr % 16 or addr >= 16384 or vif[60] > 1 or not 1 <= vif[61] <= 4):
            raise ValueError('VIF reference case state differs')
        cur.take(16384)
        size = cur.u32()
        cl, wl = regs[64], regs[65] or 256
        reads = cl*(num//wl)+min(num % wl, cl) if cl < wl else num
        required = (reads*SIZES[cmd & 15]+3) & ~3
        # Original SIMD unpack may read a full16-byte vector at the final
        # source address, including fill cycles. The native adapter supplies
        # a separate zero-initialized16-byte tail; it cannot replace consumed data.
        if not max(16, required) <= size <= 1048576:
            raise ValueError('VIF reference source payload is too short or too large')
        cur.take(size)
    if cur.offset != len(data):
        raise ValueError('VIF reference job has trailing bytes')
    return count


def reference_cases():
    """Deterministic explicit state controls, independent of browser implementation."""
    cases = []
    for kind in (8, 9, 10):
        for alignment in (1, 2, 3, 4):
            inputs = dict(kind=kind, alignment=alignment)
            cases.append((dict(name=f'v3-{kind}-{alignment}', **inputs),
                          unpack_case(**inputs, data=bytes(range(1, 113)))))
    for kind in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15):
        for variant in range(4):
            cl, wl = ((1, 1), (4, 2), (2, 5), (1, 1))[variant]
            inputs = dict(kind=kind, alignment=variant+1, cl=cl, wl=wl,
                          start=1020 if variant == 3 else 16, mode=variant,
                          masked=variant in (1, 2), unsigned=bool(variant & 1),
                          row=[0x12345678, 0xfffffffe, 3, 0x80000000],
                          col=[11, 22, 33, 44], mask=0xe41b39c6)
            case = unpack_case(**inputs, data=bytes((i*17+(i//3)*19)&255 for i in range(256)),
                               memory=bytes((i*23+7)&255 for i in range(16384)))
            cases.append((dict(name=f'broad-{kind}-{variant}', **inputs), case))
    for kind in (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15):
        for mode in (0, 1, 2):
            inputs = dict(kind=kind, alignment=1, cl=1, wl=1, start=1020,
                          mode=mode, masked=False, unsigned=False,
                          row=[0x12345678, 0xfffffffe, 3, 0x80000000],
                          col=[11, 22, 33, 44], mask=0xe41b39c6)
            case = unpack_case(**inputs, data=bytes((i*17+(i//3)*19)&255 for i in range(256)),
                               memory=bytes((i*23+7)&255 for i in range(16384)))
            cases.append((dict(name=f'broad-wrap-{kind}-{mode}', **inputs), case))
    return cases


def execute(job, output, image=DEFAULT_IMAGE):
    """Run one fresh explicit job after identity checks; return transport evidence."""
    count = validate_job(job)
    contract()
    profile = identity(image)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    job_path = output/'input.job'
    job_path.write_bytes(job)
    args = ['docker', 'run', '--rm', '--network=none', '--platform', 'linux/amd64',
            '--entrypoint', '/bin/bash', '-v', f'{ROOT}:/repo:ro', '-v', f'{output}:/work', image]
    script = ('g++ -O2 -shared -fPIC /repo/tools/reference-runtime/mc3_vif_reference.cpp -ldl -o /work/adapter.so && '
              'MC3_VIF_JOB=/work/input.job MC3_VIF_OUT=/work/result.bin LD_PRELOAD=/work/adapter.so /opt/squashfs-root/AppRun')
    log = command(args+['-c', script], timeout=120)
    raw = (output/'result.bin').read_bytes()
    if len(raw) != count*OUTPUT_SIZE:
        raise ValueError('VIF reference output length differs')
    receipt = dict(binary_sha256=BINARY_SHA, profile=profile,
                   adapter_sha256=sha(ADAPTER.read_bytes()), job_sha256=sha(job),
                   output_sha256=sha(raw), count=count)
    (output/'execution.json').write_text(json.dumps(receipt, indent=2)+'\n')
    (output/'stdout.log').write_text(log)
    return raw, receipt


def execute_reference(output, image=DEFAULT_IMAGE):
    """Fresh independent execution of every committed explicit input control."""
    proof = contract()
    cases = reference_cases()
    job = build_job([case for _, case in cases])
    if sha(job) != proof['job_sha256']:
        raise ValueError('VIF reference reconstructed inputs differ')
    raw, receipt = execute(job, output, image)
    if sha(raw) != proof['output_sha256']:
        raise ValueError('VIF reference complete native output differs')
    for index, ((_, case), expected) in enumerate(zip(cases, proof['cases'])):
        result = raw[index*OUTPUT_SIZE:(index+1)*OUTPUT_SIZE]
        if (sha(case) != expected['case_sha256']
                or sha(result[528:]) != expected['memory_sha256']
                or list(struct.unpack_from('<4I', result, 0)) != expected['result_row']):
            raise ValueError('VIF reference output differs: '+expected['name'])
    return receipt
