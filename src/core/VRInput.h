#pragma once

#include "core/Json.h"

#include <string_view>

namespace dvb
{
	class EventBus;
	struct ToolContext;

	json VRInputCapabilities();
	json HandleVRInput(const json& a_args, const ToolContext& a_ctx);
	bool IsVRInputDevice(std::string_view a_device);

	// Installs process-lifetime pass-through OpenVR interface hooks. They alter data only while
	// one owned atomic sequence is active; otherwise every call reaches the original runtime.
	// Returns true once installed; idempotent, so a platform may retry until OpenVR is up.
	bool MarkVRInputReady(EventBus& a_events);
	void ReleaseVRInputForLifecycle(const char* a_reason);
}
