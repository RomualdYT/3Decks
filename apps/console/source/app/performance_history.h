/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file performance_history.h
 * @brief Historique compact des métriques affichées sur l'écran supérieur.
 */
#pragma once

#include "model.h"

#define PERFORMANCE_HISTORY_SAMPLES 30
#define PERFORMANCE_UNKNOWN 255

typedef struct {
	/** Prochain emplacement à écrire dans les anneaux. */
	int head;
	int count;
	float elapsed;
	unsigned char cpu[PERFORMANCE_HISTORY_SAMPLES];
	unsigned char memory[PERFORMANCE_HISTORY_SAMPLES];
} PerformanceHistory;

void performance_history_init(PerformanceHistory *history);

/** Ajoute au plus un relevé par seconde, quelle que soit la cadence d'image. */
void performance_history_update(PerformanceHistory *history,
                                const PcState *state, float dt);

/** Valeur chronologique, zéro désignant la plus ancienne. */
int performance_history_cpu(const PerformanceHistory *history, int index);
int performance_history_memory(const PerformanceHistory *history, int index);
