// Research adapter for the SHA-pinned official PCSX2 v2.8.2 Linux binary.
// Register layouts below follow PCSX2 VU.h/R5900.h (GPL-3.0+), tag v2.8.2.
// SPDX-FileCopyrightText: 2002-2026 PCSX2 Dev Team (register declarations)
// SPDX-License-Identifier: GPL-3.0+
// Original opcode, pipeline, branch and arithmetic functions remain in the
// binary.
#include <cstddef>
#include <cstdint>
using u8 = uint8_t;
using s8 = int8_t;
using u16 = uint16_t;
using s16 = int16_t;
using u32 = uint32_t;
using s32 = int32_t;
using u64 = uint64_t;
using s64 = int64_t;
using u128 = __uint128_t;
using s128 = __int128_t;
using uint = unsigned;
enum VURegFlags {
  REG_STATUS_FLAG = 16,
  REG_MAC_FLAG = 17,
  REG_CLIP_FLAG = 18,
  REG_ACC_FLAG = 19, // dummy flag that indicates that VFACC is written/read
                     // (nothing to do with VI[19])
  REG_R = 20,
  REG_I = 21,
  REG_Q = 22,
  REG_P = 23, // only exists in micromode
  REG_VF0_FLAG =
      24, // dummy flag that indicates VF0 is read (nothing to do with VI[24])
  REG_TPC = 26,
  REG_CMSAR0 = 27,
  REG_FBRST = 28,
  REG_VPU_STAT = 29,
  REG_CMSAR1 = 31
};

// interpreter hacks, WIP
// #define INT_VUSTALLHACK //some games work without those, big speedup
// #define INT_VUDOUBLEHACK

enum VUStatus {
  VU_Ready = 0,
  VU_Run = 1,
  VU_Stop = 2,
};

union VECTOR {
  struct {
    float x, y, z, w;
  } f;
  struct {
    u32 x, y, z, w;
  } i;

  float F[4];

  u128 UQ;
  s128 SQ;
  u64 UD[2]; // 128 bits
  s64 SD[2];
  u32 UL[4];
  s32 SL[4];
  u16 US[8];
  s16 SS[8];
  u8 UC[16];
  s8 SC[16];
};

struct REG_VI {
  union {
    float F;
    s32 SL;
    u32 UL;
    s16 SS[2];
    u16 US[2];
    s8 SC[4];
    u8 UC[4];
  };
  u32 padding[3]; // needs padding to make them 128bit; VU0 maps VU1's VI regs
                  // as 128bits to addr 0x4xx0 in VU0 mem, with only lower 16
                  // bits valid, and the upper 112bits are hardwired to 0
                  // (cottonvibes)
};

// #define VUFLAG_BREAKONMFLAG		0x00000001
#define VUFLAG_MFLAGSET 0x00000002
#define VUFLAG_INTCINTERRUPT 0x00000004
struct fdivPipe {
  int enable;
  REG_VI reg;
  u64 sCycle;
  u32 Cycle;
  u32 statusflag;
};

struct efuPipe {
  int enable;
  REG_VI reg;
  u64 sCycle;
  u32 Cycle;
};

struct fmacPipe {
  u32 regupper;
  u32 reglower;
  int flagreg;
  u32 xyzwupper;
  u32 xyzwlower;
  u64 sCycle;
  u32 Cycle;
  u32 macflag;
  u32 statusflag;
  u32 clipflag;
};

struct ialuPipe {
  int reg;
  u64 sCycle;
  u32 Cycle;
};

struct alignas(16) VURegs {
  VECTOR VF[32]; // VF and VI need to be first in this struct for proper mapping
  REG_VI VI[32]; // needs to be 128bit x 32 (cottonvibes)

  VECTOR ACC;
  REG_VI q;
  REG_VI p;

  uint idx; // VU index (0 or 1)

  // flags/cycle are needed by VIF dma code, so they have to be here (for now)
  // We may replace these by accessors in the future, if merited.
  u64 cycle;
  u32 flags;

  // Current opcode being interpreted or recompiled (this var is used by Interps
  // but not microVU.  Would like to have it local to their respective
  // classes... someday)
  u32 code;
  u32 start_pc;

  // branch/branchpc are used by interpreter only, but making them local to the
  // interpreter classes requires considerable code refactoring.  Maybe later.
  // >_<
  u32 branch;
  u32 branchpc;
  u32 delaybranchpc;
  bool takedelaybranch;
  u32 ebit;
  u32 pending_q;
  u32 pending_p;

  alignas(16) u32 micro_macflags[4];
  alignas(16) u32 micro_clipflags[4];
  alignas(16) u32 micro_statusflags[4];
  // MAC/Status flags -- these are used by interpreters but are kind of hacky
  // and shouldn't be relied on for any useful/valid info.  Would like to move
  // them out of this struct eventually.
  u32 macflag;
  u32 statusflag;
  u32 clipflag;

  s64 nextBlockCycles;

  u8 *Mem;
  u8 *Micro;

  u32 xgkickaddr;
  u32 xgkickdiff;
  u32 xgkicksizeremaining;
  u64 xgkicklastcycle;
  u32 xgkickcyclecount;
  u32 xgkickenable;
  u32 xgkickendpacket;

  u8 VIBackupCycles;
  u32 VIOldValue;
  u32 VIRegNumber;

  fmacPipe fmac[4];
  u32 fmacreadpos;
  u32 fmacwritepos;
  u32 fmaccount;
  fdivPipe fdiv;
  efuPipe efu;
  ialuPipe ialu[4];
  u32 ialureadpos;
  u32 ialuwritepos;
  u32 ialucount;

  VURegs() {
    Mem = NULL;
    Micro = NULL;
  }

  bool IsVU1() const;
  bool IsVU0() const;
};

#ifdef MC3_REFERENCE_EE

union GPR_reg { // Declare union type GPR register
  u128 UQ;
  s128 SQ;
  u64 UD[2]; // 128 bits
  s64 SD[2];
  u32 UL[4];
  s32 SL[4];
  u16 US[8];
  s16 SS[8];
  u8 UC[16];
  s8 SC[16];
};

union GPRregs {
  struct {
    GPR_reg r0, at, v0, v1, a0, a1, a2, a3, t0, t1, t2, t3, t4, t5, t6, t7, s0,
        s1, s2, s3, s4, s5, s6, s7, t8, t9, k0, k1, gp, sp, s8, ra;
  } n;
  GPR_reg r[32];
};

union PERFregs {
  struct {
    union {
      struct {
        u32 pad0 : 1;   // LSB should always be zero (or undefined)
        u32 EXL0 : 1;   // enable PCR0 during Level 1 exception handling
        u32 K0 : 1;     // enable PCR0 during Kernel Mode execution
        u32 S0 : 1;     // enable PCR0 during Supervisor mode execution
        u32 U0 : 1;     // enable PCR0 during User-mode execution
        u32 Event0 : 5; // PCR0 event counter (all values except 1 ignored at
                        // this time)

        u32 pad1 : 1; // more zero/undefined padding [bit 10]

        u32 EXL1 : 1;   // enable PCR1 during Level 1 exception handling
        u32 K1 : 1;     // enable PCR1 during Kernel Mode execution
        u32 S1 : 1;     // enable PCR1 during Supervisor mode execution
        u32 U1 : 1;     // enable PCR1 during User-mode execution
        u32 Event1 : 5; // PCR1 event counter (all values except 1 ignored at
                        // this time)

        u32 Reserved : 11;
        u32 CTE : 1; // Counter enable bit, no counting if set to zero.
      } b;

      u32 val;
    } pccr;

    u32 pcr0, pcr1, pad;
  } n;
  u32 r[4];
};

union CP0regs {
  struct {
    u32 Index, Random, EntryLo0, EntryLo1, Context, PageMask, Wired, Reserved0,
        BadVAddr, Count, EntryHi, Compare;
    union {
      struct {
        u32 IE : 1;  // Bit 0: Interrupt Enable flag.
        u32 EXL : 1; // Bit 1: Exception Level, set on any exception not covered
                     // by ERL.
        u32 ERL : 1; // Bit 2: Error level, set on Resetm NMI, perf/debug
                     // exceptions.
        u32 KSU : 2; // Bits 3-4: Kernel [clear] / Supervisor [set] mode
        u32 unused0 : 3;
        u32 IM : 8;  // Bits 10-15: Interrupt mask (bits 12,13,14 are unused)
        u32 EIE : 1; // Bit 16: IE bit enabler.  When cleared, ints are disabled
                     // regardless of IE status.
        u32 _EDI : 1; // Bit 17: Interrupt Enable (set enables ints in all
                      // modes, clear enables ints in kernel mode only)
        u32 CH : 1; // Bit 18: Status of most recent cache instruction (set for
                    // hit, clear for miss)
        u32 unused1 : 3;
        u32 BEV : 1; // Bit 22: if set, use bootstrap for TLB/general exceptions
        u32 DEV : 1; // Bit 23: if set, use bootstrap for perf/debug exceptions
        u32 unused2 : 2;
        u32 FR : 1; // (?)
        u32 unused3 : 1;
        u32 CU : 4; // Bits 28-31: Co-processor Usable flag
      } b;
      u32 val;
    } Status;
    u32 Cause, EPC, PRid, Config, LLAddr, WatchLO, WatchHI, XContext, Reserved1,
        Reserved2, Debug, DEPC, PerfCnt, ErrCtl, CacheErr, TagLo, TagHi,
        ErrorEPC, DESAVE;
  } n;
  u32 r[32];
};

struct cpuRegisters {
  GPRregs GPR; // GPR regs
  // NOTE: don't change order since recompiler uses it
  GPR_reg HI;
  GPR_reg LO;      // hi & log 128bit wide
  CP0regs CP0;     // is COP0 32bit?
  u32 sa;          // shift amount (32bit), needs to be 16 byte aligned
  u32 IsDelaySlot; // set true when the current instruction is a delay slot.
  u32 pc;   // Program counter, when changing offset in struct, check iR5900-X.S
            // to make sure offset is correct
  u32 code; // current instruction
  PERFregs PERF;
  u32 eCycle[32];
  u64 sCycle[32]; // for internal counters
  u64 cycle;      // calculate cpucycles..
  u32 interrupt;
  int branch;
  int opmode; // operating mode
  u32 tempcycles;
  u32 dmastall;
  u32 pcWriteback;

  // if cpuRegs.cycle is greater than this cycle, should check cpuEventTest for
  // updates
  u64 nextEventCycle;
  u64 lastEventCycle;
  u64 lastCOP0Cycle;
  u64 lastPERFCycle[2];
};

// used for optimization
union GPR_reg64 {
  u64 UD[1]; // 64 bits
  s64 SD[1];
  u32 UL[2];
  s32 SL[2];
  u16 US[4];
  s16 SS[4];
  u8 UC[8];
  s8 SC[8];
};

union FPRreg {
  float f;
  u32 UL;
  s32 SL; // signed 32bit used for sign extension in interpreters.
};

struct fpuRegisters {
  FPRreg fpr[32]; // 32bit floating point registers
  u32 fprc[32];   // 32bit floating point control registers
  FPRreg ACC;     // 32 bit accumulator
  u32 ACCflag;    // an internal accumulator overflow flag
};

struct alignas(16) cpuRegistersPack {
  alignas(16) cpuRegisters cpuRegs;
  alignas(16) fpuRegisters fpuRegs;
};

#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <elf.h>
#include <fstream>
#include <immintrin.h>
#include <link.h>
#include <string>
#include <sys/mman.h>
#include <ucontext.h>
#include <vector>
static uintptr_t base;
static std::vector<u8> ram(32 * 1024 * 1024), spr(16384);
static int find_base(dl_phdr_info *i, size_t, void *) {
  if (!i->dlpi_name || !i->dlpi_name[0]) {
    base = i->dlpi_addr;
    return 1;
  }
  return 0;
}
static void *address(u32 a, u32 n) {
  if (a >= 0x70000000 && a + n <= 0x70004000)
    return spr.data() + a - 0x70000000;
  a &= 0x1fffffff;
  if (a + n > ram.size()) {
    fprintf(stderr, "bad EE read/write%08x size%u\n", a, n);
    abort();
  }
  return ram.data() + a;
}
#define READ(N, T)                                                             \
  static T read##N(u32 a) {                                                    \
    T v;                                                                       \
    std::memcpy(&v, address(a, sizeof(v)), sizeof(v));                         \
    return v;                                                                  \
  }
#define WRITE(N, T)                                                            \
  static void write##N(u32 a, T v) {                                           \
    std::memcpy(address(a, sizeof(v)), &v, sizeof(v));                         \
  }
READ(8, u8)
READ(16, u16) READ(32, u32) READ(64, u64) READ(128, __m128i) WRITE(8, u8)
    WRITE(16, u16) WRITE(32, u32) WRITE(64, u64)
        WRITE(128, __m128i) static void no_events() {}
static int no_iop() { return 0; }
static uintptr_t fake_iop[16];
static void patch(u32 offset, void *callback) {
  auto *p = (u8 *)(base + offset);
  auto pg = (uintptr_t)p & ~uintptr_t(4095);
  mprotect((void *)pg, 4096, 7);
  p[0] = 0x48;
  p[1] = 0xb8;
  auto f = (uintptr_t)callback;
  memcpy(p + 2, &f, 8);
  p[10] = 0xff;
  p[11] = 0xe0;
  __builtin___clear_cache((char *)p, (char *)p + 12);
  mprotect((void *)pg, 4096, 5);
}
static u32 get32(std::ifstream &f) {
  u32 n;
  f.read((char *)&n, 4);
  if (!f)
    abort();
  return n;
}
static void get(std::ifstream &f, void *p, u32 n) {
  f.read((char *)p, n);
  if (!f)
    abort();
}
static void fault(int, siginfo_t *si, void *ctx) {
  auto *c = (ucontext_t *)ctx;
  fprintf(stderr, "EEFAULT RIPoffset%llx addr%p\n",
          (unsigned long long)c->uc_mcontext.gregs[REG_RIP] - base,
          si->si_addr);
  _Exit(99);
}
static int ee_main(int, char **, char **) {
  struct sigaction sa {};
  sa.sa_sigaction = fault;
  sa.sa_flags = SA_SIGINFO;
  sigaction(SIGSEGV, &sa, nullptr);
  dl_iterate_phdr(find_base, nullptr);
  static_assert(sizeof(cpuRegistersPack) == 1440, "EE ABI size");
  static_assert(offsetof(cpuRegisters, pc) == 680, "EE program counter ABI");
  static_assert(offsetof(cpuRegistersPack, fpuRegs) == 0x490, "FPR ABI offset");
  const char *elf = std::getenv("MC3_EE_ELF"), *job = std::getenv("MC3_EE_JOB"),
             *out = std::getenv("MC3_EE_OUT");
  if (!elf || !job || !out)
    return 2;
  std::ifstream game(elf, std::ios::binary);
  Elf32_Ehdr hdr;
  get(game, &hdr, sizeof(hdr));
  if (memcmp(hdr.e_ident, "\177ELF\1\1", 6))
    return 3;
  for (u32 i = 0; i < hdr.e_phnum; i++) {
    game.seekg(hdr.e_phoff + i * hdr.e_phentsize);
    Elf32_Phdr p;
    get(game, &p, sizeof(p));
    if (p.p_type == PT_LOAD) {
      game.seekg(p.p_offset);
      get(game, address(p.p_vaddr, p.p_filesz), p.p_filesz);
    }
  }
  patch(0x5f7800, (void *)read8);
  patch(0x5f79a0, (void *)read16);
  patch(0x5f7b40, (void *)read32);
  patch(0x5f7ce0, (void *)read64);
  patch(0x5f74b0, (void *)read128);
  patch(0x5f7e80, (void *)write8);
  patch(0x5f8030, (void *)write16);
  patch(0x5f81e0, (void *)write32);
  patch(0x5f8390, (void *)write64);
  patch(0x5f7650, (void *)write128);
  patch(0x49b6f0, (void *)no_events);
  *(int *)(base + 0x107cd18) = 0x7fffffff;
  *(int *)(base + 0x10792e8) = 0x7fffffff;
  for (auto &f : fake_iop)
    f = (uintptr_t)&no_iop;
  *(uintptr_t *)(base + 0x30a10f0) = (uintptr_t)fake_iop;
  *(uintptr_t *)(base + 0x351c518) = base + 0x10681a0;
  *(uintptr_t *)(base + 0x351c520) = base + 0x10681b0;
  auto *pack = (cpuRegistersPack *)(base + 0x30a1870);
  memset(pack, 0, sizeof(*pack));
  auto &cpu = pack->cpuRegs;
  auto &fpu = pack->fpuRegs;
  cpu.GPR.n.sp.UD[0] = 0x1ff0000;
  cpu.GPR.n.ra.UD[0] = 0x10000;
  cpu.nextEventCycle = 0x7fffffffffffffffULL;
  cpu.CP0.n.Status.val = 0x70400004;
  auto *v = (VURegs *)(base + 0x351c530);
  for (u32 i = 0; i < 2; i++) {
    memset(v + i, 0, sizeof(VURegs));
    v[i].idx = i;
    v[i].VF[0].f.w = 1.0f;
    v[i].Mem = (u8 *)calloc(1, 16384);
    v[i].Micro = (u8 *)calloc(1, 16384);
  }
  std::ifstream input(job, std::ios::binary);
  char magic[8];
  get(input, magic, 8);
  if (memcmp(magic, "MC3EE001", 8))
    return 4;
  cpu.pc = get32(input);
  u32 limit = get32(input), ngpr = get32(input), nfpr = get32(input),
      np = get32(input);
  for (u32 i = 0; i < ngpr; i++) {
    u32 n = get32(input);
    if (n == 0 || n >= 32)
      return 5;
    get(input, &cpu.GPR.r[n], 16);
  }
  for (u32 i = 0; i < nfpr; i++) {
    u32 n = get32(input);
    if (n >= 32)
      return 6;
    get(input, &fpu.fpr[n], 4);
  }
  for (u32 i = 0; i < np; i++) {
    u32 a = get32(input), n = get32(input);
    get(input, address(a, n), n);
  }
  auto step = (void (*)())(base + 0x52e230);
  u32 native_fpcr = *(u32 *)(base + 0x30a0674);
  fprintf(stderr, "EE defaultFPCR=%08x start%08x\n", native_fpcr, cpu.pc);
  _mm_setcsr(native_fpcr);
  u32 steps = 0;
  while (cpu.pc != 0x10000 && steps++ < limit) {
    if (std::getenv("MC3_EE_TRACE"))
      fprintf(stderr, "pc%08x code%08x\n", cpu.pc, read32(cpu.pc));
    step();
  }
  fprintf(stderr, "EE end%08x steps%u f0%08x f0float%.9g mxcsr%x\n", cpu.pc,
          steps, fpu.fpr[0].UL, fpu.fpr[0].f, _mm_getcsr());
  std::ofstream f(std::string(out) + "/ee-registers.bin", std::ios::binary);
  f.write((char *)pack, sizeof(*pack));
  std::ofstream m(std::string(out) + "/ee-ram.bin", std::ios::binary);
  m.write((char *)ram.data(), ram.size());
  return cpu.pc == 0x10000 ? 0 : 7;
}
extern "C" int __libc_start_main(int (*)(int, char **, char **), int argc,
                                 char **argv, void *init, void *fini,
                                 void *rtld, void *stack) {
  auto original =
      (int (*)(int (*)(int, char **, char **), int, char **, void *, void *,
               void *, void *))dlsym(RTLD_NEXT, "__libc_start_main");
  return original(ee_main, argc, argv, init, fini, rtld, stack);
}

#else
// Research-only adapter. All VU opcodes/pipelines execute in the pinned
// original binary.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <immintrin.h>
#include <link.h>
#include <string>
#include <sys/mman.h>
#include <unistd.h>
static uintptr_t base;
static FILE *captured;
static unsigned chunk_count;
static int find_base(dl_phdr_info *i, size_t, void *) {
  if (!i->dlpi_name || !i->dlpi_name[0]) {
    base = i->dlpi_addr;
    return 1;
  }
  return 0;
}
static u32 transport(void *, u32 type, u8 *data, u32 size, bool) {
  if (size) {
    std::fprintf(stderr, "capture mxcsr=%x size%u\n", _mm_getcsr(), size);
    std::fwrite(&size, 4, 1, captured);
    std::fwrite(data, 1, size, captured);
    chunk_count++;
  }
  return size;
}
static void patch_transport() {
  auto *p = (u8 *)(base + 0x3885f0);
  uintptr_t page = (uintptr_t)p & ~uintptr_t(4095);
  if (mprotect((void *)page, 4096, PROT_READ | PROT_WRITE | PROT_EXEC))
    std::abort();
  p[0] = 0x48;
  p[1] = 0xb8;
  uintptr_t fn = (uintptr_t)&transport;
  std::memcpy(p + 2, &fn, 8);
  p[10] = 0xff;
  p[11] = 0xe0;
  __builtin___clear_cache((char *)p, (char *)p + 12);
  if (mprotect((void *)page, 4096, PROT_READ | PROT_EXEC))
    std::abort();
}
static u32 read32(std::ifstream &f) {
  u32 v;
  f.read((char *)&v, 4);
  if (!f)
    std::abort();
  return v;
}
static void readbytes(std::ifstream &f, void *p, size_t n) {
  f.read((char *)p, n);
  if (!f)
    std::abort();
}
static int harness_main(int, char **, char **) {
  dl_iterate_phdr(find_base, nullptr);
  static_assert(sizeof(VURegs) == 1680, "layout");
  static_assert(offsetof(VURegs, Mem) == 1208, "VU data pointer ABI");
  static_assert(offsetof(VURegs, Micro) == 1216, "VU code pointer ABI");
  const char *job = std::getenv("MC3_VU_JOB");
  const char *out = std::getenv("MC3_VU_OUT");
  if (!job || !out) {
    fprintf(stderr, "Missing explicit job/output\n");
    return 2;
  }
  std::ifstream input(job, std::ios::binary);
  char magic[8];
  readbytes(input, magic, 8);
  if (std::memcmp(magic, "MC3VU001", 8))
    return 3;
  auto *v = (VURegs *)(base + 0x351c530);
  for (u32 i = 0; i < 2; i++) {
    std::memset(&v[i], 0, sizeof(VURegs));
    v[i].idx = i;
    v[i].Mem = (u8 *)std::aligned_alloc(16, 16384);
    v[i].Micro = (u8 *)std::aligned_alloc(16, 16384);
    std::memset(v[i].Mem, 0, 16384);
    std::memset(v[i].Micro, 0, 16384);
    v[i].VF[0].f.w = 1.0f;
  }
  readbytes(input, v[1].Micro, 16384);
  readbytes(input, v[1].Mem, 16384);
  // Source REC_VU1 is EmuConfig.Cpu.Recompiler.EnableVU1, bit3 in +8.
  // Disable it because this adapter explicitly chooses the official
  // interpreter.
  *(u32 *)(base + 0x30a0670) &= ~8u;
  captured = std::fopen((std::string(out) + "/gif-chunks.bin").c_str(), "wb");
  if (!captured)
    return 4;
  patch_transport();
  auto execute = (void (*)(void *, u32))(base + 0x603dc0);
  std::ofstream calls(std::string(out) + "/calls.json");
  calls << "[";
  u32 count = read32(input);
  for (u32 c = 0; c < count; c++) {
    u32 pc = read32(input), top = read32(input), itop = read32(input),
        cycles = read32(input), patches = read32(input),
        vfpatches = read32(input);
    for (u32 n = 0; n < patches; n++) {
      u32 offset = read32(input), size = read32(input);
      if (offset + size > 16384)
        return 5;
      readbytes(input, v[1].Mem + offset, size);
    }
    for (u32 n = 0; n < vfpatches; n++) {
      u32 reg = read32(input);
      if (reg == 0 || reg >= 32)
        return 6;
      readbytes(input, &v[1].VF[reg], 16);
    }
    *(u32 *)(base + 0x188e000 + 0x3ce0) = top;
    *(u32 *)(base + 0x188e000 + 0x3cd0) = itop;
    u32 first_chunk = chunk_count;
    u64 first_cycle = v[1].cycle;
    v[1].VI[REG_TPC].UL = pc;
    v[0].VI[REG_VPU_STAT].UL |= 0x100;
    execute((void *)(base + 0x10681b0), cycles);
    std::fprintf(stderr,
                 "call%u start%03x end%03x cycle%llu running%u chunks%u\n", c,
                 pc, v[1].VI[REG_TPC].UL, (unsigned long long)v[1].cycle,
                 !!(v[0].VI[REG_VPU_STAT].UL & 0x100), chunk_count);
    if (c) calls << ",";
    calls << "{\"index\":" << c << ",\"pc\":" << pc
          << ",\"top\":" << top << ",\"itop\":" << itop
          << ",\"start_chunk\":" << first_chunk << ",\"end_chunk\":" << chunk_count
          << ",\"start_cycle\":" << first_cycle << ",\"end_cycle\":" << v[1].cycle
          << ",\"fpcr\":" << *(u32 *)(base + 0x30a0680) << "}";
    if (v[0].VI[REG_VPU_STAT].UL & 0x100)
      return 7;
  }
  calls << "]\n";
  std::fclose(captured);
  std::ofstream mem(std::string(out) + "/final-vumem.bin", std::ios::binary);
  mem.write((char *)v[1].Mem, 16384);
  VURegs portable;
  std::memcpy(&portable, &v[1], sizeof(VURegs));
  portable.Mem = nullptr;
  portable.Micro = nullptr;
  std::ofstream regs(std::string(out) + "/final-vuregs.bin", std::ios::binary);
  regs.write((char *)&portable, sizeof(VURegs));
  return 0;
}
extern "C" int __libc_start_main(int (*)(int, char **, char **), int argc,
                                 char **argv, void *init, void *fini,
                                 void *rtld, void *stack) {
  auto original =
      (int (*)(int (*)(int, char **, char **), int, char **, void *, void *,
               void *, void *))dlsym(RTLD_NEXT, "__libc_start_main");
  return original(harness_main, argc, argv, init, fini, rtld, stack);
}

#endif
