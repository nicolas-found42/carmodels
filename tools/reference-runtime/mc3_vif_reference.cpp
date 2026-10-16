// Research adapter to original SHA-pinned PCSX2 v2.8.2 VIF1 functions.
// VIF unpack/code generation stays in the original binary. Layouts follow its
// Vif_Dma.h/Vif.h (PCSX2 Dev Team, GPL-3.0+). No BIOS or guest configuration.
// SPDX-License-Identifier: GPL-3.0+
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>
#include <link.h>
#include <dlfcn.h>
#include <sys/mman.h>
using u8 = uint8_t;
using u32 = uint32_t;
using up = uintptr_t;
static up base;
static int find_base(dl_phdr_info* info, size_t, void*) {
  if (!info->dlpi_name || !*info->dlpi_name) base = info->dlpi_addr;
  return 0;
}
static void read(std::ifstream& input, void* data, size_t size) {
  input.read(static_cast<char*>(data), size);
  if (!input) std::abort();
}
static int harness_main(int, char**, char**) {
  dl_iterate_phdr(find_base, nullptr);
  // SysMemory's original VIF code reserves are offsets within this allocation.
  void* code = mmap(nullptr, 0x20000000, PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (code == MAP_FAILED) return 2;
  *reinterpret_cast<up*>(base + 0x188d578) = reinterpret_cast<up>(code);
  reinterpret_cast<void(*)()>(base + 0x86d350)(); // VifUnpackSSE_Init
  reinterpret_cast<void(*)(int)>(base + 0x5d9660)(1); // resetNewVif: sets idx1
  reinterpret_cast<void(*)(int)>(base + 0x86a300)(1); // dVifReset
  auto* memory = static_cast<u8*>(std::aligned_alloc(16, 16384));
  if (!memory) return 2;
  *reinterpret_cast<u8**>(base + 0x351c530 + 1680 + 1208) = memory;
  const char* job = std::getenv("MC3_VIF_JOB");
  const char* output = std::getenv("MC3_VIF_OUT");
  if (!job || !output) return 3;
  std::ifstream input(job, std::ios::binary);
  char magic[8];
  read(input, magic, 8);
  if (std::memcmp(magic, "MC3VIF02", 8)) return 3;
  u32 count;
  read(input, &count, 4);
  if (!count || count > 100000) return 3;
  std::ofstream result(output, std::ios::binary);
  auto* vif = reinterpret_cast<u8*>(base + 0x32d70a0);
  auto* regs = reinterpret_cast<u8*>(base + 0x188e000 + 0x3c00);
  for (u32 index = 0; index < count; index++) {
    read(input, vif, 144);
    read(input, regs, 384);
    read(input, memory, 16384);
    u32 size;
    read(input, &size, 4);
    const u32 sizes[16] = {4,2,1,0,8,4,2,0,12,6,3,0,16,8,4,2};
    u32 cmd = *reinterpret_cast<u32*>(vif + 48);
    u32 num = *reinterpret_cast<u32*>(regs + 0x60);
    u32 mode = *reinterpret_cast<u32*>(regs + 0x50);
    u32 address = *reinterpret_cast<u32*>(vif + 32);
    if ((cmd >> 5) != 3 || !sizes[cmd & 15] || !num || num > 256
        || mode > 3 || address >= 16384 || address % 16
        || vif[60] > 1 || !vif[61] || vif[61] > 4) return 3;
    u32 cl = regs[0x40], wl = regs[0x41] ? regs[0x41] : 256;
    u32 reads = cl < wl ? cl * (num / wl) + std::min(num % wl, cl) : num;
    u32 required = (reads * sizes[cmd & 15] + 3) & ~3u;
    if (size < std::max(16u, required) || size > 1048576) return 3;
    // The extra16 bytes permit original SIMD read-ahead, never missing source data.
    std::vector<u8> data(size + 16);
    read(input, data.data(), size);
    reinterpret_cast<void(*)(const u8*, bool)>(base + 0x86b500)(
        data.data(), cl < wl);
    result.write(reinterpret_cast<char*>(vif), 144);
    result.write(reinterpret_cast<char*>(regs), 384);
    result.write(reinterpret_cast<char*>(memory), 16384);
  }
  if (!result) return 4;
  fprintf(stderr, "Original VIF1 dynamic unpack cases: %u\n", count);
  return 0;
}
extern "C" int __libc_start_main(int(*)(int, char**, char**), int argc,
    char** argv, void(*init)(), void(*fini)(), void(*rtld)(), void* stack) {
  auto real = reinterpret_cast<int(*)(int(*)(int, char**, char**), int, char**,
      void(*)(), void(*)(), void(*)(), void*)>(dlsym(RTLD_NEXT, "__libc_start_main"));
  return real(harness_main, argc, argv, init, fini, rtld, stack);
}
