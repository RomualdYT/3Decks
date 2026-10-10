#include "app.h"
#include "artwork.h"
#include "chat_badges.h"
#include "i18n.h"
#include "sound.h"
#include "monotonic.h"
#include "support.h"

double test_now;
int test_sound_count[SOUND_COUNT];
int test_save_count;
bool test_save_ok = true;
int test_notify_count;
bool test_notify_error;
double monotonic_seconds(void) { return test_now; }
void sound_play(SoundId id) { if (id < SOUND_COUNT) test_sound_count[id]++; }
void app_touch_activity(App *app) { app->dimmed = false; }
bool app_save_settings(App *app) { (void)app; test_save_count++; return test_save_ok; }
void app_notify(App *app, const char *text, bool error) { (void)app; (void)text; test_notify_count++; test_notify_error = error; }
bool artwork_consume(const char *data, size_t size) { (void)data; (void)size; return false; }
bool chat_badges_consume(const char *data, size_t size) { (void)data; (void)size; return false; }
void chat_badges_exit(void) {}
Language i18n_language(void) { return LANG_EN; }
const char *tr(StringId id) { (void)id; return "Test status"; }
