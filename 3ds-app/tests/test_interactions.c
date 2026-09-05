#include "app_feedback.h"
#include "ui_bottom_internal.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static App app;
int main(void)
{
    app.config.page_count = 2;
    for (int i = 0; i < 2; i++) {
        app.config.pages[i].used = true;
        snprintf(app.config.pages[i].id, LEN_ID, "page%d", i);
    }
    app.list_scroll = 3;
    app_goto_page(&app, 1); assert(app.current_page == 1 && app.list_scroll == 0);
    app_goto_page(&app, 9); assert(app.current_page == 1);
    app_cycle_page(&app, 1); assert(app.current_page == 0);
    app_cycle_page(&app, -1); assert(app.current_page == 1);
    app.frame_mode = true; assert(app_effective_dashboard(&app) == DASH_FRAME);
    app.frame_mode = false; app.state.media_present = true;
    assert(app_effective_dashboard(&app) == DASH_MEDIA);
    for (int i = 0; i < GRID_SLOTS; i++) {
        Rect rect = slot_rect(i);
        assert(ui_slot_at(rect.x + rect.w/2, rect.y + rect.h/2) == i);
        assert(ui_slot_at(rect.x + rect.w, rect.y + rect.h/2) != i);
    }
    assert(ui_slot_at(-1, -1) == -1);
    Rect settings = settings_rect();
    assert(ui_settings_at(settings.x + 2, settings.y + 2));
    assert(ui_tab_at(settings.x + 2, settings.y + 2, MAX_PAGES) == -1);
    Page *page = &app.config.pages[1]; page->layout = LAYOUT_LIST; page->entry_count = 20;
    assert(ui_list_max_scroll(&app) > 0);
    assert(ui_list_at(&app, 12, SCREEN_H - 10) == -1);
    assert(ui_list_at(&app, 12, GRID_TOP + 1) == 0);
    app.list_scroll = 1; assert(ui_list_at(&app, 12, GRID_TOP + 1) == LIST_COLS);

    app.link = LINK_ONLINE;
    app_feedback_begin(&app, 1, "page1", "play");
    assert(app_action_feedback(&app, "page1", "play") == ACTION_FEEDBACK_PENDING);
    app_feedback_finish(&app, 1, true);
    assert(app_action_feedback(&app, "page1", "play") == ACTION_FEEDBACK_SUCCESS);
    app_feedback_begin(&app, 2, "page1", "play");
    app_feedback_finish(&app, 1, false);
    assert(app_action_feedback(&app, "page1", "play") == ACTION_FEEDBACK_PENDING);
    app_feedback_update(&app, 6);
    assert(app_action_feedback(&app, "page1", "play") == ACTION_FEEDBACK_ERROR);
    app_feedback_update(&app, 2);
    assert(app_action_feedback(&app, "page1", "play") == ACTION_FEEDBACK_NONE);
    app_feedback_begin(&app, 3, "page1", "play"); app.link = LINK_OFFLINE;
    app_feedback_update(&app, 0);
    assert(app_action_feedback(&app, "page1", "play") == ACTION_FEEDBACK_ERROR);
    page->buttons[0].used = true; strcpy(page->buttons[0].hold_label, "Secondary");
    app.pressed_slot = 0; app.press_time = APP_HOLD_THRESHOLD/2;
    assert(app_hold_progress(&app, 0) == 0.5f);
    app.hold_fired = true; assert(app_hold_progress(&app, 0) == 0);
    puts("interactions: navigation, touch geometry, scrolling, action correlation and hold progress passed");
}
