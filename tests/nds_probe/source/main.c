// Original DS diagnostic: independent screens, scripted input, and DLDI read/write.
#include <nds.h>
#include <fat.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    powerOn(POWER_ALL_2D);
    lcdMainOnTop();
    videoSetMode(MODE_5_2D);
    videoSetModeSub(MODE_5_2D);
    vramSetBankA(VRAM_A_MAIN_BG);
    vramSetBankC(VRAM_C_SUB_BG);
    int top = bgInit(2, BgType_Bmp16, BgSize_B16_256x256, 0, 0);
    int bottom = bgInitSub(2, BgType_Bmp16, BgSize_B16_256x256, 0, 0);
    u16 *a = bgGetGfxPtr(top), *b = bgGetGfxPtr(bottom);
    bool storage = false;
    if (fatInitDefault()) {
        char marker[32] = {0};
        FILE *f = fopen("/probe.txt", "rb");
        if (f) { fread(marker, 1, sizeof(marker)-1, f); fclose(f); }
        if (strcmp(marker, "DS_STORAGE_PROBE\n") == 0) {
            f = fopen("/probe-result.txt", "wb");
            if (f) { storage = fwrite("DS_STORAGE_OK\n", 1, 14, f) == 14; fclose(f); }
        }
    }
    unsigned frame = 0;
    while (1) {
        swiWaitForVBlank();
        scanKeys();
        u16 inputColor = (keysHeld() & KEY_A) ? RGB15(31,31,0) : RGB15(31,0,0);
        for (int y=0; y<192; ++y) for (int x=0; x<256; ++x) {
            a[y*256+x] = BIT(15) | (x < 128 ? inputColor : (storage ? RGB15(0,31,0) : RGB15(31,0,31)));
            b[y*256+x] = BIT(15) | RGB15(0,0,31);
        }
        // A heartbeat independent of input verifies execution advances.
        b[32*256+32] = BIT(15) | (frame++ & 31);
    }
}
