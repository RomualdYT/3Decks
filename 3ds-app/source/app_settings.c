/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_settings.c Persistance robuste et lisible des reglages console. */

#include "app_settings.h"

#include <3ds.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "i18n.h"

#define SETTINGS_PATH "sdmc:/3ds/deck3ds/settings.cfg"
#define SETTINGS_TMP_PATH "sdmc:/3ds/deck3ds/settings.tmp"

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
	settings->configured = false;

	FILE *file = fopen(SETTINGS_PATH, "r");
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
	mkdir("sdmc:/3ds", 0777);
	mkdir("sdmc:/3ds/deck3ds", 0777);

	FILE *file = fopen(SETTINGS_TMP_PATH, "w");
	if (file == NULL) {
		return false;
	}

	fprintf(file,
	        "# Reglages Deck3DS\n"
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
	        "# Mis a 1 une fois la configuration initiale effectuee.\n"
	        "configured = 1\n",
	        settings->agent_name, settings->host, settings->port,
	        settings->token, settings->language == (int)LANG_FR ? "fr" : "en",
	        settings->sound ? 1 : 0, settings->dim_delay,
	        settings->stereo ? 1 : 0);

	bool write_ok = fflush(file) == 0;
	if (write_ok) {
		write_ok = fsync(fileno(file)) == 0;
	}
	if (fclose(file) != 0) {
		write_ok = false;
	}
	if (!write_ok) {
		remove(SETTINGS_TMP_PATH);
		return false;
	}
	if (rename(SETTINGS_TMP_PATH, SETTINGS_PATH) != 0) {
		remove(SETTINGS_TMP_PATH);
		return false;
	}
	return true;
}
