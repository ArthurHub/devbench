#include "core/PoseControl.h"

#include "core/MainThread.h"
#include "core/PoseLogic.h"
#include "core/VRHost.h"
#include "core/VRInput.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <format>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

namespace dvb::PoseControl
{
	namespace
	{
		namespace PL = dvb::PoseLogic;
		namespace RL = dvb::ReachLogic;

		/// The game applies an injected pose a frame or two after its sequence frame.
		constexpr long kSettleMs = 150;
		constexpr long kSequenceTailMs = 300;

		/// The pose this module holds, with the sequence that holds it.
		struct Held
		{
			std::string  owner;
			std::string  token;
			PL::HeldPose pose;
			double       unitsPerMeter{ 70.0 };
		};

		std::mutex          g_mutex;
		std::optional<Held> g_held;

		json Vec3Json(const RL::Vec3& a_v)
		{
			return json::array({ a_v.x, a_v.y, a_v.z });
		}

		RL::Vec3 Vec3From(const json& a_v)
		{
			return RL::Vec3{ a_v.at(0).get<double>(), a_v.at(1).get<double>(), a_v.at(2).get<double>() };
		}

		/**
		 * Whether the held sequence still runs under its own token: it ends when its hold runs
		 * out, at a load, or when stop or another sequence (even this owner's) takes the devices.
		 * A load needs no reset of g_held: the stale hold fails this check.
		 */
		bool HeldIsActive(const Held& a_held)
		{
			return !a_held.token.empty() && dvb::VRSequenceHeldBy(a_held.owner, a_held.token);
		}

		/**
		 * Plays frames as the held sequence: replaces it in place while it is active, so the
		 * devices never fall back to the physical ones between moves.
		 */
		void Play(Held& a_held, const json& a_frames, bool a_replace, const ToolContext& a_ctx)
		{
			json args{
				{ "action", "sequence" },
				{ "owner", a_held.owner },
				{ "frames", a_frames },
				{ "tailMs", kSequenceTailMs },
			};
			if (a_replace && !a_held.token.empty())
				args["controlToken"] = a_held.token;
			const json result = dvb::HandleVRInput(args, a_ctx);
			if (result.contains("controlToken") && result["controlToken"].is_string())
				a_held.token = result["controlToken"].get<std::string>();
		}

		/**
		 * Eases the held pose to a_to over a_moveMs, then holds it for a_holdMs; returns once the
		 * game has applied the end of the move.
		 */
		void Move(Held& a_held, const PL::HeldPose& a_to, long a_moveMs, long a_holdMs, const ToolContext& a_ctx)
		{
			Play(a_held, PL::MoveFrames(a_held.pose, a_to, a_moveMs, a_holdMs), true, a_ctx);
			a_held.pose = a_to;
			std::this_thread::sleep_for(std::chrono::milliseconds(a_moveMs + kSettleMs));
		}

		/// The head and both Wands in the world, read in one main-thread task.
		struct Reading
		{
			RL::Vec3 hmd;
			RL::Vec3 left;
			RL::Vec3 right;
		};

		Reading Read()
		{
			const json result = dvb::MainThread::RunAndWait([]() -> json {
				return json{
					{ "hmd", Vec3Json(vrhost::HmdWorld()) },
					{ "left", Vec3Json(vrhost::ReachHandWorld(false)) },
					{ "right", Vec3Json(vrhost::ReachHandWorld(true)) },
				};
			});
			return Reading{ Vec3From(result.at("hmd")), Vec3From(result.at("left")), Vec3From(result.at("right")) };
		}

		/// The injected head in tracking space: at the eyes, straight above the origin.
		RL::Vec3 HmdTracking(const Held& a_held)
		{
			return RL::Vec3{ 0.0, a_held.pose.eyeHeight, 0.0 };
		}

		/// The turn between tracking space and the world, fitted from where both held Wands landed.
		double Turn(const Held& a_held, const Reading& a_reading)
		{
			return PL::FitTurn(HmdTracking(a_held), a_reading.hmd,
				{ PL::HandSample{ a_held.pose.left, a_reading.left }, PL::HandSample{ a_held.pose.right, a_reading.right } });
		}

		/// A node or world placement as a world point, read on the main thread.
		RL::Vec3 WorldTarget(const PL::HandPlacement& a_placement)
		{
			if (a_placement.kind == PL::HandPlacement::Kind::kWorld)
				return a_placement.world;
			const json     result = dvb::MainThread::RunAndWait([a_placement]() -> json {
				const double yaw = vrhost::PlayerYaw();
				return json{ { "node", Vec3Json(vrhost::ReachNodeWorld(a_placement.node, a_placement.root)) }, { "yaw", yaw } };
			});
			const double   yaw = result.at("yaw").get<double>();
			const RL::Vec3 facing{ std::sin(yaw), std::cos(yaw), 0.0 };
			return RL::Add(Vec3From(result.at("node")), RL::Add(RL::Scale(facing, a_placement.front), a_placement.offset));
		}

		/// Where a hand will be, for lookAt: its target in this call, else where its Wand is now.
		RL::Vec3 HandLookPoint(const std::optional<PL::HandPlacement>& a_placement, bool a_right, const Held& a_held, const Reading& a_reading, double a_theta)
		{
			if (!a_placement)
				return a_right ? a_reading.right : a_reading.left;
			if (a_placement->kind == PL::HandPlacement::Kind::kReady)
				return PL::WorldFor(a_theta, HmdTracking(a_held), a_reading.hmd, PL::ReadyHand(a_right, a_held.pose.eyeHeight), a_held.unitsPerMeter);
			return WorldTarget(*a_placement);
		}

		/**
		 * The world point head.lookAt aims at, read once before anything moves: a hand's target in
		 * this call (or its Wand when the call leaves it), the midpoint of both, a node, or a point.
		 */
		RL::Vec3 LookPoint(const PL::HeadLook& a_look, const PL::PoseRequest& a_request, const Held& a_held, const Reading& a_reading, double a_theta)
		{
			switch (a_look.kind) {
			case PL::HeadLook::Kind::kLeft:
				return HandLookPoint(a_request.left, false, a_held, a_reading, a_theta);
			case PL::HeadLook::Kind::kRight:
				return HandLookPoint(a_request.right, true, a_held, a_reading, a_theta);
			case PL::HeadLook::Kind::kHands:
				return RL::Scale(RL::Add(HandLookPoint(a_request.left, false, a_held, a_reading, a_theta), HandLookPoint(a_request.right, true, a_held, a_reading, a_theta)), 0.5);
			case PL::HeadLook::Kind::kWorld:
				return a_look.world;
			case PL::HeadLook::Kind::kNode:
			default:
				return Vec3From(dvb::MainThread::RunAndWait([a_look]() -> json {
					return Vec3Json(vrhost::ReachNodeWorld(a_look.node, a_look.root));
				}));
			}
		}

		/**
		 * Starts a fresh hold in the ready pose, at the eye height that stands the body naturally.
		 * A non-empty a_replaceToken is the live hold's: the fresh one replaces it in place.
		 */
		Held StartHold(const PL::PoseRequest& a_request, const std::string& a_owner, const std::string& a_replaceToken, const ToolContext& a_ctx)
		{
			const json stanceJson = dvb::MainThread::RunAndWait([]() -> json {
				const auto stance = vrhost::ReadPoseStance();
				return json{ { "unitsPerMeter", stance.unitsPerMeter }, { "roomLift", stance.roomLiftUnits }, { "camera", stance.cameraUnits } };
			});
			Held       held;
			held.owner = a_owner;
			held.token = a_replaceToken;
			held.unitsPerMeter = stanceJson.at("unitsPerMeter").get<double>();
			const double camera = a_request.cameraHeight.value_or(stanceJson.at("camera").get<double>());
			const double eye = a_request.eyeHeight.value_or(PL::EyeHeightFor(camera, stanceJson.at("roomLift").get<double>(), held.unitsPerMeter));
			held.pose = PL::HeldPose{ eye, PL::kReadyHeadPitchDeg, PL::ReadyHand(false, eye), PL::ReadyHand(true, eye) };
			Play(held, PL::MoveFrames(held.pose, held.pose, 0, a_request.holdMs), !a_replaceToken.empty(), a_ctx);
			std::this_thread::sleep_for(std::chrono::milliseconds(kSettleMs));
			return held;
		}
	}

	json Place(const json& a_args, const std::string& a_owner, const ToolContext& a_ctx)
	{
		std::string error;
		const auto  parsed = PL::ParsePose(a_args, error);
		if (!parsed)
			throw ToolError(400, std::format("pose: {}", error));
		const PL::PoseRequest& request = *parsed;

		const json status = dvb::HandleVRInput(json{ { "action", "status" } }, a_ctx);
		if (!status.value("ready", false))
			throw ToolError(503, "OpenVR is not ready");

		std::lock_guard lock(g_mutex);
		const auto      started = std::chrono::steady_clock::now();
		const bool      continuing = g_held && g_held->owner == a_owner && HeldIsActive(*g_held);
		if (!continuing) {
			g_held.reset();
			// Another sequence holds the devices, this owner's own included: pose has no token to replace it.
			const json current = dvb::HandleVRInput(json{ { "action", "status" } }, a_ctx);
			if (current.value("active", false))
				throw ToolError(409, std::format("a sequence by '{}' holds the devices; stop it first", current.value("owner", std::string{})));
		}
		const bool fresh = !continuing || request.eyeHeight || request.cameraHeight;
		if (fresh)
			g_held = StartHold(request, a_owner, continuing ? g_held->token : std::string{}, a_ctx);
		Held& held = *g_held;

		// lookAt resolves once into head angles; its point is read before anything moves.
		PL::HeldPose head = held.pose;
		if (request.headPitch)
			head.headPitchDeg = *request.headPitch;
		if (request.headYaw)
			head.headYawDeg = *request.headYaw;
		json look;
		if (request.lookAt) {
			const Reading  before = Read();
			const double   thetaBefore = Turn(held, before);
			const RL::Vec3 point = LookPoint(*request.lookAt, request, held, before, thetaBefore);
			const auto     angles = PL::LookAngles(thetaBefore, before.hmd, point, held.unitsPerMeter);
			if (!angles)
				throw ToolError(400, "pose: 'head.lookAt' target is at the eyes");
			head.headPitchDeg = angles->pitchDeg;
			head.headYawDeg = angles->yawDeg;
			look = json{ { "target", Vec3Json(point) }, { "clamped", angles->clamped } };
		}

		// The head first: a body mod leans and turns the body with it, so node targets are read in the turned pose.
		if (std::abs(head.headPitchDeg - held.pose.headPitchDeg) > 1e-6 || std::abs(head.headYawDeg - held.pose.headYawDeg) > 1e-6)
			Move(held, head, request.moveMs, request.holdMs, a_ctx);

		// Ready hands need no reading; node and world targets go through the fitted turn.
		PL::HeldPose            to = held.pose;
		std::optional<RL::Vec3> targetLeft;
		std::optional<RL::Vec3> targetRight;
		double                  theta = 0.0;
		const bool              mapped = (request.left && request.left->kind != PL::HandPlacement::Kind::kReady) || (request.right && request.right->kind != PL::HandPlacement::Kind::kReady);
		if (mapped) {
			const Reading reading = Read();
			theta = Turn(held, reading);
			const auto place = [&](const std::optional<PL::HandPlacement>& a_placement, RL::Vec3& a_tracking, std::optional<RL::Vec3>& a_target) {
				if (!a_placement || a_placement->kind == PL::HandPlacement::Kind::kReady)
					return;
				a_target = WorldTarget(*a_placement);
				a_tracking = PL::TrackingFor(theta, HmdTracking(held), reading.hmd, *a_target, held.unitsPerMeter);
			};
			place(request.left, to.left, targetLeft);
			place(request.right, to.right, targetRight);
		}
		if (request.left && request.left->kind == PL::HandPlacement::Kind::kReady)
			to.left = PL::ReadyHand(false, held.pose.eyeHeight);
		if (request.right && request.right->kind == PL::HandPlacement::Kind::kReady)
			to.right = PL::ReadyHand(true, held.pose.eyeHeight);
		// a placed hand points the way it asks, else the ready way; the Wand sits at the controller either way
		if (request.left)
			to.leftAim = request.left->aim.value_or(PL::kReadyAim);
		if (request.right)
			to.rightAim = request.right->aim.value_or(PL::kReadyAim);
		Move(held, to, request.moveMs, request.holdMs, a_ctx);

		// A hand lookAt aims again at where the Wands landed: the first turn moved the body, and a node-placed hand with it.
		if (request.lookAt && request.lookAt->kind != PL::HeadLook::Kind::kNode && request.lookAt->kind != PL::HeadLook::Kind::kWorld) {
			const Reading  landed = Read();
			const RL::Vec3 point = request.lookAt->kind == PL::HeadLook::Kind::kLeft  ? landed.left :
			                       request.lookAt->kind == PL::HeadLook::Kind::kRight ? landed.right :
			                                                                            RL::Scale(RL::Add(landed.left, landed.right), 0.5);
			const auto     angles = PL::LookAngles(Turn(held, landed), landed.hmd, point, held.unitsPerMeter);
			const bool     off = angles && (std::abs(angles->pitchDeg - held.pose.headPitchDeg) > PL::kLookAtReaimDeg || std::abs(angles->yawDeg - held.pose.headYawDeg) > PL::kLookAtReaimDeg);
			if (off) {
				PL::HeldPose again = held.pose;
				again.headPitchDeg = angles->pitchDeg;
				again.headYawDeg = angles->yawDeg;
				Move(held, again, request.moveMs, request.holdMs, a_ctx);
				look["target"] = Vec3Json(point);
				look["clamped"] = angles->clamped;
			}
			look["reaimed"] = off;
		}

		// Correct toward the world targets while a Wand misses: a body mod can move the target with the arm.
		int     corrections = 0;
		Reading reading = Read();
		for (; mapped && corrections < request.corrections; ++corrections) {
			double worst = 0.0;
			if (targetLeft)
				worst = std::max(worst, RL::Distance(*targetLeft, reading.left));
			if (targetRight)
				worst = std::max(worst, RL::Distance(*targetRight, reading.right));
			if (worst <= request.toleranceUnits)
				break;
			PL::HeldPose next = held.pose;
			if (targetLeft)
				next.left = RL::Add(next.left, PL::TrackingDelta(theta, RL::Sub(*targetLeft, reading.left), held.unitsPerMeter));
			if (targetRight)
				next.right = RL::Add(next.right, PL::TrackingDelta(theta, RL::Sub(*targetRight, reading.right), held.unitsPerMeter));
			Move(held, next, request.moveMs / 2, request.holdMs, a_ctx);
			reading = Read();
		}

		const auto handJson = [&](const RL::Vec3& a_tracking, const PL::HandAim& a_aim, const RL::Vec3& a_wand, const std::optional<RL::Vec3>& a_target) {
			json hand{ { "tracking", Vec3Json(a_tracking) }, { "pitch", a_aim.pitchDeg }, { "yaw", a_aim.yawDeg }, { "wand", Vec3Json(a_wand) } };
			if (a_target) {
				hand["target"] = Vec3Json(*a_target);
				hand["error"] = RL::Distance(*a_target, a_wand);
			}
			return hand;
		};
		json result{
			{ "owner", held.owner },
			{ "controlToken", held.token },
			{ "fresh", fresh },
			{ "eyeHeight", held.pose.eyeHeight },
			{ "headPitch", held.pose.headPitchDeg },
			{ "headYaw", held.pose.headYawDeg },
			{ "corrections", corrections },
			{ "hands", json{ { "left", handJson(held.pose.left, held.pose.leftAim, reading.left, targetLeft) }, { "right", handJson(held.pose.right, held.pose.rightAim, reading.right, targetRight) } } },
			{ "elapsedMs", std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count() },
		};
		// only a node or world target fits the turn
		if (mapped)
			result["turnDeg"] = theta * 180.0 / 3.14159265358979323846;
		if (!look.is_null())
			result["lookAt"] = look;
		return result;
	}
}
