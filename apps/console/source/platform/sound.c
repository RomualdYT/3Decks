/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "sound.h"

#include <3ds.h>
#include <math.h>
#include <string.h>

/** Fréquence d'échantillonnage. Suffisante pour des sons courts et discrets. */
#define SAMPLE_RATE 22050

/**
 * Canaux réservés.
 *
 * Plusieurs canaux permettent de superposer deux sons : un appui suivi de près
 * d'une notification ne coupe donc pas le premier. On tourne entre eux.
 */
#define CHANNEL_FIRST 8
#define CHANNEL_COUNT 3

/** Durée maximale d'un son, en échantillons. */
#define MAX_SAMPLES (SAMPLE_RATE / 4)

typedef struct {
	s16 *data;
	u32 samples;
	ndspWaveBuf buffer[CHANNEL_COUNT];
} Sound;

static Sound s_sounds[SOUND_COUNT];
static bool s_ready = false;
static bool s_enabled = true;
static int s_next_channel = 0;

/**
 * Enveloppe d'amplitude.
 *
 * Une attaque très courte suivie d'une décroissance exponentielle : c'est ce qui
 * donne l'impression d'un choc net plutôt que d'un bip électronique. Sans
 * enveloppe, le début et la fin du son produiraient un claquement.
 */
static float envelope(float position, float attack)
{
	if (position < attack) {
		return position / attack;
	}

	const float rest = (position - attack) / (1.0f - attack);
	return expf(-rest * 5.0f);
}

/**
 * Synthétise un son.
 *
 * `start_hz` et `end_hz` décrivent un glissement de hauteur : une descente
 * évoque un contact, une montée une validation. `noise` ajoute une composante
 * bruitée qui rend le résultat plus proche d'un clic mécanique que d'une note.
 */
static bool build(Sound *sound, float duration, float start_hz, float end_hz,
                 float noise, float volume)
{
	const u32 count = (u32)(duration * SAMPLE_RATE);
	if (count == 0 || count > MAX_SAMPLES) {
		return false;
	}

	/*
	 * La mémoire doit être linéaire : le processeur audio y accède
	 * directement, sans passer par la table de pages du processus.
	 */
	sound->data = (s16 *)linearAlloc(count * sizeof(s16));
	if (sound->data == NULL) {
		return false;
	}

	sound->samples = count;

	/* Générateur pseudo-aléatoire simple, pour une composante bruitée stable. */
	u32 seed = 0x2545F491;
	float phase = 0.0f;

	for (u32 i = 0; i < count; i++) {
		const float position = (float)i / (float)count;

		/* Hauteur interpolée entre le début et la fin. */
		const float hz = start_hz + (end_hz - start_hz) * position;
		phase += hz / (float)SAMPLE_RATE;
		if (phase > 1.0f) {
			phase -= 1.0f;
		}

		const float tone = sinf(phase * 6.28318530718f);

		seed ^= seed << 13;
		seed ^= seed >> 17;
		seed ^= seed << 5;
		const float grain = ((float)(seed & 0xFFFF) / 32768.0f) - 1.0f;

		const float mixed = tone * (1.0f - noise) + grain * noise;
		const float value = mixed * envelope(position, 0.02f) * volume;

		/* Bornage avant conversion, pour éviter tout repliement. */
		float scaled = value * 32000.0f;
		if (scaled > 32000.0f) {
			scaled = 32000.0f;
		}
		if (scaled < -32000.0f) {
			scaled = -32000.0f;
		}

		sound->data[i] = (s16)scaled;
	}

	/*
	 * Les données viennent d'être écrites par le processeur central : il faut
	 * vider le cache, sans quoi le processeur audio lirait de la mémoire
	 * obsolète et produirait un grésillement.
	 */
	DSP_FlushDataCache(sound->data, count * sizeof(s16));

	for (int c = 0; c < CHANNEL_COUNT; c++) {
		memset(&sound->buffer[c], 0, sizeof(sound->buffer[c]));
		sound->buffer[c].data_vaddr = sound->data;
		sound->buffer[c].nsamples = count;
	}

	return true;
}

bool sound_init(void)
{
	if (s_ready) {
		return true;
	}

	if (R_FAILED(ndspInit())) {
		return false;
	}

	ndspSetOutputMode(NDSP_OUTPUT_STEREO);

	for (int c = 0; c < CHANNEL_COUNT; c++) {
		const int channel = CHANNEL_FIRST + c;

		ndspChnReset(channel);
		ndspChnSetInterp(channel, NDSP_INTERP_LINEAR);
		ndspChnSetRate(channel, (float)SAMPLE_RATE);
		ndspChnSetFormat(channel, NDSP_FORMAT_MONO_PCM16);

		/* Mixage central, volume modéré : le son doit rester discret. */
		float mix[12];
		memset(mix, 0, sizeof(mix));
		mix[0] = 0.55f;
		mix[1] = 0.55f;
		ndspChnSetMix(channel, mix);
	}

	/*
	 * Les timbres sont choisis pour être distinguables sans être identifiables
	 * comme des notes : un contact sec pour l'appui, une descente pour l'erreur,
	 * une montée pour la connexion.
	 */
	build(&s_sounds[SOUND_TAP], 0.035f, 1900.0f, 1150.0f, 0.35f, 0.32f);
	build(&s_sounds[SOUND_TOGGLE], 0.050f, 1250.0f, 1850.0f, 0.15f, 0.34f);
	build(&s_sounds[SOUND_PAGE], 0.045f, 900.0f, 1500.0f, 0.10f, 0.26f);
	build(&s_sounds[SOUND_ERROR], 0.140f, 520.0f, 240.0f, 0.08f, 0.40f);
	build(&s_sounds[SOUND_CONNECT], 0.110f, 780.0f, 1560.0f, 0.05f, 0.30f);

	s_ready = true;
	return true;
}

void sound_exit(void)
{
	if (!s_ready) {
		return;
	}

	for (int c = 0; c < CHANNEL_COUNT; c++) {
		ndspChnReset(CHANNEL_FIRST + c);
	}

	for (int i = 0; i < SOUND_COUNT; i++) {
		if (s_sounds[i].data != NULL) {
			linearFree(s_sounds[i].data);
			s_sounds[i].data = NULL;
		}
	}

	ndspExit();
	s_ready = false;
}

void sound_set_enabled(bool enabled)
{
	s_enabled = enabled;
}

void sound_play(SoundId id)
{
	/*
	 * L'énumération ne comporte aucune valeur négative : le compilateur peut la
	 * représenter sans signe, une comparaison à zéro serait donc toujours vraie.
	 */
	if (!s_ready || !s_enabled || id >= SOUND_COUNT) {
		return;
	}

	Sound *sound = &s_sounds[id];
	if (sound->data == NULL) {
		return;
	}

	/*
	 * On tourne entre les canaux pour qu'un son n'interrompe pas le précédent.
	 * Chaque canal dispose de son propre descripteur : réutiliser celui d'un
	 * son en cours de lecture perturberait la file d'attente du processeur
	 * audio.
	 */
	const int slot = s_next_channel;
	s_next_channel = (s_next_channel + 1) % CHANNEL_COUNT;

	const int channel = CHANNEL_FIRST + slot;
	ndspWaveBuf *buffer = &sound->buffer[slot];

	/* Un descripteur encore en lecture ne doit pas être remis dans la file. */
	if (buffer->status == NDSP_WBUF_QUEUED ||
	    buffer->status == NDSP_WBUF_PLAYING) {
		return;
	}

	buffer->data_vaddr = sound->data;
	buffer->nsamples = sound->samples;
	buffer->looping = false;
	buffer->status = NDSP_WBUF_FREE;

	ndspChnWaveBufAdd(channel, buffer);
}
