#pragma once
#ifdef __arm__
// The tiny pixel loops fit in remaining executable VRAM A. The rest of the
// UI stays in main RAM; guest MPU/instruction-cache settings do not change.
#define ZELDA_HOT [[gnu::section(".zelda.hot"), gnu::noinline]]
#else
#define ZELDA_HOT
#endif
// C displays only its first 96 KiB. Compose the next complete lower-screen
// image in its unused 32 KiB tail; H remains unchanged until VBlank publication.
static constexpr unsigned kZeldaBackBuffer = 0x06858000;
// D's final 4 KiB is beyond the ROM map cache and outside the capture area.
static constexpr unsigned kZeldaPaletteBuffer = 0x0687F000;
