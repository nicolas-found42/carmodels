# Job B remedy — reverse-engineering methods survey (online)

**Problem (Job B).** The per-screen car highlight/selector value sits behind a dynamic
pointer chain (`outer+4 → +0x14c → +0x174 = entity`, store at `entity+0x64`). A **paused
savestate** does not carry those live pointers, so the three EE images expose no address to
read. The livery store itself is named but non-distinguishing at DEFAULT livery.

**Verdict from the survey.** The blocker is a *paused-dump limitation*, not a dead end. The
literature and tooling agree: read the value **live**, catch the instruction that touches it,
and follow the pointer from the registers/memory at the pause.

Sources: GitHub (gh-grep), arXiv, context-awesome, Firecrawl. Collected 2026-10-05.

---

## 1. In-emulator read/write breakpoints (primary remedy)

PCSX2 has real memory watchpoints (`CBreakPoints`); a read/write breakpoint pauses the EE/IOP
on an access and shows the code responsible.

- `pcsx2/DebugTools/Breakpoints.{h,cpp}` — `CBreakPoints`, `memChecks_`, `SetBreakpoint`,
  `BREAKPOINT_EE` / `BREAKPOINT_IOP` (github.com/PCSX2/pcsx2).
- Trigger sites: `pcsx2/x86/ix86-32/iR5900.cpp:1553` (`dynarecMemcheck`, EE),
  `pcsx2/R3000AInterpreter.cpp:130` (`psxMemcheck`, IOP) — "Hit store/load breakpoint".
- Method write-up (PS2/PCSX2 section): **suxin.space/notes/tracking-down-playstation-pointers-using-debuggers-ghidra/**
  - Find the address whose value changes; set a **Write breakpoint, width 4**; change the value
    in-game; the emulator pauses and shows the writing code.
  - Use **break-on-read** when the value is only *displayed* — our case: the highlight is drawn,
    so a read breakpoint catches the draw path.
  - "Combine debugger efforts with constant search of found pointers" — then walk the pointer
    from the code back through memory to the stable base.

**Why it cures Job B:** a live emulator with a memcheck exposes the register/pointer holding the
entity base — exactly what the paused savestate hides.

## 2. PINE — live guest-memory read/write over IPC

PCSX2's IPC protocol lets external tools read/write guest memory while the game runs.

- `pcsx2/PINE.cpp` — opcodes `MsgRead8/16/32/64`, `MsgWrite8/…`; `pcsx2/PINE.h`.
- Docs: **wiki.pcsx2.net/PCSX2_Documentation/IPC_Protocol** (client: projects.govanify.com/govanify/pine).
- Clients: **github.com/dmang-dev/mcp-pine** (`pine_read32`, `pine_read_range`, save/load state;
  PINE_TARGET/TARGET/SLOT), `pcsx2-interface` (PyPI).
- Caveats (from mcp-pine README): **PINE exposes no controller input, screenshot, or frame
  stepping** — so key delivery stays with our hidden-browser path. It can **wedge** if a client
  pipelines more than ~6 in-flight requests; restart the emulator to recover.

**Why it cures Job B:** sample `entity+0x64` and the pointer chain **live** across car selections,
instead of mining frozen dumps.

## 3. Pointer-scan tools — read the caveats first

- `github.com/korcankaraokcu/PINCE` (uses libmemscan; "Add last offset option to pointer scanner"),
  `libptrscan` (NixOS/nixpkgs `pince`), `github.com/scanmem/scanmem`, Cheat Engine
  (`PointerscanWorker/Controller`), DuckStation built-in scanner, PPSSPP cheat-search request.
- **Caveat, repeated across communities:** pointer scan **fails or is unreliable on emulators**,
  because the tool attaches to the *emulator host process*, not the guest
  (Cheat Engine forum "Pointer Scan does not find addresses on snes9x emulator"; r/cheatengine
  "Finding pointers on emulators?"; FearLess Cheat Engine "Finding pointers in emulators").

**Implication for Job B:** do not lead with CE/PINCE pointer scan; use it only on **guest** memory
via PINE or a DuckStation-style scanner, or not at all.

## 4. Structure dissection / live struct viewers

- ReClass / CE "string pointer scan" ("dissect structures" — `frmStringPointerScanUnit.pas`),
  shown in "How to Hack a 20 Year Old Game" (PINCE + ReClass workflow).
- Use after the breakpoint: define the entity struct from the live pointer and confirm `+0x64`.

## 5. arXiv — adjacent, and it names our exact problem

- **2503.15065** *A Comprehensive Quantification of Inconsistencies in Memory Dumps* — live/paused
  dumps are inconsistent (page smearing). **This is the academic statement of our blocker.**
- **2307.12060** *As if Time Had Stopped — Checking Memory Dumps for Quasi-Instantaneous
  Consistency* — same point: a paused snapshot is not a faithful live state.
- **1201.1327** *Abstracting Runtime Heaps for Program Understanding* — recovering heap-structure
  shape at runtime (reading our heap `entity`).
- **2405.00298** *The Reversing Machine: Reconstructing Memory Assumptions* — runtime memory
  reconstruction.
- **1912.00317** *An Observational Investigation of Reverse Engineers' Processes* — process study.
- Note: arXiv keyword search returned some off-topic (quantum) hits and hit 429/timeouts early;
  the on-topic set is the memory-dump/forensics group above.

## 6. context-awesome

- Cheat Engine, scanmem/GameConqueror, PINCE, `alphaseclab/awesome-reverse-engineering`,
  `onethawt/reverseengineering-reading-list`, awesome-hacking RE sections, *Reverse Engineering
  for Beginners*. Useful as a tool index; the pointer-scan-specific query returned noise
  (matched "Pointer"/"Libgen scan"), so it contributed little to the exact need.

---

## Recommended remedy (ordered)

1. **Arm a live breakpoint, not another dump.** PCSX2 memcheck: break-on-**read** on the highlight
   draw path (or break-on-write on `entity+0x64`), change the highlight with our existing key
   delivery, read the entity pointer from the registers at the pause → the chain root.
2. **Confirm live with PINE.** Poll `entity+0x64` and the cursor table over PINE while selecting
   cars; reconstruct the pointer chain from live memory (mind the ~6-request pipelining limit).
3. **Then a bounded pointer search** only on guest memory, if the breakpoint does not name the root.

## Policy question this raises

The handoff constraint is "ordinary controller input + read-only/capture APIs only (no
guest-memory writes, cheats, patches)". A **read/write breakpoint** modifies no guest memory and is
not a cheat or patch, but it is a **debugger feature** — a new class of tool for this project.
That is the one decision to confirm before using method 1.
