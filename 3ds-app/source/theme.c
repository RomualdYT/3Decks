/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "theme.h"

/*
 * C2D_Color32 produit un u32 au format ABGR :
 *   bits  0..7  = rouge
 *   bits  8..15 = vert
 *   bits 16..23 = bleu
 *   bits 24..31 = alpha
 * On manipule donc les canaux directement plutôt que via des macros.
 */

#define CH_R(c) ((u8)((c) & 0xFF))
#define CH_G(c) ((u8)(((c) >> 8) & 0xFF))
#define CH_B(c) ((u8)(((c) >> 16) & 0xFF))
#define CH_A(c) ((u8)(((c) >> 24) & 0xFF))

static u8 clamp_u8(float v)
{
	if (v <= 0.0f) {
		return 0;
	}
	if (v >= 255.0f) {
		return 255;
	}
	return (u8)(v + 0.5f);
}

u32 theme_scale(u32 color, float factor)
{
	return C2D_Color32(clamp_u8((float)CH_R(color) * factor),
	                   clamp_u8((float)CH_G(color) * factor),
	                   clamp_u8((float)CH_B(color) * factor), CH_A(color));
}

u32 theme_mix(u32 a, u32 b, float t)
{
	if (t <= 0.0f) {
		return a;
	}
	if (t >= 1.0f) {
		return b;
	}

	const float inv = 1.0f - t;
	return C2D_Color32(clamp_u8((float)CH_R(a) * inv + (float)CH_R(b) * t),
	                   clamp_u8((float)CH_G(a) * inv + (float)CH_G(b) * t),
	                   clamp_u8((float)CH_B(a) * inv + (float)CH_B(b) * t),
	                   clamp_u8((float)CH_A(a) * inv + (float)CH_A(b) * t));
}

u32 theme_alpha(u32 color, u8 alpha)
{
	return C2D_Color32(CH_R(color), CH_G(color), CH_B(color), alpha);
}

static int hex_digit(char c)
{
	if (c >= '0' && c <= '9') {
		return c - '0';
	}
	if (c >= 'a' && c <= 'f') {
		return c - 'a' + 10;
	}
	if (c >= 'A' && c <= 'F') {
		return c - 'A' + 10;
	}
	return -1;
}

u32 theme_parse_hex(const char *text, u32 fallback)
{
	if (text == NULL) {
		return fallback;
	}
	if (*text == '#') {
		text++;
	}

	int digits[6];
	int count = 0;
	while (count < 6 && text[count] != '\0') {
		const int d = hex_digit(text[count]);
		if (d < 0) {
			return fallback;
		}
		digits[count] = d;
		count++;
	}

	/* Le compteur doit tomber pile sur une forme connue. */
	if (text[count] != '\0') {
		return fallback;
	}

	if (count == 3) {
		/* #RGB : chaque chiffre est dupliqué. */
		return C2D_Color32((u8)(digits[0] * 17), (u8)(digits[1] * 17),
		                   (u8)(digits[2] * 17), 0xFF);
	}
	if (count == 6) {
		return C2D_Color32((u8)(digits[0] * 16 + digits[1]),
		                   (u8)(digits[2] * 16 + digits[3]),
		                   (u8)(digits[4] * 16 + digits[5]), 0xFF);
	}

	return fallback;
}
