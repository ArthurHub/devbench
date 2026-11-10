# devbench

devbench exposes a running game to AI agents and scripts so they can inspect it and drive it, including standing in for the VR player's headset and controllers in end-to-end tests.

## VR input

**Controller**:
A tracked VR hand device as OpenVR reports it: a pose plus button, touch and axis state. devbench drives Controllers.
_Avoid_: wand, hand (for the device)

**Hand**:
The in-game body part that follows a Controller, placed by the game or by a body mod such as FRIK.
_Avoid_: controller (for the body part)

**Wand**:
The in-game node the game places at a Controller's pose each frame, present with or without a body mod.

**Tracked set**:
The HMD and both Controllers taken together, the unit devbench replaces as a whole.
_Avoid_: devices, rig

**Frame**:
One timestamped snapshot of the Tracked set: three poses plus both Controllers' button, touch and axis state.

**Sequence**:
A bounded, timed list of Frames that devbench plays in place of the physical Tracked set, held by a single owner until it ends or is stopped.
_Avoid_: recording, replay (those name a separate feature)

**Reach**:
Driving the Controllers until their in-game nodes (Wands on Fallout 4 VR) reach a target relative to a named node, correcting against where they actually land.
_Avoid_: move hand
