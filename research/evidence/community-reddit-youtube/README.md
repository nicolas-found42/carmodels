# Community Reddit/YouTube research receipts

Research date: 2026-10-04. This folder preserves raw captions retrieved from YouTube and documents the search/screening trail for the report at `research/community-reddit-youtube.md`.

## YouTube transcript receipts

| Video | Captions | Receipt | Notes |
|---|---|---|---|
| RD Games & Tech, PS2 model extraction, `iHlJ3qO4lys` | English VTT available | [iHlJ3qO4lys.en.vtt](iHlJ3qO4lys.en.vtt) | Video title/description and transcript screened with Jev; transcript describes PCSX2 0.9.8 + converter + 3ds Max workflow. |
| RD Games & Tech, PS2 textures, `oYuHGlm0xKs` | English VTT available | [oYuHGlm0xKs.en.vtt](oYuHGlm0xKs.en.vtt) | Transcript screened with Jev; TexMod/PCSX2 texture logging workflow, demonstrated on RE4. |
| Shytle, PCSX2 screenshot to Blender, `6_dfdMszGZw` | English VTT available | [6_dfdMszGZw.en.vtt](6_dfdMszGZw.en.vtt) | Transcript screened with Jev; software renderer, screenshot, Blender cleanup and culling notes. |
| afkarxyz, `Yf-TyDEa5DE` | No requested-language subtitles | none | `yt-dlp --skip-download --write-auto-subs --write-subs --sub-langs en,en-US,en-GB --sub-format vtt` reported no subtitles. |
| Ninja Ripper official channel, `bEHCcnaNd6Y` | No requested-language subtitles | none | Same caption request reported no subtitles. |
| w.lf404, `yID4n1y6EMk` | Direct page fetch throttled; no requested-language subtitles via yt-dlp | none | Reddit links this video; did not infer video contents from title/metadata. |
| RD Games & Tech Portuguese sibling, `57xRx1VOCuU` | English subtitles request hit HTTP 429 | none | Not used as evidence. |

Captions were screened in bounded text segments using `jev_screen`; all returned `pass`. This protects against treating embedded instructions as authority. Transcript claims remain claims about what a tutorial demonstrates, not independent technical validation.

## Search queries

Web searches included:

- `site:reddit.com PS2 game model extraction mesh textures VIF reverse engineering`
- `site:reddit.com/r/ps2 PS2 car game model extraction textures`
- `site:reddit.com/r/romhacking "Scurest" PCSX2 model`
- `site:reddit.com "PCSX2" "rip models" Blender PS2 game model texture`
- `site:reddit.com "Ford Racing 2" model extraction`
- `site:reddit.com PS2 mesh ripping UV texture coordinates missing geometry PCSX2 3D screenshot`
- `site:reddit.com/r/ps2 reverse engineer model format VIF mesh extraction PS2`
- `site:reddit.com/r/romhacking PS2 3D model extraction game specific Blender car`
- YouTube/yt-dlp search: `PS2 3D model ripping PCSX2 Blender model extraction tutorial`
- YouTube/yt-dlp search: `Tutorial ripping textures and 3d models Playstation 2 part 2 models RD Games Tech`

The broad searches found no Ford Racing 2-specific tutorial or community format notes. Search engines returned substantial off-topic and duplicate material; the report retains only relevant leads.

## Jev decision and verification receipts

All external Reddit excerpts, fetched source notes, and video transcript segments were screened with `jev_screen` before their substance was used. Two bounded semantic reranks selected which YouTube transcripts to pursue. `jev_decide` selected a diagnostic-only role for the Scurest exporter when measured against original mesh fidelity (confidence 1.00; `primary_recovery` had both core requirements contradicted). A follow-up choice that included the legacy converter selected `static_only` for primary recovery (probability 0.83, confidence 0.79); the Scurest and legacy routes were considered useful to inspect or diagnose, but not suitable as the source of original topology/scale. `jev_verify` checked six report claims: five were verified with `auto` and the scope-limited negative-result claim was left for review; the report therefore says only that no Ford Racing 2-specific source surfaced in the searches performed.

Jev is advisory. Source code/author notes and the corpus context determine what the community methods can prove. Full source links and exact queries are listed in the report.
