# Blurred/feathered rounded corners on a GIF in a GitHub README

Target: a moving (GIF) asset embedded in this repo's README that must read correctly on both light (`#ffffff`) and dark (`#0d1117`) themes, with blurred/feathered (not hard) rounded corners.

## Constraint: GIF transparency is 1-bit only

GIF89a's Graphic Control Extension carries a single Transparent Color Flag plus a Transparent Color Index (one byte). A pixel is either fully transparent or fully opaque; there is no per-pixel alpha channel.

- Source: W3C "Graphics Interchange Format, Version 89a", https://www.w3.org/Graphics/GIF/spec-gif89a.txt — Graphic Control Extension fields: Transparent Color Flag (1 bit), Transparent Color Index (1 byte); "The Transparency Index is such that when encountered, the corresponding pixel of the display device is not modified..." The index is present iff the flag is 1. No alpha mask, no partial transparency.

Consequence: any "rounded corner" achieved with GIF transparency is a hard cutout (1-bit), never a feather/blur. Blurred corners require alpha compositing against a known background, i.e. pre-matting.

## Pillow's GIF encoder cannot emit partial alpha

Pillow's GifImagePlugin._save / _write_local_header writes one transparency index into the GCE (packed_flag = 1 if transparency is not None). _get_palette_bytes strips any alpha from an RGBA palette (palette[i*4 : i*4+3]). On load, a transparent index is turned into alpha 0 via putpalettealpha(..., 0) and the frame is converted to RGBA only at decode time; on save the encoder quantizes to a 256-entry RGB palette and records at most one transparent index.

- Source: Pillow source https://github.com/python-pillow/Pillow/blob/main/src/PIL/GifImagePlugin.py (_write_local_header, _get_palette_bytes, _get_global_header, _save).
- Docs: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif (save parameters transparency, disposal, optimize; no alpha parameter).

Verdict: Pillow cannot produce a GIF with 8-bit alpha. Any RGBA input is reduced to one transparent palette index (binary). Confirmed by encoder behavior above, not merely by docs.

## GitHub README rendering facts

1. Supported image formats in READMEs include PNG/JPG/GIF/PSD/SVG; SVG does not animate. No mention of APNG or WebP as first-class animated formats in the README rendering docs; "animated .gif images" are the documented animated image type, with a user motion setting controlling autoplay.
   - Source: https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files ("Rendering and diffing images": common formats PNG, JPG, GIF, PSD, SVG; "SVGs don't currently support inline scripting or animation.").
   - Motion setting: https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-user-account-settings/managing-accessibility-settings ("control how GitHub displays animated .gif images", autoplay sync/disabled).

2. Theme-aware images: GitHub supports `<picture>` with `prefers-color-scheme: dark/light` (recommended); the `#gh-dark-mode-only` / `#gh-light-mode-only` URL fragments are deprecated and will be removed.
   - Source: https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax ("Specifying the theme an image is shown to": `<picture>` example; "The old method ... is deprecated and will be removed in favor of the new method").

3. HTML in READMEs is sanitized: `<video>` is not a supported README element (docs note "some (like an embedded YouTube video) cannot" be shown). CSS `border-radius` on `img` is not documented and should be assumed stripped.
   - Source: https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files ("Viewing HTML elements").

## Candidate techniques

### (a) Single transparent GIF with hard corners
Export GIF with one transparent palette index around the rounded region; corners are a hard 1-bit cutout. Fails the blurred/feathered requirement.

### (b) Two opaque pre-matted GIFs swapped by theme (recommended — adopted)
Render the animation twice, each composited onto the target background (`#ffffff`, `#0d1117`) with a blurred rounded-corner alpha mask (28px radius, 8px Gaussian blur at render time), then flattened to opaque RGB and exported as GIFs. Swap in the README via `<picture>` + `prefers-color-scheme`. Blurred corners survive because they are baked into opaque pixels. Cost: two assets to keep in sync (~345KB + ~340KB); re-matte if the README background changes.

Adopted in this repo as `docs/screenshots/dealership-views-light.gif` / `dealership-views-dark.gif`, generated from the same Side→Front→Top→Reset capture sequence with Pillow (`ImageDraw.rounded_rectangle` + `GaussianBlur` + `paste` with mask).

### (c) APNG with 8-bit alpha
PNG alpha gives feathered corners in one asset, but GitHub does not document APNG animation in READMEs; the documented animated type is GIF. Unreliable — not used.

### (d) Rounded-corner `<video>` / (e) CSS `border-radius`
Not viable: README HTML is sanitized, `<video>` unsupported, CSS on `img` undocumented.

## Sources
- W3C GIF89a spec: https://www.w3.org/Graphics/GIF/spec-gif89a.txt
- Pillow source: https://github.com/python-pillow/Pillow/blob/main/src/PIL/GifImagePlugin.py
- Pillow docs: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif
- GitHub basic writing/formatting (theme images): https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
- GitHub non-code files (image formats, HTML elements): https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files
- GitHub accessibility/motion (animated GIF autoplay): https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-user-account-settings/managing-accessibility-settings

Research delegation: background agent GifCorners (2026-10-20); findings verified against the cited sources before adoption. The adopted README markup uses `<picture>` (recommended method), not the deprecated fragments.
