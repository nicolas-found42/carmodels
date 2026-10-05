# Pass 4 and 5: decoded handlers and the captured packets

The static handler receipt is `evidence/vu-dispatch/handlers-pass4-pass5.json`. The separate capture comparison is `evidence/vu-dispatch/handler-dump-comparison.json`. Run `tools/verify_vu_pass_handlers.py` and `tools/verify_vu_handler_dump.py` to reproduce them and reject their corruption controls. `tools/check.sh` runs the static checks with configured inputs and the capture checks when the pinned runtime files are present.

The comparison uses the existing 37 pass-4 and 63 pass-5 retained/GSDump alignments. These are content matches between separate captures of the same scene. They establish the measured relationships below; they do not prove live dispatch or same-frame execution.

| Property | Pass 4 | Pass 5 |
| --- | --- | --- |
| Draws / vertices | 37 / 2,189 | 63 / 3,666 |
| XYZF including ADC equals preceding aligned output | 37/37 | 63/63 |
| STQ Q/w equals preceding aligned output | 37/37 | 63/63 |
| RGB equals retained colour × raw float alpha, truncated | 37/37 | Not this formula |
| RGBA equals decoded DM[5] clamp formula from retained matrix upload | Not this formula | 63/63 |
| T equals host binary32 `colour.w × Q` exactly | Not checked | 3,387/3,666 vertices; 54/63 draws |
| Remaining T error | Not checked | 279 vertices differ by one ULP; none exceeds one ULP |

Pass 4 writes its colour factor to the RGBA alpha lane as an unconverted float. Reading that raw word as a float gives a finite factor in [0,1] on all 2,189 vertices. Multiplying the retained RGB vector by that factor predicts the three stored integer lanes on every draw. This supports the decoded RGB/alpha relationship; it does not independently establish the view-vector/normal calculation of that factor. The names “reflection map” and “specular” remain readings of the arithmetic.

## Per-draw inputs

The retained DMA chain contains 205 fourteen-qword V4-32 uploads with command `0x6c0e800c`, starting at TOP offset 12. The decoded overlay-0 prologue (pairs 26–59) stores TOP[21] into DM[5], negates TOP[22].xyz into DM[6].xyz while preserving its w lane, and stores TOP[23] into DM[7]. TOP[12]–TOP[14] supply the pass-4 matrix. That mapping is now derived, word-bound to the pinned disassembly, and has a changed-store control.

Each comparison row records the nearest preceding matrix upload before the retained draw head, the pass-4 matrix source words, DM[6]/DM[7] source words and, for pass 5, DM[5] and predicted RGBA. All 63 pass-5 draws agree with `ftoi0(min(DM[5].xyz × colour.xyz,128))` and `ftoi0(min(DM[5].w,128))`. The paused race95 VU image's DM[5] predicts none of those draws. Its bytes are pinned and kept as a context-negative comparison; a paused working buffer cannot substitute for the per-draw packet.

The T comparison includes colour.w values near 1, 0.05 and 0.3. Omitting colour.w exceeds the one-ULP bound on 512 vertices. The 279 one-ULP differences against host multiplication remain visible. The current numeric executor is a host binary32 reconstruction; hardware rounding, flags, latency and bit-exact arithmetic are not established.

## ADC and limits

The decoded pass-4/5 handlers copy XYZF from the preceding output buffer. Every compared draw preserves those raw words, including ADC. Pass 4 follows an aligned pass-2 output; pass 5 follows pass 4 in 37 cases and pass 2 in 26. This identifies an inherited-output relationship, not the branch that first computes ADC.

All 100 compared descriptors have the epilogue's clip flag (0x100) clear. The flag-set clip stage and the static kick packet origins remain open. Full pass-4 UV, the independent reconstruction of its view/normal factor, and pass-5 S require the per-vertex working-plane state; recorded matrix inputs alone do not supply it. `render_fidelity_complete` remains false.

The capture comparison rejects eight deliberate changes for their intended reasons: a retained descriptor that differs from raw EE packet bytes, ADC, Q, pass-4 RGB, pass-4 alpha, pass-5 RGBA, T beyond tolerance, and retained DM[5]. Its test also rejects a missing matrix upload and non-finite input. These controls protect the measured subset; they do not turn it into a full renderer verifier.
