# The displayed version of a Fallout build of the ArthurHub fork (DEVBENCH_VERSION_STRING: `ping`, the load log).
#
# The fork releases under its own `fo4-vX.Y.Z` tags, while VERSION / MAJOR / MINOR / PATCH stay upstream's: they
# make DEVBENCH_BUILD_NUMBER, which mods compare against before calling late API slots, so only the string follows
# the fork. See docs/plans/python-client/issues/17-fork-release.md.

set(DEVBENCH_VERSION "" CACHE STRING
	"Displayed devbench version (the release passes the fo4-v tag's X.Y.Z). Empty: derived from git describe.")

# Turns `git describe --dirty --tags --long --match "fo4-v*"` output into setuptools-scm's default version
# (guess-next-dev + node-and-date), so `ping` and `pip show devbench-client` print the same string on one commit:
# on a clean tag `1.0.0`; past it `1.0.1.dev5+gabc1234`; uncommitted changes add `.dYYYYMMDD` (UTC, today).
# Sets <out> to "" when the text is not that shape.
function(devbench_version_from_describe out describe)
	set(result "")
	if(describe MATCHES "^fo4-v([0-9]+)\\.([0-9]+)\\.([0-9]+)-([0-9]+)-(g[0-9a-f]+)(-dirty)?$")
		set(major ${CMAKE_MATCH_1})
		set(minor ${CMAKE_MATCH_2})
		set(patch ${CMAKE_MATCH_3})
		set(distance ${CMAKE_MATCH_4})
		set(node ${CMAKE_MATCH_5})
		set(dirty "${CMAKE_MATCH_6}")
		if(distance EQUAL 0 AND dirty STREQUAL "")
			set(result "${major}.${minor}.${patch}")
		else()
			math(EXPR next "${patch} + 1")
			set(result "${major}.${minor}.${next}.dev${distance}+${node}")
			if(NOT dirty STREQUAL "")
				string(TIMESTAMP today "%Y%m%d" UTC)
				string(APPEND result ".d${today}")
			endif()
		endif()
	endif()
	set(${out} "${result}" PARENT_SCOPE)
endfunction()

# Sets <out> to the displayed version: DEVBENCH_VERSION when given, else the fork's git describe, else <fallback>
# (no git, no fo4-v tag, a source archive). Runs at configure time, so the string goes stale until CMake reconfigures.
function(devbench_display_version out fallback)
	if(NOT DEVBENCH_VERSION STREQUAL "")
		set(${out} "${DEVBENCH_VERSION}" PARENT_SCOPE)
		return()
	endif()
	set(result "")
	find_package(Git QUIET)
	if(GIT_FOUND)
		execute_process(
			COMMAND "${GIT_EXECUTABLE}" describe --dirty --tags --long --match "fo4-v*"
			WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
			OUTPUT_VARIABLE describe
			OUTPUT_STRIP_TRAILING_WHITESPACE
			ERROR_QUIET
			RESULT_VARIABLE rc)
		if(rc EQUAL 0)
			devbench_version_from_describe(result "${describe}")
		endif()
	endif()
	if(result STREQUAL "")
		set(result "${fallback}")
	endif()
	set(${out} "${result}" PARENT_SCOPE)
endfunction()
