#include "core/HandednessLogic.h"

#include <format>

namespace dvb::HandednessLogic
{
	namespace
	{
		bool IsLogical(std::string_view a_name)
		{
			return a_name == "primary" || a_name == "offhand";
		}

		/**
		 * Whether a_value is a string naming a logical hand.
		 */
		bool IsLogicalValue(const json& a_value)
		{
			return a_value.is_string() && IsLogical(a_value.get<std::string>());
		}

		/**
		 * The head.lookAt value of the arguments, or null when there is none.
		 */
		const json& LookAt(const json& a_args)
		{
			static const json none;
			if (!a_args.contains("head") || !a_args["head"].is_object() || !a_args["head"].contains("lookAt"))
				return none;
			return a_args["head"]["lookAt"];
		}
	}

	/**
	 * The physical controller ("left" / "right") a hand name means: a physical name as is, a
	 * logical one for the handedness (the primary hand is the right controller unless
	 * left-handed). nullopt for any other name.
	 */
	std::optional<std::string> PhysicalHand(std::string_view a_name, bool a_leftHanded)
	{
		if (a_name == "left" || a_name == "right")
			return std::string(a_name);
		if (a_name == "primary")
			return a_leftHanded ? "left" : "right";
		if (a_name == "offhand")
			return a_leftHanded ? "right" : "left";
		return std::nullopt;
	}

	/**
	 * Whether VR input arguments name a logical hand where a hand is named: press's 'hand',
	 * a key of pose's 'hands' object, or head.lookAt.
	 */
	bool UsesLogicalHands(const json& a_args)
	{
		if (!a_args.is_object())
			return false;
		if (a_args.contains("hand") && IsLogicalValue(a_args["hand"]))
			return true;
		if (a_args.contains("hands") && a_args["hands"].is_object())
			for (const auto& [key, value] : a_args["hands"].items())
				if (IsLogical(key))
					return true;
		return IsLogicalValue(LookAt(a_args));
	}

	/**
	 * A copy of VR input arguments with every logical hand name replaced by its physical
	 * controller for the handedness. Fails (nullopt, a_error filled) when pose's 'hands' names
	 * one controller twice, e.g. left and primary while left-handed. Other values pass through
	 * for the action's own validation.
	 */
	std::optional<json> ResolveHands(const json& a_args, bool a_leftHanded, std::string& a_error)
	{
		json out = a_args;
		if (!out.is_object())
			return out;
		if (out.contains("hand") && IsLogicalValue(out["hand"]))
			out["hand"] = *PhysicalHand(out["hand"].get<std::string>(), a_leftHanded);
		if (out.contains("hands") && out["hands"].is_object()) {
			json hands = json::object();
			for (const auto& [key, value] : out["hands"].items()) {
				const std::string physical = IsLogical(key) ? *PhysicalHand(key, a_leftHanded) : key;
				if (hands.contains(physical)) {
					a_error = std::format("'hands' names the {} controller twice ({}handed)", physical, a_leftHanded ? "left-" : "right-");
					return std::nullopt;
				}
				hands[physical] = value;
			}
			out["hands"] = std::move(hands);
		}
		if (IsLogicalValue(LookAt(out)))
			out["head"]["lookAt"] = *PhysicalHand(out["head"]["lookAt"].get<std::string>(), a_leftHanded);
		return out;
	}

	/**
	 * Whether the wand slots sit too close together for a swap to show.
	 */
	bool TooClose(const WandSlots& a_slots)
	{
		return ReachLogic::Distance(a_slots.primary, a_slots.secondary) < kMinApartUnits;
	}

	/**
	 * Whether each wand slot now sits where the other one was, within kSwapToleranceUnits.
	 */
	bool Swapped(const WandSlots& a_before, const WandSlots& a_now)
	{
		return ReachLogic::Distance(a_now.primary, a_before.secondary) <= kSwapToleranceUnits &&
		       ReachLogic::Distance(a_now.secondary, a_before.primary) <= kSwapToleranceUnits;
	}
}
