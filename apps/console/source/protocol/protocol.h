/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file protocol.h
 * @brief Encodage et décodage des messages Deck3DS.
 *
 * Cette couche ne connaît ni les sockets ni le rendu : elle traduit du JSON
 * vers le modèle et inversement. Elle est donc testable indépendamment.
 */
#pragma once

#include <stdbool.h>

#include "model.h"

/** Version de protocole implémentée. */
#define PROTOCOL_VERSION 1

typedef enum {
	MSG_UNKNOWN = 0,
	MSG_HELLO_OK,
	MSG_HELLO_ERROR,
	MSG_CONFIG_SNAPSHOT,
	MSG_STATE_UPDATE,
	MSG_MEDIA_LYRICS,
	MSG_ACTION_RESULT,
	MSG_PONG,
} MessageKind;

/** Annonce UDP d'un agent détecté sur le réseau local. */
typedef struct {
	char name[64];
	char platform[24];
	int port;
	bool pairing_required;
} AgentAnnouncement;

/** Résultat du décodage d'un message entrant. */
typedef struct {
	MessageKind kind;

	/* MSG_ACTION_RESULT */
	int action_id;
	bool action_ok;
	char message[LEN_TEXT];
	/** Renseigné si l'agent demande une navigation (`page.open`). */
	char open_page[LEN_ID];
	/** Vrai si l'agent demande l'ouverture des réglages de la console. */
	bool open_settings;
	/** Vrai si l'agent demande l'ouverture du panneau de volumes. */
	bool open_modal;
	/** Vrai si l'agent demande le basculement en plein écran. */
	bool toggle_frame;

	/* MSG_HELLO_ERROR */
	char reason[LEN_TEXT];
	bool pairing_required;

	/* MSG_HELLO_OK, uniquement après consommation d'un code court. */
	char paired_token[LEN_PAIRING_TOKEN];

	/* MSG_PONG */
	int ping_id;

	/**
	 * Notification venant d'arriver, à annoncer.
	 * `has_notification` distingue l'absence d'une notification vide.
	 */
	bool has_notification;
	char notification_app[LEN_APP_NAME];
	char notification_title[LEN_TEXT];
	IconId notification_icon;
} IncomingMessage;

/**
 * Décode un message JSON.
 *
 * `config` et `state` sont mis à jour sur place pour les messages
 * correspondants. Retourne `false` si le message est illisible ; dans ce cas
 * ni `config` ni `state` ne sont modifiés de façon partielle observable.
 */
bool protocol_decode(const char *json, size_t length, IncomingMessage *out,
                     Config *config, PcState *state);

/** Décode une réponse de découverte locale. */
bool protocol_decode_discovery(const char *json, size_t length,
                               AgentAnnouncement *out);

/** Construit le message `hello`. Retourne le nombre d'octets écrits. */
int protocol_encode_hello(char *dest, size_t dest_size, const char *device,
                          const char *token, const char *pair_code,
                          const char *language);

/** Construit un message `button.press`. */
int protocol_encode_button(char *dest, size_t dest_size, int id,
                           const char *page, const char *button, bool hold);

/** Construit un message `config.request`. */
int protocol_encode_config_request(char *dest, size_t dest_size, int id);

/** Construit un message `ping`. */
int protocol_encode_ping(char *dest, size_t dest_size, int id);

/**
 * Construit un message `value.set`.
 *
 * Sert aux réglages continus, comme les curseurs de volume : la console envoie
 * directement la valeur voulue plutôt qu'une succession d'incréments.
 */
int protocol_encode_value(char *dest, size_t dest_size, int id,
                          const char *target, int value);

/** Sélectionne une sortie par son jeton opaque annoncé dans `state.update`. */
int protocol_encode_audio_output_select(char *dest, size_t dest_size, int id,
                                        const char *output);
