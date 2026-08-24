/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "artwork.h"
#include "draw.h"
#include "i18n.h"
#include "icons.h"
#include "text.h"
#include "theme.h"
#include "ui.h"

/*
 * L'écran supérieur est un tableau de bord contextuel. Il n'est pas un miroir
 * de l'écran tactile : il montre ce que l'on veut lire d'un coup d'œil, alors
 * que l'écran bas sert à agir.
 *
 * Mise en page :
 *   - un bandeau supérieur avec heure, hôte et état de connexion ;
 *   - une zone centrale variable selon le mode ;
 *   - un bandeau inférieur avec volume et micro.
 */

#define HEADER_H 30.0f
#define FOOTER_H 34.0f
#define PAD 12.0f

/** Dessine le fond, légèrement dégradé pour éviter un aplat terne. */
static void draw_background(const App *app)
{
	const u32 top = app->dimmed ? C2D_Color32(0x06, 0x07, 0x0B, 0xFF) : COL_BG;
	const u32 bottom =
	    app->dimmed ? C2D_Color32(0x04, 0x05, 0x08, 0xFF) : COL_BG_ALT;
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG, top, bottom);

	/* Liseré d'accent en haut, discret repère visuel. */
	const u32 accent = (app->link == LINK_ONLINE) ? COL_ACCENT : COL_TEXT_FAINT;
	draw_rect(0.0f, 0.0f, SCREEN_TOP_W, 2.0f, Z_CARD, theme_alpha(accent, 0x99));
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
	if (app->state.date[0] != '\0') {
		const float clock_middle = 8.0f + TEXT_LINE_PX(TEXT_TITLE) * 0.5f;

		text_draw_clipped(SCREEN_TOP_W * 0.5f,
		                  clock_middle - TEXT_LINE_PX(TEXT_SMALL) * 0.5f,
		                  Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER,
		                  150.0f, app->state.date);
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

/** Jauge horizontale avec libellé, utilisée pour le volume, le CPU, etc. */
static void draw_gauge(float x, float y, float w, const char *label, int value,
                       u32 color, bool known)
{
	text_draw(x, y, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT, ALIGN_LEFT, label);

	char text[16];
	if (known) {
		snprintf(text, sizeof(text), "%d%%", value);
	} else {
		snprintf(text, sizeof(text), "--");
	}
	text_draw(x + w, y, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM, ALIGN_RIGHT, text);

	const float ratio = known ? (float)value / 100.0f : 0.0f;
	draw_progress(x, y + 14.0f, w, 5.0f, ratio, Z_CONTENT, COL_SURFACE_HI,
	              color);
}

static void draw_footer(const App *app)
{
	const float y = SCREEN_H - FOOTER_H;
	draw_rect(0.0f, y, SCREEN_TOP_W, FOOTER_H, Z_CARD,
	          theme_alpha(COL_SURFACE_LO, 0xE0));
	draw_rect(0.0f, y, SCREEN_TOP_W, 1.0f, Z_CARD, COL_BORDER);

	/*
	 * Volume à gauche. Lorsque le lecteur expose son propre volume, les deux
	 * sont affichés : c'est indispensable quand la musique sort sur une enceinte
	 * externe, car le volume du système n'agit alors plus sur elle.
	 */
	const bool vol_known = app->state.volume >= 0;
	const int volume = vol_known ? app->state.volume : 0;
	const u32 vol_color = app->state.muted ? COL_ERR : COL_ACCENT;
	const bool has_app_volume = app->state.app_volume >= 0;

	icons_draw(app->state.muted ? ICON_VOLUME_MUTE : ICON_VOLUME_UP, PAD + 8.0f,
	           has_app_volume ? y + 11.0f : y + 17.0f, has_app_volume ? 14.0f : 20.0f,
	           Z_CONTENT, vol_color);

	if (has_app_volume) {
		/*
		 * Deux jauges compactes empilées, chacune précédée d'un libellé.
		 *
		 * La colonne des barres est calculée depuis la largeur réelle du plus
		 * long libellé : un écart fixe faisait chevaucher la barre et le texte
		 * « MUS », plus large que « PC ».
		 */
		const float label_x = PAD + 19.0f;
		const float label_w = text_width("MUS", TEXT_MICRO);
		const float bar_x = label_x + label_w + 7.0f;
		const float bar_w = 78.0f;
		const float value_x = bar_x + bar_w + 6.0f;

		/* Le libellé est centré sur sa barre, pour un alignement optique net. */
		const float bar_h = 4.0f;
		const float label_offset = (bar_h - TEXT_LINE_PX(TEXT_MICRO)) * 0.5f;

		const float pc_bar_y = y + 8.0f;
		const float mus_bar_y = y + 21.0f;

		text_draw(label_x, pc_bar_y + label_offset, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_LEFT, "PC");
		draw_progress(bar_x, pc_bar_y, bar_w, bar_h,
		              vol_known ? (float)volume / 100.0f : 0.0f, Z_CONTENT,
		              COL_SURFACE_HI, vol_color);

		/*
		 * Les volumes sont bornés à l'analyse du message, mais le compilateur
		 * ne peut pas le déduire : le modulo le lui garantit et écarte tout
		 * risque de troncature.
		 */
		char pc_text[8];
		snprintf(pc_text, sizeof(pc_text), "%u", (unsigned)volume % 101u);
		text_draw(value_x, pc_bar_y + label_offset, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_DIM, ALIGN_LEFT, pc_text);

		text_draw(label_x, mus_bar_y + label_offset, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_LEFT, "MUS");
		draw_progress(bar_x, mus_bar_y, bar_w, bar_h,
		              (float)app->state.app_volume / 100.0f, Z_CONTENT,
		              COL_SURFACE_HI, COL_BLUE);

		char app_text[8];
		snprintf(app_text, sizeof(app_text), "%u",
		         (unsigned)app->state.app_volume % 101u);
		text_draw(value_x, mus_bar_y + label_offset, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_DIM, ALIGN_LEFT, app_text);
	} else {
		draw_progress(PAD + 24.0f, y + 14.0f, 110.0f, 6.0f,
		              vol_known ? (float)volume / 100.0f : 0.0f, Z_CONTENT,
		              COL_SURFACE_HI, vol_color);

		char vol_text[16];
		if (vol_known) {
			snprintf(vol_text, sizeof(vol_text), "%d", volume);
		} else {
			snprintf(vol_text, sizeof(vol_text), "--");
		}
		text_draw(PAD + 142.0f, y + 10.0f, Z_CONTENT, TEXT_BODY, COL_TEXT_DIM,
		          ALIGN_LEFT, vol_text);
	}

	/*
	 * Micro à droite, l'information la plus critique en visioconférence.
	 *
	 * L'indicateur n'est affiché que si l'état est réellement connu. Sur
	 * certaines cartes son, le niveau d'entrée n'est pas lisible : afficher un
	 * point d'interrogation occuperait alors une place précieuse sans rien
	 * apprendre. Le bouton de la grille reste évidemment fonctionnel.
	 */
	if (app->state.mic_known) {
		const bool mic_muted = app->state.mic_muted;
		const u32 mic_color = mic_muted ? COL_ERR : COL_OK;
		const char *mic_label =
		    mic_muted ? tr(STR_MIC_MUTED) : tr(STR_MIC_ACTIVE);

		const float label_w = text_width(mic_label, TEXT_SMALL);
		const float icon_cx = SCREEN_TOP_W - PAD - label_w - 13.0f;
		const float middle = y + FOOTER_H * 0.5f;

		icons_draw(mic_muted ? ICON_MIC_OFF : ICON_MIC, icon_cx, middle, 18.0f,
		           Z_CONTENT, mic_color);
		text_draw(SCREEN_TOP_W - PAD,
		          middle - TEXT_LINE_PX(TEXT_SMALL) * 0.5f, Z_CONTENT,
		          TEXT_SMALL, mic_color, ALIGN_RIGHT, mic_label);
	}
}

/** Vue média : titre, artiste, pochette symbolique et état de lecture. */
static void draw_media(const App *app)
{
	const float top = HEADER_H + 6.0f;
	const float height = SCREEN_H - FOOTER_H - top - 8.0f;

	draw_shadow(PAD, top, SCREEN_TOP_W - PAD * 2.0f, height, 10.0f, Z_BG);
	draw_round_rect_vgrad(PAD, top, SCREEN_TOP_W - PAD * 2.0f, height, 10.0f,
	                      Z_CARD, COL_SURFACE, COL_SURFACE_LO);

	if (!app->state.media_present) {
		icons_draw(ICON_MUSIC, SCREEN_TOP_W * 0.5f, top + height * 0.42f, 42.0f,
		           Z_CONTENT, COL_TEXT_FAINT);
		text_draw(SCREEN_TOP_W * 0.5f, top + height * TEXT_TITLE, Z_CONTENT, TEXT_SMALL,
		          COL_TEXT_FAINT, ALIGN_CENTER, tr(STR_NOTHING_PLAYING));
		return;
	}

	/* Vignette carrée à gauche : la pochette réelle si le PC l'a transmise. */
	const float art = height - 26.0f;
	const float art_x = PAD + 13.0f;
	const float art_y = top + 13.0f;

	const u32 tint = app->state.media_playing ? COL_ACCENT : COL_TEXT_FAINT;

	draw_shadow(art_x, art_y, art, art, 7.0f, Z_CARD);

	if (artwork_available()) {
		/*
		 * L'image est dessinée puis encadrée d'un liseré sombre : sans lui, une
		 * pochette claire se fondrait dans le fond de la carte.
		 */
		artwork_draw(art_x, art_y, art, Z_CONTENT, 0xFF);
		draw_round_rect_outline(art_x, art_y, art, art, 4.0f, 1.0f, Z_OVERLAY,
		                        theme_alpha(COL_WHITE, 0x28));
	} else {
		/* Substitut : le morceau est connu mais l'image n'est pas encore là. */
		draw_round_rect_vgrad(art_x, art_y, art, art, 7.0f, Z_CONTENT,
		                      theme_alpha(tint, 0x30),
		                      theme_alpha(tint, 0x14));
		draw_round_rect_outline(art_x, art_y, art, art, 7.0f, 1.2f, Z_CONTENT,
		                        theme_alpha(tint, 0x55));
		icons_draw(ICON_MUSIC, art_x + art * 0.5f, art_y + art * 0.5f,
		           art * 0.50f, Z_OVERLAY, theme_alpha(tint, 0xCC));
	}

	/* Bloc texte à droite de la vignette. */
	const float text_x = art_x + art + 15.0f;
	const float text_w = SCREEN_TOP_W - PAD - 13.0f - text_x;

	/* Nom du lecteur, en petites capitales colorées. */
	if (app->state.media_app[0] != '\0') {
		icons_draw(ICON_MUSIC, text_x + 5.0f, art_y + 7.0f, 11.0f, Z_CONTENT,
		           tint);
		text_draw_clipped(text_x + 14.0f, art_y + 1.0f, Z_CONTENT, TEXT_SMALL, tint,
		                  ALIGN_LEFT, text_w - 14.0f, app->state.media_app);
	}

	text_draw_clipped(text_x, art_y + 18.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT,
	                  ALIGN_LEFT, text_w, app->state.media_title);

	if (app->state.media_artist[0] != '\0') {
		text_draw_clipped(text_x, art_y + 42.0f, Z_CONTENT, TEXT_BODY, COL_TEXT_DIM,
		                  ALIGN_LEFT, text_w, app->state.media_artist);
	}

	if (app->state.media_album[0] != '\0') {
		text_draw_clipped(text_x, art_y + 60.0f, Z_CONTENT, TEXT_SMALL,
		                  COL_TEXT_FAINT, ALIGN_LEFT, text_w,
		                  app->state.media_album);
	}

	/*
	 * Progression de lecture, si le PC la connaît. Une barre pleine largeur est
	 * plus lisible qu'un simple texte et donne une notion immédiate d'avancement.
	 */
	const float bar_y = art_y + art - 15.0f;

	if (app->state.media_duration > 0) {
		const int position = (app->state.media_position >= 0)
		                         ? app->state.media_position
		                         : 0;
		const float ratio =
		    (float)position / (float)app->state.media_duration;

		char elapsed[16];
		char total[16];
		snprintf(elapsed, sizeof(elapsed), "%d:%02d", position / 60,
		         position % 60);
		snprintf(total, sizeof(total), "%d:%02d",
		         app->state.media_duration / 60,
		         app->state.media_duration % 60);

		const float time_w = 30.0f;
		text_draw(text_x, bar_y - 3.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM,
		          ALIGN_LEFT, elapsed);
		text_draw(text_x + text_w, bar_y - 3.0f, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_RIGHT, total);

		draw_progress(text_x + time_w, bar_y + 2.0f,
		              text_w - time_w * 2.0f - 4.0f, 4.0f, ratio, Z_CONTENT,
		              theme_alpha(COL_SURFACE_HI, 0xEE), tint);
	} else {
		/* Sans durée connue, on se limite à l'état de lecture. */
		const IconId icon = app->state.media_playing ? ICON_PLAY : ICON_PAUSE;
		const char *label = app->state.media_playing ? tr(STR_PLAYING) : tr(STR_PAUSED);

		icons_draw(icon, text_x + 6.0f, bar_y + 3.0f, 13.0f, Z_CONTENT, tint);
		text_draw(text_x + 16.0f, bar_y - 3.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM,
		          ALIGN_LEFT, label);
	}
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
		const float height = SCREEN_H - FOOTER_H - top - 8.0f;
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
	const float height = SCREEN_H - FOOTER_H - top - 8.0f;
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

/** Vue système : jauges CPU, mémoire, volume et batterie de la console. */
static void draw_system(const App *app)
{
	const float top = HEADER_H + 6.0f;
	const float height = SCREEN_H - FOOTER_H - top - 8.0f;
	const float card_w = SCREEN_TOP_W - PAD * 2.0f;

	draw_shadow(PAD, top, card_w, height, 10.0f, Z_BG);
	draw_round_rect_vgrad(PAD, top, card_w, height, 10.0f, Z_CARD, COL_SURFACE,
	                      COL_SURFACE_LO);

	const float col_w = (card_w - 48.0f) * 0.5f;
	const float left = PAD + 16.0f;
	const float right = left + col_w + 16.0f;

	draw_gauge(left, top + 16.0f, col_w, tr(STR_PROCESSOR), app->state.cpu, COL_BLUE,
	           app->state.cpu >= 0);
	draw_gauge(right, top + 16.0f, col_w, tr(STR_MEMORY), app->state.memory,
	           COL_WARN, app->state.memory >= 0);

	draw_gauge(left, top + 58.0f, col_w, tr(STR_VOLUME), app->state.volume,
	           app->state.muted ? COL_ERR : COL_ACCENT, app->state.volume >= 0);

	/* Hôte connecté. */
	text_draw(right, top + 58.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT, ALIGN_LEFT,
	          tr(STR_COMPUTER));
	text_draw_clipped(right, top + 72.0f, Z_CONTENT, TEXT_BODY, COL_TEXT,
	                  ALIGN_LEFT, col_w,
	                  app->state.host[0] != '\0' ? app->state.host : "--");
}

/**
 * Barre verticale d'égaliseur.
 *
 * L'animation n'est pas une analyse du son : la console ne reçoit pas le flux
 * audio. Les hauteurs sont dérivées du volume et d'oscillations déphasées, ce
 * qui produit un mouvement crédible et vivant sans coût de calcul. Les barres
 * se figent lorsque la lecture est en pause, afin que l'affichage reste honnête.
 */
static void draw_equalizer(const App *app, float x, float y, float w, float h,
                           u32 color, int level, bool animated)
{
	const int bars = 14;
	const float gap = 2.0f;
	const float bar_w = (w - gap * (float)(bars - 1)) / (float)bars;

	const float base = (level > 0) ? (float)level / 100.0f : 0.0f;

	for (int i = 0; i < bars; i++) {
		float amount;

		if (animated && base > 0.01f) {
			/*
			 * Deux sinusoïdes de fréquences différentes par barre : le motif ne
			 * se répète pas de façon perceptible et évoque un vrai spectre.
			 */
			const float phase = (float)i * 0.7f;
			const float slow = sinf(app->uptime * 3.1f + phase);
			const float fast = sinf(app->uptime * 7.3f + phase * 1.9f);

			/* Les basses fréquences, à gauche, bougent plus amplement. */
			const float weight = 1.0f - (float)i / (float)bars * 0.45f;

			amount = base * weight * (0.55f + 0.30f * slow + 0.15f * fast);
		} else {
			/* En pause : profil statique, symétrique et discret. */
			const float centre = 1.0f - fabsf((float)i - 6.5f) / 7.0f;
			amount = base * centre * 0.35f;
		}

		if (amount < 0.05f) {
			amount = 0.05f;
		}
		if (amount > 1.0f) {
			amount = 1.0f;
		}

		const float bar_h = h * amount;
		const float bx = x + (float)i * (bar_w + gap);
		const float by = y + h - bar_h;

		/* Rail sombre en fond : la barre reste lisible même très basse. */
		draw_round_rect(bx, y, bar_w, h, bar_w * 0.4f, Z_CONTENT,
		                theme_alpha(COL_SURFACE_LO, 0xAA));

		/*
		 * Dégradé du bas vers le haut : la crête est plus claire, ce qui donne
		 * l'impression d'une intensité qui monte.
		 */
		draw_round_rect_vgrad(bx, by, bar_w, bar_h, bar_w * 0.4f, Z_OVERLAY,
		                      theme_mix(color, COL_WHITE, 0.45f), color);
	}
}

/** Vue audio : volumes, sortie active et égaliseur. */
static void draw_audio(const App *app)
{
	const float top = HEADER_H + 6.0f;
	const float height = SCREEN_H - FOOTER_H - top - 8.0f;
	const float card_w = SCREEN_TOP_W - PAD * 2.0f;

	draw_shadow(PAD, top, card_w, height, 10.0f, Z_BG);
	draw_round_rect_vgrad(PAD, top, card_w, height, 10.0f, Z_CARD, COL_SURFACE,
	                      COL_SURFACE_LO);

	/* Sortie audio active, mise en avant : c'est l'information structurante. */
	const bool has_output = app->state.audio_output[0] != '\0';

	icons_draw(ICON_VOLUME_UP, PAD + 22.0f, top + 20.0f, 17.0f, Z_CONTENT,
	           COL_ACCENT);
	text_draw(PAD + 36.0f, top + 8.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_AUDIO_OUTPUT));
	text_draw_clipped(PAD + 36.0f, top + 20.0f, Z_CONTENT, TEXT_SMALL,
	                  has_output ? COL_TEXT : COL_TEXT_FAINT, ALIGN_LEFT,
	                  card_w - 60.0f,
	                  has_output ? app->state.audio_output : tr(STR_OUTPUT_UNKNOWN));

	/* Pastilles des autres sorties : montre ce vers quoi on peut basculer. */
	if (app->state.audio_output_count > 1) {
		float chip_x = PAD + 36.0f;
		const float chip_y = top + 42.0f;
		const float limit = PAD + card_w - 12.0f;

		for (int i = 0; i < app->state.audio_output_count; i++) {
			const char *name = app->state.audio_outputs[i];
			if (name[0] == '\0') {
				continue;
			}

			const bool current =
			    has_output && strcmp(name, app->state.audio_output) == 0;

			const float label_w = text_width(name, TEXT_MICRO);
			const float chip_w = label_w + 14.0f;
			if (chip_x + chip_w > limit) {
				break;
			}

			draw_round_rect(chip_x, chip_y, chip_w, 15.0f, 7.5f, Z_CONTENT,
			                current ? theme_alpha(COL_ACCENT, 0x40)
			                        : theme_alpha(COL_SURFACE_HI, 0xAA));
			text_draw(chip_x + 7.0f, chip_y + 2.0f, Z_OVERLAY, TEXT_MICRO,
			          current ? COL_ACCENT : COL_TEXT_FAINT, ALIGN_LEFT, name);

			chip_x += chip_w + 5.0f;
		}
	}

	/* Égaliseur, sur la moitié basse de la carte. */
	const float eq_y = top + 64.0f;
	const float eq_h = height - 64.0f - 32.0f;

	const int level = (app->state.app_volume >= 0) ? app->state.app_volume
	                                               : app->state.volume;
	const bool animated = app->state.media_playing && !app->state.muted;
	const u32 eq_color = app->state.muted ? COL_ERR : COL_ACCENT;

	if (eq_h > 10.0f) {
		draw_equalizer(app, PAD + 16.0f, eq_y, card_w - 32.0f, eq_h, eq_color,
		               level, animated);
	}

	/* Deux valeurs chiffrées sous l'égaliseur. */
	const float info_y = top + height - 24.0f;
	const float half = card_w * 0.5f;

	char text[24];

	snprintf(text, sizeof(text), "PC %u %%",
	         (unsigned)(app->state.volume < 0 ? 0 : app->state.volume) % 101u);
	text_draw(PAD + 16.0f, info_y, Z_CONTENT, TEXT_SMALL,
	          app->state.muted ? COL_ERR : COL_TEXT_DIM, ALIGN_LEFT, text);

	if (app->state.app_volume >= 0) {
		snprintf(text, sizeof(text), "%s %u %%", tr(STR_MUSIC),
		         (unsigned)app->state.app_volume % 101u);
		text_draw(PAD + half + 16.0f, info_y, Z_CONTENT, TEXT_SMALL, COL_BLUE,
		          ALIGN_LEFT, text);
	} else if (app->state.media_present) {
		text_draw(PAD + half + 16.0f, info_y, Z_CONTENT, TEXT_SMALL, COL_TEXT_FAINT,
		          ALIGN_LEFT, tr(STR_MUSIC));
	}
}

/**
 * Mode cadre à musique : la console devient un objet posé sur le bureau.
 *
 * La pochette occupe la hauteur disponible, le fond reprend sa couleur
 * dominante et les bandeaux habituels disparaissent. L'heure reste affichée,
 * discrètement, pour que l'objet garde une utilité au repos.
 */
static void draw_frame_mode(const App *app)
{
	const u32 accent = app->state.media_accent_known ? app->state.media_accent
	                                                 : COL_ACCENT;

	/*
	 * Fond teinté : un dégradé sombre vers la couleur de la pochette suffit à
	 * donner une impression d'ambiance sans nuire à la lisibilité du texte.
	 */
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, accent, 0.16f),
	                theme_mix(COL_BG, accent, 0.04f));

	if (!app->state.media_present) {
		icons_draw(ICON_MUSIC, SCREEN_TOP_W * 0.5f, SCREEN_H * 0.42f, 56.0f,
		           Z_CONTENT, theme_alpha(COL_TEXT_FAINT, 0xAA));
		text_draw(SCREEN_TOP_W * 0.5f, SCREEN_H * TEXT_LARGE, Z_CONTENT, TEXT_BODY,
		          COL_TEXT_FAINT, ALIGN_CENTER, tr(STR_NOTHING_PLAYING));
		text_draw(SCREEN_TOP_W * 0.5f, SCREEN_H - 24.0f, Z_CONTENT, TEXT_BODY,
		          COL_TEXT_FAINT, ALIGN_CENTER,
		          app->state.time[0] != '\0' ? app->state.time
		                                     : app->local_time);
		return;
	}

	/* Pochette carrée, centrée verticalement, occupant presque tout l'écran. */
	const float art = SCREEN_H - 34.0f;
	const float art_x = 18.0f;
	const float art_y = 17.0f;

	/* Halo coloré derrière la pochette : suggère une lumière diffuse. */
	draw_round_rect(art_x - 4.0f, art_y - 4.0f, art + 8.0f, art + 8.0f, 12.0f,
	                Z_BG, theme_alpha(accent, 0x3A));

	if (artwork_available()) {
		artwork_draw(art_x, art_y, art, Z_CARD, 0xFF);
		draw_round_rect_outline(art_x, art_y, art, art, 4.0f, 1.2f, Z_CONTENT,
		                        theme_alpha(COL_WHITE, 0x33));
	} else {
		draw_round_rect_vgrad(art_x, art_y, art, art, 10.0f, Z_CARD,
		                      theme_alpha(accent, 0x44),
		                      theme_alpha(accent, 0x1A));
		icons_draw(ICON_MUSIC, art_x + art * 0.5f, art_y + art * 0.5f,
		           art * 0.45f, Z_OVERLAY, theme_alpha(COL_WHITE, 0xAA));
	}

	/* Bloc d'informations à droite de la pochette. */
	const float text_x = art_x + art + 18.0f;
	const float text_w = SCREEN_TOP_W - 16.0f - text_x;

	/*
	 * Heure discrète en haut, sauf en veille : l'écran tactile l'affiche alors
	 * en grand avec la date, la répéter ici n'apporterait rien et chargerait
	 * inutilement l'image.
	 */
	if (!app->frame_from_idle) {
		text_draw(SCREEN_TOP_W - 16.0f, art_y, Z_CONTENT, TEXT_SMALL,
		          theme_alpha(COL_TEXT, 0xAA), ALIGN_RIGHT,
		          app->state.time[0] != '\0' ? app->state.time
		                                     : app->local_time);
	}

	/* Titre sur deux niveaux de taille selon la place disponible. */
	text_draw_clipped(text_x, art_y + 42.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT,
	                  ALIGN_LEFT, text_w, app->state.media_title);

	if (app->state.media_artist[0] != '\0') {
		text_draw_clipped(text_x, art_y + 68.0f, Z_CONTENT, TEXT_BODY,
		                  theme_mix(COL_TEXT_DIM, accent, 0.45f), ALIGN_LEFT,
		                  text_w, app->state.media_artist);
	}

	if (app->state.media_album[0] != '\0') {
		text_draw_clipped(text_x, art_y + 88.0f, Z_CONTENT, TEXT_SMALL,
		                  COL_TEXT_FAINT, ALIGN_LEFT, text_w,
		                  app->state.media_album);
	}

	/* Progression, en bas du bloc. */
	if (app->state.media_duration > 0) {
		const int position =
		    (app->state.media_position >= 0) ? app->state.media_position : 0;

		char elapsed[16];
		snprintf(elapsed, sizeof(elapsed), "%d:%02d", position / 60,
		         position % 60);
		char total[16];
		snprintf(total, sizeof(total), "%d:%02d",
		         app->state.media_duration / 60,
		         app->state.media_duration % 60);

		const float bar_y = art_y + art - 26.0f;

		draw_progress(text_x, bar_y, text_w, 5.0f,
		              (float)position / (float)app->state.media_duration,
		              Z_CONTENT, theme_alpha(COL_SURFACE_HI, 0xDD), accent);

		text_draw(text_x, bar_y + 8.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_LEFT, elapsed);
		text_draw(text_x + text_w, bar_y + 8.0f, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_RIGHT, total);
	}

	/* État de lecture, sous forme de pastille discrète. */
	const IconId icon = app->state.media_playing ? ICON_PLAY : ICON_PAUSE;
	icons_draw(icon, text_x + 7.0f, art_y + 22.0f, 13.0f, Z_CONTENT, accent);

	if (app->state.media_app[0] != '\0') {
		text_draw_clipped(text_x + 18.0f, art_y + 16.0f, Z_CONTENT, TEXT_MICRO,
		                  theme_alpha(accent, 0xEE), ALIGN_LEFT, text_w - 18.0f,
		                  app->state.media_app);
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
	const float height = SCREEN_H - FOOTER_H - top - 8.0f;
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

	icons_draw(ICON_POWER, cx, 96.0f, 52.0f, Z_CONTENT,
	           app->link == LINK_CONNECTING ? COL_WARN : COL_TEXT_FAINT);

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
		draw_frame_mode(app);
		draw_toast(app);
		return;
	}

	draw_background(app);
	draw_header(app);

	switch (mode) {
	case DASH_MEDIA:
		draw_media(app);
		break;
	case DASH_SYSTEM:
		draw_system(app);
		break;
	case DASH_AUDIO:
		draw_audio(app);
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

	draw_footer(app);
	draw_toast(app);
}
