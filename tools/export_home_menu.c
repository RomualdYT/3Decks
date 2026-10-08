/** HOME artwork from the same original pixel renderer as the application. */
#include "decky.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void paint(void *out, int x, int y, int w, int h, uint32_t rgb)
{
    fprintf(out, "<rect x='%d' y='%d' width='%d' height='%d' fill='#%06x'/>",
            x, y, w, h, (unsigned)rgb);
}

int main(int argc, char **argv)
{
    if (argc != 3) return EXIT_FAILURE;
    const int icon = strcmp(argv[2], "icon") == 0;
    if (!icon && strcmp(argv[2], "banner")) return EXIT_FAILURE;
    FILE *out = fopen(argv[1], "w");
    if (!out) return EXIT_FAILURE;
    fprintf(out, "<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d'>",
            icon ? 48 : 256, icon ? 48 : 128);
    fputs("<defs><radialGradient id='glow'><stop stop-color='#66cb10' stop-opacity='.24'/>"
          "<stop offset='1' stop-color='#66cb10' stop-opacity='0'/></radialGradient></defs>"
          "<path fill='#111514' d='M0 0H256V128H0z'/>", out);
    if (icon) {
        fputs("<circle cx='24' cy='23' r='26' fill='url(#glow)'/>"
              "<g transform='translate(4 3)' shape-rendering='crispEdges'>", out);
    } else {
        fputs("<ellipse cx='67' cy='62' rx='92' ry='82' fill='url(#glow)'/>"
              "<rect x='4' y='4' width='248' height='120' rx='10' fill='none' stroke='#344135'/>"
              "<g transform='translate(18 24) scale(2)' shape-rendering='crispEdges'>", out);
    }
    decky_draw(DECKY_WAVE, 0, paint, out);
    fputs("</g>", out);
    if (!icon) {
        fputs("<g font-family='Inter' fill='#edf4e9'>"
              "<text x='103' y='77' font-size='36' letter-spacing='-1.5'>3Decks</text></g>", out);
    }
    fputs("</svg>\n", out);
    const int failed = ferror(out);
    return fclose(out) == 0 && !failed ? EXIT_SUCCESS : EXIT_FAILURE;
}
