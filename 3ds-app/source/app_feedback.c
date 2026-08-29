/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_feedback.c Confirmation, erreur et progression des actions. */

#include "app_feedback.h"

#include <stdio.h>
#include <string.h>

#define ACTION_PENDING_TIMEOUT 5.0f
#define ACTION_SUCCESS_DURATION 1.0f
#define ACTION_ERROR_DURATION 1.4f

void app_feedback_begin(App *app, int request_id, const char *page_id,
	                    const char *item_id)
{
	ActionFeedback *feedback =
	    &app->action_feedback[app->action_feedback_cursor];
	app->action_feedback_cursor =
	    (app->action_feedback_cursor + 1) % MAX_ACTION_FEEDBACK;

	memset(feedback, 0, sizeof(*feedback));
	feedback->request_id = request_id;
	snprintf(feedback->page_id, sizeof(feedback->page_id), "%s", page_id);
	snprintf(feedback->item_id, sizeof(feedback->item_id), "%s", item_id);
	feedback->state = ACTION_FEEDBACK_PENDING;
	feedback->ttl = ACTION_PENDING_TIMEOUT;
}

void app_feedback_finish(App *app, int request_id, bool success)
{
	for (int i = 0; i < MAX_ACTION_FEEDBACK; i++) {
		ActionFeedback *feedback = &app->action_feedback[i];
		if (feedback->state == ACTION_FEEDBACK_PENDING &&
		    feedback->request_id == request_id) {
			feedback->state = success ? ACTION_FEEDBACK_SUCCESS
			                          : ACTION_FEEDBACK_ERROR;
			feedback->ttl = success ? ACTION_SUCCESS_DURATION
			                        : ACTION_ERROR_DURATION;
			return;
		}
	}
}

ActionFeedbackState app_action_feedback(const App *app, const char *page_id,
	                                    const char *item_id)
{
	ActionFeedbackState state = ACTION_FEEDBACK_NONE;
	int newest_request = -1;
	if (page_id == NULL || item_id == NULL) {
		return state;
	}

	for (int i = 0; i < MAX_ACTION_FEEDBACK; i++) {
		const ActionFeedback *feedback = &app->action_feedback[i];
		if (feedback->state != ACTION_FEEDBACK_NONE &&
		    feedback->request_id > newest_request &&
		    strcmp(feedback->page_id, page_id) == 0 &&
		    strcmp(feedback->item_id, item_id) == 0) {
			state = feedback->state;
			newest_request = feedback->request_id;
		}
	}
	return state;
}

float app_hold_progress(const App *app, int slot)
{
	const Page *page = app_current_page(app);
	if (page == NULL || slot < 0 || slot >= MAX_BUTTONS ||
	    app->pressed_slot != slot || app->hold_fired ||
	    !page->buttons[slot].used || page->buttons[slot].hold_label[0] == '\0') {
		return 0.0f;
	}
	float progress = app->press_time / APP_HOLD_THRESHOLD;
	if (progress < 0.0f) {
		return 0.0f;
	}
	return progress > 1.0f ? 1.0f : progress;
}

void app_feedback_update(App *app, float dt)
{
	for (int i = 0; i < MAX_ACTION_FEEDBACK; i++) {
		ActionFeedback *feedback = &app->action_feedback[i];
		if (feedback->state == ACTION_FEEDBACK_NONE) {
			continue;
		}
		if (feedback->state == ACTION_FEEDBACK_PENDING &&
		    app->link != LINK_ONLINE) {
			feedback->state = ACTION_FEEDBACK_ERROR;
			feedback->ttl = ACTION_ERROR_DURATION;
			continue;
		}

		feedback->ttl -= dt;
		if (feedback->ttl > 0.0f) {
			continue;
		}
		if (feedback->state == ACTION_FEEDBACK_PENDING) {
			feedback->state = ACTION_FEEDBACK_ERROR;
			feedback->ttl = ACTION_ERROR_DURATION;
		} else {
			feedback->state = ACTION_FEEDBACK_NONE;
		}
	}
}

