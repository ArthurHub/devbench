#include "core/VRHost.h"

#include "core/ToolRegistry.h"

// Fallout 4's side of the VR input seam (core/VRHost.h). No OpenVR interfaces yet, so the
// VR input API reports "not ready" and nothing below is reached through it.
namespace dvb::vrhost
{
	vr::IVRSystem* System()
	{
		return nullptr;
	}

	vr::IVRCompositor* Compositor()
	{
		return nullptr;
	}

	std::pair<std::uint32_t, std::uint32_t> SetControllerIndices(std::uint32_t a_left, std::uint32_t a_right)
	{
		return { a_left, a_right };
	}

	ReachLogic::Vec3 ReachHandWorld(bool)
	{
		throw ToolError(501, "reach is not available on Fallout 4 yet");
	}

	ReachLogic::Vec3 ReachNodeWorld(const std::string&)
	{
		throw ToolError(501, "reach is not available on Fallout 4 yet");
	}

	double PlayerYaw()
	{
		throw ToolError(501, "reach is not available on Fallout 4 yet");
	}
}
