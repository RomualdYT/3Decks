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
static inline Result socInit(u32 *buffer, size_t size) { (void)buffer; (void)size; return 0; }
static inline void socExit(void) {}
#define CFG_LANGUAGE_FR 2
static inline Result cfguInit(void) { return -1; }
static inline Result CFGU_GetSystemLanguage(u8 *language) { (void)language; return -1; }
static inline void cfguExit(void) {}
