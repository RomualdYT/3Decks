#pragma once
#include "ui.h"
typedef struct { float x, y, w, h; } Rect;
#define TAB_H 28.0f
#define SETTINGS_TAB_W 34.0f
#define LIST_COLS 2
#define LIST_ROW_H 38.0f
#define LIST_GAP 4.0f
#define LIST_MARGIN 10.0f

Rect slot_rect(int slot);
Rect settings_rect(void);
Rect waiting_settings_rect(void);
Rect tab_rect(int index, int page_count);
Rect list_item_rect(int index, float scroll);
int list_visible_rows(void);
int list_total_rows(int count);
void draw_action_feedback(ActionFeedbackState state, float cx, float cy, float uptime);
void draw_button(const App *app, const Button *button, int slot);
void draw_list(const App *app, const Page *page);
void draw_waiting(const App *app);
void draw_standby(const App *app);
