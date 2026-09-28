/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "draw.h"
#include "i18n.h"
#include "icons.h"
#include "text.h"
#include "theme.h"
#include "ui.h"
#include "extension_ui.h"

#include "ui_bottom_internal.h"

void draw_waiting(const App *app)
{
	const float cx = SCREEN_BOTTOM_W * 0.5f;

	/* Grille fantôme : montre la disposition à venir. */
	for (int slot = 0; slot < GRID_SLOTS; slot++) {
		const Rect rect = slot_rect(slot);

		/* Balayage lumineux, indique une attente active. */
		const float phase = app->uptime * 1.6f - (float)slot * 0.25f;
		float pulse = phase - (float)((int)(phase / 2.0f)) * 2.0f;
		if (pulse > 1.0f) {
			pulse = 2.0f - pulse;
		}
		if (pulse < 0.0f) {
			pulse = 0.0f;
		}

		const u8 alpha = (u8)(0x28 + pulse * 0x30);
		draw_round_rect(rect.x, rect.y, rect.w, rect.h, 9.0f, Z_CARD,
		                theme_alpha(COL_SURFACE, alpha));
		draw_round_rect_outline(rect.x, rect.y, rect.w, rect.h, 9.0f, 1.0f,
		                       Z_CONTENT, theme_alpha(COL_BORDER, 0x77));
	}

	text_draw(cx, 12.0f, Z_OVERLAY, TEXT_BODY, COL_TEXT_DIM, ALIGN_CENTER,
	          app->link == LINK_ONLINE ? tr(STR_RECEIVING_CONFIG)
	                                   : tr(STR_WAITING_PC));

	/*
	 * Pendant une recherche ou une connexion impossible, l'utilisateur doit
	 * pouvoir corriger l'adresse immédiatement. Le bouton est volontairement
	 * large et libellé : une icône seule serait trop discrète sur cet écran.
	 */
	const Rect settings = waiting_settings_rect();
	const float radius = settings.h * 0.5f;
	draw_round_rect(settings.x, settings.y, settings.w, settings.h, radius,
	                Z_CARD, theme_alpha(COL_SURFACE_HI, 0xE8));
	draw_round_rect_outline(settings.x, settings.y, settings.w, settings.h,
	                        radius, 1.0f, Z_CONTENT,
	                        theme_alpha(COL_ACCENT, 0xCC));
	icons_draw(ICON_GEAR, settings.x + 19.0f,
	           settings.y + settings.h * 0.5f, 15.0f, Z_OVERLAY, COL_ACCENT);
	text_draw_clipped(settings.x + 36.0f, settings.y + 7.0f, Z_OVERLAY,
	                  TEXT_SMALL, COL_TEXT, ALIGN_LEFT, settings.w - 44.0f,
	                  tr(STR_SETTINGS));
}

/**
 * Écran tactile en veille.
 *
 * La grille n'a plus de sens : en veille, le moindre contact réveille
 * l'application, aucun bouton n'est donc actionnable. Afficher des commandes
 * inertes serait trompeur, et le rétroéclairage serait dépensé pour rien.
 *
 * L'écran devient donc un panneau d'information sur fond noir : heure, date,
 * dernières notifications et état de la console.
 */
void draw_standby(const App *app)
{
	/* Noir franc plutôt qu'assombri : l'économie d'énergie est réelle. */
	draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_BG,
	          C2D_Color32(0x00, 0x00, 0x00, 0xFF));

	const float cx = SCREEN_BOTTOM_W * 0.5f;

	/*
	 * Liseré d'alerte : il pulse brièvement à l'arrivée d'une notification, ce
	 * qui se remarque du coin de l'œil sans exiger de lire l'écran.
	 */
	if (app->alert_glow > 0.01f) {
		const float pulse = 0.45f + 0.55f * (0.5f + 0.5f * sinf(app->uptime * 5.0f));
		const u8 alpha = (u8)(app->alert_glow * pulse * 0xCC);
		const u32 glow = theme_alpha(COL_WARN, alpha);

		draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, 2.0f, Z_CONTENT, glow);
		draw_rect(0.0f, SCREEN_H - 2.0f, SCREEN_BOTTOM_W, 2.0f, Z_CONTENT, glow);
		draw_rect(0.0f, 0.0f, 2.0f, SCREEN_H, Z_CONTENT, glow);
		draw_rect(SCREEN_BOTTOM_W - 2.0f, 0.0f, 2.0f, SCREEN_H, Z_CONTENT,
		          glow);
	}

	/* Heure en grand, information la plus recherchée sur un objet posé. */
	const char *clock = (app->state.time[0] != '\0' && app->link == LINK_ONLINE)
	                        ? app->state.time
	                        : app->local_time;

	text_draw(cx, 24.0f, Z_CONTENT, TEXT_HUGE, COL_TEXT, ALIGN_CENTER, clock);

	if (app->local_date[0] != '\0') {
		text_draw_clipped(cx, 24.0f + TEXT_LINE_PX(TEXT_HUGE) + 2.0f, Z_CONTENT,
		                  TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER,
		                  SCREEN_BOTTOM_W - 40.0f, app->local_date);
	}

	draw_rect(30.0f, 88.0f, SCREEN_BOTTOM_W - 60.0f, 1.0f, Z_CONTENT,
	          theme_alpha(COL_BORDER, 0x88));

	/* Deux dernières notifications, avec leur ancienneté. */
	const int shown = (app->state.notification_count < 2)
	                      ? app->state.notification_count
	                      : 2;

	if (shown == 0) {
		text_draw(cx, 118.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_CENTER, tr(STR_NO_NOTIFICATIONS));
	}

	for (int i = 0; i < shown; i++) {
		const float y = 100.0f + (float)i * 40.0f;
		const u32 tint = (i == 0) ? COL_WARN : COL_TEXT_FAINT;

		icons_draw(app->state.notifications[i].icon, 42.0f, y + 12.0f, 14.0f,
		           Z_CONTENT, tint);

		char age[12];
		const int seconds = app->state.notifications[i].age;
		if (seconds < 60) {
			snprintf(age, sizeof(age), "%ds", seconds % 100);
		} else if (seconds < 3600) {
			snprintf(age, sizeof(age), "%dmin", (seconds / 60) % 100);
		} else {
			snprintf(age, sizeof(age), "%dh", (seconds / 3600) % 100);
		}

		text_draw(SCREEN_BOTTOM_W - 30.0f, y, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_RIGHT, age);

		text_draw_clipped(56.0f, y, Z_CONTENT, TEXT_MICRO, tint, ALIGN_LEFT,
		                  SCREEN_BOTTOM_W - 110.0f,
		                  app->state.notifications[i].app);

		text_draw_clipped(56.0f, y + 14.0f, Z_CONTENT, TEXT_SMALL,
		                  (i == 0) ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT,
		                  SCREEN_BOTTOM_W - 86.0f,
		                  app->state.notifications[i].title);
	}

	/* Bandeau d'état, en bas. */
	const float info_y = SCREEN_H - 44.0f;
	draw_rect(30.0f, info_y - 10.0f, SCREEN_BOTTOM_W - 60.0f, 1.0f, Z_CONTENT,
	          theme_alpha(COL_BORDER, 0x88));

	/*
	 * Bandeau d'état : intitulé à gauche, jauge et volume à droite.
	 *
	 * La console rapporte un niveau de zéro à cinq, non un pourcentage : la
	 * jauge à segments est donc plus honnête qu'une valeur chiffrée, qui
	 * suggérerait une précision inexistante.
	 */
	if (app->battery_level >= 0) {
		text_draw(34.0f, info_y, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_LEFT, tr(STR_BATTERY));

		/* La jauge est calée à droite, le volume juste après. */
		const float gauge_w = 5.0f * 7.0f - 2.0f;
		const float charge_w = app->battery_charging ? 16.0f : 0.0f;

		float right = SCREEN_BOTTOM_W - 34.0f;

		if (app->state.volume >= 0) {
			char volume[16];
			snprintf(volume, sizeof(volume), "%u %%",
			         (unsigned)app->state.volume % 101u);

			text_draw(right, info_y, Z_CONTENT, TEXT_MICRO,
			          app->state.muted ? COL_ERR : COL_TEXT_DIM, ALIGN_RIGHT,
			          volume);
			right -= text_width(volume, TEXT_MICRO) + 14.0f;
		}

		const float bx = right - gauge_w - charge_w;
		const float by = info_y + 2.0f;

		if (app->battery_charging) {
			icons_draw(ICON_POWER, right - 8.0f, by + 5.0f, 11.0f, Z_CONTENT,
			           COL_ACCENT);
		}

		for (int i = 0; i < 5; i++) {
			const bool filled = i < app->battery_level;
			draw_round_rect(bx + (float)i * 7.0f, by, 5.0f, 10.0f, 1.5f,
			                Z_CONTENT,
			                filled ? (app->battery_level <= 1 ? COL_ERR
			                                                  : COL_OK)
			                       : theme_alpha(COL_SURFACE_HI, 0xCC));
		}
	} else if (app->state.volume >= 0) {
		/* Sans niveau de batterie, le volume reste seul à droite. */
		char volume[16];
		snprintf(volume, sizeof(volume), "%u %%",
		         (unsigned)app->state.volume % 101u);
		text_draw(SCREEN_BOTTOM_W - 34.0f, info_y, Z_CONTENT, TEXT_MICRO,
		          app->state.muted ? COL_ERR : COL_TEXT_DIM, ALIGN_RIGHT,
		          volume);
	}

	/* Sans cette mention, on pourrait croire l'application figée. */
	text_draw(cx, SCREEN_H - 18.0f, Z_CONTENT, TEXT_MICRO,
	          theme_alpha(COL_TEXT_FAINT, 0x99), ALIGN_CENTER,
	          tr(STR_TOUCH_TO_WAKE));
}
