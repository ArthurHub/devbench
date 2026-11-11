#pragma once

#include "core/Json.h"

#include <cstddef>
#include <string>
#include <string_view>

namespace RE
{
	class NiAVObject;
}

namespace dvb
{
	class ToolRegistry;
	class EventBus;

	/// Register the Fallout 4 game tools (`inspect`, `console`, `menu`, `nodes`, `input`, `player`). The
	/// game-agnostic tools (`ping`, `memory`, `log`) come from
	/// dvb::tools::RegisterCommonTools.
	void RegisterGameTools(ToolRegistry& a_registry, EventBus& a_events);

	/// Register `nodes` (scene-graph traversal). Called by RegisterGameTools.
	void RegisterNodeTools(ToolRegistry& a_registry);

	/// Register `input` (VR tracked-set injection). Called by RegisterGameTools.
	void RegisterInputTool(ToolRegistry& a_registry);

	/// Register `player` (power armor). Called by RegisterGameTools.
	void RegisterPlayerTool(ToolRegistry& a_registry);

	/// Main thread. Runs console commands now and returns their output (Tools_Fallout4.cpp).
	json RunConsoleCapture(const std::string& a_command, std::size_t a_maxLines);

	/// Main thread. A player node by name for Reach (Nodes_Fallout4.cpp).
	RE::NiAVObject* FindPlayerNode(std::string_view a_name);
	/// Main thread. The Wand node that follows one physical controller (Nodes_Fallout4.cpp).
	RE::NiAVObject* WandNode(bool a_right);
	/// Main thread. True when bLeftHandedMode:VR makes the left controller the primary hand.
	bool LeftHandedMode();
}
