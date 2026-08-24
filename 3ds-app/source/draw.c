/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "draw.h"

#include <math.h>

#include "stereo.h"
#include "theme.h"

#define TAU 6.28318530718f

/**
 * Décalage horizontal donnant le relief, dérivé de la profondeur de rendu.
 *
 * Placer cette conversion ici évite d'avoir à modifier chaque appel de dessin :
 * la hiérarchie de profondeur déjà employée par l'interface devient
 * automatiquement une hiérarchie spatiale.
 */
static inline float shift(float z)
{
	return stereo_offset(z * STEREO_FROM_Z);
}

void draw_rect(float x, float y, float w, float h, float z, u32 color)
{
	if (w <= 0.0f || h <= 0.0f) {
		return;
	}
	C2D_DrawRectSolid(x + shift(z), y, z, w, h, color);
}

void draw_rect_vgrad(float x, float y, float w, float h, float z, u32 top,
                     u32 bottom)
{
	if (w <= 0.0f || h <= 0.0f) {
		return;
	}
	C2D_DrawRectangle(x + shift(z), y, z, w, h, top, top, bottom, bottom);
}

/**
 * Secteur de disque, tracé en éventail de triangles.
 *
 * `from` désigne l'angle de départ et `sweep` l'ouverture, tous deux exprimés
 * en tours : 0,25 correspond à un quart de cercle, 0,5 à un demi.
 *
 * Cette construction remplace le tracé d'un disque entier : elle ne peint que
 * la surface réellement utile, sans jamais empiéter sur les bandes voisines.
 * C'est ce qui permet d'assembler une forme arrondie translucide sans que
 * l'opacité ne s'accumule par endroits.
 */
static void draw_corner(float cx, float cy, float r, float from, float sweep,
                        float z, u32 color)
{
	if (r <= 0.0f || sweep <= 0.0f) {
		return;
	}

	/*
	 * Nombre de segments proportionné au rayon et à l'ouverture.
	 *
	 * Le facteur est choisi pour qu'un segment couvre environ deux pixels
	 * d'arc : au-delà, le gain visuel devient imperceptible sur un écran de
	 * cette taille, alors que le coût en géométrie continue d'augmenter.
	 */
	int steps = (int)(r * sweep * 3.2f);
	if (steps < 3) {
		steps = 3;
	}
	if (steps > 14) {
		steps = 14;
	}

	const float start = from * TAU;
	const float span = sweep * TAU;

	float px = cx + cosf(start) * r;
	float py = cy + sinf(start) * r;

	for (int i = 1; i <= steps; i++) {
		const float angle = start + span * ((float)i / (float)steps);
		const float nx = cx + cosf(angle) * r;
		const float ny = cy + sinf(angle) * r;

		const float dx = shift(z);
		C2D_DrawTriangle(cx + dx, cy, color, px + dx, py, color, nx + dx, ny,
		                 color, z);

		px = nx;
		py = ny;
	}
}

static float clamp_radius(float w, float h, float r)
{
	const float max_r = ((w < h) ? w : h) * 0.5f;
	if (r > max_r) {
		return max_r;
	}
	if (r < 0.0f) {
		return 0.0f;
	}
	return r;
}

/**
 * Rectangle aux coins arrondis, sans recouvrement.
 *
 * La décomposition évite scrupuleusement de couvrir deux fois le même pixel.
 * C'est indispensable avec des couleurs translucides : deux primitives
 * superposées cumulent leur opacité, ce qui produisait des taches sombres aux
 * extrémités et un centre plus clair, particulièrement visible sur les formes
 * en pastille où les disques d'angle finissaient par se confondre.
 *
 * Composition retenue :
 *
 *   - une bande centrale pleine largeur, entre les deux zones d'angle ;
 *   - en haut et en bas, un rectangle bordé de deux demi-disques.
 *
 * Les demi-disques sont obtenus en dessinant des disques dont la moitié inutile
 * est ensuite recouverte par la bande centrale, laquelle est tracée en dernier
 * pour rester opaque. On préfère ici tracer les disques d'abord et le corps
 * ensuite, de sorte qu'aucune surface translucide ne se superpose.
 */
void draw_round_rect(float x, float y, float w, float h, float radius, float z,
                     u32 color)
{
	if (w <= 0.0f || h <= 0.0f) {
		return;
	}

	const float r = clamp_radius(w, h, radius);
	if (r <= 0.5f) {
		draw_rect(x, y, w, h, z, color);
		return;
	}

	const float inner_w = w - 2.0f * r;
	const float inner_h = h - 2.0f * r;

	/*
	 * Les angles sont tracés comme des éventails de triangles plutôt que comme
	 * des disques entiers. Un disque déborderait dans les bandes voisines, et
	 * une couleur translucide y cumulerait son opacité.
	 */
	if (inner_h <= 0.0f) {
		/*
		 * Forme en pastille : le rayon égale la demi-hauteur, si bien que les
		 * angles hauts et bas partagent le même centre. Quatre quarts de disque
		 * se recouvriraient donc entièrement ; on trace deux demi-disques.
		 */
		draw_corner(x + r, y + r, r, 0.25f, 0.5f, z, color);
		draw_corner(x + w - r, y + r, r, 0.75f, 0.5f, z, color);
	} else {
		/* Chaque quart couvre exactement son quadrant, sans empiéter. */
		draw_corner(x + r, y + r, r, 0.5f, 0.25f, z, color);         /* 9h-12h */
		draw_corner(x + w - r, y + r, r, 0.75f, 0.25f, z, color);    /* 12h-3h */
		draw_corner(x + w - r, y + h - r, r, 0.0f, 0.25f, z, color); /* 3h-6h */
		draw_corner(x + r, y + h - r, r, 0.25f, 0.25f, z, color);    /* 6h-9h */

		/* Flancs gauche et droit, strictement entre les angles. */
		draw_rect(x, y + r, r, inner_h, z, color);
		draw_rect(x + w - r, y + r, r, inner_h, z, color);
	}

	/* Bande centrale pleine hauteur, disjointe des colonnes d'angle. */
	if (inner_w > 0.0f) {
		draw_rect(x + r, y, inner_w, h, z, color);
	}
}

void draw_round_rect_vgrad(float x, float y, float w, float h, float radius,
                           float z, u32 top, u32 bottom)
{
	if (w <= 0.0f || h <= 0.0f) {
		return;
	}

	const float r = clamp_radius(w, h, radius);
	if (r <= 0.5f) {
		draw_rect_vgrad(x, y, w, h, z, top, bottom);
		return;
	}

	/*
	 * Même découpage que `draw_round_rect` : aucune surface ne doit être peinte
	 * deux fois. Des disques entiers, employés auparavant, se recouvraient
	 * entre eux et avec le corps ; avec une couleur translucide, l'opacité
	 * s'additionnait et laissait voir deux taches sombres se rejoignant au
	 * milieu de la forme.
	 *
	 * Le dégradé est reconstitué en attribuant à chaque morceau la couleur
	 * interpolée à sa hauteur, ce qui évite d'avoir recours à un shader.
	 */
	const float inner_w = w - 2.0f * r;
	const float inner_h = h - 2.0f * r;

	const u32 c_top = theme_mix(top, bottom, r / h);
	const u32 c_bottom = theme_mix(top, bottom, (h - r) / h);

	/* Colonnes latérales, angles compris. */
	if (inner_h <= 0.0f) {
		/*
		 * Forme en pastille : les angles hauts et bas se confondent, on trace
		 * donc un demi-disque par côté. Sa couleur est prise à mi-hauteur, là
		 * où se situe son centre de masse.
		 */
		const u32 mid = theme_mix(top, bottom, 0.5f);
		draw_corner(x + r, y + r, r, 0.25f, 0.5f, z, mid);
		draw_corner(x + w - r, y + r, r, 0.75f, 0.5f, z, mid);
	} else {
		draw_corner(x + r, y + r, r, 0.5f, 0.25f, z, c_top);
		draw_corner(x + w - r, y + r, r, 0.75f, 0.25f, z, c_top);
		draw_corner(x + w - r, y + h - r, r, 0.0f, 0.25f, z, c_bottom);
		draw_corner(x + r, y + h - r, r, 0.25f, 0.25f, z, c_bottom);

		draw_rect_vgrad(x, y + r, r, inner_h, z, c_top, c_bottom);
		draw_rect_vgrad(x + w - r, y + r, r, inner_h, z, c_top, c_bottom);
	}

	/* Bande centrale pleine hauteur, disjointe des colonnes d'angle. */
	if (inner_w > 0.0f) {
		draw_rect_vgrad(x + r, y, inner_w, h, z, top, bottom);
	}
}

void draw_round_rect_outline(float x, float y, float w, float h, float radius,
                             float thickness, float z, u32 color)
{
	if (w <= 0.0f || h <= 0.0f || thickness <= 0.0f) {
		return;
	}

	const float r = clamp_radius(w, h, radius);
	const float t = (thickness > r) ? r : thickness;

	/* Bords droits. */
	draw_rect(x + r, y, w - 2.0f * r, t, z, color);
	draw_rect(x + r, y + h - t, w - 2.0f * r, t, z, color);
	draw_rect(x, y + r, t, h - 2.0f * r, z, color);
	draw_rect(x + w - t, y + r, t, h - 2.0f * r, z, color);

	/* Angles : anneaux partiels approximés par des arcs. */
	if (r > 0.5f) {
		draw_arc(x + r, y + r, r - t * 0.5f, t, 0.75f, 0.25f, z, color);
		draw_arc(x + w - r, y + r, r - t * 0.5f, t, 0.0f, 0.25f, z, color);
		draw_arc(x + w - r, y + h - r, r - t * 0.5f, t, 0.25f, 0.25f, z, color);
		draw_arc(x + r, y + h - r, r - t * 0.5f, t, 0.5f, 0.25f, z, color);
	}
}

void draw_circle(float cx, float cy, float radius, float z, u32 color)
{
	if (radius <= 0.0f) {
		return;
	}
	C2D_DrawCircleSolid(cx + shift(z), cy, z, radius, color);
}

void draw_ring(float cx, float cy, float radius, float thickness, float z,
               u32 color)
{
	draw_ellipse_ring(cx, cy, radius, radius, thickness, z, color);
}

void draw_ellipse_ring(float cx, float cy, float rx, float ry, float thickness,
                       float z, u32 color)
{
	if (rx <= 0.0f || ry <= 0.0f || thickness <= 0.0f) {
		return;
	}

	/*
	 * citro2d ne sait pas dessiner un anneau. On l'approxime par une série de
	 * segments épais le long du périmètre. Le nombre de segments s'adapte au
	 * rayon pour éviter les facettes visibles sans gaspiller de géométrie.
	 */
	const float r_max = (rx > ry) ? rx : ry;
	int steps = (int)(r_max * 1.6f);
	if (steps < 12) {
		steps = 12;
	}
	if (steps > 48) {
		steps = 48;
	}

	const float rx_mid = rx - thickness * 0.5f;
	const float ry_mid = ry - thickness * 0.5f;

	float prev_x = cx + rx_mid;
	float prev_y = cy;

	for (int i = 1; i <= steps; i++) {
		const float a = ((float)i / (float)steps) * TAU;
		const float px = cx + cosf(a) * rx_mid;
		const float py = cy + sinf(a) * ry_mid;
		draw_line(prev_x, prev_y, px, py, thickness, z, color);
		prev_x = px;
		prev_y = py;
	}
}

void draw_arc(float cx, float cy, float radius, float thickness, float start,
              float sweep, float z, u32 color)
{
	if (radius <= 0.0f || thickness <= 0.0f || sweep <= 0.0f) {
		return;
	}

	int steps = (int)(radius * sweep * 8.0f);
	if (steps < 4) {
		steps = 4;
	}
	if (steps > 32) {
		steps = 32;
	}

	/* L'origine est en haut (-90°) et la progression se fait dans le sens horaire. */
	const float base = (start - 0.25f) * TAU;
	const float span = sweep * TAU;

	float prev_x = cx + cosf(base) * radius;
	float prev_y = cy + sinf(base) * radius;

	for (int i = 1; i <= steps; i++) {
		const float a = base + span * ((float)i / (float)steps);
		const float px = cx + cosf(a) * radius;
		const float py = cy + sinf(a) * radius;
		draw_line(prev_x, prev_y, px, py, thickness, z, color);
		prev_x = px;
		prev_y = py;
	}
}

void draw_line(float x0, float y0, float x1, float y1, float thickness, float z,
               u32 color)
{
	if (thickness <= 0.0f) {
		return;
	}
	const float dx = shift(z);
	C2D_DrawLine(x0 + dx, y0, color, x1 + dx, y1, color, thickness, z);
}

void draw_triangle(float x0, float y0, float x1, float y1, float x2, float y2,
                   float z, u32 color)
{
	const float dx = shift(z);
	C2D_DrawTriangle(x0 + dx, y0, color, x1 + dx, y1, color, x2 + dx, y2, color,
	                 z);
}

void draw_spoke(float cx, float cy, float angle, float inner, float outer,
                float thickness, float z, u32 color)
{
	const float dx = cosf(angle);
	const float dy = sinf(angle);
	draw_line(cx + dx * inner, cy + dy * inner, cx + dx * outer,
	          cy + dy * outer, thickness, z, color);
}

void draw_star(float cx, float cy, float outer, float inner, float z, u32 color)
{
	/*
	 * Étoile à cinq branches : on relie alternativement rayon externe et rayon
	 * interne, puis on remplit par un éventail de triangles depuis le centre.
	 */
	float xs[10];
	float ys[10];

	for (int i = 0; i < 10; i++) {
		const float a = -0.25f * TAU + ((float)i / 10.0f) * TAU;
		const float r = (i % 2 == 0) ? outer : inner;
		xs[i] = cx + cosf(a) * r;
		ys[i] = cy + sinf(a) * r;
	}

	for (int i = 0; i < 10; i++) {
		const int j = (i + 1) % 10;
		draw_triangle(cx, cy, xs[i], ys[i], xs[j], ys[j], z, color);
	}
}

void draw_progress(float x, float y, float w, float h, float ratio, float z,
                   u32 track, u32 fill)
{
	if (w <= 0.0f || h <= 0.0f) {
		return;
	}

	float r = ratio;
	if (r < 0.0f) {
		r = 0.0f;
	}
	if (r > 1.0f) {
		r = 1.0f;
	}

	const float radius = h * 0.5f;
	const float filled = w * r;

	/*
	 * Le rail est tracé entier puis recouvert par le remplissage : avec des
	 * couleurs translucides, la portion remplie cumulerait alors deux couches
	 * et paraîtrait plus sombre que le reste.
	 *
	 * On dessine donc le rail au-dessus du remplissage, à une profondeur
	 * inférieure, en le limitant à la portion encore vide. Chaque pixel n'est
	 * ainsi peint qu'une seule fois.
	 */
	if (filled >= w) {
		/* Barre pleine : le rail n'est pas visible. */
		draw_round_rect(x, y, w, h, radius, z, fill);
		return;
	}

	draw_round_rect(x, y, w, h, radius, z, track);

	if (filled <= 0.5f) {
		return; /* rien à remplir */
	}

	/*
	 * En dessous d'un diamètre complet, un rectangle arrondi produirait une
	 * pastille difforme : on trace alors un simple disque.
	 */
	if (filled < h) {
		draw_circle(x + radius, y + radius, radius, z + 0.01f, fill);
		return;
	}

	draw_round_rect(x, y, filled, h, radius, z + 0.01f, fill);
}

void draw_shadow(float x, float y, float w, float h, float radius, float z)
{
	/*
	 * Ombre approximée par deux halos concentriques translucides. Suffisant pour
	 * détacher une carte du fond sans coût de flou.
	 */
	const u32 outer = C2D_Color32(0x00, 0x00, 0x00, 0x22);
	const u32 inner = C2D_Color32(0x00, 0x00, 0x00, 0x33);

	draw_round_rect(x - 1.5f, y + 1.0f, w + 3.0f, h + 3.0f, radius + 1.5f, z,
	                outer);
	draw_round_rect(x - 0.5f, y + 1.0f, w + 1.0f, h + 1.5f, radius + 0.5f, z,
	                inner);
}
