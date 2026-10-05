# Job B — gap solutions for the mark number (web + Jev research)

For each gap that blocked the mark number: the gap, the researched solution, and Jev's read.

## G1 — the mark is not stored in any savestate
- **Evidence:** exhaustive scan of every savestate member (EE, IOP, VU, hw regs, PAD, scratchpad, SPU2, GS, PCSX2 CPU structures), every width → 0 hits for the highlight tuple; 0 per-entity flag.
- **Jev:** "the mark is computed, not stored, so a saved state can never reveal it" = **0.91 likely**.
- **Solution:** read it **live** — either a debugger breakpoint on the code that touches it, or a live value scan.

## G2 — PINE cannot unpause; the container boots paused
- **Evidence:** PINE opcodes are read/write 8-64, save/load, version/title/id/status. **No pause/resume.** (glama.ai/mcp-pine: "PINE has no pause/resume opcode".)
- **Solution:** send the emulator's **ESC/Space** key to the container's own display. Two headless ways: the **existing hidden Playwright→noVNC browser** (already proven to deliver keys), or **xdotool on :99**. Neither touches host focus.

## G3 — no X tools in the container
- **Evidence:** container has none of xdotool/xte/wmctrl/xwininfo.
- **Solution:** `apt install xdotool` (standard Xvfb+xdotool Docker pattern) — **or** reuse the existing noVNC key path, which needs **no image change**.

## G4 — PCSX2's debugger has no headless/remote API
- **Evidence:** breakpoints live in the GUI (`CBreakPoints`, `DebugTools/Breakpoints.cpp`); no GDB stub (only a forum request).
- **Solutions found:**
  - **hkmodd/PCSX2-MCP** — a ~1-file GPL **DebugServer** patch giving a TCP debug API (breakpoints/watchpoints, registers, memory diff). Prebuilt release is **WINDOWS-ONLY** (`pcsx2-qt.exe`/MSVC); on Linux it needs a **full PCSX2 source build**. Jev: "runs as-is on Linux" = **contradicted 0.98**.
  - **xdotool + the built-in debugger** on :99 (small).
  - **Live value scan** (scanmem/PINCE/libmemscan) against the process — Jev rates it **0.94 likely** the mark is reachable this way, and "a breakpoint is required" = **0.11 unlikely**.

## Jev's recommendation
`jev_decide` leaned **live value scan (pince_scan 0.46)** over xdotool-debugger (0.29) and the heavy DebugServer build (0); `jev_find` ranked the source-build path highest but Jev rated it *unavailable* on Linux. Combined with "computed not stored" (0.91) and "scan can find it" (0.94), the recommendation is:

> **A headless, read-only live value scan**, using only tools already present: the **noVNC key path** to unpause/move the highlight, and **PINE reads** to snapshot + diff the heap region — **no image change, no breakpoint, no host focus.**

Concretely: unpause via noVNC (Space), snapshot the EE heap region over PINE, move the highlight (J/L) via noVNC, snapshot again, diff, narrow over a few moves. The word that changes in step with the highlight — and is decompilation-reachable (menu struct / DAT table) — is the mark.

## What still needs the user
- The **live run** itself (unpause + move the highlight). It is ordinary input + read-only PINE reads, headless — but it is a fresh live experiment, so it wants a go-ahead.
- Only if the scan is inconclusive: an **image change** (xdotool) or the heavy **DebugServer source build**.
