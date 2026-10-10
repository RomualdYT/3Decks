/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_settings.h Lecture et remplacement recuperable des reglages SD. */
#pragma once

#include "app.h"

/** Charge les valeurs par defaut puis le fichier present sur la carte SD. */
void app_settings_load(Settings *settings);

/** Ecrit et synchronise un fichier temporaire puis remplace les reglages. */
bool app_settings_save(const Settings *settings);

/** Operation et code de la derniere erreur, sans donnees d'appairage. */
const char *app_settings_save_error(void);

/** Utilise l'adresse fournie par 3dslink lorsqu'elle est disponible. */
bool app_settings_detect_netload_host(Settings *settings);
