"""Original MC3 wheel lookup/frame and vehicle morph-palette helper jobs.

Runtime state remains explicit. Matrix products, scalar palette arithmetic and
lookup generation execute the original EE code in the pinned reference. This
module supplies no simulation, rider pose or guessed damage/suspension state.
"""
import hashlib
import json
from pathlib import Path
import struct

from mc3_environment_raster import EXECUTABLE_SHA, _read_elf, encode_ee_job

EVIDENCE = (Path(__file__).resolve().parents[1] / 'research/evidence/'
            'midnight-club-3-remix/previews/vehicle-animation.json')
PROOF_SHA = '630f697ed5931b036301738572dfa348f415f9e76f42e2273b0f410596e8c568'
ACTOR, WRAPPER, LEFT, RIGHT, DEST = 0x1F02000, 0x1F00000, 0x1F04000, 0x1F06000, 0x1F08000


def need(condition, message):
    if not condition:
        raise ValueError(message)


def source_contract(executable=None, receipt=None):
    proof = json.loads(EVIDENCE.read_text()) if receipt is None else receipt
    digest = hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    need(digest == PROOF_SHA, 'vehicle animation receipt changed')
    need(proof['source_executable_sha256'] == EXECUTABLE_SHA, 'vehicle animation source identity changed')
    if executable is not None:
        need(hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
             'vehicle animation executable changed')
        for pin in proof['source_intervals'].values():
            raw = _read_elf(executable, pin['start'], pin['end']-pin['start'])
            need(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'vehicle animation source changed')
    return proof


def lookup_job(executable):
    source_contract(executable)
    return encode_ee_job(0x2233F0, {4: 1, 5: 0xFFFF}, [])


def wheel_basis_words(index, *, steering=False, suspension_word=0):
    """Raw source-assembled compact frame; no host trig or normalization."""
    proof = source_contract()
    need(type(index) is int and 0 <= index < 128, 'wheel lookup index outside native range')
    need(type(steering) is bool and type(suspension_word) is int
         and 0 <= suspension_word <= 0xFFFFFFFF, 'invalid explicit wheel frame input')
    sine, cosine = proof['lookup_words'][index]
    one, zero = 0x3F800000, 0
    if steering:
        return [cosine, zero, sine ^ 0x80000000, zero, one, zero,
                sine, zero, cosine, zero, suspension_word, zero]
    return [one, zero, zero, zero, cosine, sine ^ 0x80000000,
            zero, sine, cosine, zero, suspension_word, zero]


def _frame(words):
    need(isinstance(words, list) and len(words) == 12
         and all(type(x) is int and 0 <= x <= 0xFFFFFFFF for x in words),
         'invalid native compact frame words')
    return struct.pack('<12I', *words)


def rotation_job(executable, roll_index, steer_index):
    """Original in-place23e860 composes front-wheel roll and steering."""
    source_contract(executable)
    return encode_ee_job(0x23E860, {4: LEFT, 5: RIGHT},
                         [(LEFT, _frame(wheel_basis_words(roll_index))),
                          (RIGHT, _frame(wheel_basis_words(steer_index, steering=True)))])


def frame_job(executable, rotation_words, rest_words):
    """Original23e308 frame composition, with explicit source-derived frames."""
    source_contract(executable)
    return encode_ee_job(0x23E308, {4: DEST, 5: LEFT, 6: RIGHT},
                         [(LEFT, _frame(rotation_words)), (RIGHT, _frame(rest_words))])


def morph_palette_job(executable, state_byte):
    """Run original22ac20 with an explicitly initialized packet buffer.

    The wrapper only sets packet pointers and preserves the caller return
    address; all state-byte interpretation and floating-point math stay native.
    Resulting UNPACK headers and16palette rows are retained in EE RAM atLEFT.
    """
    source_contract(executable)
    need(type(state_byte) is int and 0 <= state_byte <= 255, 'invalid native morph state byte')
    actor = bytearray(0x158)
    actor[0x157] = state_byte
    wrapper = [0x03E0B82D, 0x3C087000, 0x3C0901F0, 0x35294000,
               0x3C0A01F0, 0x354A6000, 0xAD0905AC, 0xAD0A05B0,
               0x0C000000 | (0x22AC20 >> 2), 0, 0x02E0F82D, 0x03E00008, 0]
    return encode_ee_job(WRAPPER, {4: ACTOR},
                         [(WRAPPER, struct.pack('<'+'I'*len(wrapper), *wrapper)), (ACTOR, bytes(actor))])


def read_morph_palette(ram):
    need(isinstance(ram, bytes) and len(ram) == 32*1024*1024, 'invalid native morph RAM output')
    need(struct.unpack_from('<4I', ram, LEFT) == (0x10000001, 0, 0x11000000, 0x6C014034)
         and struct.unpack_from('<4I', ram, LEFT+32) == (0x10000010, 0, 0x11000000, 0x6C104318),
         'native morph packet headers changed')
    return {'vu52_words': list(struct.unpack_from('<4I', ram, LEFT+16)),
            'palette_words': [list(struct.unpack_from('<4I', ram, LEFT+48+i*16)) for i in range(16)]}


def execute_reference(executable, output, runner=None):
    """Rederive the lookup first, then verify thirteen original helper probes."""
    from mc3_reference_runtime import run_job
    runner = run_job if runner is None else runner
    proof = source_contract(executable)
    output = Path(output)
    need(not output.exists(), 'choose a fresh vehicle animation output directory')
    output.mkdir(parents=True)
    source = output/'SLUS_213.55'
    source.write_bytes(executable)

    def execute(name, job, expected_sha):
        need(hashlib.sha256(job).hexdigest() == expected_sha, 'vehicle animation job changed')
        path, directory = output/(name+'.job'), output/name
        path.write_bytes(job)
        receipt = runner(path, directory, mode='ee', executable=source)
        need(receipt['status'] == 'executed' and receipt['job_sha256'] == expected_sha
             and receipt['runtime']['binary_sha256'] == proof['reference_binary_sha256']
             and receipt['adapter_sha256'] == proof['adapter_sha256'],
             'vehicle animation execution binding changed')
        ram = (directory/'ee-ram.bin').read_bytes()
        need(len(ram) == 32*1024*1024, 'invalid vehicle animation RAM output')
        return ram, receipt

    ram, receipt = execute('lookup', lookup_job(executable), proof['lookup_job_sha256'])
    raw = ram[proof['lookup_address']:proof['lookup_address']+1024]
    need(hashlib.sha256(raw).hexdigest() == proof['lookup_sha256']
         and [list(struct.unpack_from('<2I', raw, i*8)) for i in range(128)] == proof['lookup_words'],
         'executed native wheel lookup changed')
    result = [{'name': 'lookup', 'execution': receipt}]
    for index, probe in enumerate(proof['numerical_probes']):
        kind = probe['kind']
        if kind == 'morph':
            job = morph_palette_job(executable, probe['state_byte'])
        elif kind == 'rotation':
            job = rotation_job(executable, probe['roll'], probe['steer'])
        elif kind == 'frame':
            job = frame_job(executable, probe['rotation_words'], probe['rest_words'])
        else:
            raise ValueError('unsupported vehicle animation probe')
        ram, receipt = execute(str(index)+'-'+kind, job, probe['job_sha256'])
        actual = read_morph_palette(ram) if kind == 'morph' else list(struct.unpack_from(
            '<12I', ram, LEFT if kind == 'rotation' else DEST))
        need(actual == probe['output' if kind == 'morph' else 'output_words'],
             'executed vehicle animation output changed')
        result.append({'name': str(index)+'-'+kind, 'output': actual, 'execution': receipt})
    (output/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
