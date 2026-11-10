#pragma once

#include "core/ReachLogic.h"

#include <cstdint>
#include <string>
#include <utility>

namespace vr
{
	class IVRSystem;
	class IVRCompositor;
}

// The VR input seam.
//
// Everything the core's VR input (core/VRInput.cpp) and Reach (core/ReachControl.cpp) need
// from the game. Each platform links exactly one definition of these functions; a platform
// without VR input returns nullptr from the interface getters, which keeps the input API
// reporting "not ready" instead of failing to link.
//
// Threading: the interface getters are callable from any thread. Everything else is called
// on the game's main thread (the core marshals with MainThread::RunAndWait first).
namespace dvb::vrhost
{
	/// The game's own OpenVR system interface (IVRSystem_019 ABI), or nullptr while unavailable.
	vr::IVRSystem* System();
	/// The game's own OpenVR compositor interface (IVRCompositor_022 ABI), or nullptr while unavailable.
	vr::IVRCompositor* Compositor();

	/// Points the game's left/right controller devices at the given OpenVR device indices and
	/// returns the indices they had, so a Sequence can restore them. Throws ToolError(503) while
	/// the game's controller devices are unavailable.
	std::pair<std::uint32_t, std::uint32_t> SetControllerIndices(std::uint32_t a_left, std::uint32_t a_right);

	/// World position of the in-game node Reach measures for one Controller.
	ReachLogic::Vec3 ReachHandWorld(bool a_right);
	/// World position of a Reach target node, looked up by name. Throws ToolError(404) when absent.
	ReachLogic::Vec3 ReachNodeWorld(const std::string& a_name);
	/// The player's heading in radians (game yaw, 0 = +Y, increasing clockwise seen from above).
	double PlayerYaw();
}
