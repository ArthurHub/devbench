#include "core/PoseLogic.h"

#include <algorithm>
#include <cmath>
#include <format>

namespace dvb::PoseLogic
{
	namespace
	{
		constexpr double kPi = 3.14159265358979323846;
		constexpr double kEpsilon = 1e-12;

		double Radians(double a_degrees)
		{
			return a_degrees * kPi / 180.0;
		}

		double EaseInOut(double a_t)
		{
			return a_t * a_t * (3.0 - 2.0 * a_t);
		}

		bool ReadNumber(const json& a_value, const std::string& a_path, double a_min, double a_max, double& a_out, std::string& a_error)
		{
			const std::string range = std::format("{}..{}", a_min, a_max);
			if (!a_value.is_number() || !std::isfinite(a_value.get<double>()) || a_value.get<double>() < a_min || a_value.get<double>() > a_max) {
				a_error = std::format("'{}' must be a number {}", a_path, range);
				return false;
			}
			a_out = a_value.get<double>();
			return true;
		}

		bool ReadInteger(const json& a_value, const std::string& a_path, long a_min, long a_max, long& a_out, std::string& a_error)
		{
			if (!a_value.is_number_integer() || a_value.get<long long>() < a_min || a_value.get<long long>() > a_max) {
				a_error = std::format("'{}' must be an integer {}..{}", a_path, a_min, a_max);
				return false;
			}
			a_out = static_cast<long>(a_value.get<long long>());
			return true;
		}

		bool ReadVec3(const json& a_value, const std::string& a_path, double a_limit, Vec3& a_out, std::string& a_error)
		{
			if (!a_value.is_array() || a_value.size() != 3) {
				a_error = std::format("'{}' must be an array of three numbers within +-{}", a_path, a_limit);
				return false;
			}
			double components[3]{};
			for (std::size_t i = 0; i < 3; ++i) {
				if (!ReadNumber(a_value[i], std::format("{}[{}]", a_path, i), -a_limit, a_limit, components[i], a_error))
					return false;
			}
			a_out = Vec3{ components[0], components[1], components[2] };
			return true;
		}

		bool ReadHand(const json& a_value, const std::string& a_path, HandPlacement& a_out, std::string& a_error)
		{
			if (a_value.is_string()) {
				if (a_value.get<std::string>() != "ready") {
					a_error = std::format("'{}' must be \"ready\" or an object", a_path);
					return false;
				}
				a_out.kind = HandPlacement::Kind::kReady;
				return true;
			}
			if (!a_value.is_object()) {
				a_error = std::format("'{}' must be \"ready\" or an object", a_path);
				return false;
			}
			const bool hasNode = a_value.contains("node");
			const bool hasWorld = a_value.contains("world");
			if (hasNode == hasWorld) {
				a_error = std::format("'{}' needs exactly one of 'node' or 'world'", a_path);
				return false;
			}
			if (a_value.contains("pitch") || a_value.contains("yaw")) {
				HandAim aim = kReadyAim;
				if (a_value.contains("pitch") && !ReadNumber(a_value["pitch"], a_path + ".pitch", -kHandAimLimitDeg, kHandAimLimitDeg, aim.pitchDeg, a_error))
					return false;
				if (a_value.contains("yaw") && !ReadNumber(a_value["yaw"], a_path + ".yaw", -kHandAimLimitDeg, kHandAimLimitDeg, aim.yawDeg, a_error))
					return false;
				a_out.aim = aim;
			}
			if (hasWorld) {
				a_out.kind = HandPlacement::Kind::kWorld;
				return ReadVec3(a_value["world"], a_path + ".world", kWorldLimit, a_out.world, a_error);
			}
			if (!a_value["node"].is_string() || a_value["node"].get<std::string>().empty() || a_value["node"].get<std::string>().size() > ReachLogic::kNodeMaxLen) {
				a_error = std::format("'{}.node' must be a non-empty string of at most {} characters", a_path, ReachLogic::kNodeMaxLen);
				return false;
			}
			a_out.kind = HandPlacement::Kind::kNode;
			a_out.node = a_value["node"].get<std::string>();
			if (a_value.contains("root")) {
				const json& root = a_value["root"];
				if (!root.is_string() || (root.get<std::string>() != "player" && root.get<std::string>() != "firstPerson")) {
					a_error = std::format("'{}.root' must be \"player\" or \"firstPerson\"", a_path);
					return false;
				}
				a_out.root = root.get<std::string>();
			}
			if (a_value.contains("front") && !ReadNumber(a_value["front"], a_path + ".front", ReachLogic::kFrontMin, ReachLogic::kFrontMax, a_out.front, a_error))
				return false;
			if (a_value.contains("offset") && !ReadVec3(a_value["offset"], a_path + ".offset", ReachLogic::kOffsetLimit, a_out.offset, a_error))
				return false;
			return true;
		}

		Vec3 Lerp(const Vec3& a_a, const Vec3& a_b, double a_t)
		{
			return ReachLogic::Add(a_a, ReachLogic::Scale(ReachLogic::Sub(a_b, a_a), a_t));
		}

		json FrameAt(long a_tMs, int a_packet, const HeldPose& a_pose)
		{
			return ReachLogic::MakeFrame(a_tMs, a_packet,
				Oriented(Vec3{ 0.0, a_pose.eyeHeight, 0.0 }, a_pose.headPitchDeg),
				Oriented(a_pose.left, a_pose.leftAim.pitchDeg, a_pose.leftAim.yawDeg),
				Oriented(a_pose.right, a_pose.rightAim.pitchDeg, a_pose.rightAim.yawDeg));
		}

		HandAim LerpAim(const HandAim& a_a, const HandAim& a_b, double a_t)
		{
			return HandAim{ a_a.pitchDeg + (a_b.pitchDeg - a_a.pitchDeg) * a_t, a_a.yawDeg + (a_b.yawDeg - a_a.yawDeg) * a_t };
		}
	}

	std::optional<PoseRequest> ParsePose(const json& a_args, std::string& a_error)
	{
		if (!a_args.is_object()) {
			a_error = "arguments must be an object";
			return std::nullopt;
		}
		PoseRequest request;
		if (a_args.contains("hands") && !a_args["hands"].is_null()) {
			const json& hands = a_args["hands"];
			if (!hands.is_object()) {
				a_error = "'hands' must be an object {left?, right?}";
				return std::nullopt;
			}
			for (const auto& [key, value] : hands.items()) {
				if (key != "left" && key != "right") {
					a_error = std::format("'hands.{}' is not a hand (left|right)", key);
					return std::nullopt;
				}
				HandPlacement placement;
				if (!ReadHand(value, "hands." + key, placement, a_error))
					return std::nullopt;
				(key == "left" ? request.left : request.right) = placement;
			}
		}
		if (a_args.contains("head") && !a_args["head"].is_null()) {
			const json& head = a_args["head"];
			if (!head.is_object()) {
				a_error = "'head' must be an object {pitch?, eyeHeight?, cameraHeight?}";
				return std::nullopt;
			}
			for (const auto& [key, value] : head.items()) {
				if (key != "pitch" && key != "eyeHeight" && key != "cameraHeight") {
					a_error = std::format("'head.{}' is not a pose head field (pitch|eyeHeight|cameraHeight)", key);
					return std::nullopt;
				}
			}
			if (head.contains("pitch")) {
				double pitch = 0.0;
				if (!ReadNumber(head["pitch"], "head.pitch", -kHeadPitchLimitDeg, kHeadPitchLimitDeg, pitch, a_error))
					return std::nullopt;
				request.headPitch = pitch;
			}
			if (head.contains("eyeHeight")) {
				double eye = 0.0;
				if (!ReadNumber(head["eyeHeight"], "head.eyeHeight", kEyeHeightMin, kEyeHeightMax, eye, a_error))
					return std::nullopt;
				request.eyeHeight = eye;
			}
			if (head.contains("cameraHeight")) {
				double camera = 0.0;
				if (!ReadNumber(head["cameraHeight"], "head.cameraHeight", 1.0, kCameraHeightMax, camera, a_error))
					return std::nullopt;
				request.cameraHeight = camera;
			}
		}
		if (a_args.contains("moveMs") && !ReadInteger(a_args["moveMs"], "moveMs", 0, kMoveMsMax, request.moveMs, a_error))
			return std::nullopt;
		if (a_args.contains("holdMs") && !ReadInteger(a_args["holdMs"], "holdMs", ReachLogic::kHoldMsMin, ReachLogic::kHoldMsMax, request.holdMs, a_error))
			return std::nullopt;
		if (a_args.contains("toleranceUnits") && !ReadNumber(a_args["toleranceUnits"], "toleranceUnits", ReachLogic::kToleranceMin, ReachLogic::kToleranceMax, request.toleranceUnits, a_error))
			return std::nullopt;
		if (a_args.contains("corrections")) {
			long corrections = 0;
			if (!ReadInteger(a_args["corrections"], "corrections", 0, kCorrectionsMax, corrections, a_error))
				return std::nullopt;
			request.corrections = static_cast<int>(corrections);
		}
		return request;
	}

	Vec3 ReadyHand(bool a_right, double a_eyeHeight)
	{
		const double w = Radians(kHandYawDeg);
		const double x = a_right ? kReadySide : -kReadySide;
		const double z = -kReadyForward;
		return Vec3{ x * std::cos(w) + z * std::sin(w), a_eyeHeight - kReadyBelow, -x * std::sin(w) + z * std::cos(w) };
	}

	Pose Oriented(const Vec3& a_position, double a_pitchDeg, double a_yawDeg)
	{
		const double p = Radians(a_pitchDeg);
		const double w = Radians(a_yawDeg);
		const double cp = std::cos(p), sp = std::sin(p), cw = std::cos(w), sw = std::sin(w);
		// yaw(Y) * pitch(X)
		return Pose{
			cw, sw * sp, sw * cp, a_position.x,
			0.0, cp, -sp, a_position.y,
			-sw, cw * sp, cw * cp, a_position.z
		};
	}

	double EyeHeightFor(double a_cameraUnits, double a_roomLiftUnits, double a_unitsPerMeter)
	{
		if (!(a_unitsPerMeter > kEpsilon))
			return kEyeHeightMin;
		return std::clamp((a_cameraUnits - a_roomLiftUnits) / a_unitsPerMeter, kEyeHeightMin, kEyeHeightMax);
	}

	Vec3 GameAxes(const Vec3& a_tracking)
	{
		return Vec3{ a_tracking.x, -a_tracking.z, a_tracking.y };
	}

	Vec3 TrackingAxes(const Vec3& a_game)
	{
		return Vec3{ a_game.x, a_game.z, -a_game.y };
	}

	double FitTurn(const Vec3& a_hmdTracking, const Vec3& a_hmdWorld, const std::vector<HandSample>& a_hands)
	{
		double cross = 0.0;
		double dot = 0.0;
		for (const auto& hand : a_hands) {
			const Vec3 t = GameAxes(ReachLogic::Sub(hand.tracking, a_hmdTracking));
			const Vec3 w = ReachLogic::Sub(hand.wandWorld, a_hmdWorld);
			cross += t.x * w.y - t.y * w.x;
			dot += t.x * w.x + t.y * w.y;
		}
		if (std::abs(cross) < kEpsilon && std::abs(dot) < kEpsilon)
			return 0.0;
		return std::atan2(cross, dot);
	}

	Vec3 TrackingDelta(double a_theta, const Vec3& a_worldDelta, double a_unitsPerMeter)
	{
		const double c = std::cos(-a_theta), s = std::sin(-a_theta);
		const Vec3   d = ReachLogic::Scale(a_worldDelta, 1.0 / a_unitsPerMeter);
		return TrackingAxes(Vec3{ c * d.x - s * d.y, s * d.x + c * d.y, d.z });
	}

	Vec3 TrackingFor(double a_theta, const Vec3& a_hmdTracking, const Vec3& a_hmdWorld, const Vec3& a_world, double a_unitsPerMeter)
	{
		return ReachLogic::Add(a_hmdTracking, TrackingDelta(a_theta, ReachLogic::Sub(a_world, a_hmdWorld), a_unitsPerMeter));
	}

	Vec3 WorldFor(double a_theta, const Vec3& a_hmdTracking, const Vec3& a_hmdWorld, const Vec3& a_tracking, double a_unitsPerMeter)
	{
		const Vec3   g = ReachLogic::Scale(GameAxes(ReachLogic::Sub(a_tracking, a_hmdTracking)), a_unitsPerMeter);
		const double c = std::cos(a_theta), s = std::sin(a_theta);
		return ReachLogic::Add(a_hmdWorld, Vec3{ c * g.x - s * g.y, s * g.x + c * g.y, g.z });
	}

	json MoveFrames(const HeldPose& a_from, const HeldPose& a_to, long a_moveMs, long a_holdMs)
	{
		json frames = json::array();
		int  packet = 1;
		long tMs = 0;
		if (a_moveMs > 0) {
			const long steps = std::max(1L, a_moveMs / kMoveStepMs);
			for (long k = 0; k <= steps; ++k) {
				const double t = EaseInOut(static_cast<double>(k) / static_cast<double>(steps));
				HeldPose     pose = a_to;
				pose.headPitchDeg = a_from.headPitchDeg + (a_to.headPitchDeg - a_from.headPitchDeg) * t;
				pose.left = Lerp(a_from.left, a_to.left, t);
				pose.right = Lerp(a_from.right, a_to.right, t);
				pose.leftAim = LerpAim(a_from.leftAim, a_to.leftAim, t);
				pose.rightAim = LerpAim(a_from.rightAim, a_to.rightAim, t);
				tMs = k * a_moveMs / steps;
				frames.push_back(FrameAt(tMs, packet++, pose));
			}
		} else {
			frames.push_back(FrameAt(0, packet++, a_to));
		}
		const long holdEnd = tMs + std::max(a_holdMs, kHoldStepMs);
		for (long t = tMs + kHoldStepMs; t <= holdEnd; t += kHoldStepMs)
			frames.push_back(FrameAt(t, packet++, a_to));
		return frames;
	}
}
