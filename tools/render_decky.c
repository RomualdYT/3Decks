/** Export a contact sheet from the production renderer; no SDK or image library.
 * cc -std=c11 -Iapps/console/source/graphics tools/render_decky.c \
 *    apps/console/source/graphics/decky.c -lm -o /tmp/render-decky
 * /tmp/render-decky /tmp/decky.svg
 */
#include "decky.h"
#include <stdio.h>
#include <stdlib.h>

static void paint(void *context, int x, int y, int w, int h, uint32_t color)
{
    FILE *out = context;
    fprintf(out, "<rect x='%d' y='%d' width='%d' height='%d' fill='#%06x'/>\n",
            x, y, w, h, (unsigned)color);
}
int main(int argc, char **argv)
{
    if (argc != 2) return EXIT_FAILURE;
    FILE *out = fopen(argv[1], "w");
    if (!out) return EXIT_FAILURE;
    fputs("<svg xmlns='http://www.w3.org/2000/svg' width='720' height='620' viewBox='0 0 720 620'>"
          "<rect width='720' height='620' rx='24' fill='#111514'/>"
          "<g font-family='system-ui,sans-serif' text-anchor='middle'>"
          "<text x='360' y='48' fill='#b4f575' font-size='14' letter-spacing='4'>3DECKS COMPANION</text>"
          "<text x='360' y='94' fill='#edf3e9' font-size='36' font-weight='700'>Meet Decky.</text>"
          "<text x='360' y='124' fill='#9ba89f' font-size='15'>A little company. Right in your pocket.</text>", out);
    const char *labels[] = {"Curious", "Hello!", "Looking for you", "Listening", "Sweet dreams", "Hmm?"};
    for (int mood = 0; mood < DECKY_MOOD_COUNT; mood++) {
        const int x = 24 + (mood % 3) * 228, y = 155 + (mood / 3) * 215;
        fprintf(out,"<rect x='%d' y='%d' width='216' height='200' rx='16' fill='#1c2420'/>"
                    "<g transform='translate(%d %d) scale(3)' shape-rendering='crispEdges'>",x,y,x+48,y+18);
        decky_draw((DeckyMood)mood, 0, paint, out);
        fprintf(out,"</g><text x='%d' y='%d' fill='#dce6db' font-size='16'>%s</text>",x+108,y+173,labels[mood]);
    }
    fputs("<text x='360' y='604' fill='#7a8b80' font-size='12'>Original pixel artwork · rendered by the same code as the 3DS</text></g></svg>",out);
    const int failed = ferror(out);
    return fclose(out) == 0 && !failed ? EXIT_SUCCESS : EXIT_FAILURE;
}
