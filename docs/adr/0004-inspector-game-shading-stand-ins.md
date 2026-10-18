---
status: accepted
---
# The inspector's candidate game shading uses labelled stand-ins for game-state inputs

The decoded pass-4 handler needs a game-state eye position (`DM[7]`) and a 3x3 matrix (`TOP[12]`-`TOP[14]`) that no
receipt carries per vertex, so the Recovered inspector's "Game shading (candidate)" control takes the inspector
camera as the eye, derives the matrix from the camera's world basis, and reconstructs the position plane's w lane as
`1/|position - eye|` because the exported geometry has no such lane and the capture comparison's factor range
([0, 1] on every aligned vertex, i.e. a cosine) reads that lane as making V unit length. The alternative - waiting for a capture that supplies both inputs -
would leave the decoded arithmetic unreproducible in the inspector, where a labelled approximation is testable and
visible. The cost is that the control demonstrates the decoded form and its colour factor, not the game's own
reflection.

The decoded pass-5 handler needs the same eye and w lane, and in addition a light colour and intensity (`DM[5]`) and
the direction that light is reflected about the normal (`DM[6]`); its per-draw RGBA constant is `ftoi0(min(DM[5] *
colour, 128))`. Those two inputs come from game state as well, and no receipt carries them per vertex either. All 63
aligned pass-5 draws of the capture comparison carry the same retained `DM[5]` and `DM[6]` words, so the control
substitutes exactly those retained words as one fixed light and adds no light of its own; a per-draw light that the
capture does not show is not invented. The term is composited the same way as pass 4 - added over the baseline
pass-2 colour, because the draw's `ALPHA_1` blend equation and the sampled specular texture function are not in the
receipt - and with the retained `DM[5].w` the RGBA alpha lane truncates to 0, so the highlight adds to RGB only. The
cost is that the control shows the decoded highlight and how it moves with the eye, not the game's own light.

Every stand-in is recorded in the module header, in `dealership/public/game-shading.json`'s `claim_limits`, in the
honesty label shown while the control is on, in its tooltip, and in the note it cites.
