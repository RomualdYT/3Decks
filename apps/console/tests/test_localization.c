#include "i18n.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    i18n_set_language(LANG_EN);
    assert(!strcmp(tr(STR_WELCOME_TITLE), "Welcome to 3Decks"));
    assert(!strcmp(tr(STR_SETUP_FINISH), "Start using 3Decks"));
    i18n_set_language(LANG_FR);
    assert(!strcmp(tr(STR_WELCOME_TITLE), "Bienvenue dans 3Decks"));
    for (int language = 0; language < LANG_COUNT; language++) {
        i18n_set_language((Language)language);
        for (int id = 0; id < STR_COUNT; id++)
            assert(strstr(tr((StringId)id), "Deck3DS") == NULL);
    }
    puts("localization: console product name is 3Decks in English and French");
}
