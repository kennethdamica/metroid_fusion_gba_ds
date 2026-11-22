// Original GBA diagnostic; no game assets and no BIOS SWIs.
typedef unsigned short u16;
typedef unsigned int u32;
#define REG16(a) (*(volatile u16 *)(a))
int main(void) {
    REG16(0x04000000) = 0x0403; // mode 3, background 2
    volatile u16 *pixels = (volatile u16 *)0x06000000;
    volatile u32 *status = (volatile u32 *)0x02000000;
    u32 frame = 0;
    while (1) {
        while (REG16(0x04000006) >= 160) {}
        while (REG16(0x04000006) < 160) {}
        u16 color = (REG16(0x04000130) & 1) ? 31 : (31 | (31 << 5));
        for (int y=0; y<160; y++) for (int x=0; x<240; x++)
            pixels[y*240+x] = x < 120 ? color : (31 << 10);
        status[0] = 0x47424150; // GBAP marker in guest EWRAM
        status[1] = ++frame;
        status[2] = REG16(0x04000130);
    }
}
