---
status: accepted
---
# The inspector's candidate pass-4 shading uses labelled stand-ins for game-state inputs

The decoded pass-4 handler needs a game-state eye position (`DM[7]`) and a 3x3 matrix (`TOP[12]`-`TOP[14]`) that no
receipt carries per vertex, so the Recovered inspector's "Game shading (candidate)" control takes the inspector
camera as the eye, derives the matrix from the camera's world basis, and reconstructs the position plane's w lane as
`1/|position - eye|` because the exported geometry has no such lane and the capture comparison's factor range
([0, 1] on every aligned vertex, i.e. a cosine) reads that lane as making V unit length. The alternative - waiting for a capture that supplies both inputs -
would leave the decoded arithmetic unreproducible in the inspector, where a labelled approximation is testable and
visible. The cost is that the control demonstrates the decoded form and its colour factor, not the game's own
reflection. Every stand-in is recorded in the module header, in `dealership/public/game-shading-pass4.json`'s
`claim_limits`, in the honesty label shown while the control is on, and in the note it cites.
