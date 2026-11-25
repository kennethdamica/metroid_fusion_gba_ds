#include "common.h"
#include <libtwl/mem/memVram.h>
#include <libtwl/gfx/gfx.h>
#include <libtwl/gfx/gfxBackground.h>
#include <libtwl/sys/sysPower.h>
#include "SystemIpc.h"
#include "FusionScreen.h"
#include "DisplayAudio.h"
#include "Fat/ff.h"
#include <memory>

extern FIL gFile;

// Keep mutable bytes out of VRAM: ARM9 VRAM stores must be 16 or 32 bits.
extern "C" { [[gnu::section(".ewram.bss")]] u32 gFusionScreenActive; }
[[gnu::section(".ewram.bss")]] static u32 sTicks, sLastRoom, sRoomMask[32];
[[gnu::section(".ewram.bss")]] static u16 sQueue[1024], sBaseMap[640];
[[gnu::section(".ewram.bss")]] static bool sReady, sWasLive;
[[gnu::section(".ewram.bss")]] static u32 sLastPosition, sLastTile;
static volatile u16* const sMap = (volatile u16*)0x06206800;
static volatile u16* const sWorld = (volatile u16*)0x06206000;
static constexpr u16 Blank = 448;
static const char sAreaNames[7][18] = {
    "MAIN DECK        ", "SECTOR 1 SRX     ", "SECTOR 2 TRO     ",
    "SECTOR 3 PYR     ", "SECTOR 4 AQA     ", "SECTOR 5 ARC     ",
    "SECTOR 6 NOC     "
};

// Original 5x7 glyphs, packed as five-bit rows. No game assets are reused.
struct Glyph { char character; u8 rows[7]; };
[[gnu::section(".ewram")]] static const Glyph sGlyphs[] = {
    {'0',{14,17,19,21,25,17,14}}, {'1',{4,12,4,4,4,4,14}},
    {'2',{14,17,1,2,4,8,31}}, {'3',{30,1,1,14,1,1,30}},
    {'4',{2,6,10,18,31,2,2}}, {'5',{31,16,16,30,1,1,30}},
    {'6',{14,16,16,30,17,17,14}}, {'7',{31,1,2,4,8,8,8}},
    {'8',{14,17,17,14,17,17,14}}, {'9',{14,17,17,15,1,1,14}},
    {'A',{14,17,17,31,17,17,17}}, {'B',{30,17,17,30,17,17,30}},
    {'C',{14,17,16,16,16,17,14}}, {'D',{30,17,17,17,17,17,30}},
    {'E',{31,16,16,30,16,16,31}}, {'F',{31,16,16,30,16,16,16}},
    {'G',{14,17,16,23,17,17,15}}, {'H',{17,17,17,31,17,17,17}},
    {'I',{14,4,4,4,4,4,14}}, {'J',{7,2,2,2,18,18,12}},
    {'K',{17,18,20,24,20,18,17}}, {'L',{16,16,16,16,16,16,31}},
    {'M',{17,27,21,21,17,17,17}}, {'N',{17,25,21,19,17,17,17}},
    {'O',{14,17,17,17,17,17,14}}, {'P',{30,17,17,30,16,16,16}},
    {'Q',{14,17,17,17,21,18,13}}, {'R',{30,17,17,30,20,18,17}},
    {'S',{15,16,16,14,1,1,30}}, {'T',{31,4,4,4,4,4,4}},
    {'U',{17,17,17,17,17,17,14}}, {'V',{17,17,17,17,17,10,4}},
    {'W',{17,17,17,21,21,21,10}}, {'X',{17,17,10,4,10,17,17}},
    {'Y',{17,17,10,4,4,4,4}}, {'Z',{31,1,2,4,8,16,31}},
    {'-',{0,0,0,31,0,0,0}}, {'/',{1,1,2,4,8,16,16}}
};

static void text(int x, int y, const char* value)
{
    while (*value) sMap[y * 32 + x++] = 0xF000 | (u8)*value++;
}

static void hex(int x, int y, u32 value)
{
    static const char digits[] = "0123456789ABCDEF";
    sMap[y * 32 + x] = 0xF000 | digits[(value >> 4) & 15];
    sMap[y * 32 + x + 1] = 0xF000 | digits[value & 15];
}

bool fusionScreenSupports(const GbaHeader& header)
{
    return header.gameCode == GAMECODE("AMTE") && header.softwareVersion == 0;
}

// Fusion US map graphics: metroidret/mf database.json, pinned in map notes.
// Load once before guest execution. No SD or ROM paging occurs in the IRQ.
static bool loadTiles()
{
    auto buffer = std::make_unique<u32[]>(0x3860 / 4);
    UINT count = 0;
    if (f_lseek(&gFile, 0x561FA8) != FR_OK ||
        f_read(&gFile, buffer.get(), 0x3860, &count) != FR_OK || count != 0x3860)
        return false;
    auto tiles = (volatile u32*)0x06200000;
    for (unsigned i = 0; i < 0x3800 / 4; ++i) tiles[i] = buffer[i];
    auto palette = (volatile u16*)0x05000400;
    auto colors = (const u16*)&buffer[0x3800 / 4];
    for (int i = 0; i < 48; ++i) palette[i] = colors[i];
    for (int i = 0; i < 16; ++i)
    {
        palette[48 + i] = colors[16 + i];
        palette[64 + i] = colors[16 + i];
    }
    // Recolor the room interior while retaining walls, doors and icon inks.
    palette[50] = palette[51] = 31 | (22 << 5) | (6 << 10);
    palette[66] = palette[67] = 0x7FFF;
    return true;
}

void fusionScreenInitialize()
{
    displayAudioInitialize();
    sys_setMainEngineToTopScreen();
    sys_set2DGraphicsSubPower(true);
    sysipc_setTopBacklight(true);
    sysipc_setBottomBacklight(true);
    REG_DISPCAPCNT = 0;
    // H holds the complete tiled map. C displays a centered copy of the
    // previous frame captured in D, without using the guest's windows/OAM.
    mem_setVramCMapping(MEM_VRAM_C_LCDC);
    mem_setVramDMapping(MEM_VRAM_D_LCDC);
    mem_setVramHMapping(MEM_VRAM_H_SUB_BG_00000);
    auto frame = (volatile u32*)0x06840000;
    for (unsigned i = 0; i < 0x40000 / 4; ++i) frame[i] = 0;
    REG_DISPCNT_SUB = 0x10000;
    REG_MASTER_BRIGHT_SUB = 0;
    REG_BLDCNT_SUB = 0;
    REG_BG0CNT_SUB = (1 << 2) | (13 << 8); // font at 0x4000, text at 0x6800
    REG_BG1CNT_SUB = 1 | (12 << 8);       // Fusion tiles at 0, map at 0x6000
    REG_BG0HOFS_SUB = REG_BG0VOFS_SUB = 0;
    REG_BG1HOFS_SUB = REG_BG1VOFS_SUB = 0;
    auto vram = (volatile u32*)0x06200000;
    for (unsigned i = 0; i < 0x7000 / 4; ++i) vram[i] = 0;
    auto font = (volatile u32*)0x06204000;
    for (const auto& glyph : sGlyphs)
        for (int y = 0; y < 7; ++y)
        {
            u32 pixels = 0;
            for (int x = 0; x < 5; ++x)
                if (glyph.rows[y] & (16 >> x)) pixels |= 1u << ((x + 1) * 4);
            font[(u8)glyph.character * 8 + y] = pixels;
        }
    sReady = loadTiles();
    auto palette = (volatile u16*)0x05000400;
    palette[0] = 1 | (2 << 5) | (4 << 10);
    palette[241] = 10 | (28 << 5) | (31 << 10);
    for (int i = 0; i < 1024; ++i) sWorld[i] = Blank;
    text(1, 0, "FUSION");
    text(1, 1, "AREA -- ROOM --");
    text(1, 23, "GOLD ROOM / WHITE SAMUS");
    text(20, 1, sReady ? "WAIT" : "MAP ERROR");
    sTicks = 0;
    sLastRoom = 0xFFFFFFFF;
    sWasLive = false;
    gFusionScreenActive = 1;
    REG_DISPCNT = (REG_DISPCNT & ~0xF0000) | 0xA0000;
    REG_DISPCNT_SUB = 0x10300;
}

// Read the map artwork in display orientation. Ink 3 is room interior; walls,
// hatches and the background use other inks. Thus flood fill follows actual
// room shapes, rather than filling every cell of an overlapping bounding box.
static unsigned ink(u16 tile, unsigned x, unsigned y)
{
    unsigned index = tile & 1023;
    if (index >= 448) return 0;
    if (tile & 0x400) x = 7 - x;
    if (tile & 0x800) y = 7 - y;
    u16 packed = ((volatile const u16*)0x06200000)[index * 16 + y * 2 + x / 4];
    return (packed >> ((x & 3) * 4)) & 15;
}

static void roomMask(unsigned px, unsigned py)
{
    for (int i = 0; i < 32; ++i) sRoomMask[i] = 0;
    const unsigned rx = *(volatile const u8*)0x030000B2;
    const unsigned ry = *(volatile const u8*)0x030000B3;
    const unsigned width = *(volatile const u16*)0x030000A0;
    const unsigned height = *(volatile const u16*)0x030000A2;
    // Clipdata dimensions include two 16px blocks of padding on each edge.
    const unsigned rw = width > 4 ? (width - 4 + 14) / 15 : 0;
    const unsigned rh = height > 4 ? (height - 4 + 9) / 10 : 0;
    if (px < rx || py < ry || px >= rx + rw || py >= ry + rh) return;
    auto raw = (volatile const u16*)0x02034800;
    unsigned head = 0, tail = 1;
    sQueue[0] = py * 32 + px;
    sRoomMask[py] = 1u << px;
    while (head < tail)
    {
        displayServiceAudio();
        unsigned at = sQueue[head++], x = at & 31, y = at >> 5;
        for (unsigned d = 0; d < 4; ++d)
        {
            unsigned nx = x, ny = y;
            if (d == 0) --nx;
            if (d == 1) ++nx;
            if (d == 2) --ny;
            if (d == 3) ++ny;
            if (nx >= 32 || ny >= 32 || nx < rx || ny < ry ||
                nx >= rx + rw || ny >= ry + rh || (sRoomMask[ny] & (1u << nx))) continue;
            unsigned ax = d < 2 ? (d == 0 ? 0 : 7) : 3;
            unsigned ay = d < 2 ? 3 : (d == 2 ? 0 : 7);
            if (ink(raw[at], ax, ay) != 3 || ink(raw[ny * 32 + nx],
                    d < 2 ? 7 - ax : ax, d < 2 ? ay : 7 - ay) != 3) continue;
            sRoomMask[ny] |= 1u << nx;
            sQueue[tail++] = ny * 32 + nx;
        }
    }
}

[[gnu::noinline]] static void updateMap()
{
    // Read-only guest state, at most 7.5 updates/second. Update only changed
    // tilemap entries; the DS draws all map pixels. No allocation/SD/DMA here.
    if (!sReady) return;
    const unsigned area = *(volatile const u8*)0x0300002C;
    const unsigned room = *(volatile const u8*)0x0300002D;
    const unsigned px = *(volatile const u8*)0x03000031;
    const unsigned py = *(volatile const u8*)0x03000032;
    const bool live = *(volatile const u16*)0x03000BDE == 1 &&
        *(volatile const u16*)0x03000BE0 == 2 && *(volatile const u8*)0x03001242 == 0 &&
        area < 7 && *(volatile const u8*)0x03000B86 == area && px < 32 && py < 32;
    if (!live)
    {
        if (sWasLive)
        {
            // Preserve the last valid map, remove the live highlight, and do
            // not read guest scratch buffers while menus/cutscenes reuse them.
            for (int i = 0; i < 640; ++i) sWorld[96 + i] = sBaseMap[i];
            text(6, 1, "--"); text(14, 1, "--"); text(20, 1, "WAIT");
        }
        sWasLive = false;
        sLastRoom = 0xFFFFFFFF;
        return;
    }
    unsigned id = area * 256 + room;
    auto visited = (volatile const u16*)0x02034000;
    unsigned position = py * 32 + px;
    unsigned currentTile = visited[position];
    // Exploration changes as Samus enters map cells. Item symbols can change
    // in place. Menus and room changes force a refresh of the complete view.
    if (sWasLive && id == sLastRoom && position == sLastPosition && currentTile == sLastTile) return;
    sLastPosition = position;
    sLastTile = currentTile;
    if (id != sLastRoom || !(sRoomMask[py] & (1u << px)))
    {
        roomMask(px, py);
        sLastRoom = id;
        text(10, 0, sAreaNames[area]);
        hex(6, 1, area); hex(14, 1, room); text(20, 1, "LIVE");
    }
    // Keep the current cell central, clamped to the 32-row map's edges.
    unsigned top = py > 10 ? py - 10 : 0;
    if (top > 12) top = 12;
    for (unsigned i = 0; i < 640; ++i)
    {
        if((i&15)==0) displayServiceAudio();
        unsigned x = i & 31, y = (i >> 5) + top;
        u16 tile = visited[y * 32 + x];
        if ((tile & 1023) >= 448 || (tile & 1023) == 160 || (tile >> 12) > 2) tile = Blank;
        sBaseMap[i] = tile;
        if (tile != Blank && (sRoomMask[y] & (1u << x)))
            tile = (tile & 0xFFF) | ((x == px && y == py ? 4 : 3) << 12);
        if (sWorld[96 + i] != tile) sWorld[96 + i] = tile;
    }
    sWasLive = true;
}

// Keep the every-frame path tiny: the renderer's large stack frame and code
// must not disturb the guest's instruction-cache working set on skipped ticks.
extern "C" [[gnu::section(".itcm")]] void fusionScreenVBlank()
{
    // Crop the captured 256px stride to the GBA's 240x160 image. C's black
    // 8px/16px borders are initialized once and are never overwritten.
    // ARM block transfers avoid DMA channels owned by guest emulation.
    const void* src = (const void*)0x06860000;
    void* dst = (void*)(0x06840000 + (16 * 256 + 8) * 2);
    asm volatile(
        "mov r2, #160\n"
        "1: mov r3, #15\n"
        "2: ldmia %0!, {r4-r11}\n"
        "stmia %1!, {r4-r11}\n"
        "subs r3, r3, #1\n"
        "bne 2b\n"
        "add %0, %0, #32\n"
        "add %1, %1, #32\n"
        "subs r2, r2, #1\n"
        "tst r2, #15\n"
        "bne 1b\n"
        "push {r0-r3,r12,lr}\n"
        "bl displayServiceAudio\n"
        "pop {r0-r3,r12,lr}\n"
        "cmp r2, #0\n"
        "bne 1b\n"
        : "+r"(src), "+r"(dst) : : "r2", "r3", "r4", "r5", "r6", "r7",
          "r8", "r9", "r10", "r11", "lr", "cc", "memory");
    REG_DISPCAPCNT = 0x80330000; // engine A -> D, 256x192, every frame
    if ((++sTicks & 7) == 0) updateMap();
}
