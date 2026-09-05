/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_settings.h Lecture et ecriture atomique des reglages SD. */
#pragma once

#include "app.h"

/** Charge les valeurs par defaut puis le fichier present sur la carte SD. */
void app_settings_load(Settings *settings);

/** Ecrit les reglages dans un fichier temporaire puis le remplace atomiquement. */
bool app_settings_save(const Settings *settings);

/** Utilise l'adresse fournie par 3dslink lorsqu'elle est disponible. */
bool app_settings_detect_netload_host(Settings *settings);
