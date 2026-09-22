#pragma once
/* Host-only SDK boundary: no hardware behavior is simulated here. */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t Result;
#define R_FAILED(result) ((result) < 0)
#define R_SUCCEEDED(result) ((result) >= 0)
static inline Result socInit(u32 *buffer, size_t size) { (void)buffer; (void)size; return 0; }
static inline void socExit(void) {}
#define CFG_LANGUAGE_FR 2
static inline Result cfguInit(void) { return -1; }
static inline Result CFGU_GetSystemLanguage(u8 *language) { (void)language; return -1; }
static inline void cfguExit(void) {}

#define CFG_MODEL_3DS 0
#define CFG_MODEL_3DSXL 1
#define CFG_MODEL_N3DS 2
#define CFG_MODEL_2DS 3
#define CFG_MODEL_N3DSXL 4
#define CFG_MODEL_N2DSXL 5
static inline Result CFGU_GetSystemModel(u8 *model) { (void)model; return -1; }
static inline Result osSetSpeedupEnable(bool enable) { (void)enable; return 0; }
static inline void gspWaitForVBlank(void) {}

typedef int16_t s16;
typedef struct {
	s16 dx;
	s16 dy;
} circlePosition;
static inline void hidCircleRead(circlePosition *pos) { if (pos) { pos->dx = 0; pos->dy = 0; } }
static inline void hidCstickRead(circlePosition *pos) { if (pos) { pos->dx = 0; pos->dy = 0; } }
