#include "app.h"
#include "artwork.h"
#include "i18n.h"
#include "sound.h"
#include "monotonic.h"
#include "support.h"

double test_now;
double monotonic_seconds(void) { return test_now; }
void sound_play(SoundId id) { (void)id; }
void app_touch_activity(App *app) { app->dimmed = false; }
bool app_save_settings(App *app) { (void)app; return true; }
void app_notify(App *app, const char *text, bool error) { (void)app; (void)text; (void)error; }
bool artwork_consume(const char *data, size_t size) { (void)data; (void)size; return false; }
Language i18n_language(void) { return LANG_EN; }
const char *tr(StringId id) { (void)id; return "Test status"; }
