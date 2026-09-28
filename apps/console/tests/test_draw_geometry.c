#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "draw.h"

#define TAU 6.28318530718f

static int line_count;
static int triangle_count;
static int expected_steps;
static float max_error;
static float expected_cx;
static float expected_cy;
static float expected_rx;
static float expected_ry;
static float expected_base;
static float expected_sweep;

float stereo_offset(float depth)
{
	(void)depth;
	return 0.0f;
}

u32 theme_mix(u32 a, u32 b, float t)
{
	(void)b;
	(void)t;
	return a;
}

void C2D_DrawRectSolid(float x, float y, float depth, float width, float height,
                       u32 color)
{
	(void)x; (void)y; (void)depth; (void)width; (void)height; (void)color;
}

void C2D_DrawRectangle(float x, float y, float depth, float width, float height,
                       u32 c0, u32 c1, u32 c2, u32 c3)
{
	(void)x; (void)y; (void)depth; (void)width; (void)height;
	(void)c0; (void)c1; (void)c2; (void)c3;
}

void C2D_DrawCircleSolid(float x, float y, float depth, float radius, u32 color)
{
	(void)x; (void)y; (void)depth; (void)radius; (void)color;
}

void C2D_DrawTriangle(float x0, float y0, u32 c0,
                      float x1, float y1, u32 c1,
                      float x2, float y2, u32 c2, float depth)
{
	(void)x0; (void)y0; (void)c0; (void)x1; (void)y1; (void)c1;
	(void)c2; (void)depth;
	assert(isfinite(x0) && isfinite(y0) && isfinite(x1) && isfinite(y1));
	assert(isfinite(x2) && isfinite(y2));
	triangle_count++;
}

void C2D_DrawLine(float x0, float y0, u32 c0, float x1, float y1, u32 c1,
                  float thickness, float depth)
{
	(void)c0; (void)c1; (void)thickness; (void)depth;
	const float a0 = expected_base + expected_sweep *
	                 ((float)line_count / (float)expected_steps);
	const float a1 = expected_base + expected_sweep *
	                 ((float)(line_count + 1) / (float)expected_steps);
	const float e0 = hypotf(x0 - expected_cx - cosf(a0) * expected_rx,
	                        y0 - expected_cy - sinf(a0) * expected_ry);
	const float e1 = hypotf(x1 - expected_cx - cosf(a1) * expected_rx,
	                        y1 - expected_cy - sinf(a1) * expected_ry);
	if (e0 > max_error) max_error = e0;
	if (e1 > max_error) max_error = e1;
	line_count++;
}

int main(void)
{
	/* 32 segments pour ce rayon : mêmes sommets malgré la récurrence. */
	expected_cx = 100.0f;
	expected_cy = 80.0f;
	expected_steps = 32;
	expected_rx = expected_ry = 30.0f;
	expected_base = -0.25f * TAU;
	expected_sweep = 0.4f * TAU;
	draw_arc(expected_cx, expected_cy, 30.0f, 2.0f, 0.0f, 0.4f,
	         0.0f, 0xffffffffu);
	assert(line_count == 32);
	assert(max_error < 0.001f);

	line_count = 0;
	max_error = 0.0f;
	expected_steps = 48;
	expected_rx = 31.0f;
	expected_ry = 19.0f;
	expected_base = 0.0f;
	expected_sweep = TAU;
	draw_ellipse_ring(expected_cx, expected_cy, 32.0f, 20.0f,
	                  2.0f, 0.0f, 0xffffffffu);
	assert(line_count == 48);
	assert(max_error < 0.001f);

	/* Le nombre de triangles des coins arrondis ne doit pas augmenter. */
	draw_round_rect(0.0f, 0.0f, 100.0f, 40.0f, 12.0f,
	                0.0f, 0xffffffffu);
	assert(triangle_count == 4 * 9);
	puts("draw geometry: arcs, elliptical rings and rounded corners passed");
	return 0;
}
