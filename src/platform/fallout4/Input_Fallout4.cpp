#include "Tools_Fallout4.h"

#include "core/ToolRegistry.h"
#include "core/VRInput.h"
#include "core/VRInputState.h"

#include <format>

// The `input` tool on Fallout 4: only device='vrTrackedSet', with the same arguments and
// results as Skyrim's input tool for that device (core/VRInput.cpp handles both).
namespace dvb
{
	namespace
	{
		json HandleInput(const json& a_args, const ToolContext& a_ctx)
		{
			if (!a_args.is_object())
				throw ToolError(400, "input arguments must be an object");
			if (a_args.contains("action") && !a_args["action"].is_string())
				throw ToolError(400, "'action' must be a string");
			const std::string action = a_args.value("action", std::string("capabilities"));
			if (action == "capabilities")
				return json{ { "capabilities", json{ { "vrTrackedSet", VRInputCapabilities() } } } };
			if (a_args.contains("device") && !a_args["device"].is_string())
				throw ToolError(400, "'device' must be a string");
			const std::string device = a_args.value("device", std::string("vrTrackedSet"));
			if (!IsVRInputDevice(device))
				throw ToolError(400, std::format("device '{}' is not supported here; Fallout 4 supports device='vrTrackedSet'", device));
			return HandleVRInput(a_args, a_ctx);
		}
	}

	void RegisterInputTool(ToolRegistry& a_registry)
	{
		ToolDescriptor input;
		input.name = "input";
		input.description =
			"Synthetic VR input. action='capabilities' (default) returns the contract version, readiness, limits and "
			"supported actions; clients should check it rather than assume this tool exists. device='vrTrackedSet' "
			"(the only device on Fallout 4) replaces the HMD and both controllers at the OpenVR boundary. 'status' "
			"reports readiness, the active sequence and, per hooked OpenVR call, whether devbench sits closest to the "
			"runtime (when false, another mod hooked that call first and injected input bypasses it). 'observe' returns "
			"the current physical HMD and controllers as one frame. 'sequence' plays a prevalidated timestamped list of "
			"frames, each holding the HMD, left and right poses plus both controllers' OpenVR button/touch/axis state; it "
			"is asynchronous, has one owner, and returns a controlToken that 'stop' requires. 'releaseAll' stops this "
			"owner's sequence. The real devices pass through whenever no sequence is active, and a sequence stops on "
			"load and new game. Emits input.vrTrackedSet events.";
		input.inputSchema = json{
			{ "type", "object" },
			{ "properties", json{
								{ "action", json{ { "type", "string" }, { "enum", json::array({ "capabilities", "status", "observe", "sequence", "stop", "releaseAll" }) } } },
								{ "device", json{ { "type", "string" }, { "enum", json::array({ "vrTrackedSet" }) }, { "description", "the only device on Fallout 4 (default)" } } },
								{ "owner", json{ { "type", "string" }, { "minLength", 1 }, { "maxLength", 128 }, { "description", "stable task/session owner; defaults to MCP session id or rest:anonymous" } } },
								{ "frames", json{ { "type", "array" }, { "minItems", 1 }, { "maxItems", kMaximumVRTrackedFrames }, { "description", "sequence: monotonic atomic frames; each requires tMs, originCode, hmd, left, right; controller objects carry packetNumber/pressed/touched/five axes" }, { "items", json{ { "type", "object" } } } } },
								{ "tailMs", json{ { "type", "integer" }, { "minimum", 10 }, { "maximum", 1000 }, { "description", "sequence: final-state visibility before automatic release (default 50ms)" } } },
								{ "controlToken", json{ { "type", "string" }, { "description", "stop/releaseAll: opaque token returned by sequence start" } } },
							} },
		};
		a_registry.Register(std::move(input), &HandleInput);
	}
}
