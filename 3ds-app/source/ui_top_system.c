/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file ui_top_system.c
 * @brief Cockpit de performances lisible à distance.
 *
 * La hiérarchie commence par un diagnostic humain. Les pourcentages et les
 * courbes viennent ensuite pour expliquer ce diagnostic, sans transformer la
 * console en tableau technique dense.
 */

#include "ui_top_system.h"

#include <stdio.h>

#include "draw.h"
#include "i18n.h"
#include "text.h"
#include "theme.h"

#define CONTENT_TOP 36.0f
#define CARD_W 182.0f
#define CARD_H 66.0f
#define LEFT_X 12.0f
#define RIGHT_X 206.0f

static u32 metric_color(int value, int warning, int critical)
{
	if (value < 0) {
		return COL_TEXT_FAINT;
	}
	if (value >= critical) {
		return COL_ERR;
	}
	if (value >= warning) {
		return COL_WARN;
	}
	return COL_ACCENT;
}

static void draw_card(float x, float y, float w, float h)
{
	draw_shadow(x, y, w, h, 9.0f, Z_BG);
	draw_round_rect_vgrad(x, y, w, h, 9.0f, Z_CARD, COL_SURFACE,
	                      COL_SURFACE_LO);
	draw_round_rect_outline(x, y, w, h, 9.0f, 1.0f, Z_CONTENT,
	                        theme_alpha(COL_BORDER, 0x78));
}

static void format_percent(int value, char *dest, size_t size)
{
	if (value < 0) {
		snprintf(dest, size, "--");
	} else {
		snprintf(dest, size, "%d%%", value);
	}
}

static void format_capacity(int first_mb, int total_mb, char *dest,
                            size_t size)
{
	if (first_mb < 0 || total_mb <= 0) {
		snprintf(dest, size, "--");
		return;
	}
	snprintf(dest, size, "%.1f / %.1f GB", (double)first_mb / 1024.0,
	         (double)total_mb / 1024.0);
}

static void format_rate(int kbps, char *dest, size_t size)
{
	if (kbps < 0) {
		snprintf(dest, size, "--");
	} else if (kbps < 1000) {
		snprintf(dest, size, "%d Kbps", kbps);
	} else if (kbps < 1000000) {
		snprintf(dest, size, "%.1f Mbps", (double)kbps / 1000.0);
	} else {
		snprintf(dest, size, "%.1f Gbps", (double)kbps / 1000000.0);
	}
}

typedef int (*HistoryGetter)(const PerformanceHistory *, int);

static void draw_sparkline(const PerformanceHistory *history,
                           HistoryGetter getter, float x, float y, float w,
                           float h, u32 color)
{
	/* Deux repères suffisent à lire la tendance sans quadrillage envahissant. */
	draw_line(x, y + h * 0.5f, x + w, y + h * 0.5f, 0.6f, Z_CONTENT,
	          theme_alpha(COL_BORDER, 0x64));
	draw_line(x, y + h, x + w, y + h, 0.6f, Z_CONTENT,
	          theme_alpha(COL_BORDER, 0x82));

	if (history->count < 2) {
		return;
	}

	const float step = w / (float)(PERFORMANCE_HISTORY_SAMPLES - 1);
	const float offset =
	    (float)(PERFORMANCE_HISTORY_SAMPLES - history->count) * step;
	int previous = getter(history, 0);
	for (int i = 1; i < history->count; i++) {
		const int value = getter(history, i);
		if (previous >= 0 && value >= 0) {
			const float x0 = x + offset + (float)(i - 1) * step;
			const float x1 = x + offset + (float)i * step;
			const float y0 = y + h - (float)previous / 100.0f * h;
			const float y1 = y + h - (float)value / 100.0f * h;
			draw_line(x0, y0, x1, y1, 1.5f, Z_OVERLAY, color);
		}
		previous = value;
	}
}

static void draw_cpu_card(const App *app, float x, float y)
{
	draw_card(x, y, CARD_W, CARD_H);
	const u32 color = metric_color(app->state.cpu, 75, 92);
	char value[12];
	format_percent(app->state.cpu, value, sizeof(value));

	text_draw(x + 10.0f, y + 7.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_PROCESSOR));
	text_draw(x + CARD_W - 10.0f, y + 7.0f, Z_OVERLAY, TEXT_MICRO,
	          COL_TEXT_FAINT, ALIGN_RIGHT, tr(STR_LAST_30_SECONDS));
	text_draw(x + 10.0f, y + 24.0f, Z_OVERLAY, TEXT_HUGE, color, ALIGN_LEFT,
	          value);
	draw_sparkline(&app->performance_history, performance_history_cpu,
	               x + 78.0f, y + 25.0f, CARD_W - 88.0f, 28.0f, color);
}

static void draw_memory_card(const App *app, float x, float y)
{
	draw_card(x, y, CARD_W, CARD_H);
	const u32 color = metric_color(app->state.memory, 82, 94);
	char value[12];
	char capacity[32];
	format_percent(app->state.memory, value, sizeof(value));
	format_capacity(app->state.memory_used_mb, app->state.memory_total_mb,
	                capacity, sizeof(capacity));

	text_draw(x + 10.0f, y + 7.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_MEMORY));
	text_draw(x + 10.0f, y + 23.0f, Z_OVERLAY, TEXT_LARGE, color, ALIGN_LEFT,
	          value);
	text_draw_clipped(x + 63.0f, y + 25.0f, Z_OVERLAY, TEXT_MICRO,
	                  COL_TEXT_DIM, ALIGN_LEFT, CARD_W - 73.0f, capacity);

	const float ratio = app->state.memory >= 0
	                        ? (float)app->state.memory / 100.0f
	                        : 0.0f;
	draw_progress(x + 10.0f, y + 50.0f, CARD_W - 20.0f, 5.0f, ratio,
	              Z_OVERLAY, COL_SURFACE_HI, color);
}

static void draw_network_card(const App *app, float x, float y)
{
	draw_card(x, y, CARD_W, CARD_H);
	char down[24];
	char up[24];
	format_rate(app->state.network_down_kbps, down, sizeof(down));
	format_rate(app->state.network_up_kbps, up, sizeof(up));

	text_draw(x + 10.0f, y + 7.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_NETWORK));

	/* Flèches dessinées : elles restent nettes même si la police est incomplète. */
	draw_line(x + 14.0f, y + 27.0f, x + 14.0f, y + 38.0f, 1.6f,
	          Z_OVERLAY, COL_ACCENT);
	draw_triangle(x + 10.5f, y + 35.0f, x + 17.5f, y + 35.0f,
	              x + 14.0f, y + 40.0f, Z_OVERLAY, COL_ACCENT);
	draw_line(x + 99.0f, y + 40.0f, x + 99.0f, y + 29.0f, 1.6f,
	          Z_OVERLAY, COL_TEXT_DIM);
	draw_triangle(x + 95.5f, y + 32.0f, x + 102.5f, y + 32.0f,
	              x + 99.0f, y + 27.0f, Z_OVERLAY, COL_TEXT_DIM);

	text_draw(x + 23.0f, y + 20.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_DOWNLOAD));
	text_draw_clipped(x + 23.0f, y + 36.0f, Z_OVERLAY, TEXT_SMALL, COL_TEXT,
	                  ALIGN_LEFT, 68.0f, down);
	text_draw(x + 108.0f, y + 20.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_UPLOAD));
	text_draw_clipped(x + 108.0f, y + 36.0f, Z_OVERLAY, TEXT_SMALL,
	                  COL_TEXT_DIM, ALIGN_LEFT, 64.0f, up);
}

static void draw_disk_or_gpu_card(const App *app, float x, float y)
{
	draw_card(x, y, CARD_W, CARD_H);
	const bool gpu_available = app->state.gpu >= 0;
	const int metric = gpu_available ? app->state.gpu : app->state.disk;
	const u32 color = metric_color(metric, gpu_available ? 85 : 90,
	                               gpu_available ? 96 : 97);
	char value[12];
	format_percent(metric, value, sizeof(value));

	text_draw(x + 10.0f, y + 7.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, gpu_available ? tr(STR_GRAPHICS) : tr(STR_STORAGE));
	text_draw(x + 10.0f, y + 23.0f, Z_OVERLAY, TEXT_LARGE, color, ALIGN_LEFT,
	          value);

	char detail[36];
	if (gpu_available) {
		if (app->state.temperature >= 0) {
			snprintf(detail, sizeof(detail), "%d C", app->state.temperature);
		} else {
			snprintf(detail, sizeof(detail), "--");
		}
	} else {
		format_capacity(app->state.disk_free_mb, app->state.disk_total_mb,
		                detail, sizeof(detail));
	}
	text_draw_clipped(x + 63.0f, y + 25.0f, Z_OVERLAY, TEXT_MICRO,
	                  COL_TEXT_DIM, ALIGN_LEFT, CARD_W - 73.0f, detail);

	const float ratio = metric >= 0 ? (float)metric / 100.0f : 0.0f;
	draw_progress(x + 10.0f, y + 50.0f, CARD_W - 20.0f, 5.0f, ratio,
	              Z_OVERLAY, COL_SURFACE_HI, color);
}

static void draw_health(const App *app)
{
	const PcState *state = &app->state;
	const bool known = state->cpu >= 0 || state->memory >= 0 || state->disk >= 0 ||
	                   state->gpu >= 0 || state->temperature >= 0;
	const bool critical = state->cpu >= 92 || state->memory >= 94 ||
	                      state->disk >= 97 || state->gpu >= 96 ||
	                      state->temperature >= 90;
	const bool warning = state->cpu >= 75 || state->memory >= 82 ||
	                     state->disk >= 90 || state->gpu >= 85 ||
	                     state->temperature >= 80;

	const char *label = tr(STR_PERFORMANCE_HEALTHY);
	u32 color = COL_ACCENT;
	if (!known) {
		label = tr(STR_PERFORMANCE_WAITING);
		color = COL_TEXT_FAINT;
	} else if (critical) {
		label = tr(STR_PERFORMANCE_ALERT);
		color = COL_ERR;
	} else if (warning) {
		label = tr(STR_PERFORMANCE_BUSY);
		color = COL_WARN;
	}

	draw_round_rect(LEFT_X, CONTENT_TOP, SCREEN_TOP_W - 24.0f, 27.0f, 9.0f,
	                Z_CARD, theme_alpha(color, 0x20));
	draw_round_rect_outline(LEFT_X, CONTENT_TOP, SCREEN_TOP_W - 24.0f, 27.0f,
	                        9.0f, 1.0f, Z_CONTENT, theme_alpha(color, 0x68));
	draw_circle(LEFT_X + 13.0f, CONTENT_TOP + 13.5f, 3.2f, Z_OVERLAY, color);
	text_draw_clipped(LEFT_X + 23.0f, CONTENT_TOP + 6.0f, Z_OVERLAY,
	                  TEXT_SMALL, COL_TEXT, ALIGN_LEFT, 300.0f, label);

	if (state->temperature >= 0) {
		char temperature[16];
		snprintf(temperature, sizeof(temperature), "%d C", state->temperature);
		text_draw(SCREEN_TOP_W - 22.0f, CONTENT_TOP + 6.0f, Z_OVERLAY,
		          TEXT_SMALL, color, ALIGN_RIGHT, temperature);
	}
}

static void draw_top_process(const App *app)
{
	const float y = 214.0f;
	draw_round_rect(LEFT_X, y, SCREEN_TOP_W - 24.0f, 18.0f, 7.0f, Z_CARD,
	                theme_alpha(COL_SURFACE, 0xD8));
	text_draw(LEFT_X + 9.0f, y + 2.0f, Z_OVERLAY, TEXT_MICRO, COL_TEXT_FAINT,
	          ALIGN_LEFT, tr(STR_TOP_PROCESS));

	const char *name = app->state.top_process[0] != '\0'
	                       ? app->state.top_process
	                       : tr(STR_UNKNOWN);
	char cpu[12] = "";
	if (app->state.top_process_cpu >= 0) {
		snprintf(cpu, sizeof(cpu), "%d%%", app->state.top_process_cpu);
		text_draw(SCREEN_TOP_W - 21.0f, y + 2.0f, Z_OVERLAY, TEXT_MICRO,
		          COL_TEXT_DIM, ALIGN_RIGHT, cpu);
	}
	text_draw_clipped(LEFT_X + 78.0f, y + 2.0f, Z_OVERLAY, TEXT_MICRO,
	                  COL_TEXT, ALIGN_LEFT, 245.0f, name);
}

void ui_top_system_draw(const App *app)
{
	draw_health(app);
	draw_cpu_card(app, LEFT_X, 69.0f);
	draw_memory_card(app, RIGHT_X, 69.0f);
	draw_network_card(app, LEFT_X, 141.0f);
	draw_disk_or_gpu_card(app, RIGHT_X, 141.0f);
	draw_top_process(app);
}

