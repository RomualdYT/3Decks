/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "artwork.h"

#include <string.h>

#include "stereo.h"

/*
 * La texture est allouée une fois pour toutes : une pochette remplace la
 * précédente sans nouvelle allocation, ce qui évite toute fragmentation de la
 * mémoire vidéo au fil des morceaux.
 */
static C3D_Tex s_texture;
static bool s_ready = false;
static bool s_has_image = false;
static u32 s_token = 0;

/*
 * citro2d dessine une image à partir d'une sous-texture décrivant la portion à
 * utiliser. Ici l'image occupe toute la texture.
 */
static Tex3DS_SubTexture s_subtex = {
    .width = ART_SIZE,
    .height = ART_SIZE,
    .left = 0.0f,
    .top = 1.0f,
    .right = 1.0f,
    .bottom = 0.0f,
};

bool artwork_init(void)
{
	if (s_ready) {
		return true;
	}

	if (!C3D_TexInit(&s_texture, ART_SIZE, ART_SIZE, GPU_RGB565)) {
		return false;
	}

	/*
	 * Filtrage linéaire : la pochette est affichée à une taille différente de
	 * sa taille native, un filtrage au plus proche produirait des escaliers
	 * visibles.
	 */
	C3D_TexSetFilter(&s_texture, GPU_LINEAR, GPU_LINEAR);
	C3D_TexSetWrap(&s_texture, GPU_CLAMP_TO_EDGE, GPU_CLAMP_TO_EDGE);

	s_ready = true;
	s_has_image = false;
	s_token = 0;
	return true;
}

void artwork_exit(void)
{
	if (s_ready) {
		C3D_TexDelete(&s_texture);
		s_ready = false;
		s_has_image = false;
		s_token = 0;
	}
}

bool artwork_consume(const char *payload, size_t length)
{
	/* La signature distingue une pochette d'un message JSON. */
	if (length < 12 || memcmp(payload, "ART0", 4) != 0) {
		return false;
	}

	/* En-tête : largeur, hauteur et jeton, en little-endian. */
	const unsigned char *header = (const unsigned char *)payload;
	const u16 width = (u16)(header[4] | (header[5] << 8));
	const u16 height = (u16)(header[6] | (header[7] << 8));
	const u32 token = (u32)header[8] | ((u32)header[9] << 8) |
	                  ((u32)header[10] << 16) | ((u32)header[11] << 24);

	/*
	 * On refuse toute dimension inattendue : la texture est allouée pour une
	 * taille fixe, accepter autre chose écrirait hors de la mémoire réservée.
	 */
	if (width != ART_SIZE || height != ART_SIZE ||
	    length != ART_PAYLOAD_SIZE || !s_ready) {
		return true; /* trame reconnue mais inutilisable */
	}

	/*
	 * Les pixels sont déjà dans l'agencement attendu par le processeur
	 * graphique : un simple téléversement suffit.
	 */
	C3D_TexUpload(&s_texture, payload + 12);
	C3D_TexFlush(&s_texture);

	s_has_image = true;
	s_token = token;
	return true;
}

bool artwork_available(void)
{
	return s_ready && s_has_image;
}

u32 artwork_token(void)
{
	return s_has_image ? s_token : 0;
}

void artwork_draw(float x, float y, float size, float depth, u8 alpha)
{
	if (!artwork_available()) {
		return;
	}

	const C2D_Image image = {&s_texture, &s_subtex};

	C2D_DrawParams params = {
	    .pos = {x + stereo_offset(depth * STEREO_FROM_Z), y, size, size},
	    .center = {0.0f, 0.0f},
	    .depth = depth,
	    .angle = 0.0f,
	};

	if (alpha >= 0xFF) {
		C2D_DrawImage(image, &params, NULL);
		return;
	}

	/*
	 * Fondu à l'apparition : on module l'opacité sans altérer les couleurs de
	 * l'image.
	 */
	C2D_ImageTint tint;
	C2D_AlphaImageTint(&tint, (float)alpha / 255.0f);
	C2D_DrawImage(image, &params, &tint);
}
