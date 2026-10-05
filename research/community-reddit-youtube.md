# Community research: PS2 model and texture recovery

Research snapshot: 2026-10-04. Scope: Reddit discussions and YouTube transcripts for practical PlayStation 2 asset capture, model cleanup, and texture recovery, with emphasis on methods that could help recover the original Ford Racing 2 cars. Community sources are leads and workflow reports; the claims below are limited to what their authors document. Search receipts, Jev records, and available transcripts are retained in [the evidence folder](evidence/community-reddit-youtube/README.md).

## Finding for carmodels

The strongest applicable community lead is Scurest's unofficial [PCSX2 3D Screenshot build](https://github.com/scurest/pcsx2/releases/tag/latest-3d-screenshot), linked from a 2025 Reddit tutorial post. It exports a model and textures from the current game scene. Scurest's own [technical notes](https://github.com/scurest/pcsx2/wiki/Notes-for-3D-screenshots) make its limits unusually clear: prototype quality, Software renderer only, incomplete scene coverage, no view of the PS2 VU vertex-shading stage, camera-depth squish that must be scaled by eye, no exported normals, and often incorrect triangle-strip winding. A “Culled” vertex group combines wanted offscreen/backface polygons with unwanted garbage. These shortcomings overlap the carmodels' scale/topology recovery needs, so the export is best treated as an in-game diagnostic reference for appearance, visible material assignment, or candidate-object discovery. The sources do not demonstrate it recovering the original Ford Racing 2 disk mesh.

The Scurest route is reproducible enough to inform an optional visual comparison: use its documented Software renderer, capture a stable game view with Shift+F8, import the OBJ with Vertex Groups enabled, then use material selection and inspect the “Normal” and “Culled” groups. Keep exported coordinates and topology explicitly provisional. Scurest notes that the OBJ positions are approximated from data visible at the GS and that the author cannot recover VU-side vertex processing, depth scale, normals, or reliable winding. [Instructions and limitations](https://github.com/scurest/pcsx2/wiki/Notes-for-3D-screenshots)

A much older path appears in RD Games & Tech's [part 2 tutorial transcript](https://www.youtube.com/watch?v=iHlJ3qO4lys): PCSX2 0.9.8 Software rendering, Shift+F8 scene dump, then screenshot-dimension correction with “PCSX2 Model Converter,” Repair Mesh, cleanup and correction in 3ds Max, followed by manual face-orientation, smoothing, and skew fixes. The transcript's converter download is a MediaFire binary and its workflow depends on 3ds Max; a 2024 PCSX2 forum user following the tutorial reported Repair Mesh did not create the expected `_meshFixed.obj`, and the output did not open in Blender. [Forum report](https://forums.pcsx2.net/Thread-Pls-help-me-with-PCSX2-Model-Converter?pid=640070). This is useful as a record of failure modes and historical attempts, not a reliable route to the original car assets.

Jev decision results agree with that distinction. With the user's stated priority of original topology and defensible scale, Jev selected using the Scurest output only as a diagnostic in the first bounded choice (confidence 1.00; primary recovery was contradicted by the requirements). In a second choice including the older converter and static recovery, it favored continuing static recovery (0.83 probability; 0.79 confidence). This is advisory, not proof; the evidence and complete outputs are saved in the receipts.

## What the Reddit and YouTube sources add

The [r/romhacking post](https://www.reddit.com/r/romhacking/comments/1nqq1yw/how-to-rip-3d-models-with-materials-and-textures-from-playstation-2-game-using-pcsx2/) from 2025 links the afkarxyz video [“How to Rip 3D Models with Materials and Textures from PlayStation 2 Games Using PCSX2”](https://www.youtube.com/watch?v=Yf-TyDEa5DE) and Scurest's fork. Its author says the build emits OBJ/MTL and textures; a commenter describes separating imported geometry by material in Blender, while another says the result is not very useful without a projection matrix. The same post was cross-posted to [r/ps2](https://www.reddit.com/r/ps2/comments/1nu0466/how_to_rip_3d_models_with_materials_and_textures/). Those are user reports; the Scurest notes are the stronger technical source.

A separate [Shytle tutorial transcript](https://www.youtube.com/watch?v=6_dfdMszGZw) shows the PCSX2 screenshot workflow in Blender on Armored Core: set Software rendering, capture a scene, import the OBJ with vertex groups, separate by material, and inspect/remove “Culled” content. The presenter manually adjusts game-specific scale and describes visible-scene limits and artifacts. Its specific scale values are for that game and must not be transferred to Ford Racing 2. The cleaned caption transcript is retained as [6_dfdMszGZw.en.vtt](evidence/community-reddit-youtube/6_dfdMszGZw.en.vtt).

RD Games & Tech's [part 1 texture tutorial](https://www.youtube.com/watch?v=oYuHGlm0xKs) describes TexMod interception of a PCSX2 scene to browse and dump textures, using Resident Evil 4 as its example. The presenter reports channel reversal in that capture and manually swaps red/blue channels. This is a game/tool-specific warning, not a Ford Racing 2 decoding rule. The related model tutorial's workflow and subsequent forum failure are described above. The cleaned transcript is [oYuHGlm0xKs.en.vtt](evidence/community-reddit-youtube/oYuHGlm0xKs.en.vtt).

The [r/AskReverseEngineering UV discussion](https://www.reddit.com/r/AskReverseEngineering/comments/1jip49w/reverse_engineering_game_model_format/) is about a different custom game format. The poster separates mesh/model/render metadata from VB/IB files, suspects vertex and UV data share a vertex buffer, and cannot identify UVs. It is a useful reminder to trace material and buffer ownership separately, but its layout cannot be applied to Ford Racing 2.

Other posts reinforce that PS2 game formats are game-specific. For example, [a r/PCSX2 thread](https://www.reddit.com/r/PCSX2/comments/1ry6pbl/how_do_i_rip_models/) advises reversing the particular game and converting its container when scene capture is inadequate; [a r/ps2 thread](https://www.reddit.com/r/ps2/comments/1kj4uy8/help_with-extracting-some-game-files/) distinguishes title-specific extractors and GS texture dumps. These are broad community suggestions, not evidence about Ford Racing 2's binary layout.

## Original technical references behind the leads

Scurest's [release page](https://github.com/scurest/pcsx2/releases/tag/latest-3d-screenshot) calls the build a rough draft and an unofficial feature branch. The author's [notes](https://github.com/scurest/pcsx2/wiki/Notes-for-3D-screenshots) explain that the exporter observes data at the GS, after game code has performed vertex shading on the vector units (or CPU). It reconstructs positions from screen X/Y and Q; it cannot undo camera-space squishing, ignores GS depth Z, and loses scale near the origin. It exports RGB vertex color but not alpha or normals. The author also warns that culled polygons can be offscreen geometry, backfaces, or garbage, and that triangle-strip winding is often wrong. The notes name better position recovery, garbage classification, face orientation, and more shading export as open problems.

For a separate downstream diagnostic, [libgpu2](https://github.com/aap/libgpu2) documents replaying PCSX2 GS dumps containing a VRAM seed, register state, and GIF frames. It can render frames and log or step through GS register writes and primitive transfers. That is a way to investigate final GS/VRAM behavior, not a substitute for identifying the VU-side mesh inputs or original asset records.

Scurest's [DuckStation 3D Screenshot documentation](https://github.com/scurest/duckstation-3D-Screenshot/wiki/How-it-works) gives a useful analogy for why scene rippers pair transformed positions with later polygon/texture state, but it describes the PS1 GTE/GPU path, not PS2 VIF/VU behavior. It should not be used to infer the Ford Racing 2 format.

## Search coverage and negative results

Searches covered Reddit discussions for PS2 model ripping, game-format reverse engineering, UV recovery, emulator screenshot extraction, and Ford Racing 2-specific extraction. Searches also covered YouTube tutorial titles and the RD Games & Tech part-2 follow-up. The targeted queries did not surface a Ford Racing 2-specific mesh/texture extraction thread or tutorial. The broader PS2 leads found here are generic and provide no carmodel-specific parser, coordinate scale, topology mapping, UV mapping, or PTG decoder.

YouTube transcript availability was mixed. Captions were successfully retrieved and screened for the RD Games & Tech model tutorial (`iHlJ3qO4lys.en.vtt`), its texture tutorial (`oYuHGlm0xKs.en.vtt`), and Shytle's PCSX2/Blender tutorial (`6_dfdMszGZw.en.vtt`). No English captions were returned for afkarxyz's video (`Yf-TyDEa5DE`) or the official Ninja Ripper PS2 tutorial (`bEHCcnaNd6Y`); direct page retrieval for the linked w.lf404 tutorial (`yID4n1y6EMk`) was throttled and yt-dlp reported no captions in the requested languages. A Portuguese sibling of the RD Games & Tech part-2 video was found, but subtitle retrieval hit HTTP 429, so it was not used.

## Sources

- [Scurest PCSX2 3D Screenshot release](https://github.com/scurest/pcsx2/releases/tag/latest-3d-screenshot)
- [Scurest PCSX2 technical notes](https://github.com/scurest/pcsx2/wiki/Notes-for-3D-screenshots)
- [Reddit r/romhacking PCSX2 3D-rip post](https://www.reddit.com/r/romhacking/comments/1nqq1yw/how-to-rip-3d-models-with-materials-and-textures-from-playstation-2-game-using-pcsx2/)
- [Reddit r/ps2 cross-post](https://www.reddit.com/r/ps2/comments/1nu0466/how-to-rip-3d-models-with-materials-and-textures/)
- [afkarxyz tutorial](https://www.youtube.com/watch?v=Yf-TyDEa5DE)
- [Shytle tutorial](https://www.youtube.com/watch?v=6_dfdMszGZw)
- [RD Games & Tech, part 1](https://www.youtube.com/watch?v=oYuHGlm0xKs)
- [RD Games & Tech, part 2](https://www.youtube.com/watch?v=iHlJ3qO4lys)
- [PCSX2 forum report on converter failure](https://forums.pcsx2.net/Thread-Pls-help-me-with-PCSX2-Model-Converter?pid=640070)
- [Reddit custom model/UV format discussion](https://www.reddit.com/r/AskReverseEngineering/comments/1jip49w/reverse_engineering_game_model_format/)
- [aap/libgpu2 GS reference implementation](https://github.com/aap/libgpu2)
- [Scurest DuckStation 3D Screenshot explanation](https://github.com/scurest/duckstation-3D-Screenshot/wiki/How-it-works)
