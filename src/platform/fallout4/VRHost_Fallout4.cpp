#include "core/VRHost.h"

#include "core/ToolRegistry.h"

#include "openvr.h"

#include <atomic>

// Fallout 4 VR's side of the VR input seam (core/VRHost.h).
namespace dvb::vrhost
{
	namespace
	{
		using GetGenericInterface_t = void* (*)(const char*, vr::EVRInitError*);

		/**
		 * Asks the loaded openvr_api.dll for an interface by version string. GetProcAddress
		 * returns the real export, so this gets the runtime's own object even when another mod
		 * (FO4VRTools) patched the game's import to hand the game a proxy; the proxy forwards to
		 * this object, so hooks on it still see the game's calls. Null until the game has
		 * initialized OpenVR.
		 */
		void* LookUp(const char* a_version)
		{
			const HMODULE module = GetModuleHandleW(L"openvr_api.dll");
			if (!module)
				return nullptr;
			const auto getInterface = reinterpret_cast<GetGenericInterface_t>(GetProcAddress(module, "VR_GetGenericInterface"));
			if (!getInterface)
				return nullptr;
			vr::EVRInitError error = vr::VRInitError_None;
			void*            object = getInterface(a_version, &error);
			return error == vr::VRInitError_None ? object : nullptr;
		}

		/**
		 * Caches an interface once found; the runtime returns the same object for the life of
		 * the process.
		 */
		template <class T>
		T* Cached(std::atomic<T*>& a_cache, const char* a_version)
		{
			if (auto* cached = a_cache.load(std::memory_order_acquire))
				return cached;
			auto* found = static_cast<T*>(LookUp(a_version));
			if (found)
				a_cache.store(found, std::memory_order_release);
			return found;
		}

		std::atomic<vr::IVRSystem*>     g_system{ nullptr };
		std::atomic<vr::IVRCompositor*> g_compositor{ nullptr };
	}

	vr::IVRSystem* System()
	{
		return Cached(g_system, vr::IVRSystem_Version);
	}

	vr::IVRCompositor* Compositor()
	{
		return Cached(g_compositor, vr::IVRCompositor_Version);
	}

	/**
	 * No-op: no Fallout 4 VR structure holding a per-hand OpenVR device index is known, so
	 * the core's role hooks (GetTrackedDeviceIndexForControllerRole and its inverse) are what
	 * map devices to hands during a Sequence. Whether the game also caches the indices
	 * somewhere is unverified. Returns the requested indices unchanged.
	 */
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
