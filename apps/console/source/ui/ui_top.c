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
#include "ui_top_media.h"
#include "ui_top_system.h"
#include "ui_companion.h"
#include "extension_ui.h"
#include "ui_top_chat.h"

/*
 * L'écran supérieur est un tableau de bord contextuel. Il n'est pas un miroir
 * de l'écran tactile : il montre ce que l'on veut lire d'un coup d'œil, alors
 * que l'écran bas sert à agir.
 *
 * Mise en page :
 *   - un bandeau supérieur avec heure, hôte et état de connexion ;
 *   - une zone centrale variable selon le mode ;
 *   - un dock de volumes reserve a la page Audio.
 */

#define HEADER_H 30.0f
#define PAD 12.0f

/** Dessine le fond, légèrement dégradé pour éviter un aplat terne. */
static void draw_background(const App *app)
{
	const u32 top = app->dimmed ? C2D_Color32(0x06, 0x07, 0x0B, 0xFF) : COL_BG;
	const u32 bottom =
	    app->dimmed ? C2D_Color32(0x04, 0x05, 0x08, 0xFF) : COL_BG_ALT;
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG, top, bottom);
}

/** Pastille d'état de connexion, avec pulsation pendant la connexion. */
static void draw_link_badge(const App *app, float x, float y)
{
	u32 color;
	const char *label;

	switch (app->link) {
	case LINK_ONLINE:
		color = COL_OK;
		label = tr(STR_CONNECTED);
		break;
	case LINK_CONNECTING:
		color = COL_WARN;
		label = tr(STR_CONNECTING);
		break;
	case LINK_OFFLINE:
	default:
		color = COL_ERR;
		label = tr(STR_OFFLINE);
		break;
	}

	float alpha = 1.0f;
	if (app->link != LINK_ONLINE) {
		/* Pulsation lente : signale une activité sans être agressive. */
		const float phase = app->uptime * 3.0f;
		alpha = 0.55f + 0.45f * (0.5f + 0.5f * sinf(phase));
	}

	const float text_w = text_width(label, TEXT_SMALL);
	const float dot_r = 3.0f;
	const float badge_h = 18.0f;
	const float badge_w = text_w + dot_r * 2.0f + 18.0f;
	const float badge_x = x - badge_w;

	/*
	 * Pastille et texte partagent la même ligne médiane. Le texte était
	 * auparavant positionné par son sommet, ce qui le faisait paraître d'un
	 * pixel et demi trop bas par rapport au point coloré.
	 */
	const float middle = y + badge_h * 0.5f;

	draw_round_rect(badge_x, y, badge_w, badge_h, badge_h * 0.5f, Z_CARD,
	                theme_alpha(COL_SURFACE, 0xCC));
	draw_circle(badge_x + 10.0f, middle, dot_r, Z_CONTENT,
	            theme_alpha(color, (u8)(alpha * 255.0f)));
	text_draw(badge_x + 17.0f, middle - TEXT_LINE_PX(TEXT_SMALL) * 0.5f,
	          Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM, ALIGN_LEFT, label);
}

static void draw_header(const App *app)
{
	/* Heure : le PC est prioritaire, l'horloge locale sert de repli. */
	const char *clock = (app->state.time[0] != '\0' && app->link == LINK_ONLINE)
	                        ? app->state.time
	                        : app->local_time;

	text_draw(PAD, 8.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_LEFT, clock);

	/*
	 * La date est centrée sur l'écran plutôt qu'accolée à l'heure : les trois
	 * informations du bandeau se répartissent alors sur toute la largeur, ce qui
	 * aère nettement l'ensemble.
	 *
	 * Le centrage est optique, calé sur la ligne médiane de l'heure.
	 */
	if (app->local_date[0] != '\0') {
		const float clock_middle = 8.0f + TEXT_LINE_PX(TEXT_TITLE) * 0.5f;

		text_draw_clipped(SCREEN_TOP_W * 0.5f,
		                  clock_middle - TEXT_LINE_PX(TEXT_SMALL) * 0.5f,
		                  Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER,
		                  150.0f, app->local_date);
	}

	/*
	 * Compteur de notifications, à gauche du badge de liaison.
	 *
	 * Il reste visible sur toutes les pages : savoir qu'il s'est passé quelque
	 * chose importe plus que d'en connaître le détail immédiatement.
	 */
	float badge_left = SCREEN_TOP_W - PAD;

	if (app->state.notification_total > 0) {
		char count[8];
		snprintf(count, sizeof(count), "%u",
		         (unsigned)app->state.notification_total % 100u);

		const float text_w = text_width(count, TEXT_MICRO);
		const float pill_w = text_w + 22.0f;
		const float pill_h = 18.0f;
		const float pill_x = badge_left - pill_w;
		const float middle = 7.0f + pill_h * 0.5f;

		draw_round_rect(pill_x, 7.0f, pill_w, pill_h, pill_h * 0.5f, Z_CARD,
		                theme_alpha(COL_SURFACE, 0xCC));
		icons_draw(ICON_CHAT, pill_x + 10.0f, middle, 11.0f, Z_CONTENT,
		           COL_WARN);
		text_draw(pill_x + 17.0f, middle - TEXT_LINE_PX(TEXT_MICRO) * 0.5f,
		          Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM, ALIGN_LEFT, count);

		badge_left = pill_x - 6.0f;
	}

	draw_link_badge(app, badge_left, 7.0f);
}

/** Vue applications : application active mise en avant, puis les autres. */
static void draw_apps(const App *app)
{
	/*
	 * Sur une page en mode liste, l'écran supérieur sert d'aperçu : il affiche
	 * le titre complet de l'élément désigné, que la largeur d'une colonne ne
	 * permet pas de montrer entièrement.
	 */
	const Page *current = app_current_page(app);
	if (current != NULL && current->layout == LAYOUT_LIST &&
	    app->list_focus >= 0 && app->list_focus < current->entry_count) {
		const ListEntry *entry = &current->entries[app->list_focus];

		const float top = HEADER_H + 6.0f;
		const float height = SCREEN_H - top - 8.0f;
		const float card_w = SCREEN_TOP_W - PAD * 2.0f;

		draw_shadow(PAD, top, card_w, height, 10.0f, Z_BG);
		draw_round_rect_vgrad(PAD, top, card_w, height, 10.0f, Z_CARD,
		                      COL_SURFACE, COL_SURFACE_LO);

		icons_draw(entry->icon, PAD + 32.0f, top + 34.0f, 30.0f, Z_CONTENT,
		           theme_mix(entry->color, COL_WHITE, 0.3f));

		text_draw_clipped(PAD + 58.0f, top + 16.0f, Z_CONTENT, TEXT_TITLE,
		                  COL_TEXT, ALIGN_LEFT, card_w - 74.0f, entry->label);

		if (entry->detail[0] != '\0') {
			text_draw_clipped(PAD + 58.0f, top + 42.0f, Z_CONTENT, TEXT_SMALL,
			                  COL_TEXT_DIM, ALIGN_LEFT, card_w - 74.0f,
			                  entry->detail);
		}

		if (entry->active) {
			text_draw(PAD + 58.0f, top + 66.0f, Z_CONTENT, TEXT_MICRO,
			          entry->color, ALIGN_LEFT, tr(STR_FOREGROUND));
		}

		/* Rappel du nombre d'éléments et de la position courante. */
		char counter[32];
		snprintf(counter, sizeof(counter), "%u / %u",
		         (unsigned)(app->list_focus + 1) % 100u,
		         (unsigned)current->entry_count % 100u);
		text_draw(PAD + card_w - 14.0f, top + height - 24.0f, Z_CONTENT,
		          TEXT_MICRO, COL_TEXT_FAINT, ALIGN_RIGHT, counter);
		return;
	}

	const float top = HEADER_H + 6.0f;
	const float height = SCREEN_H - top - 8.0f;
	const float card_w = SCREEN_TOP_W - PAD * 2.0f;

	draw_shadow(PAD, top, card_w, height, 10.0f, Z_BG);
	draw_round_rect_vgrad(PAD, top, card_w, height, 10.0f, Z_CARD, COL_SURFACE,
	                      COL_SURFACE_LO);

	/* Application active, en grand. */
	const bool has_active = app->state.active_app[0] != '\0';

	text_draw(PAD + 16.0f, top + 12.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_FOREGROUND));

	if (has_active) {
		icons_draw(ICON_APP, PAD + 26.0f, top + 44.0f, 22.0f, Z_CONTENT,
		           COL_ACCENT);
		text_draw_clipped(PAD + 44.0f, top + 32.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT,
		                  ALIGN_LEFT, card_w - 70.0f, app->state.active_app);
	} else {
		text_draw(PAD + 16.0f, top + 32.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT_FAINT,
		          ALIGN_LEFT, tr(STR_UNKNOWN));
	}

	/* Séparateur. */
	draw_rect(PAD + 16.0f, top + 66.0f, card_w - 32.0f, 1.0f, Z_CONTENT,
	          COL_BORDER);

	/* Autres applications, en pastilles. */
	if (app->state.app_count == 0) {
		text_draw(PAD + 16.0f, top + 78.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT,
		          ALIGN_LEFT, tr(STR_NO_APPS));
		return;
	}

	float x = PAD + 16.0f;
	float y = top + 76.0f;
	const float max_x = PAD + card_w - 16.0f;

	for (int i = 0; i < app->state.app_count; i++) {
		const char *name = app->state.apps[i];
		if (name[0] == '\0') {
			continue;
		}

		const bool active = has_active &&
		                    strcmp(name, app->state.active_app) == 0;

		const float label_w = text_width(name, TEXT_SMALL);
		const float chip_w = label_w + 18.0f;

		/* Passage à la ligne, puis abandon si la carte est pleine. */
		if (x + chip_w > max_x) {
			x = PAD + 16.0f;
			y += 22.0f;
			if (y + 18.0f > top + height - 6.0f) {
				break;
			}
		}

		const u32 chip_bg = active ? theme_alpha(COL_ACCENT, 0x30)
		                           : theme_alpha(COL_SURFACE_HI, 0xCC);
		const u32 chip_fg = active ? COL_ACCENT : COL_TEXT_DIM;

		draw_round_rect(x, y, chip_w, 18.0f, 9.0f, Z_CONTENT, chip_bg);
		if (active) {
			draw_round_rect_outline(x, y, chip_w, 18.0f, 9.0f, 1.0f, Z_OVERLAY,
			                        theme_alpha(COL_ACCENT, 0x88));
		}
		text_draw(x + 9.0f, y + 3.0f, Z_OVERLAY, TEXT_SMALL, chip_fg, ALIGN_LEFT,
		          name);

		x += chip_w + 6.0f;
	}
}

/** Met en forme une ancienneté : « 45 s », « 12 min », « 3 h ». */
static void format_age(int seconds, char *dest, size_t size)
{
	if (seconds < 60) {
		snprintf(dest, size, "%ds", seconds % 100);
	} else if (seconds < 3600) {
		snprintf(dest, size, "%dmin", (seconds / 60) % 100);
	} else {
		snprintf(dest, size, "%dh", (seconds / 3600) % 100);
	}
}

/** Vue notifications : les plus récentes, avec application et ancienneté. */
static void draw_notifications(const App *app)
{
	const float top = HEADER_H + 6.0f;
	const float height = SCREEN_H - top - 8.0f;
	const float card_w = SCREEN_TOP_W - PAD * 2.0f;

	draw_shadow(PAD, top, card_w, height, 10.0f, Z_BG);
	draw_round_rect_vgrad(PAD, top, card_w, height, 10.0f, Z_CARD, COL_SURFACE,
	                      COL_SURFACE_LO);

	text_draw(PAD + 16.0f, top + 8.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_NOTIFICATIONS));

	if (app->state.notification_total > 0) {
		char total[8];
		snprintf(total, sizeof(total), "%u",
		         (unsigned)app->state.notification_total % 100u);
		text_draw(PAD + card_w - 16.0f, top + 8.0f, Z_CONTENT, TEXT_MICRO,
		          COL_WARN, ALIGN_RIGHT, total);
	}

	if (app->state.notification_count == 0) {
		icons_draw(ICON_STAR, SCREEN_TOP_W * 0.5f, top + height * 0.44f, 34.0f,
		           Z_CONTENT, theme_alpha(COL_TEXT_FAINT, 0x88));
		text_draw(SCREEN_TOP_W * 0.5f, top + height * 0.62f, Z_CONTENT,
		          TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER,
		          tr(STR_NO_NOTIFICATIONS));
		return;
	}

	/*
	 * Chaque notification occupe une bande : application et ancienneté sur la
	 * première ligne, titre sur la seconde, corps si la place le permet.
	 */
	const float list_top = top + 24.0f;
	const float row_h = (height - 32.0f) / (float)MAX_NOTIFICATIONS;

	for (int i = 0; i < app->state.notification_count; i++) {
		const float y = list_top + (float)i * row_h;
		const bool first = (i == 0);

		/* Séparateur discret entre les entrées. */
		if (i > 0) {
			draw_rect(PAD + 16.0f, y - 1.0f, card_w - 32.0f, 1.0f, Z_CONTENT,
			          theme_alpha(COL_BORDER, 0x66));
		}

		const u32 tint = first ? COL_WARN : COL_TEXT_DIM;

		icons_draw(app->state.notifications[i].icon, PAD + 28.0f,
		           y + row_h * 0.42f, 15.0f, Z_CONTENT, tint);

		char age[12];
		format_age(app->state.notifications[i].age, age, sizeof(age));
		text_draw(PAD + card_w - 16.0f, y + 2.0f, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_RIGHT, age);

		const float text_x = PAD + 42.0f;
		const float text_w = card_w - 58.0f - text_width(age, TEXT_MICRO) - 8.0f;

		text_draw_clipped(text_x, y + 1.0f, Z_CONTENT, TEXT_MICRO, tint,
		                  ALIGN_LEFT, text_w,
		                  app->state.notifications[i].app);

		text_draw_clipped(text_x, y + 14.0f, Z_CONTENT, TEXT_SMALL,
		                  first ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT,
		                  card_w - 58.0f,
		                  app->state.notifications[i].title);

		/* Le corps n'apparaît que si la bande est assez haute. */
		if (row_h >= 42.0f && app->state.notifications[i].body[0] != '\0') {
			text_draw_clipped(text_x, y + 30.0f, Z_CONTENT, TEXT_MICRO,
			                  COL_TEXT_FAINT, ALIGN_LEFT, card_w - 58.0f,
			                  app->state.notifications[i].body);
		}
	}
}

/** Écran de connexion, affiché tant que la configuration n'est pas reçue. */
static void draw_link_screen(const App *app)
{
	const float cx = SCREEN_TOP_W * 0.5f;

	if (app->settings.companion) {
		ui_companion_draw(app->link == LINK_CONNECTING ? DECKY_SEARCH : DECKY_CONFUSED,
		                  app->uptime, cx - 40, 42, 2);
	} else {
		icons_draw(ICON_POWER, cx, 96.0f, 52.0f, Z_CONTENT,
		           app->link == LINK_CONNECTING ? COL_WARN : COL_TEXT_FAINT);
	}

	text_draw(cx, 126.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER,
	          app->link == LINK_CONNECTING ? tr(STR_CONNECTING_TO_PC)
	                                       : tr(STR_PC_NOT_FOUND));

	char detail[128];
	snprintf(detail, sizeof(detail), "%s:%d", app->settings.host,
	         app->settings.port);
	text_draw(cx, 152.0f, Z_CONTENT, TEXT_BODY, COL_TEXT_DIM, ALIGN_CENTER, detail);

	/*
	 * Préciser l'origine de l'adresse évite une confusion fréquente : sans
	 * cette mention, on peut corriger le fichier de réglages sans comprendre
	 * pourquoi l'application utilise une autre adresse.
	 */
	if (app->host_from_netload) {
		text_draw(cx, 168.0f, Z_CONTENT, TEXT_MICRO, COL_ACCENT, ALIGN_CENTER,
		          tr(STR_DETECTED_VIA_LINK));
	}

	/* Les lignes suivantes descendent si la mention 3dslink est affichée. */
	const float shift = app->host_from_netload ? 14.0f : 0.0f;

	if (app->link == LINK_OFFLINE) {
		if (app->link_error[0] != '\0') {
			text_draw_clipped(cx, 172.0f + shift, Z_CONTENT, TEXT_SMALL, COL_ERR,
			                  ALIGN_CENTER, SCREEN_TOP_W - 40.0f,
			                  app->link_error);
		}

		char retry[64];
		snprintf(retry, sizeof(retry), tr(STR_RETRY_IN),
		         app->reconnect_in < 0.0f ? 0.0f : app->reconnect_in + 0.5f);
		text_draw(cx, 190.0f + shift, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT,
		          ALIGN_CENTER, retry);
	}

	if (!app->host_from_netload) {
		text_draw(cx, SCREEN_H - 26.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT,
		          ALIGN_CENTER, tr(STR_HELP_RELOAD));
	}
}

/** Notification superposée, avec fondu. */
static void draw_toast(const App *app)
{
	if (app->toast.alpha <= 0.01f || app->toast.text[0] == '\0') {
		return;
	}

	const u8 alpha = (u8)(app->toast.alpha * 235.0f);
	const u32 accent = app->toast.error ? COL_ERR : COL_OK;

	const float text_w = text_width(app->toast.text, TEXT_BODY);
	float w = text_w + 46.0f;
	const float max_w = SCREEN_TOP_W - 32.0f;
	if (w > max_w) {
		w = max_w;
	}

	const float h = 30.0f;
	const float x = (SCREEN_TOP_W - w) * 0.5f;
	/* Glisse légèrement vers le haut en apparaissant. */
	const float y = HEADER_H + 8.0f - (1.0f - app->toast.alpha) * 6.0f;

	draw_shadow(x, y, w, h, 15.0f, Z_OVERLAY);
	draw_round_rect(x, y, w, h, 15.0f, Z_OVERLAY,
	                theme_alpha(COL_SURFACE_HI, alpha));
	draw_round_rect_outline(x, y, w, h, 15.0f, 1.0f, Z_OVERLAY,
	                        theme_alpha(accent, (u8)(alpha * 0.7f)));

	/*
	 * L'icône transmise par la notification est privilégiée : reconnaître
	 * l'application d'un coup d'œil compte plus qu'un symbole générique.
	 */
	IconId toast_icon = app->toast.icon;
	if (toast_icon == ICON_NONE) {
		toast_icon = app->toast.error ? ICON_MIC_OFF : ICON_STAR;
	}

	icons_draw(toast_icon, x + 17.0f, y + h * 0.5f, 15.0f, Z_OVERLAY,
	           theme_alpha(accent, alpha));

	text_draw_clipped(x + 30.0f, y + 7.0f, Z_OVERLAY, TEXT_BODY,
	                  theme_alpha(COL_TEXT, alpha), ALIGN_LEFT, w - 40.0f,
	                  app->toast.text);
}

void ui_draw_top(const App *app)
{
	if (ui_companion_standby(app)) {
		ui_companion_standby_draw(app);
		draw_toast(app);
		return;
	}
	/*
	 * Tant que la configuration n'est pas arrivée, l'écran de liaison est plus
	 * utile qu'un tableau de bord vide : il indique quoi corriger.
	 */
	if (!app->config_received) {
		draw_background(app);
		draw_header(app);
		draw_link_screen(app);
		draw_toast(app);
		return;
	}

	const DashboardMode mode = app_effective_dashboard(app);

	/*
	 * Le mode cadre occupe tout l'écran : il dessine son propre fond teinté et
	 * se passe des bandeaux, il est donc traité avant eux.
	 */
	if (mode == DASH_FRAME) {
		ui_top_frame_draw(app);
		draw_toast(app);
		return;
	}

	draw_background(app);

	/*
	 * La vue pochette reprend le fond immersif du mode cadre. Le bandeau est
	 * dessine ensuite par-dessus afin de conserver heure, date et connexion.
	 */
	if (mode == DASH_MEDIA) {
		ui_top_media_draw(app);
		draw_header(app);
		draw_toast(app);
		return;
	}
	if (mode == DASH_LYRICS) {
		ui_top_lyrics_draw(app);
		draw_header(app);
		draw_toast(app);
		return;
	}

	draw_header(app);

	switch (mode) {
	case DASH_MEDIA:
	case DASH_LYRICS:
		break; /* traite plus haut pour respecter l'ordre des plans */
	case DASH_SYSTEM:
		ui_top_system_draw(app);
		break;
	case DASH_STREAM_CHAT:
		ui_top_chat_draw(app);
		break;
	case DASH_EXTENSION:
		extension_dashboard_draw(app);
		break;
	case DASH_AUDIO:
		ui_top_audio_draw(app);
		break;
	case DASH_NOTIFICATIONS:
		draw_notifications(app);
		break;
	case DASH_FRAME:
		break; /* traité plus haut */
	case DASH_APPS:
	case DASH_AUTO:
	default:
		draw_apps(app);
		break;
	}

	draw_toast(app);
}
