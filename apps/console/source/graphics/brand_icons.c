#include "brand_icons.h"

#include <citro2d.h>
#include <math.h>

#include "stereo.h"

static C2D_SpriteSheet s_spotify;

void brand_icons_init(void)
{
	if (s_spotify) return;
	s_spotify = C2D_SpriteSheetLoad("romfs:/brands/spotify.t3x");
	if (s_spotify) {
		C2D_Image image = C2D_SpriteSheetGetImage(s_spotify, 0);
		/* Antialiasing is baked into the RGBA asset at its native size. */
		C3D_TexSetFilter(image.tex, GPU_NEAREST, GPU_NEAREST);
	}
}

void brand_icons_exit(void)
{
	if (s_spotify) C2D_SpriteSheetFree(s_spotify);
	s_spotify = NULL;
}

bool brand_icons_draw_spotify(float cx, float cy, float z)
{
	if (!s_spotify) return false;
	C2D_Image image = C2D_SpriteSheetGetImage(s_spotify, 0);
	return C2D_DrawImageAt(image,
	                      roundf(cx - 8.0f + stereo_offset(z * STEREO_FROM_Z)),
	                      roundf(cy - 8.0f), z, NULL, 1.0f, 1.0f);
}
