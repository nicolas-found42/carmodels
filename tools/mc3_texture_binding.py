"""Source texture state and PF05 image-resource joins, without VRAM defaults.

Constructor state is not effective draw state: native residency selects the
base mip/VRAM addresses, and the binder applies material mode and LOD bias.
"""

import hashlib
import json
from pathlib import Path
import struct

from mc3_textures import (
    SLOT_CLASS,
    indexed_to_rgba,
    native_shared_levels,
    palette_csm1,
    unswizzle8,
)

EXECUTABLE_SHA = "1b237ade5cafaf8ddd9fd049f40d81eb46f38f2600a8f1c7273d4f836973fe9d"
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "research/evidence/midnight-club-3-remix/previews/texture-binding.json"
)
INTERVALS = [
    (
        0x2B73F8,
        0x2B7C54,
        "18b3af82ee8c8aefe523ce0f0236fbfcfb7f842b20fc3de64da70dfd40a8b461",
    ),
    (
        0x2B7F28,
        0x2B8B08,
        "bc1bd2d6c7ed1c702a15d9fa6a075a4cc94040c2793cb487ca6b826f960b0460",
    ),
    (
        0x42CA90,
        0x42CCD0,
        "cc3e2e42476b697ac66cfee7ebe658c712445854cfeb2f08806b086d8d263351",
    ),
    (
        0x3B0FA8,
        0x3B1008,
        "b0cd1f6de65e75271aa0d1d047d98478220b8809555c7fbea312bf20537daaef",
    ),
    (
        0x615FE0,
        0x616004,
        "c3f73bd0199b83c9e996ff6f6838697d932b7a3c7d9abb454898ace28c17e524",
    ),
    (
        0x627280,
        0x6272C4,
        "6632da58a1d95671ac032917345e90cdf76993affefe1bd47feefeafedad3ac9",
    ),
]


def need(value, message):
    if not value:
        raise ValueError(message)


def from_executable(executable):
    from mc3_environment_raster import _read_elf

    need(
        hashlib.sha256(executable).hexdigest() == EXECUTABLE_SHA,
        "native texture executable changed",
    )
    for start, end, digest in INTERVALS:
        need(
            hashlib.sha256(_read_elf(executable, start, end - start)).hexdigest()
            == digest,
            "native texture source interval changed",
        )
    return dict(source_executable_sha256=EXECUTABLE_SHA, intervals=INTERVALS)


def fixture():
    return json.loads(FIXTURE.read_text())


def native_texture_slot(data, offset, profile_delta=0):
    need(
        isinstance(data, bytes)
        and type(offset) is int
        and 0 <= offset <= len(data) - 160,
        "native texture slot outside source",
    )
    need(
        struct.unpack_from("<I", data, offset)[0] == SLOT_CLASS + profile_delta,
        "unknown native texture slot class",
    )
    count = data[offset + 0x86]
    need(1 <= count <= 4, "unsupported native texture level count")
    levels = []
    for i in range(count):
        descriptor, tex0 = struct.unpack_from("<2Q", data, offset + 8 + i * 16)
        pointer, resource_offset, packed = struct.unpack_from(
            "<3I", data, offset + 0x48 + i * 12
        )
        levels.append(
            dict(
                tex0=f"0x{tex0:016x}",
                transfer=f"0x{descriptor:016x}",
                width=1 << (tex0 >> 26 & 15),
                height=1 << (tex0 >> 30 & 15),
                psm=tex0 >> 20 & 63,
                resource=dict(
                    pointer=pointer, offset=resource_offset, packed_handle=packed
                ),
            )
        )
    return dict(
        schema=1,
        source_slot_offset=offset,
        source_slot=data[offset : offset + 160],
        levels=levels,
        tex1=f"0x{struct.unpack_from('<Q', data, offset + 0x88)[0]:016x}",
        clamp=data[offset + 0x85],
        palette_offset=struct.unpack_from("<H", data, offset + 0x80)[0] * 16,
        claim_limits=[
            "Serialized constructor state; effective residency/VRAM/material/LOD context is separate."
        ],
    )


def resolver_reference_job(packed_handle, offset, loaded_base):
    """Original42cc80/42ca90 with an explicitly resident native page entry."""
    from mc3_environment_raster import encode_ee_job

    need(
        type(packed_handle) is int
        and 0x800000 <= packed_handle <= 0xFFFFFFFF
        and type(offset) is int
        and 0 <= offset < 0x10000
        and type(loaded_base) is int
        and 0x1010000 <= loaded_base <= 0x1020000,
        "invalid native resident page context",
    )
    archive, page = packed_handle >> 23, packed_handle & 0x7FFFFF
    need(page < 256, "resident reference page table exceeds controlled profile")
    handle = struct.pack("<3I", 0, offset, packed_handle)
    manager = bytearray(32)
    struct.pack_into("<I", manager, 12, 0x1002000)
    table = bytearray(256 * 4)
    struct.pack_into("<I", table, page * 4, 0x1003000)
    entry = bytearray(64)
    struct.pack_into("<I", entry, 0, loaded_base)
    struct.pack_into("<I", entry, 28, 0x400)
    patches = [
        (0x1000000, handle),
        (0x1001000, bytes(manager)),
        (0x1002000, bytes(table)),
        (0x1003000, bytes(entry)),
        (0x714CC0 + archive * 4, struct.pack("<I", 0x1001000)),
        (loaded_base + offset, bytes(144)),
    ]
    return encode_ee_job(0x42CC80, {4: 0x1000000, 5: 4}, patches, {12: 0xBF800000})


def native_shared_texture_state(data):
    """Default native2b7498 image-constructor fields, before residency/binding.

    The source file loader places its u32 flags at image+8 from file+10. Native
    default615ffc limits to4mips,616000 stops before a next width<=4,615fe0=0
    choosesMMIN4. No effective TBP/CBP or global LOD bias is fabricated here.
    """
    decoded = native_shared_levels(data)
    need(decoded["decode_status"] == "decoded", "shared native image format unresolved")
    flags = struct.unpack_from("<I", data, 10)[0]
    levels = []
    psm = 19 if decoded["index_bits"] == 8 else 20
    for level in decoded["levels"][:4]:
        width, height = level["width"], level["height"]
        if levels and width <= 4:
            break
        tex0 = (
            ((width + 63) // 64 & 63) << 14
            | psm << 20
            | (width.bit_length() - 1) << 26
            | (height.bit_length() - 1) << 30
            | 0x2000000400000000
        )
        levels.append(dict(width=width, height=height, tex0=f"0x{tex0:016x}"))
    tex1 = 0xFFFFFFC000000120 | (len(levels) - 1) << 2
    return dict(
        schema=1,
        source_sha256=hashlib.sha256(data).hexdigest(),
        levels=levels,
        tex1=f"0x{tex1:016x}",
        clamp=(flags & 1) | (4 if flags & 0x10000 else 0),
        claim_limits=[
            "Native default image-constructor state, not filename-loader resizing/fallback or effective draw binding."
        ],
    )


def factory_reference_job(
    data, *, base_mip, lod_bias_word, material_mode, vram_base, vram_end
):
    """Whole original2b73f8 ->2b7498 ->2b7f28 ->2b8768, no callback stubs.

    The image input uses the independently proven .tex loader translation.
    Explicit original bump-heap fields disable small pools and register its
    native heap list, so original malloc/free and upload conversion execute.
    The wrapper copies constructor bytes and the DMA cursor only; all native
    texture allocation, conversion, residency and binding code is unchanged.
    """
    decoded = native_shared_levels(data)
    need(decoded["decode_status"] == "decoded", "reference image unresolved")
    need(
        len(decoded["levels"]) <= 4, "reference image exceeds controlled source layout"
    )
    need(
        type(base_mip) is int
        and 0 <= base_mip < min(4, len(decoded["levels"]))
        and type(lod_bias_word) is int
        and 0 <= lod_bias_word <= 0xFFFFFFFF
        and material_mode in (0, 1, 2)
        and 0 <= vram_base < vram_end <= 0x4000,
        "invalid explicit native binding context",
    )
    palette = decoded["source_palette"]
    native_palette = bytes(
        v
        for i in range(0, len(palette), 4)
        for v in (
            palette[i + 2],
            palette[i + 1],
            palette[i],
            palette[i + 3] * 128 // 255,
        )
    )
    patches = [(0x1000000, bytes(160)), (0x1020000, native_palette)]
    image_format = 5 if decoded["index_bits"] == 8 else 6
    for i, level in enumerate(decoded["levels"]):
        width, height = level["width"], level["height"]
        pitch = width if image_format == 5 else (width + 1) // 2
        node = struct.pack(
            "<4H5I",
            width,
            height,
            pitch,
            0x100 | image_format,
            struct.unpack_from("<I", data, 10)[0],
            0x1030000 + i * 0x40000,
            0x1020000,
            1,
            0x1001000 + (i + 1) * 32 if i + 1 < len(decoded["levels"]) else 0,
        )
        patches += [
            (0x1001000 + i * 32, node),
            (0x1030000 + i * 0x40000, level["source_indices"]),
        ]
    heap = bytearray(0x124)
    heap[0x2A] = 1
    struct.pack_into("<3I", heap, 4, 0x1400000, 0x200000, 0)
    # The copied160bytes are before upload mutates residency/VRAM fields.
    code = struct.pack(
        "<23I",
        0x44C0F800,
        0x3C040100,
        0x3C050100,
        0x34A51000,
        0x0C000000 | (0x2B73F8 >> 2),
        0,
        0x3C040100,
        0x34843000,
        0x3C050100,
        0x240600A0,
        0x0C000000 | (0x432B20 >> 2),
        0,
        0x3C040100,
        0x0C000000 | (0x2B8768 >> 2),
        0,
        0x3C087000,
        0x8D0905AC,
        0x3C0A0100,
        0xAD492000,
        0x3C1F0001,
        0x03E00008,
        0,
        0,
    )
    patches += [
        (0x100A000, code),
        (0x1004000, bytes(heap)),
        (0x70E500, struct.pack("<I", 0x1004000)),
        (0x711DB4, struct.pack("<I", 0x1004000)),
        (0x700005AC, struct.pack("<2I", 0x1100000, 0x1180000)),
        (0x6BE810, struct.pack("<I", base_mip)),
        (0x70FBE4, struct.pack("<4I", lod_bias_word, vram_end, vram_base, vram_base)),
        (0x70000114, struct.pack("<I", material_mode)),
    ]
    result = bytearray(b"MC3EE001") + struct.pack(
        "<5I", 0x100A000, 10000000, 0, 0, len(patches)
    )
    for address, raw in patches:
        result += struct.pack("<2I", address, len(raw)) + raw
    return bytes(result)


def slot_reference_job(slot, resource_block, *, vram_base, vram_end):
    """Execute the original upload/binder on a relocated resident PF05 slot.

    The supplied one-level block is unchanged. Only runtime vtable, resident
    resource pointer and stale cache frame are relocated, after the separately
    executed original42cc80/42ca90 handle-to-page join.
    """
    source = native_texture_slot(slot, 0, 0x1308)
    need(
        len(source["levels"]) == 1 and 0 <= vram_base < vram_end <= 0x4000,
        "unsupported original slot reference context",
    )
    need(
        isinstance(resource_block, bytes) and len(resource_block) >= 0x90,
        "missing original native resource block",
    )
    image = bytearray(slot)
    struct.pack_into("<I", image, 0, 0x627280)
    struct.pack_into("<I", image, 0x48, 0x1200000)
    struct.pack_into("<I", image, 0x7C, 0x80000000)
    code = struct.pack(
        "<11I",
        0x44C0F800,
        0x3C040100,
        0x0C000000 | (0x2B8768 >> 2),
        0,
        0x3C087000,
        0x8D0905AC,
        0x3C0A0100,
        0xAD492000,
        0x3C1F0001,
        0x03E00008,
        0,
    )
    patches = [
        (0x1000000, bytes(image)),
        (0x1200000, resource_block),
        (0x100A000, code),
        (0x700005AC, struct.pack("<2I", 0x1100000, 0x1180000)),
        (0x6BE810, bytes(4)),
        (0x70FBE4, struct.pack("<4I", 0, vram_end, vram_base, vram_base)),
        (0x70000114, struct.pack("<I", 2)),
    ]
    result = bytearray(b"MC3EE001") + struct.pack(
        "<5I", 0x100A000, 1000000, 0, 0, len(patches)
    )
    for address, raw in patches:
        result += struct.pack("<2I", address, len(raw)) + raw
    return bytes(result)


def decode_factory_reference(ram):
    need(len(ram) == 32 * 1024 * 1024, "native texture reference RAM extent differs")
    end = struct.unpack_from("<I", ram, 0x1002000)[0]
    need(
        0x1100000 < end <= 0x1180000 and end % 16 == 0,
        "native texture DMA cursor invalid",
    )
    offset, payloads, refs = 0x1100000, [], []
    while offset < end:
        tag, address, _, command = struct.unpack_from("<4I", ram, offset)
        size, kind = (tag & 65535) * 16, tag >> 28 & 7
        need(
            kind in (1, 3) and command >> 24 == 0x50 and command & 65535 == size // 16,
            "unexpected native texture DMA/VIF profile",
        )
        source = offset + 16 if kind == 1 else address & 0x7FFFFFFF
        need(0 <= source <= len(ram) - size, "native texture DMA read outside RAM")
        raw = ram[source : source + size]
        payloads.append(raw)
        if kind == 3:
            refs.append(
                dict(address=source, bytes=size, sha256=hashlib.sha256(raw).hexdigest())
            )
        offset += 16 + size if kind == 1 else 16
    stream, offset, registers = b"".join(payloads), 0, []
    while offset < len(stream):
        tag, regs = struct.unpack_from("<2Q", stream, offset)
        offset += 16
        count, fmt = tag & 32767, tag >> 58 & 3
        if fmt == 2:
            need(
                offset + count * 16 <= len(stream),
                "truncated native texture IMAGE payload",
            )
            offset += count * 16
            continue
        need(
            fmt == 0 and tag >> 60 & 15 == 1 and regs == 14,
            "unexpected native texture GIF format",
        )
        need(offset + count * 16 <= len(stream), "truncated native texture A+D payload")
        for _ in range(count):
            value, register = struct.unpack_from("<2Q", stream, offset)
            registers.append([register, f"0x{value:016x}"])
            offset += 16
    return dict(
        constructor_hex=ram[0x1003000:0x10030A0].hex(),
        bound_hex=ram[0x1000000:0x10000A0].hex(),
        registers=registers,
        image_refs=refs,
        gif_sha256=hashlib.sha256(stream).hexdigest(),
        dma_sha256=hashlib.sha256(ram[0x1100000:end]).hexdigest(),
    )


def decode_pf05_texture(data, slot_offset, *, archive_index, profile_delta=0x1308):
    """Resolve measured one-level PSMT8/PSMT4 wheel image resource handles.

    Native42ca90 resolves archive/page then adds handle+4 byteoffset. Data begins
    at descriptor+90; the palette offset is slot+80 times16, as used by2b7f28.
    Existing source-proven PSMT8/CSM1 and8x8PSMT4 layouts remain separate.
    """
    from mc3_wheels import ppf_page

    source = native_texture_slot(data, slot_offset, profile_delta)
    need(
        len(source["levels"]) == 1, "PF05 multi-level upload profile remains unresolved"
    )
    level = source["levels"][0]
    handle = level["resource"]
    packed = handle["packed_handle"]
    need(
        type(archive_index) is int
        and 0 <= archive_index <= 511
        and packed >> 23 == archive_index,
        "native texture selects another archive",
    )
    page = ppf_page(data, packed & 0x7FFFFF)
    block = page["offset"] + handle["offset"]
    need(
        page["offset"] <= block <= page["offset"] + page["bytes"] - 0x90,
        "native resource offset outside selected page",
    )
    block_size = struct.unpack_from("<I", data, block + 12)[0]
    need(
        0x90 <= block_size <= page["offset"] + page["bytes"] - block,
        "native texture block outside page",
    )
    start = block + 0x90
    width, height, psm = level["width"], level["height"], level["psm"]
    tex0 = int(level["tex0"], 16)
    need(
        tex0 >> 51 & 15 == 0 and tex0 >> 55 & 1 == 0 and tex0 >> 56 & 31 == 0,
        "unsupported native texture CLUT layout",
    )
    if psm == 19:
        need(
            width == height and width in (16, 32, 64, 128, 256),
            "unresolved PF05 PSMT8 dimensions",
        )
        size, palette_size = width * height, 1024
    else:
        need(
            psm == 20 and (width, height) == (8, 8),
            "unresolved PF05 indexed texture layout",
        )
        size, palette_size = 32, 64
    need(
        source["palette_offset"] == size
        and start + size + palette_size <= block + block_size,
        "native palette/upload extent differs",
    )
    pixels = data[start : start + size]
    palette = data[start + size : start + size + palette_size]
    if psm == 19:
        rgba = indexed_to_rgba(
            unswizzle8(pixels, width, height), palette_csm1(palette), 1
        )
    else:
        indices = [n for v in pixels for n in (v & 15, v >> 4)]
        rgba = b"".join(palette[i * 4 : i * 4 + 4] for i in indices)
    return dict(
        decode_status="decoded",
        levels=[
            dict(
                width=width,
                height=height,
                rgba=rgba,
                source_indices=pixels,
                source_offset=start,
            )
        ],
        source_palette=palette,
        source_slot=source["source_slot"],
        source_descriptor=data[block : block + 0x90],
        source_page_index=page["index"],
        source_page_offset=page["offset"],
        source_block_offset=block,
        source_slot_offset=slot_offset,
        tex0=level["tex0"],
        tex1=source["tex1"],
        clamp=source["clamp"],
        palette_order="RGBA-CSM1" if psm == 19 else "RGBA",
        alpha_conversion="original palette byte",
        claim_limits=[
            "Measured one-level native resource profile; no missing VRAM or other image format is inferred."
        ],
    )
