// Coupled original VIF1 dispatcher -> VU1 -> GIF transport reference.
// Reuse the already source-pinned VU ABI declarations/transport adapter;
// neither VIF handlers nor VU opcode, pipeline or numerical code is replaced.
// SPDX-License-Identifier: GPL-3.0+
#include <vector>
#define harness_main reference_standalone_main
#define __libc_start_main reference_libc_start_main
#include "/repo/tools/reference-runtime/mc3_reference.cpp"
#undef harness_main
#undef __libc_start_main
static int coupled_main(int, char**, char**) {
  const char* job = getenv("MC3_COUPLED_JOB");
  const char* out = getenv("MC3_COUPLED_OUT");
  if (!job || !out) return 2;
  std::ifstream input(job, std::ios::binary);
  if (!input) return 2;
  char magic[8];
  readbytes(input, magic, 8);
  if (memcmp(magic, "MC3CV001", 8)) return 3;
  dl_iterate_phdr(find_base, nullptr);
  auto* v = reinterpret_cast<VURegs*>(base + 0x351c530);
  for (int i = 0; i < 2; i++) {
    memset(&v[i], 0, sizeof(VURegs));
    v[i].idx = i;
    v[i].Mem = static_cast<u8*>(aligned_alloc(16, 16384));
    v[i].Micro = static_cast<u8*>(aligned_alloc(16, 16384));
    if (!v[i].Mem || !v[i].Micro) return 2;
    memset(v[i].Mem, 0, 16384);
    memset(v[i].Micro, 0, 16384);
    v[i].VF[0].f.w = 1;
  }
  // Explicit interpreter context. No original running-game configuration is
  // inferred. The fixed EE clock is not a cumulative VU-cycle oracle.
  *reinterpret_cast<u32*>(base + 0x30a0670) = 0;
  *reinterpret_cast<uintptr_t*>(base + 0x351c518) = base + 0x10681a0;
  *reinterpret_cast<uintptr_t*>(base + 0x351c520) = base + 0x10681b0;
  *reinterpret_cast<int*>(base + 0x107cd18) = 0x7fffffff;
  *reinterpret_cast<int*>(base + 0x10792e8) = 0x7fffffff;
  void* code = mmap(nullptr, 0x20000000, PROT_READ | PROT_WRITE | PROT_EXEC,
                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (code == MAP_FAILED) return 2;
  *reinterpret_cast<uintptr_t*>(base + 0x188d578) = reinterpret_cast<uintptr_t>(code);
  reinterpret_cast<void(*)()>(base + 0x86d350)(); // VifUnpackSSE_Init
  reinterpret_cast<void(*)(int)>(base + 0x5d9660)(1); // resetNewVif
  reinterpret_cast<void(*)(int)>(base + 0x86a300)(1); // dVifReset
  readbytes(input, v[1].Micro, 16384);
  readbytes(input, v[1].Mem, 16384);
  readbytes(input, reinterpret_cast<void*>(base + 0x32d70a0), 144);
  readbytes(input, reinterpret_cast<void*>(base + 0x188e000 + 0x3c00), 384);
  u32 size = read32(input);
  if (!size || size % 4 || size > 10485760) return 3;
  std::vector<u32> stream((size + 16 + 3) / 4);
  readbytes(input, stream.data(), size);
  captured = fopen((std::string(out) + "/gif-chunks.bin").c_str(), "wb");
  if (!captured) return 4;
  patch_transport();
  // TTE=true leaves DMA address/channel ownership with the explicit carrier.
  // The original function still dispatches every VIF command and VU call.
  bool result = reinterpret_cast<bool(*)(u32*, int, bool)>(base + 0x5c45b0)(
      stream.data(), size / 4, true);
  reinterpret_cast<void(*)()>(base + 0x5b9860)(); // original vif1FLUSH
  fprintf(stderr, "Original VIF transfer: complete%d running%u cycle%llu\n",
          result, !!(v[0].VI[REG_VPU_STAT].UL & 0x100),
          static_cast<unsigned long long>(v[1].cycle));
  if (!result || (v[0].VI[REG_VPU_STAT].UL & 0x100)) return 5;
  fclose(captured);
  std::ofstream memory(std::string(out) + "/final-vumem.bin", std::ios::binary);
  memory.write(reinterpret_cast<char*>(v[1].Mem), 16384);
  VURegs portable = v[1];
  portable.Mem = nullptr;
  portable.Micro = nullptr;
  std::ofstream regs(std::string(out) + "/final-vuregs.bin", std::ios::binary);
  regs.write(reinterpret_cast<char*>(&portable), sizeof portable);
  return memory && regs ? 0 : 4;
}
extern "C" int __libc_start_main(int(*)(int, char**, char**), int argc,
    char** argv, void* init, void* fini, void* rtld, void* stack) {
  auto real = reinterpret_cast<int(*)(int(*)(int, char**, char**), int, char**,
      void*, void*, void*, void*)>(dlsym(RTLD_NEXT, "__libc_start_main"));
  return real(coupled_main, argc, argv, init, fini, rtld, stack);
}
