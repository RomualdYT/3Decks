#pragma once

#include <string.h>

/* Keep wire identifiers intact; translate only at the display boundary. */
static inline const char *platform_label(const char *platform)
{
	if (!platform || !*platform) return "3Decks";
	if (!strcmp(platform, "darwin") || !strcmp(platform, "macos")) return "macOS";
	if (!strcmp(platform, "win32") || !strcmp(platform, "windows")) return "Windows";
	if (!strcmp(platform, "linux")) return "Linux";
	return platform;
}
