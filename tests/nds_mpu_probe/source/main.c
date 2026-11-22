// Original focused regression for ARM9's base-restored data-abort model.
#include <nds.h>

extern void run_abort_cases(u32 *results);
static u32 results[20];

int main(void) {
    u32 ime = REG_IME;
    REG_IME = 0;
    run_abort_cases(results);
    REG_IME = ime;
    powerOn(POWER_ALL_2D);
    lcdMainOnTop();
    videoSetMode(MODE_5_2D);
    vramSetBankA(VRAM_A_MAIN_BG);
    int bg = bgInit(2, BgType_Bmp16, BgSize_B16_256x256, 0, 0);
    u16 *pixels = bgGetGfxPtr(bg);
    bool pass[5] = {
        results[0] == 0x11223344 && results[1] == 0x02080000,
        results[2] == 0x11223344 && results[3] == 0x02080000,
        results[4] == 0x11223344 && results[5] == 0x02080000,
        results[6] == 0x11223344 && results[7] == 0x02080004,
        results[8] == 4,
    };
    for (int y=0;y<192;y++) for(int x=0;x<256;x++)
        pixels[y*256+x] = BIT(15) | (pass[y/40] ? RGB15(0,31,0) : RGB15(31,0,0));
    while (1) swiWaitForVBlank();
}
