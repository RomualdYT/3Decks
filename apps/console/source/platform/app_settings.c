/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_settings.c Persistance robuste et lisible des reglages console. */

#include "app_settings.h"

#include <3ds.h>
#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "i18n.h"

#define SETTINGS_PATH "sdmc:/3ds/deck3ds/settings.cfg"
#define SETTINGS_TMP_PATH "sdmc:/3ds/deck3ds/settings.tmp"
#define SETTINGS_BACKUP_PATH "sdmc:/3ds/deck3ds/settings.bak"

static char save_error[64];

const char *app_settings_save_error(void)
{
	return save_error;
}

static bool save_failed(const char *operation)
{
	/* libctru preserves unmapped FS Result values in errno. Keep all bits. */
	snprintf(save_error, sizeof(save_error), "%s: 0x%08X", operation,
	         (unsigned int)errno);
	return false;
}

static bool ensure_directory(const char *path, const char *operation)
{
	if (mkdir(path, 0777) == 0) return true;
	if (errno == EEXIST) {
		struct stat info;
		if (stat(path, &info) == 0) {
			if (S_ISDIR(info.st_mode)) return true;
			errno = ENOTDIR;
		}
	}
	return save_failed(operation);
}

static bool replace_settings(void)
{
#ifdef __3DS__
	/* Call FS directly: libctru's file-to-directory fallback masks the
	 * original RenameFile error with ENOENT. Keep a recoverable old copy. */
	FS_Archive archive;
	Result result = FSUSER_OpenArchive(&archive, ARCHIVE_SDMC,
	                                  fsMakePath(PATH_EMPTY, ""));
	if (R_FAILED(result)) {
		errno = (int)result;
		return save_failed("archive");
	}
	const FS_Path temporary = fsMakePath(PATH_ASCII, "/3ds/deck3ds/settings.tmp");
	const FS_Path destination = fsMakePath(PATH_ASCII, "/3ds/deck3ds/settings.cfg");
	const FS_Path backup = fsMakePath(PATH_ASCII, "/3ds/deck3ds/settings.bak");
	bool moved_old = false;
	struct stat info;
	if (stat(SETTINGS_PATH, &info) == 0) {
		/* A valid primary still exists if removing a stale backup fails. */
		if (remove(SETTINGS_BACKUP_PATH) != 0 && errno != ENOENT) {
			save_failed("backup remove");
			FSUSER_CloseArchive(archive);
			return false;
		}
		result = FSUSER_RenameFile(archive, destination, archive, backup);
		moved_old = R_SUCCEEDED(result);
	} else if (errno == ENOENT) {
		result = 0;
	} else {
		save_failed("stat");
		FSUSER_CloseArchive(archive);
		return false;
	}
	if (R_SUCCEEDED(result)) {
		result = FSUSER_RenameFile(archive, temporary, archive, destination);
	}
	if (R_FAILED(result)) {
		errno = (int)result;
		save_failed("rename FS");
		if (moved_old) FSUSER_RenameFile(archive, backup, archive, destination);
	}
	FSUSER_CloseArchive(archive);
	if (R_FAILED(result)) return false;
	if (moved_old) remove(SETTINGS_BACKUP_PATH);
	return true;
#else
	if (rename(SETTINGS_TMP_PATH, SETTINGS_PATH) == 0) return true;
	return save_failed("rename");
#endif
}

static void trim(char *text)
{
	size_t start = 0;
	while (text[start] == ' ' || text[start] == '\t') {
		start++;
	}

	size_t end = strlen(text);
	while (end > start) {
		const char value = text[end - 1];
		if (value == ' ' || value == '\t' || value == '\r' || value == '\n') {
			end--;
		} else {
			break;
		}
	}

	const size_t length = end - start;
	if (start > 0) {
		memmove(text, text + start, length);
	}
	text[length] = '\0';
}

void app_settings_load(Settings *settings)
{
	settings->agent_name[0] = '\0';
	settings->host[0] = '\0';
	settings->port = 38123;
	settings->token[0] = '\0';
	settings->sound = true;
	settings->language = (int)LANG_EN;
	settings->dim_delay = 45;
	settings->stereo = true;
	settings->companion = 1;
	settings->configured = false;

	FILE *file = fopen(SETTINGS_PATH, "r");
	if (file == NULL && errno == ENOENT) {
		/* Recover a previous save interrupted between the two SD renames. */
		file = fopen(SETTINGS_BACKUP_PATH, "r");
	}
	if (file == NULL) {
		return;
	}

	char line[192];
	while (fgets(line, sizeof(line), file) != NULL) {
		if (line[0] == '#' || line[0] == ';') {
			continue;
		}
		char *separator = strchr(line, '=');
		if (separator == NULL) {
			continue;
		}
		*separator = '\0';
		char *key = line;
		char *value = separator + 1;
		trim(key);
		trim(value);

		if (strcmp(key, "agent_name") == 0) {
			snprintf(settings->agent_name, sizeof(settings->agent_name), "%s",
			         value);
		} else if (strcmp(key, "host") == 0) {
			snprintf(settings->host, sizeof(settings->host), "%s", value);
		} else if (strcmp(key, "port") == 0) {
			const int port = atoi(value);
			if (port > 0 && port < 65536) {
				settings->port = port;
			}
		} else if (strcmp(key, "token") == 0) {
			snprintf(settings->token, sizeof(settings->token), "%s", value);
		} else if (strcmp(key, "sound") == 0) {
			settings->sound = strcmp(value, "0") != 0 &&
			                  strcmp(value, "false") != 0 &&
			                  strcmp(value, "off") != 0;
		} else if (strcmp(key, "language") == 0) {
			settings->language = strcmp(value, "fr") == 0 ? (int)LANG_FR
			                                                : (int)LANG_EN;
		} else if (strcmp(key, "dim_delay") == 0) {
			const int delay = atoi(value);
			if (delay >= 0 && delay <= 600) {
				settings->dim_delay = delay;
			}
		} else if (strcmp(key, "stereo") == 0) {
			settings->stereo = strcmp(value, "0") != 0 &&
			                   strcmp(value, "false") != 0 &&
			                   strcmp(value, "off") != 0;
		} else if (strcmp(key, "companion") == 0) {
			if (strcmp(value, "0") == 0 || strcmp(value, "1") == 0 || strcmp(value, "2") == 0) {
				settings->companion = value[0] - '0';
			}
		} else if (strcmp(key, "configured") == 0) {
			settings->configured = strcmp(value, "0") != 0 &&
			                       strcmp(value, "false") != 0;
		}
	}
	fclose(file);
}

bool app_settings_detect_netload_host(Settings *settings)
{
	if (__3dslink_host.s_addr == 0) {
		return false;
	}
	const char *text = inet_ntoa(__3dslink_host);
	if (text == NULL || text[0] == '\0') {
		return false;
	}
	snprintf(settings->host, sizeof(settings->host), "%s", text);
	return true;
}

bool app_settings_save(const Settings *settings)
{
	save_error[0] = '\0';
	if (!ensure_directory("sdmc:/3ds", "mkdir 3ds") ||
	    !ensure_directory("sdmc:/3ds/deck3ds", "mkdir deck3ds")) {
		return false;
	}

	FILE *file = fopen(SETTINGS_TMP_PATH, "w");
	if (file == NULL) {
		return save_failed("open");
	}

	const int written = fprintf(file,
	        "# Reglages 3Decks\n"
	        "# Fichier ecrit par l'application. Modifiable a la main.\n\n"
	        "# Nom affiche par la decouverte automatique.\n"
	        "agent_name = %s\n\n"
	        "# Adresse de l'ordinateur qui execute l'agent.\n"
	        "host = %s\n"
	        "port = %d\n\n"
	        "# Jeton partage, si l'agent en exige un.\n"
	        "token = %s\n\n"
	        "# Langue de l'interface : en ou fr.\n"
	        "language = %s\n\n"
	        "# Retour au toucher : 1 ou 0.\n"
	        "sound = %d\n\n"
	        "# Assombrissement apres inactivite, en secondes. 0 pour jamais.\n"
	        "dim_delay = %d\n\n"
	        "# Relief 3D de l'ecran du haut : 1 ou 0.\n"
	        "# L'intensite suit le curseur 3D de la console.\n"
	        "stereo = %d\n\n"
	        "# Decky: 0 off, 1 discreet, 2 companion standby.\n"
	        "companion = %d\n\n"
	        "# Mis a 1 une fois la configuration initiale effectuee.\n"
	        "configured = 1\n",
	        settings->agent_name, settings->host, settings->port,
	        settings->token, settings->language == (int)LANG_FR ? "fr" : "en",
	        settings->sound ? 1 : 0, settings->dim_delay,
	        settings->stereo ? 1 : 0, settings->companion);

	bool write_ok = written >= 0;
	if (!write_ok) save_failed("write");
	if (write_ok && fflush(file) != 0) {
		save_failed("fflush");
		write_ok = false;
	}
	if (write_ok) {
		write_ok = fsync(fileno(file)) == 0;
		if (!write_ok) save_failed("fsync");
	}
	if (fclose(file) != 0) {
		if (write_ok) save_failed("close");
		write_ok = false;
	}
	if (!write_ok) {
		remove(SETTINGS_TMP_PATH);
		return false;
	}
	if (!replace_settings()) {
		remove(SETTINGS_TMP_PATH);
		return false;
	}
	return true;
}
