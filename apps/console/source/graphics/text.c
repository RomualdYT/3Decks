/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "text.h"

#include <stdio.h>
#include <string.h>

#include "stereo.h"
#include "text_cache.h"
#include "text_layout.h"

/*
 * Trois tampons distincts :
 *  - `s_cached` conserve d'une frame à l'autre les textes déjà analysés, pour
 *    ne pas refaire l'analyse et le tri des glyphes à chaque image (et deux
 *    fois en relief) ;
 *  - `s_frame` est vidé à chaque frame et reçoit ce que le cache refuse ;
 *  - `s_measure` sert uniquement aux mesures, pour ne pas consommer le budget
 *    de glyphes du tampon de frame.
 */
static C2D_TextBuf s_cached = NULL;
static C2D_TextBuf s_frame = NULL;
static C2D_TextBuf s_measure = NULL;

/*
 * Index des textes de `s_cached`. Les textes changeants (horloge, position de
 * lecture) finissent par le remplir : il est alors vidé au début de l'image
 * suivante, ce qui coûte une seule image d'analyse complète.
 */
static TextCache s_cache_index;
static C2D_Text s_cache_text[TEXT_CACHE_SLOTS];
static bool s_cache_full = false;

/**
 * Police embarquée, ou NULL pour utiliser celle du système.
 *
 * La police système est un bitmap de trente pixels de haut. Aux tailles
 * employées par cette interface, l'afficher revient à la réduire fortement, ce
 * qui détruit les détails des caractères et rend le texte illisible. On charge
 * donc une police matricielle générée à la taille d'affichage, ce qui maintient
 * les facteurs d'échelle proches de 1.
 */
static C2D_Font s_font = NULL;

#define CACHED_GLYPHS 4096
#define FRAME_GLYPHS 4096
#define MEASURE_GLYPHS 512

/** Chemin de la police embarquée dans le système de fichiers de l'application. */
#define FONT_PATH "romfs:/deck.bcfnt"

/**
 * Hauteur de référence d'une ligne à l'échelle 1.
 *
 * Trente pixels correspondent à la police système ; la police embarquée est
 * générée à dix-sept points, d'où le rapport appliqué lorsqu'elle est utilisée.
 */
#define SYSTEM_LINE_HEIGHT 30.0f
#define EMBEDDED_LINE_HEIGHT 17.0f

bool text_init(void)
{
	text_layout_reset();
	text_cache_reset(&s_cache_index);
	s_cache_full = false;
	s_cached = C2D_TextBufNew(CACHED_GLYPHS);
	s_frame = C2D_TextBufNew(FRAME_GLYPHS);
	s_measure = C2D_TextBufNew(MEASURE_GLYPHS);

	if (s_cached == NULL || s_frame == NULL || s_measure == NULL) {
		text_exit();
		return false;
	}

	/*
	 * On essaie d'abord depuis RomFS (fonctionne sur vraie 3DS et avec le paquet CIA).
	 * En repli (notamment pour Citra en mode .3dsx où RomFS n'est pas monté par SelfNCCH),
	 * on charge la police depuis la carte SD dans le répertoire de l'application.
	 */
	s_font = C2D_FontLoad(FONT_PATH);
	if (s_font == NULL) {
		s_font = C2D_FontLoad("sdmc:/3ds/deck3ds/deck.bcfnt");
	}
	if (s_font == NULL) {
		s_font = C2D_FontLoad("sdmc:/3ds/deck.bcfnt");
	}

	return true;
}

bool text_has_custom_font(void)
{
	return s_font != NULL;
}

void text_exit(void)
{
	text_layout_reset();
	text_cache_reset(&s_cache_index);
	if (s_font != NULL) {
		C2D_FontFree(s_font);
		s_font = NULL;
	}
	if (s_cached != NULL) {
		C2D_TextBufDelete(s_cached);
		s_cached = NULL;
	}
	if (s_frame != NULL) {
		C2D_TextBufDelete(s_frame);
		s_frame = NULL;
	}
	if (s_measure != NULL) {
		C2D_TextBufDelete(s_measure);
		s_measure = NULL;
	}
}

/**
 * Convertit une échelle exprimée pour la police système en échelle adaptée à la
 * police réellement utilisée.
 *
 * Les échelles de `text.h` sont définies par rapport à une hauteur de trente
 * pixels. La police embarquée mesurant dix-sept points, le facteur nécessaire
 * pour obtenir la même hauteur apparente est plus grand.
 */
static float adjust(float scale)
{
	if (s_font == NULL) {
		return scale;
	}
	return scale * (SYSTEM_LINE_HEIGHT / EMBEDDED_LINE_HEIGHT);
}

void text_frame_begin(void)
{
	if (s_frame != NULL) {
		C2D_TextBufClear(s_frame);
	}
	/*
	 * Le cache n'est vidé qu'entre deux images : aucun texte de l'image en
	 * cours ne peut alors désigner des glyphes effacés.
	 */
	if (s_cache_full && s_cached != NULL) {
		C2D_TextBufClear(s_cached);
		text_cache_reset(&s_cache_index);
		s_cache_full = false;
	}
}

/** Analyse `str` dans `buf` ; faux si le tampon n'a pas tout accueilli. */
static bool parse_into(C2D_Text *text, C2D_TextBuf buf, const char *str)
{
	const char *end = C2D_TextFontParse(text, s_font, buf, str);
	if (end == NULL || *end != '\0') {
		/*
		 * Tampon saturé en cours d'analyse : on ne garde pas un texte tronqué.
		 * Les glyphes déjà écrits restent perdus jusqu'au prochain vidage.
		 */
		return false;
	}
	C2D_TextOptimize(text);
	return true;
}

/** Texte prêt à dessiner, depuis le cache si possible. */
static bool prepare_text(C2D_Text *out, const char *str)
{
	const int hit = text_cache_find(&s_cache_index, str);
	if (hit >= 0) {
		*out = s_cache_text[hit];
		return true;
	}

	/* Un texte trop long pour être indexé passe directement par la frame. */
	if (!s_cache_full && s_cached != NULL &&
	    text_cache_cacheable(str)) {
		C2D_Text parsed;
		if (text_cache_has_room(&s_cache_index) &&
		    parse_into(&parsed, s_cached, str)) {
			const int slot = text_cache_insert(&s_cache_index, str);
			s_cache_text[slot] = parsed;
			*out = parsed;
			return true;
		}
		/* Tampon ou index plein : la frame prend le relais jusqu'au vidage. */
		s_cache_full = true;
	}

	return s_frame != NULL && parse_into(out, s_frame, str);
}

static float measure_width(const char *str, float scale)
{
	if (str == NULL || str[0] == '\0' || s_measure == NULL) {
		return 0.0f;
	}

	C2D_TextBufClear(s_measure);

	C2D_Text text;
	if (C2D_TextFontParse(&text, s_font, s_measure, str) == NULL) {
		return 0.0f;
	}

	const float applied = adjust(scale);
	float width = 0.0f;
	float height = 0.0f;
	C2D_TextGetDimensions(&text, applied, applied, &width, &height);
	return width;
}

float text_width(const char *str, float scale)
{
	return text_layout_width(str, scale, measure_width);
}

float text_height(float scale)
{
	/*
	 * La hauteur apparente est identique quelle que soit la police employée :
	 * l'ajustement d'échelle compense la différence de taille native.
	 */
	return SYSTEM_LINE_HEIGHT * scale;
}

float text_draw(float x, float y, float depth, float scale, u32 color,
                TextAlign align, const char *str)
{
	if (str == NULL || str[0] == '\0') {
		return 0.0f;
	}

	C2D_Text text;
	if (!prepare_text(&text, str)) {
		/*
		 * Les tampons sont saturés. On abandonne ce texte plutôt que de
		 * dessiner des glyphes invalides.
		 */
		return 0.0f;
	}

	const float applied = adjust(scale);
	float width = 0.0f;
	float height = 0.0f;
	C2D_TextGetDimensions(&text, applied, applied, &width, &height);

	float draw_x = x;
	if (align == ALIGN_CENTER) {
		draw_x = x - width * 0.5f;
	} else if (align == ALIGN_RIGHT) {
		draw_x = x - width;
	}

	/* Le texte suit le relief de la couche à laquelle il appartient. */
	draw_x += stereo_offset(depth * STEREO_FROM_Z);

	C2D_DrawText(&text, C2D_WithColor, draw_x, y, depth, applied, applied,
	             color);
	return width;
}

void text_draw_clipped(float x, float y, float depth, float scale, u32 color,
                       TextAlign align, float max_width, const char *str)
{
	if (str == NULL || str[0] == '\0') {
		return;
	}

	if (text_width(str, scale) <= max_width) {
		text_draw(x, y, depth, scale, color, align, str);
		return;
	}

	char buffer[128];
	text_layout_clip(buffer, str, scale, max_width, measure_width);
	text_draw(x, y, depth, scale, color, align, buffer);
}
