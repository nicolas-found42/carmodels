# Evidence receipts: GitHub and Stack Overflow pass

Research report: [`research/community-github-stackoverflow.md`](../../community-github-stackoverflow.md)

## Screened source set

Jev `jev_screen` was used on external search-result excerpts and relevant source excerpts before substantive use. Each of these had a `pass` disposition:

| Source/material | Screen probabilities (injection / substance / relevance) | Disposition |
|---|---:|---|
| ChoroQ extractor README excerpt | 0.03 / 0.88 / 0.89 | Pass |
| ChoroQ `car.py` source excerpt | 0.03 / 0.93 / 0.78 | Pass |
| ChoroQ `ps2_utils.py` / UNPACK excerpt | 0.12 / 0.96 / 0.90 | Pass |
| ChoroQ mesh decoder excerpt with VIF and GIF parsing | 0.04 / 0.96 / 0.93 | Pass |
| ChoroQ `texture.py` source and CLUT excerpt | 0.03 / 0.47 / 0.91 | Pass |
| Rumble Racing README excerpt | 0.03 / 0.95 / 0.93 | Pass |
| PS2SDK VIF API excerpt | 0.08 / 0.95 / 0.90 | Pass |
| Stack Overflow UV seam summary | 0.09 / 0.94 / 0.78 | Pass |
| Stack Overflow OBJ attributes summary | 0.23 / 0.94 / 0.79 | Pass |
| Search coverage/no direct FR2 hit summary | 0.06 / 0.94 / 0.70 | Pass |

Two generic results received `review` during first screening: a MaxScript mesh-export question (injection 0.28, relevance 0.05) and a PCSX2 Ford Racing 2 shadow-rendering release-note excerpt (injection 0.29, relevance 0.10). Inspection showed ordinary question/release-note material without an instruction directed at an agent. Both were omitted from format conclusions; the first was excluded, and the PCSX2 note is identified in the report as unrelated to asset extraction. A Speedrun.com result was `skip` (relevance 0.23), so none of its content was used.

## Primary evidence URLs and excerpts

- ChoroQ source README: <https://github.com/mholeys/roadtrip-choroq-tools>
- ChoroQ car parser: <https://github.com/mholeys/roadtrip-choroq-tools/blob/master/choroq/egame/car.py>
  - Parser documentation says the file contains offsets, DMA tags, VIF tags, GIF tags and vertex data.
  - Code collects VIF-expanded bytes, recognizes a GIF register sequence, extracts position/normal/color/UV values, and calls a synthesized face-list routine.
- ChoroQ face-list implementation: <https://github.com/mholeys/roadtrip-choroq-tools/blob/master/choroq/egame/amesh.py>
  - Source comments credit a Xentax forum post; the routine forms triangles from sequential indices with alternating winding.
- ChoroQ VIF helper: <https://github.com/mholeys/roadtrip-choroq-tools/blob/master/choroq/ps2_utils.py>
  - Its own `UNPACK` decoder reports compact V2-16, V3-16, V4-16 and other formats as unimplemented.
- ChoroQ texture helper: <https://github.com/mholeys/roadtrip-choroq-tools/blob/master/choroq/egame/texture.py>
  - Reads texture data under DMA/GIF/GS state and contains a title-specific unswizzle path.
- ChoroQ extractor: <https://github.com/mholeys/roadtrip-choroq-tools/blob/master/car_extractor.py>
  - Associates a parsed texture with CLUT data, unswizzles the palette, and writes mesh and material outputs.
- Rumble Racing PS2 source: <https://github.com/mattbruv/rumble-racing-re>
  - README describes original disc assets exported to PNG textures and glTF models for Blender.
- Climax toolkit VIF example: <https://github.com/BlackLineInteractive/Climax_Game_Engine_Toolkit/blob/master/docs/formats/SH_FORMAT.md>
- PS2SDK VIF API: <https://ps2dev.github.io/ps2sdk/group__packet2__vif.html>
- Stack Overflow UV seam discussion: <https://stackoverflow.com/questions/13327379/how-to-export-per-vertex-uv-coordinates-in-blender-export-script>
- Stack Overflow OBJ importer data requirements: <https://stackoverflow.com/questions/28260272/trouble-loading-simple-mesh-into-opengl>
- Stack Overflow Blender tangent access: <https://stackoverflow.com/questions/36214962/how-to-export-tangent-data-of-a-3d-model-from-blender>
- Old Xentax lead named by the ChoroQ source: <https://forum.xentax.com/viewtopic.php?t=17567>
- Archived Zenhax lead named by the ChoroQ source: <https://web.archive.org/web/20220309142950/https://zenhax.com/viewtopic.php?t=7405>

## Jev decision and claim checks

- Semantic source ranking (`jev_rerank`) ranked `mholeys car.py` at 0.90, `ps2_utils.py` at 0.83, `texture.py` at 0.78, PS2Docs texture notes at 0.61, and PS2SDK VIF docs at 0.55. Rumble Racing ranked at 0.31 because it is a useful export pipeline example, not an FR2 format match. Generic Stack Overflow results ranked below 0.20.
- Bounded research-priority decision (`jev_decide`) selected `vif_gif` with probability 0.98. Its requirement checks said the path is testable with current FR2 files and can avoid importing ChoroQ-specific assumptions.
- Claim verification (`jev_verify`) checked eight claims against the excerpts listed above: seven verified, zero contradicted, one unsupported, zero requiring human review. The unsupported claim was deliberately worded as “FR2 is guaranteed to share the ChoroQ file layout”; the evidence does not establish that.
- A later focused verification of report-level wording returned six verified claims, one unsupported claim, and three `review` actions. The unsupported item was the deliberately false proposition that the report claims FR2 and ChoroQ are identical; the report explicitly says the opposite. Two compound claims received a `review` action because confidence was below the automatic threshold: that an alternating-winding synthetic face list is a triangle-strip interpretation, and that the Stack Overflow answer supports per-corner UV seam preservation. Direct inspection of the cited source supports the report's qualified language: the ChoroQ face list uses sequential sliding indices with alternating winding (the report calls this “consistent with” a strip); the Stack Overflow answer says one geometric vertex can have different UVs and suggests duplicating vertices in flattened output. The final report keeps both points narrow and labels them as transferable hints.

All ratings are judgment signals. They do not establish truth beyond the cited repository/code text.
