// Appended only to the hardware diagnostic build. Reuse the map's original
// font and text helpers. Never wait for IPC, SD, interrupts or a frame here:
// a stalled operation must not leave the preceding stage visible.
extern "C" { [[gnu::section(".ewram.bss")]] volatile u32 gFusionBootStage; }

[[gnu::noinline]]
void fusionBootStage(u32 stage)
{
    gFusionBootStage = stage;
    sys_set2DGraphicsSubPower(true);
    mem_setVramCMapping(MEM_VRAM_C_SUB_BG_00000);
    REG_DISPCNT_SUB = 0x10100;
    REG_MASTER_BRIGHT_SUB = REG_BLDCNT_SUB = 0;
    REG_BG0CNT_SUB = (1 << 2) | (13 << 8);
    REG_BG0HOFS_SUB = REG_BG0VOFS_SUB = 0;
    if (stage == 1)
    {
        auto vram = (volatile u32*)0x06204000;
        for (unsigned i = 0; i < 0x3000 / 4; ++i) vram[i] = 0;
        for (const auto& glyph : sGlyphs)
            for (int y = 0; y < 7; ++y)
            {
                u32 pixels = 0;
                for (int x = 0; x < 5; ++x)
                    if (glyph.rows[y] & (16 >> x)) pixels |= 1u << ((x + 1) * 4);
                vram[(u8)glyph.character * 8 + y] = pixels;
            }
        text(2, 3, "FUSION HARDWARE TEST 5");
        text(2, 5, "BOOT STAGE");
        text(2, 10, "IF THIS STOPS");
        text(2, 12, "REPORT CODE AND LABEL");
        text(2, 16, (*(volatile u16*)0x04004000 & 3) == 1 ? "MODE DSI" : "MODE DS");
    }
    auto palette = (volatile u16*)0x05000400;
    palette[0] = 1 | (2 << 5) | (4 << 10);
    palette[241] = stage >= 0xE0 ? 31 : 0x7FFF;
    hex(13, 5, stage);
    static const char* const labels[] = {
        "", "CORE READY", "MOUNT FLASHCART", "LOAD CONFIG",
        "LOAD BIOS", "LOAD ROM", "LOAD SAVE", "APPLY PATCHES",
        "WAIT LOGO", "SET DISPLAY", "INIT EMULATOR", "SET CACHES", "LOAD MAP",
        "", "", "", "ENV DETECTED", "DEBUG PROBE", "SET LOGGER",
        "SET BUS PRIORITY", "SETUP IRQ", "ENABLE IRQ", "IRQ RUNNING",
        "CLEAR ENV FLAGS", "READ MODE", "MODE READ OK"
    };
    text(2, 7, "                            ");
    text(2, 7, stage < sizeof(labels) / sizeof(labels[0]) ? labels[stage] : "FILE READ FAILED");
}

[[gnu::noinline, noreturn]]
void fusionBootFail(u32 stage)
{
    fusionBootStage(stage);
    while (true) asm volatile("nop");
}
