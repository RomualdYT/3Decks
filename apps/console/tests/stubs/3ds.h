#pragma once
/* Host-only SDK boundary: no hardware behavior is simulated here. */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <netinet/in.h>
extern struct in_addr __3dslink_host;
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t Result;
#define R_FAILED(result) ((result) < 0)
#define R_SUCCEEDED(result) ((result) >= 0)
static inline Result socInit(u32 *buffer, size_t size) { (void)buffer; (void)size; return 0; }
static inline void socExit(void) {}
#define KEY_A (1 << 0)
#define KEY_B (1 << 1)
#define KEY_SELECT (1 << 2)
#define KEY_START (1 << 3)
#define KEY_DRIGHT (1 << 4)
#define KEY_DLEFT (1 << 5)
#define KEY_DUP (1 << 6)
#define KEY_DDOWN (1 << 7)
#define KEY_R (1 << 8)
#define KEY_L (1 << 9)
#define KEY_X (1 << 10)
#define KEY_Y (1 << 11)
#define KEY_ZL (1 << 14)
#define KEY_ZR (1 << 15)
#define KEY_TOUCH (1 << 20)

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
