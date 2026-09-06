/** Original 3Decks companion artwork. GPL-3.0, like the application.
 * Rectangles deliberately stay on whole pixels; animation is quantized to 4 Hz.
 * The same renderer can be captured on a host without citro2d or texture files.
 */
#include "decky.h"
#include <math.h>
#include <stddef.h>

#define INK 0x111619u
#define SHELL 0x909a98u
#define LIGHT 0xdce6dbu
#define SHADE 0x53625fu
#define SCREEN 0x182a23u
#define GREEN 0xb4f575u
#define PINK 0xf2a696u

void decky_draw(DeckyMood mood, float seconds, DeckyPixelRect paint, void *context)
{
	if (paint == NULL) return;
	if (!isfinite(seconds) || seconds < 0) seconds = 0;
	const int tick = (int)(fmodf(seconds, 60.0f) * 4.0f);
	const int phase = tick % 4;
	const int bob = (mood == DECKY_MUSIC && phase < 2) ? -1 : 0;
	const int look = mood == DECKY_SEARCH ? (phase < 2 ? -1 : 1) : 0;
	const int blink = tick % 19 == 18;
#define P(x,y,w,h,c) paint(context,(x),(y)+bob,(w),(h),(c))
	/* Tiny grounding shadow, boots and mittens. */
	paint(context, 11, 38, 19, 1, 0x26322cu);
	P(12,34,6,3,INK); P(23,34,6,3,INK);
	P(11,36,7,2,SHADE); P(23,36,7,2,SHADE);
	P(6,25,4,6,INK); P(7,26,3,4,SHELL);
	const int hand = mood == DECKY_WAVE ? (phase < 2 ? 18 : 20) : 26;
	P(30,hand,4,5,INK); P(30,hand+1,3,3,LIGHT);
	if (mood == DECKY_WAVE) { P(29,23,2,4,SHADE); }
	/* Hinged lower screen: a pocket-sized console, not a human torso. */
	P(10,24,20,10,INK); P(11,25,18,8,SHELL); P(12,32,16,1,SHADE);
	P(15,26,11,5,SCREEN); P(12,27,2,2,INK); P(27,28,1,1,GREEN);
	P(14,22,12,3,INK); P(15,23,10,1,SHADE);
	/* Stepped corners, rim highlight and oversized dark face. */
	P(10,6,20,17,INK); P(8,8,24,13,INK);
	P(10,7,20,15,SHELL); P(9,9,22,11,SHELL);
	P(11,7,18,1,LIGHT); P(9,9,1,9,LIGHT); P(11,21,18,1,SHADE);
	P(11,9,18,11,SCREEN); P(12,9,16,1,0x274536u);
	/* Two little aerials with warm green tips. */
	P(13,4,2,3,SHADE); P(26,4,2,3,SHADE);
	P(12,2,4,3,INK); P(25,2,4,3,INK);
	P(13,2,2,2,GREEN); P(26,2,2,2,GREEN);
	if (mood == DECKY_SLEEP || blink) {
		P(14,14,4,1,GREEN); P(23,14,4,1,GREEN);
	} else if (mood == DECKY_WAVE || mood == DECKY_MUSIC) {
		P(14,12,4,1,GREEN); P(14,13,1,2,GREEN); P(17,13,1,2,GREEN);
		P(23,12,4,1,GREEN); P(23,13,1,2,GREEN); P(26,13,1,2,GREEN);
	} else {
		P(15+look,12,2,3,GREEN); P(24+look,12,2,mood == DECKY_CONFUSED ? 2 : 3,GREEN);
	}
	P(12,16,2,1,PINK); P(27,16,2,1,PINK);
	P(19,17,3,1,GREEN);
	if (mood != DECKY_SLEEP && mood != DECKY_CONFUSED) {
		P(18,16,1,1,GREEN); P(22,16,1,1,GREEN);
	}
	/* Belly heart. A note replaces it while listening. */
	if (mood == DECKY_MUSIC) {
		P(21,26,1,4,GREEN); P(19,29,2,1,GREEN); P(22,26,2,1,GREEN);
		P(7,10,2,8,SHADE); P(31,10,2,8,SHADE);
		P(8,6,2,5,SHADE); P(30,6,2,5,SHADE); P(10,5,20,1,SHADE);
	} else {
		P(18,27,2,1,GREEN); P(21,27,2,1,GREEN);
		P(18,28,5,1,GREEN); P(19,29,3,1,GREEN); P(20,30,1,1,GREEN);
	}
	if (mood == DECKY_SLEEP) {
		/* Pixel Z drifts up by one pixel, never over the face. */
		const int y = phase < 2 ? 4 : 3;
		P(34,y,4,1,GREEN); P(36,y+1,1,1,GREEN);
		P(35,y+2,1,1,GREEN); P(34,y+3,4,1,GREEN);
	} else if (mood == DECKY_WAVE && phase < 2) {
		P(35,12,1,3,GREEN); P(34,13,3,1,GREEN);
	} else if (mood == DECKY_CONFUSED) {
		P(34,5,3,1,PINK); P(36,6,1,2,PINK); P(35,8,1,1,PINK); P(35,10,1,1,PINK);
	}
#undef P
}
