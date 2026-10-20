"""Execute bounded MC3 jobs in the SHA-pinned official PCSX2 reference binary.

This is an optional independent emulator oracle, not PS2 hardware capture.
No BIOS, personal emulator configuration, ports or unrelated services are used.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import time
import uuid

from mc3_specular_native import EXECUTABLE_SHA

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools/reference-runtime/mc3_reference.cpp"
DEFAULT_IMAGE = "carmodels-mc3-vu-reference:2.8.2"
BINARY_PATH = "/opt/squashfs-root/usr/bin/pcsx2-qt"
BINARY_SHA = "9b935133f224d29981200272492797eee4cb16fece3357119bf90c33cd62e48a"
APPIMAGE_SHA = "0c46bb6a88aa2782b10853a7b07cf3387ba99cbef2b966372cd2315b8571abea"
LIMITS = [
    "Official PCSX2 v2.8.2 software/interpreter reference, not physical PS2.",
    "Explicit source-derived context inputs; no original running-game frame is asserted.",
    "EE jobs isolate pure helpers with inert IOP and future timer events.",
    "VU opcode/pipeline/math and GIF packet scheduling remain in the original binary.",
    "Selected AVX2/FMA profile; other SIMD paths are not certified.",
]


class RuntimeUnavailable(RuntimeError):
    """The optional reference runtime has not been provisioned."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, *, timeout=60):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(
            f"reference command failed ({result.returncode}): {result.stderr[-2000:]}"
        )
    return result.stdout


EVIDENCE = (
    ROOT
    / "research/evidence/midnight-club-3-remix/previews/environment/reference-runtime.json"
)
RECEIPT_SHA = "e5c7feb53e07462cb2248703dabd69b842e24f29216ae7dc56ea30323d3d2a58"
SYMBOLS = {
    "vu_registers": "vuRegs",
    "ee_registers": "_cpuRegistersPack",
    "vu_step": "_Z7vu1ExecP6VURegs",
    "vu_execute": "_ZN9InterpVU17ExecuteEj",
    "gif_transport": "_ZN8Gif_Unit20TransferGSPacketDataE17GIF_TRANSFER_TYPEPhjb",
    "gif_packet_size": "_ZN8Gif_Unit15GetGSPacketSizeE8GIF_PATHPhjjb",
    "ee_step": "_ZL7intStepv",
    "ee_event_callback": "_Z12intEventTestv",
    "configuration": "EmuConfig",
    "ee_hardware": "eeHw",
    "interpreter_vu0": "CpuIntVU0",
    "interpreter_vu1": "CpuIntVU1",
    "provider_vu0": "CpuVU0",
    "provider_vu1": "CpuVU1",
    "iop_provider": "psxCpu",
    "ee_counter_delta": "nextDeltaCounter",
    "iop_counter_delta": "psxNextDeltaCounter",
    "read8": "_Z12vtlb_memReadIhET_j",
    "read16": "_Z12vtlb_memReadItET_j",
    "read32": "_Z12vtlb_memReadIjET_j",
    "read64": "_Z12vtlb_memReadImET_j",
    "read128": "_Z15vtlb_memRead128j",
    "write8": "_Z13vtlb_memWriteIhEvjT_",
    "write16": "_Z13vtlb_memWriteItEvjT_",
    "write32": "_Z13vtlb_memWriteIjEvjT_",
    "write64": "_Z13vtlb_memWriteImEvjT_",
    "write128": "_Z16vtlb_memWrite128jDv2_x",
}


def binary_symbols(data):
    """Read original ELF symbols and instruction hashes, not model-authored addresses."""
    if sha(data) != BINARY_SHA:
        raise ValueError("reference binary identity differs")
    offset = struct.unpack_from("<Q", data, 40)[0]
    width, count = struct.unpack_from("<HH", data, 58)
    sections = [
        struct.unpack_from("<IIQQQQIIQQ", data, offset + i * width)
        for i in range(count)
    ]
    found = {}
    names = {name: role for role, name in SYMBOLS.items()}
    for section in sections:
        if section[1] != 2:
            continue
        strings = sections[section[6]]
        table = data[strings[4] : strings[4] + strings[5]]
        for start in range(section[4], section[4] + section[5], section[9]):
            name, info, _, index, address, size = struct.unpack_from(
                "<IBBHQQ", data, start
            )
            name = table[name : table.index(b"\0", name)].decode()
            if name not in names:
                continue
            value = {"symbol": name, "address": hex(address), "bytes": size}
            if info & 15 == 2:
                segment = sections[index]
                source = segment[4] + address - segment[3]
                value["instruction_sha256"] = sha(data[source : source + size])
            found[names[name]] = value
    if found.keys() != SYMBOLS.keys():
        raise ValueError("reference binary symbols missing")
    return found


def contract(proof=None):
    proof = json.loads(EVIDENCE.read_text()) if proof is None else proof
    if (
        sha(json.dumps(proof, sort_keys=True, separators=(",", ":")).encode())
        != RECEIPT_SHA
    ):
        raise ValueError("reference adapter receipt changed")
    return proof


def from_binary(data):
    proof = contract()
    if binary_symbols(data) != proof["symbols"]:
        raise ValueError("reference adapter source symbols differ")
    return proof


def identity(image=DEFAULT_IMAGE):
    """Check actual executable bytes before using any private ABI offsets."""
    proof = contract()
    if sha(ADAPTER.read_bytes()) != proof["adapter_source_sha256"]:
        raise ValueError("reference adapter source differs")
    if shutil.which("docker") is None:
        raise RuntimeUnavailable("Docker is unavailable")
    try:
        image_id = command(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image]
        ).strip()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise RuntimeUnavailable("Pinned reference image is unavailable") from error
    script = (
        "import hashlib,json;from pathlib import Path;"
        'flags=next((line.split(":",1)[1].split() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("flags")),[]);'
        "print(json.dumps({"
        f'"binary":hashlib.sha256(Path({BINARY_PATH!r}).read_bytes()).hexdigest(),'
        '"appimage":hashlib.sha256(Path("/opt/pcsx2.AppImage").read_bytes()).hexdigest(),"flags":flags}))'
    )
    value = json.loads(
        command(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--platform",
                "linux/amd64",
                "--entrypoint",
                "python3",
                image,
                "-c",
                script,
            ]
        )
    )
    if value.get("binary") != BINARY_SHA or value.get("appimage") != APPIMAGE_SHA:
        raise ValueError(
            "reference binary identity differs; ABI offsets must not be used"
        )
    if not {"avx2", "fma"} <= set(value.get("flags", [])):
        raise RuntimeUnavailable("Selected reference profile requires AVX2/FMA")
    return {
        "image": image,
        "image_id": image_id,
        "binary_sha256": BINARY_SHA,
        "appimage_sha256": APPIMAGE_SHA,
        "gs_simd_profile": "AVX2/FMA",
        "cpu_extensions": [
            flag
            for flag in ("sse4_1", "sse4_2", "avx", "avx2", "fma")
            if flag in value["flags"]
        ],
    }


class Cursor:
    def __init__(self, data):
        self.data, self.offset = data, 0

    def take(self, size):
        if size < 0 or self.offset + size > len(self.data):
            raise ValueError("truncated reference job")
        result = self.data[self.offset : self.offset + size]
        self.offset += size
        return result

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]


def validate_job(data, mode):
    """Refuse malformed adapters before starting foreign code."""
    cur = Cursor(data)
    if mode == "vu":
        if cur.take(8) != b"MC3VU001":
            raise ValueError("VU reference job magic differs")
        cur.take(32768)
        count = cur.u32()
        if not 1 <= count <= 4096:
            raise ValueError("VU reference call count is out of bounds")
        for _ in range(count):
            pc, top, itop, cycles, patches, vfpatches = [cur.u32() for _ in range(6)]
            if (
                pc >= 2048
                or top >= 1024
                or itop >= 65536
                or not 1 <= cycles <= 10_000_000
            ):
                raise ValueError("VU reference call input is out of bounds")
            if patches > 4096 or vfpatches > 31:
                raise ValueError("VU reference patch count is out of bounds")
            for _ in range(patches):
                offset, size = cur.u32(), cur.u32()
                if offset + size > 16384:
                    raise ValueError("VU reference data patch is out of bounds")
                cur.take(size)
            for _ in range(vfpatches):
                if not 1 <= cur.u32() < 32:
                    raise ValueError("VU reference VF patch is out of bounds")
                cur.take(16)
    elif mode == "ee":
        if cur.take(8) != b"MC3EE001":
            raise ValueError("EE reference job magic differs")
        pc, cycles, gprs, fprs, patches = [cur.u32() for _ in range(5)]
        if (
            pc >= 32 * 1024 * 1024
            or not 1 <= cycles <= 10_000_000
            or gprs > 31
            or fprs > 32
            or patches > 4096
        ):
            raise ValueError("EE reference call input is out of bounds")
        for count, size, minimum in [(gprs, 16, 1), (fprs, 4, 0)]:
            for _ in range(count):
                if not minimum <= cur.u32() < 32:
                    raise ValueError("EE reference register patch is out of bounds")
                cur.take(size)
        for _ in range(patches):
            address, size = cur.u32(), cur.u32()
            physical = address & 0x1FFFFFFF
            if not (
                physical + size <= 32 * 1024 * 1024
                or 0x70000000 <= address <= address + size <= 0x70004000
            ):
                raise ValueError("EE reference RAM patch is out of bounds")
            cur.take(size)
    else:
        raise ValueError("unknown reference mode")
    if cur.offset != len(data):
        raise ValueError("reference job has trailing data")


def gif_chunks(data):
    """Keep exact native transport order; chunks need not align to GIF tags."""
    cur, result = Cursor(data), []
    while cur.offset < len(data):
        size = cur.u32()
        if not size or size % 16 or size > 16384:
            raise ValueError("invalid native GIF transport chunk")
        result.append(cur.take(size))
    return result


def fresh_directory(path):
    path = Path(path).resolve()
    if path.exists() and any(path.iterdir()):
        raise ValueError("reference output directory must be empty")
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_job(job, output, mode="vu", executable=None, image=DEFAULT_IMAGE):
    job = Path(job).resolve()
    data = job.read_bytes()
    validate_job(data, mode)
    if mode == "ee":
        if executable is None or sha(Path(executable).read_bytes()) != EXECUTABLE_SHA:
            raise ValueError("original MC3 executable identity differs")
        executable = Path(executable).resolve()
    runtime = identity(image)
    output = fresh_directory(output)
    compile_args = ["g++", "-std=c++17", "-shared", "-fPIC", "-O2"]
    if mode == "ee":
        compile_args.append("-DMC3_REFERENCE_EE")
    compile_args += ["-o", "/out/adapter.so", "/src/mc3_reference.cpp", "-ldl"]
    base = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--platform",
        "linux/amd64",
        "--entrypoint",
        "/bin/sh",
        "-v",
        f"{ADAPTER.parent}:/src:ro",
        "-v",
        f"{output}:/out",
    ]
    command(base + [image, "-c", " ".join(compile_args)])
    args = base + [
        "-v",
        f"{job}:/input/job.bin:ro",
        "-e",
        f"MC3_{mode.upper()}_JOB=/input/job.bin",
        "-e",
        f"MC3_{mode.upper()}_OUT=/out",
    ]
    if mode == "ee":
        args += [
            "-v",
            f"{executable}:/input/SLUS_213.55:ro",
            "-e",
            "MC3_EE_ELF=/input/SLUS_213.55",
        ]
    # AppRun configures its bundled Qt dependencies; replacement main never opens Qt.
    result = subprocess.run(
        args + [image, "-c", "LD_PRELOAD=/out/adapter.so /opt/squashfs-root/AppRun"],
        capture_output=True,
        timeout=120,
    )
    (output / "execution.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(
            f"original {mode.upper()} execution failed ({result.returncode}); see execution.log"
        )
    names = (
        ["gif-chunks.bin", "final-vumem.bin", "final-vuregs.bin", "calls.json"]
        if mode == "vu"
        else ["ee-registers.bin", "ee-ram.bin"]
    )
    files = {
        name: {
            "bytes": (output / name).stat().st_size,
            "sha256": sha((output / name).read_bytes()),
        }
        for name in names
    }
    if mode == "vu":
        gif_chunks((output / "gif-chunks.bin").read_bytes())
    receipt = {
        "status": "executed",
        "mode": mode,
        "runtime": runtime,
        "job_sha256": sha(data),
        "original_mc3_executable_sha256": EXECUTABLE_SHA if mode == "ee" else None,
        "adapter_sha256": sha(ADAPTER.read_bytes()),
        "portable_vu_pointer_fields_zeroed": mode == "vu",
        "outputs": files,
        "claim_limits": LIMITS,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def ad(items):
    return struct.pack("<QQ", len(items) | (1 << 15) | (1 << 60), 0xE) + b"".join(
        struct.pack("<QQ", value, reg) for reg, value in items
    )


def upload_rgba(data, width, height, base=0x2000):
    if (
        not 1 <= width <= 512
        or not 1 <= height <= 512
        or len(data) != width * height * 4
        or len(data) % 16
    ):
        raise ValueError("reference texture upload dimensions differ")
    # NLOOP is fifteen bits. Consecutive IMAGE tags continue the same native
    # BITBLT/TRX stream; do not reset its destination between payload chunks.
    result = bytearray(
        ad(
            [
                (0x50, base << 32 | ((width + 63) // 64) << 48),
                (0x51, 0),
                (0x52, width | height << 32),
                (0x53, 0),
            ]
        )
    )
    for start in range(0, len(data), 0x7FFF * 16):
        payload = data[start : start + 0x7FFF * 16]
        result.extend(struct.pack("<QQ", len(payload) // 16 | (1 << 15) | (2 << 58), 0))
        result.extend(payload)
    return bytes(result)


def write_gs_dump(path, packets, width=256, height=256, display_fbp=0):
    """Synthetic carrier for original GS events, never labelled a live capture."""
    if (
        not 1 <= width <= 2048
        or not 1 <= height <= 2048
        or any(len(p) % 16 for p in packets)
    ):
        raise ValueError("invalid GS reference carrier")
    if type(display_fbp) is not int or not 0 <= display_fbp <= 511:
        raise ValueError("invalid GS reference display framebuffer")
    state, regs = bytearray(5 * 1024 * 1024), bytearray(8192)
    struct.pack_into("<I", state, 0, 8)
    struct.pack_into("<Q", regs, 0, 1 | (1 << 5) | (128 << 8))
    # VSync only flushes pending draws intersecting an enabled display.
    # Map readout to the target under test without modifying its GIF events.
    struct.pack_into("<Q", regs, 0x70, display_fbp | ((width + 63) // 64) << 9)
    struct.pack_into("<Q", regs, 0x80, ((width - 1) << 32) | ((height - 1) << 44))
    header = struct.pack("<9I", 8, len(state), 36, 0, 0, 0, 0, 36, 0)
    data = bytearray(
        struct.pack("<II", 0xFFFFFFFF, len(header)) + header + state + regs
    )
    for _ in range(3):
        for packet in packets:
            data.extend(b"\0\2" + struct.pack("<I", len(packet)) + packet)
        data.extend(b"\3" + regs + b"\1\0")
    Path(path).write_bytes(data)


GS_CONFIG = """[UI]
SettingsVersion = 1
SetupWizardIncomplete = false
StartPaused = false
ConfirmShutdown = false
[EmuCore/GS]
Renderer = 13
SWExtraThreads = 0
DumpGSData = true
SaveRT = true
SaveAlpha = true
SaveFrame = true
SaveDrawCount = 4096
SaveFrameCount = 3
SWDumpDirectory = /data/draws
HWDumpDirectory = /data/draws
[SPU2/Output]
Backend = Null
"""


def gs_configuration(save_depth=False):
    if type(save_depth) is not bool:
        raise ValueError("reference GS save_depth must be boolean")
    return (
        GS_CONFIG.replace("SaveRT = true\n", "SaveRT = true\nSaveDepth = true\n")
        if save_depth
        else GS_CONFIG
    )


def gs_frame_complete(draws, *, save_depth=False):
    # A draw's RT1 can precede later passes. GetOutput's frame snapshot is
    # emitted at VSync after the whole frame; it is only a completion marker.
    draws = Path(draws)
    markers = list(draws.glob("*_f00002_fr0_*_C_32.png"))
    targets = list(draws.glob("*_rt1_*_C_32.png"))
    depths = list(draws.glob("*_f00002_rz1_*_Z_16S.png")) if save_depth else []
    if not markers or not targets:
        return False
    if save_depth and not depths:
        return False
    for path in markers + targets:
        for candidate in (path, path.with_name(path.stem + "_alpha.png")):
            if not candidate.is_file():
                return False
            data = candidate.read_bytes()
            if (
                len(data) < 20
                or data[:8] != b"\x89PNG\r\n\x1a\n"
                or data[-12:-4] != b"\0\0\0\0IEND"
            ):
                return False
    for candidate in depths:
        data = candidate.read_bytes()
        if (
            len(data) < 20
            or data[:8] != b"\x89PNG\r\n\x1a\n"
            or data[-12:-4] != b"\0\0\0\0IEND"
        ):
            return False
    return True


def run_gs(dump, output, image=DEFAULT_IMAGE, timeout=40, *, save_depth=False):
    configuration = gs_configuration(save_depth)
    runtime = identity(image)
    dump, output = Path(dump).resolve(), fresh_directory(output)
    (output / "draws").mkdir()
    (output / "PCSX2/inis").mkdir(parents=True)
    (output / "PCSX2/inis/PCSX2.ini").write_text(configuration)
    name = "carmodels-mc3-reference-" + uuid.uuid4().hex[:12]
    command(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--network=none",
            "--shm-size=1g",
            "--name",
            name,
            "--platform",
            "linux/amd64",
            "-v",
            f"{output}:/data",
            "-v",
            f"{dump}:/input.gs:ro",
            image,
            "/input.gs",
        ]
    )
    try:
        deadline = time.monotonic() + timeout
        while not gs_frame_complete(output / "draws", save_depth=save_depth):
            if time.monotonic() >= deadline:
                raise TimeoutError("reference GS draw output did not complete")
            time.sleep(0.1)
        script = (
            "from PIL import Image;from pathlib import Path;import json;out=[]\n"
            'for p in sorted(Path("/data/draws").glob("*_rt1_*_C_32.png")):\n'
            ' a=Image.open(p.with_name(p.stem+"_alpha.png")).convert("L").tobytes();'
            'im=Image.open(p).convert("RGB");r=im.tobytes();'
            "raw=bytes(v for i in range(len(a)) for v in (*r[i*3:i*3+3],a[i]));"
            'f=Path("/data")/(p.stem+".rgba");f.write_bytes(raw);'
            'out.append({"file":f.name,"size":im.size})\n'
        )
        if save_depth:
            # Pinned GSLocalMemory::SaveBMP stores ReadPixel16SZ's raw u16 in
            # a u32 RGB_A PNG. R/G are the exact low/high bytes, not RGB5551.
            script += (
                'for p in sorted(Path("/data/draws").glob("*_rz1_*_Z_16S.png")):\n'
                ' im=Image.open(p).convert("RGB");r=im.tobytes();'
                "assert all(r[i]==0 for i in range(2,len(r),3));"
                "raw=bytes(v for i in range(0,len(r),3) for v in r[i:i+2]);"
                'f=Path("/data")/(p.stem+".z16");f.write_bytes(raw);'
                'out.append({"file":f.name,"size":im.size,"kind":"depth16"})\n'
            )
        script += "print(json.dumps(out))"
        frames = json.loads(command(["docker", "exec", name, "python3", "-c", script]))
    finally:
        subprocess.run(["docker", "stop", name], capture_output=True, timeout=15)
    depth_frames = [frame for frame in frames if frame.get("kind") == "depth16"]
    frames = [frame for frame in frames if "kind" not in frame]
    for frame in frames + depth_frames:
        data = (output / frame["file"]).read_bytes()
        frame.update(bytes=len(data), sha256=sha(data))
    receipt = {
        "status": "executed",
        "mode": "gs",
        "runtime": runtime,
        "dump_sha256": sha(dump.read_bytes()),
        "frames": frames,
        "claim_limits": LIMITS,
    }
    if save_depth:
        receipt["depth_frames"] = depth_frames
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--available", action="store_true")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--mode", choices=["vu", "ee", "gs"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--save-depth", action="store_true")
    args = parser.parse_args()
    if args.save_depth and args.mode != "gs":
        parser.error("--save-depth requires --mode gs")
    try:
        if args.available:
            value = {"status": "available", **identity(args.image)}
        elif args.mode and args.input and args.output:
            value = (
                run_gs(args.input, args.output, args.image, save_depth=args.save_depth)
                if args.mode == "gs"
                else run_job(
                    args.input, args.output, args.mode, args.executable, args.image
                )
            )
        else:
            parser.error("choose --available or provide --mode, --input and --output")
    except RuntimeUnavailable as error:
        print(
            json.dumps(
                {"status": "unavailable", "reason": str(error), "claim_limits": LIMITS}
            )
        )
        return 3
    print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
