#include "Tools_Fallout4.h"

#include "core/Json.h"
#include "core/MainThread.h"
#include "core/ToolRegistry.h"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <format>
#include <optional>
#include <thread>
#include <vector>

// The `player` tool on Fallout 4: put the player in and out of a power armor frame and
// say whether they are in one, so a test can set up power armor without a headset.
//
// The state is the engine's own answer, PowerArmor::ActorInPowerArmor (REL::ID 1176757;
// the VR address library maps it to 0x9BF5D0, the RVA F4VR-CommonFramework calls too:
// Modding-Reference F4VR/Analysis/gold/F4VR-CommonFramework_RE_REFERENCE.md, Power Armor).
// The switch is the console's `player.cf "Actor.SwitchToPowerArmor" <frame>` / `none`,
// the path Immersive Flashlight's release check drives on FO4VR. Activating a frame
// does not get the player in. The switch lands on a later frame, and the skeleton
// swap can hold the main thread, so the wait polls from the listener thread with short
// main-thread reads instead of blocking the main thread.
namespace dvb
{
	namespace
	{
		// the keyword on the furniture base of every power armor frame standing in the world
		constexpr std::string_view kFrameKeyword = "FurnitureTypePowerArmor";

		constexpr std::chrono::milliseconds kPollInterval{ 100 };
		constexpr std::chrono::milliseconds kPollTaskTimeout{ 2000 };
		constexpr std::int64_t              kDefaultTimeoutMs = 10000;
		constexpr std::int64_t              kMaxTimeoutMs = 60000;
		constexpr double                    kDefaultRadius = 500.0;
		constexpr double                    kMaxRadius = 20000.0;
		constexpr std::int64_t              kDefaultLimit = 5;
		constexpr std::int64_t              kMaxLimit = 50;
		constexpr std::size_t               kCommandMaxLines = 50;

		/**
		 * Main thread. The player, or a 409 when no save is loaded.
		 */
		RE::PlayerCharacter& RequirePlayer(std::string_view a_action)
		{
			auto* player = RE::PlayerCharacter::GetSingleton();
			if (!player || !player->GetParentCell())
				throw ToolError(409, std::format("player {}: no player in the world (no save loaded yet)", a_action));
			return *player;
		}

		/**
		 * Main thread. The engine's own "is this actor in power armor".
		 */
		bool InPowerArmor(RE::PlayerCharacter& a_player)
		{
			return RE::PowerArmor::ActorInPowerArmor(a_player);
		}

		/**
		 * The furniture base of a reference when it is a power armor frame, else nullptr.
		 */
		RE::TESFurniture* FrameBase(RE::TESObjectREFR* a_ref)
		{
			if (!a_ref || !a_ref->data.objectReference)
				return nullptr;
			auto* furniture = a_ref->data.objectReference->As<RE::TESFurniture>();
			return furniture && furniture->HasKeywordString(kFrameKeyword) ? furniture : nullptr;
		}

		float DistanceTo(const RE::TESObjectREFR& a_from, const RE::TESObjectREFR& a_to)
		{
			const auto a = a_from.GetPosition();
			const auto b = a_to.GetPosition();
			return std::sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y) + (a.z - b.z) * (a.z - b.z));
		}

		json FrameToJson(RE::TESObjectREFR& a_ref, RE::TESFurniture& a_base, float a_distance)
		{
			json out{
				{ "formId", std::format("0x{:08X}", a_ref.GetFormID()) },
				{ "baseFormId", std::format("0x{:08X}", a_base.GetFormID()) },
				{ "distance", std::round(static_cast<double>(a_distance) * 10.0) / 10.0 },
			};
			if (const auto name = RE::TESFullName::GetFullName(a_base); !name.empty())
				out["name"] = std::string{ name };
			return out;
		}

		struct Frame
		{
			RE::TESObjectREFR* ref;
			RE::TESFurniture*  base;
			float              distance;
		};

		/**
		 * Main thread. The power armor frames in the player's cell within a_radius game units,
		 * nearest first. Only the player's own cell: a frame just over an exterior cell border
		 * is not listed.
		 */
		std::vector<Frame> FindFrames(RE::PlayerCharacter& a_player, float a_radius)
		{
			std::vector<Frame> found;
			auto*              cell = a_player.GetParentCell();
			if (!cell)
				return found;
			for (const auto& refPtr : cell->references) {
				auto* ref = refPtr.get();
				if (!ref || ref->IsDeleted() || ref->IsDisabled())
					continue;
				auto* base = FrameBase(ref);
				if (!base)
					continue;
				const float distance = DistanceTo(a_player, *ref);
				if (distance <= a_radius)
					found.push_back({ ref, base, distance });
			}
			std::ranges::sort(found, {}, &Frame::distance);
			return found;
		}

		/**
		 * A form ID from a JSON string ("0x0001F2A3" or "1F2A3", hex) or integer.
		 */
		std::uint32_t ParseFormId(const json& a_value)
		{
			if (a_value.is_number_unsigned())
				return a_value.get<std::uint32_t>();
			if (!a_value.is_string())
				throw ToolError(400, "player: 'formId' must be a hex string such as \"0x0001F2A3\"");
			std::string text = a_value.get<std::string>();
			if (text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X'))
				text.erase(0, 2);
			std::uint32_t id = 0;
			const auto [end, ec] = std::from_chars(text.data(), text.data() + text.size(), id, 16);
			if (text.empty() || ec != std::errc{} || end != text.data() + text.size())
				throw ToolError(400, std::format("player: 'formId' '{}' is not a hex form ID", a_value.get<std::string>()));
			return id;
		}

		float RadiusArg(const json& a_args)
		{
			return static_cast<float>(std::clamp(a_args.value("radius", kDefaultRadius), 1.0, kMaxRadius));
		}

		/**
		 * Polls the player's power armor state from the listener thread until it equals
		 * a_target or a_timeout passes. A poll the main thread does not serve in time (a
		 * skeleton swap or a load) counts as a stall and the wait goes on.
		 */
		json WaitForPowerArmor(bool a_target, std::chrono::milliseconds a_timeout)
		{
			const auto start = std::chrono::steady_clock::now();
			const auto deadline = start + a_timeout;
			bool       in = !a_target;
			int        stalls = 0;
			for (;;) {
				try {
					in = MainThread::RunAndWait([]() -> json { return InPowerArmor(RequirePlayer("wait")); }, kPollTaskTimeout).get<bool>();
				} catch (const MainThread::TaskTimeout&) {
					++stalls;
				}
				const auto now = std::chrono::steady_clock::now();
				if (in == a_target || now >= deadline)
					break;
				std::this_thread::sleep_for(std::min<std::chrono::steady_clock::duration>(kPollInterval, deadline - now));
			}
			const auto waited = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start);
			json       out{ { "inPowerArmor", in }, { "waitedMs", waited.count() } };
			if (stalls)
				out["mainThreadStalls"] = stalls;
			return out;
		}

		json HandleStatus()
		{
			return MainThread::RunAndWait([]() -> json {
				return json{ { "inPowerArmor", InPowerArmor(RequirePlayer("status")) } };
			});
		}

		json HandleFind(const json& a_args)
		{
			const float radius = RadiusArg(a_args);
			const auto  limit = static_cast<std::size_t>(std::clamp(a_args.value("limit", kDefaultLimit), std::int64_t{ 1 }, kMaxLimit));
			return MainThread::RunAndWait([radius, limit]() -> json {
				auto&      player = RequirePlayer("findPowerArmor");
				const auto found = FindFrames(player, radius);
				json       frames = json::array();
				for (std::size_t i = 0; i < found.size() && i < limit; ++i)
					frames.push_back(FrameToJson(*found[i].ref, *found[i].base, found[i].distance));
				return json{ { "inPowerArmor", InPowerArmor(player) }, { "radius", radius }, { "frames", std::move(frames) } };
			});
		}

		/**
		 * enterPowerArmor / exitPowerArmor: switch on the main thread, then wait for the
		 * engine state from here. `outcome` is switched, already, refused (the state did not
		 * change within timeoutMs) or notWaited (wait=false).
		 */
		json HandleSwitch(const std::string& a_action, const json& a_args)
		{
			const bool                   enter = a_action == "enterPowerArmor";
			const bool                   wait = a_args.value("wait", true);
			const auto                   timeout = std::chrono::milliseconds(std::clamp(a_args.value("timeoutMs", kDefaultTimeoutMs), std::int64_t{ 0 }, kMaxTimeoutMs));
			std::optional<std::uint32_t> formId;
			if (enter && a_args.contains("formId"))
				formId = ParseFormId(a_args["formId"]);
			const float radius = RadiusArg(a_args);

			json out = MainThread::RunAndWait([a_action, enter, formId, radius]() -> json {
				auto& player = RequirePlayer(a_action);
				if (InPowerArmor(player) == enter)
					return json{ { "inPowerArmor", enter }, { "outcome", "already" } };

				json        result = json::object();
				std::string target = "none";
				if (enter) {
					RE::TESObjectREFR* ref = nullptr;
					RE::TESFurniture*  base = nullptr;
					if (formId) {
						ref = RE::TESForm::GetFormByID<RE::TESObjectREFR>(*formId);
						if (!ref)
							throw ToolError(404, std::format("player enterPowerArmor: no reference 0x{:08X}", *formId));
						base = FrameBase(ref);
						if (!base)
							throw ToolError(400, std::format("player enterPowerArmor: 0x{:08X} is not a power armor frame (its base has no {} keyword)", *formId, kFrameKeyword));
					} else {
						const auto found = FindFrames(player, radius);
						if (found.empty())
							throw ToolError(404, std::format("player enterPowerArmor: no power armor frame within {} units in the player's cell; pass formId or a larger radius", radius));
						ref = found.front().ref;
						base = found.front().base;
					}
					result["frame"] = FrameToJson(*ref, *base, DistanceTo(player, *ref));
					target = std::format("{:08X}", ref->GetFormID());
				}
				const auto command = std::format("player.cf \"Actor.SwitchToPowerArmor\" {}", target);
				const auto console = RunConsoleCapture(command, kCommandMaxLines);
				result["command"] = command;
				for (const char* key : { "compiled", "lines" }) {
					if (console.contains(key))
						result[key] = console[key];
				}
				result["inPowerArmor"] = InPowerArmor(player);
				return result;
			});

			out["action"] = a_action;
			if (out.contains("outcome"))
				return out;
			if (!wait) {
				out["outcome"] = "notWaited";
				out["note"] = "inPowerArmor was read right after the command; the switch can land on a later frame, so read action='status' to see it";
				return out;
			}
			const json waited = WaitForPowerArmor(enter, timeout);
			out.update(waited);
			const bool switched = waited["inPowerArmor"].get<bool>() == enter;
			out["outcome"] = switched ? "switched" : "refused";
			if (!switched) {
				out["note"] = std::format(
					"the player is still {} power armor after {} ms. The switch was refused or has not finished: a mod can "
					"block it (KabutoVR blocks the scripted exit), `lines` holds what the command printed, and a Papyrus "
					"error goes to the Papyrus log",
					enter ? "out of" : "in", timeout.count());
			}
			return out;
		}

		json HandlePlayer(const json& a_args, const ToolContext&)
		{
			if (!a_args.is_object())
				throw ToolError(400, "player arguments must be an object");
			const std::string action = a_args.value("action", std::string("status"));
			if (action == "status")
				return HandleStatus();
			if (action == "findPowerArmor")
				return HandleFind(a_args);
			if (action == "enterPowerArmor" || action == "exitPowerArmor")
				return HandleSwitch(action, a_args);
			throw ToolError(400, std::format("player: unknown action '{}' (status|findPowerArmor|enterPowerArmor|exitPowerArmor)", action));
		}
	}

	void RegisterPlayerTool(ToolRegistry& a_registry)
	{
		ToolDescriptor player;
		player.name = "player";
		player.description =
			"The player's power armor. action='status' (default) → { inPowerArmor }, the engine's own answer "
			"(PowerArmor::ActorInPowerArmor). 'findPowerArmor' (radius default 500 units, limit default 5) → { inPowerArmor, "
			"radius, frames:[{ formId, baseFormId, name, distance }] }, the power armor frames (furniture with the "
			"FurnitureTypePowerArmor keyword) in the player's cell, nearest first; a frame across an exterior cell border is "
			"not listed. 'enterPowerArmor' (formId, default the nearest frame within radius) and 'exitPowerArmor' switch at "
			"once, without the step-in animation, through the console's player.cf \"Actor.SwitchToPowerArmor\" <frame> / "
			"none, then wait (wait default true) until the engine state flips or timeoutMs (default 10000, max 60000) "
			"passes, polling short main-thread reads so the skeleton swap is never blocked. Returns { action, frame?, "
			"command, compiled, lines, inPowerArmor, waitedMs, mainThreadStalls?, outcome, note? }; outcome is 'switched', "
			"'already' (nothing was run), 'refused' (the state did not change in time: KabutoVR blocks the scripted exit) "
			"or 'notWaited'. 409 when no save is loaded.";
		player.inputSchema = json{
			{ "type", "object" },
			{ "properties", json{
								{ "action", json{ { "type", "string" }, { "enum", json::array({ "status", "findPowerArmor", "enterPowerArmor", "exitPowerArmor" }) }, { "description", "default 'status'" } } },
								{ "formId", json{ { "type", "string" }, { "description", "enterPowerArmor: the frame reference, hex (\"0x0001F2A3\"), as findPowerArmor lists it; default the nearest frame within radius" } } },
								{ "radius", json{ { "type", "number" }, { "minimum", 1 }, { "maximum", kMaxRadius }, { "description", "findPowerArmor / enterPowerArmor without formId: how far to look, in game units (default 500)" } } },
								{ "limit", json{ { "type", "integer" }, { "minimum", 1 }, { "maximum", kMaxLimit }, { "description", "findPowerArmor: most frames to list (default 5)" } } },
								{ "wait", json{ { "type", "boolean" }, { "description", "enterPowerArmor / exitPowerArmor: wait for the engine state to flip (default true)" } } },
								{ "timeoutMs", json{ { "type", "integer" }, { "minimum", 0 }, { "maximum", kMaxTimeoutMs }, { "description", "enterPowerArmor / exitPowerArmor: how long to wait (default 10000)" } } },
							} },
		};
		a_registry.Register(std::move(player), &HandlePlayer);
	}
}
