#include "app.h"
#include "sound.h"

const Page *app_current_page(const App *app)
{
	return model_page_at(&app->config, app->current_page);
}

DashboardMode app_effective_dashboard(const App *app)
{
	/*
	 * Le plein écran est un état de l'affichage, pas une page : il prime donc
	 * sur le tableau de bord de la page courante. C'est ce qui permet de
	 * l'activer depuis n'importe où et de le réutiliser pour la veille.
	 */
	if (app->frame_mode) {
		return DASH_FRAME;
	}

	const Page *page = app_current_page(app);
	const DashboardMode mode = (page != NULL) ? page->dashboard : DASH_AUTO;

	if (mode != DASH_AUTO) {
		return mode;
	}

	/*
	 * En mode automatique, le média prime dès qu'un titre est connu : c'est
	 * l'information la plus utile en un coup d'œil.
	 */
	if (app->state.media_present) {
		return DASH_MEDIA;
	}
	return DASH_APPS;
}

void app_goto_page(App *app, int index)
{
	if (app->config.page_count <= 0) {
		return;
	}
	if (index < 0 || index >= app->config.page_count) {
		return;
	}
	if (index == app->current_page) {
		return;
	}

	app->current_page = index;
	app->page_fade = 0.0f; /* relance l'animation d'entrée */
	sound_play(SOUND_PAGE);
	app->enter_anim = 0.0f;

	/* Le défilement repart du haut à chaque changement de page. */
	app->list_scroll = 0.0f;
	app->list_target = 0.0f;
	app->list_focus = -1;
	app->grid_focus = -1;
	app_touch_activity(app);
}

void app_cycle_page(App *app, int delta)
{
	const int count = app->config.page_count;
	if (count <= 0) {
		return;
	}

	int index = app->current_page + delta;
	while (index < 0) {
		index += count;
	}
	index %= count;

	app_goto_page(app, index);
}
