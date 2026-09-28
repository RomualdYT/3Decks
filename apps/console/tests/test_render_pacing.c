#include <assert.h>
#include <stdio.h>

#include "render_pacing.h"

int main(void)
{
	RenderPacing pacing = {0};
	assert(render_pacing_should_draw(&pacing, 0.1f, false, 0.0));
	assert(render_pacing_should_draw(&pacing, 0.1f, true, 0.0));
	assert(!render_pacing_should_draw(&pacing, 0.5f, true, 0.0));
	assert(render_pacing_should_draw(&pacing, 0.5f, true, 0.0));
	assert(!render_pacing_should_draw(&pacing, 0.1f, true, 0.0));
	assert(render_pacing_should_draw(&pacing, 0.1f, true, 1.0));
	assert(!render_pacing_should_draw(&pacing, 0.1f, true, 1.0));
	assert(render_pacing_should_draw(&pacing, 0.1f, false, 1.0));
	assert(render_pacing_should_draw(&pacing, 0.1f, true, 1.0));
	puts("render pacing: OK");
	return 0;
}
