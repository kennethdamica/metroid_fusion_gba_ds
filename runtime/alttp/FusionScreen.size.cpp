#include "common.h"
#include <libtwl/mem/memVram.h>
#include <libtwl/gfx/gfx.h>
#include <libtwl/gfx/gfxStatus.h>
#include <libtwl/gfx/gfxBackground.h>
#include <libtwl/sys/sysPower.h>
#include "SystemIpc.h"
#include "FusionScreen.h"
#include "DisplayAudio.h"
#include "ZeldaVideo.h"
#include "Fat/ff.h"
extern FIL gFile;
extern void sysipc_setTouchBuffer(u32* buffer);
extern "C" {
[[gnu::section(".ewram.bss")]] u32 gFusionScreenActive;
// Main runtime RAM, outside the guest EWRAM MPU region.
[[gnu::section(".ewram.bss"), gnu::aligned(32)]] volatile u32 gZeldaTouch;
[[gnu::section(".ewram.bss")]] volatile u32 gZeldaDebug[8];
[[gnu::section(".ewram.bss")]] volatile u32 gZeldaVideoDebug[8];
[[gnu::section(".ewram.bss")]] volatile u32 gZeldaRenderDebug[8];
[[gnu::section(".ewram.bss")]] volatile u32 gZeldaMapHblankDebug[2]; // updates, crossed-scanline updates
}
[[gnu::section(".ewram.bss")]] static bool sReady, sDown;
[[gnu::section(".ewram.bss")]] static u32 sPacket, sStale, sTicks;
[[gnu::section(".ewram.bss")]] static u8 sItemTypes[25];
[[gnu::section(".ewram.bss")]] static u16 sIcons[24][9][4];
static volatile u16* const sMap = (volatile u16*)(kZeldaBackBuffer+0x6800);
static volatile u16* const sPanels = (volatile u16*)(kZeldaBackBuffer+0x7000);
static volatile u16* const sWorld = (volatile u16*)(kZeldaBackBuffer+0x6000);
static volatile u16* const sPalette = (volatile u16*)kZeldaPaletteBuffer;
// Word stores are required for state in VRAM A.
static u32 sFramePending, sNextBg1=1|(12<<8), sNextScroll=4;
static volatile u8& guest8(u32 address) { return *(volatile u8*)address; }
static void text(unsigned x, unsigned y, const char* value, u16 color = 0xF000)
{
    while (*value && x < 32) sMap[y*32+x++] = color | (u8)*value++;
    displayServiceAudio();
}
static void number(unsigned x, unsigned y, unsigned value, unsigned digits)
{
    while (digits) { sMap[y*32+x+--digits]=0xF000 | ('0'+value%10); value/=10; }
}
bool fusionScreenSupports(const GbaHeader& header)
{
    return header.gameCode == GAMECODE("AZLE") && header.softwareVersion == 0;
}
static bool readAt(u32 offset, void* data, unsigned bytes)
{
    UINT count;
    return f_lseek(&gFile, offset) == FR_OK && f_read(&gFile, data, bytes, &count) == FR_OK && count == bytes;
}
static bool loadProfile()
{
    if (!readAt(0x16B62C, sItemTypes, sizeof(sItemTypes))) return false;
    u32 pointers[24];
    if (!readAt(0x16B5A8, pointers, sizeof(pointers))) return false;
    for (unsigned i=0; i<24; ++i)
    {
        if (pointers[i] < 0x08000000 || pointers[i] > 0x087FFFB8) return false;
        if (!readAt(pointers[i]-0x08000000, sIcons[i], sizeof(sIcons[i]))) return false;
    }
    return true;
}
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

static bool live();
static bool loadNativeInventory();
static u32 sSessionReady;
#include "ZeldaMap.h"

static unsigned rgb(unsigned r,unsigned g,unsigned b) { return r|(g<<5)|(b<<10); }

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
    REG_BG1CNT_SUB = 1 | (12 << 8);
    REG_BG2CNT_SUB = 3 | (1 << 2) | (14 << 8);
    REG_BG2HOFS_SUB = REG_BG2VOFS_SUB = 0;
    REG_BG0HOFS_SUB = REG_BG0VOFS_SUB = 0;
    REG_BG1HOFS_SUB = REG_BG1VOFS_SUB = 0;
    auto vram = (volatile u32*)kZeldaBackBuffer;
    for (unsigned i = 0; i < 0x8000 / 4; ++i) {
        vram[i] = 0;
        ((volatile u32*)0x06200000)[i] = 0;
    }
    auto font = (volatile u32*)(kZeldaBackBuffer+0x4000);
    for (const auto& glyph : sGlyphs)
        for (int y = 0; y < 7; ++y)
        {
            u32 pixels = 0;
            for (int x = 0; x < 5; ++x)
                if (glyph.rows[y] & (16 >> x)) pixels |= 1u << ((x + 1) * 4);
            font[(u8)glyph.character * 8 + y] = pixels;
        }
    auto palette = sPalette;
    for(unsigned i=0;i<256;++i) palette[i]=0;
    // Forest green, warm parchment and brass. UI owns palette banks 12..15.
    palette[0]=rgb(3,5,4);
    for(unsigned bank=12;bank<16;++bank) {
        palette[bank*16+1]=bank==13?rgb(7,12,9):rgb(4,7,6);
        palette[bank*16+2]=bank==13?rgb(31,24,7):rgb(10,15,11);
        palette[bank*16+3]=rgb(2,4,3);
    }
    palette[241]=rgb(30,29,23); palette[225]=rgb(14,18,14);
    // UI tiles in the font's unused upper half. Rounded card corners.
    for(unsigned edges=0;edges<16;++edges) for(unsigned y=0;y<8;++y) {
        u32 pixels=0;
        for(unsigned x=0;x<8;++x) {
            bool edge=((edges&1)&&x==0)||((edges&2)&&x==7)||((edges&4)&&y==0)||((edges&8)&&y==7);
            bool corner=(((edges&1)&&x<2) || ((edges&2)&&x>5)) && (((edges&4)&&y<2) || ((edges&8)&&y>5));
            pixels|=(corner?0u:(edge?2u:1u))<<(x*4);
        }
        font[(128+edges)*8+y]=pixels;
    }
    sReady=loadProfile() && loadNativeInventory();
    sMapReady=sReady && loadMaps();
    sysipc_setTouchBuffer((u32*)&gZeldaTouch);
    gFusionScreenActive = 1;
    REG_DISPCNT = (REG_DISPCNT & ~0xF0000) | 0xA0000;
    REG_DISPCNT_SUB = 0x10000; // black and inert until a loaded game is ready
    ((volatile u16*)0x05000400)[0]=0;
}

// US AZLE r0: gRam=0x03002230. The normal item dispatcher consumes
// 0x178C and retains an in-use item in 0x178D until animations complete.
static bool live()
{
    unsigned mode=guest8(0x03002BDC);
    return sReady && *(volatile const u32*)0x03006D10==13 &&
        (mode==7 || mode==9) && guest8(0x03002BDD)==0 &&
        guest8(0x03002C7C)==0 && guest8(0x03002C7D)==0;
}
static bool canEquip()
{
    return live() && guest8(0x030039BA)==0 && guest8(0x03003A3C)==0 &&
        guest8(0x03003918)==0 && guest8(0x03003919)==0 &&
        guest8(0x0300391A)==0 && guest8(0x03003928)==0 && guest8(0x03003879)==0 &&
        guest8(0x030039BC)==guest8(0x030039BD);
}
static unsigned variant(unsigned slot)
{
    return slot==3 ? 1 : guest8(0x02002320+slot);
}
static void equip(unsigned slot)
{
    unsigned value=guest8(0x02002320+slot), v=variant(slot);
    if (!canEquip() || value==0 || value>=128 || v>=9) return;
    // Guest is stopped during this IRQ. Publish coherent slot/type/HUD state;
    // leave the dispatcher's in-use latch to the game and never change ownership.
    guest8(0x03002C7E)=slot+1;
    guest8(0x03002C7F)=0;
    guest8(0x030039BC)=sItemTypes[slot+1];
    auto hud=(volatile u16*)0x0200B1F8;
    hud[0]=sIcons[slot][v][0]; hud[1]=sIcons[slot][v][1];
    hud[32]=sIcons[slot][v][2]; hud[33]=sIcons[slot][v][3];
    guest8(0x03002BDE)=1; // game's HUD tilemap upload flag
    ++gZeldaDebug[1];
}
static void panel(unsigned x,unsigned y,unsigned w,unsigned h,bool selected=false)
{
    for(unsigned row=0;row<h;++row) for(unsigned col=0;col<w;++col) {
        if(col==0) displayServiceAudio();
        unsigned edges=(col==0?1:0)|(col==w-1?2:0)|(row==0?4:0)|(row==h-1?8:0);
        sPanels[(y+row)*32+x+col]=(selected?0xD000:0xC000)|(128+edges);
    }
}
static void marker(unsigned x,unsigned y)
{
    // Four private transparent font tiles give sub-tile positioning without OAM.
    if(x<4 || y<4) return;
    x-=4; y-=4;
    auto tiles=(volatile u32*)((kZeldaBackBuffer+0x4000)+120*32);
    for(unsigned i=0;i<32;++i) tiles[i]=0;
    unsigned ox=(x&7)+2,oy=(y&7)+2;
    for(unsigned py=0;py<5;++py) for(unsigned px=0;px<5;++px) {
        unsigned distance=(px>2?px-2:2-px)+(py>2?py-2:2-py);
        if(distance>2) continue;
        unsigned dx=ox+px,dy=oy+py,index=(dy/8*2+dx/8)*8+(dy&7);
        tiles[index]|=(distance==2?3u:2u)<<((dx&7)*4);
    }
    for(unsigned row=0;row<2;++row) for(unsigned col=0;col<2;++col)
        sMap[(y/8+row)*32+x/8+col]=0xD000| (120+row*2+col);
}
static u32 sUiState[32], sUiStateValid;
static u32 sInventoryFrame, sInventorySelection, sSelectionOnly;
static unsigned inventoryByte(unsigned offset)
{
    return (sUiState[3+offset/4]>>((offset&3)*8))&255;
}
static unsigned inventoryVariant(unsigned slot) { return slot==3?1:inventoryByte(slot); }
static bool selectedOwned()
{
    unsigned selected=sUiState[1]?sUiState[2]:0;
    return selected && selected<=24 && inventoryByte(selected-1)>0 && inventoryVariant(selected-1)<9;
}
#include "ZeldaInventory.h"
static void floorLabel(unsigned x,unsigned y,int floor)
{
    if(floor<0) { text(x,y,"B"); number(x+1,y,-floor,1); }
    else { number(x,y,floor+1,1); text(x+1,y,"F"); }
}
static void drawMapViewStep(unsigned step)
{
    sNextBg1=1|128|(12<<8); sNextScroll=0;
    if(!sMapReady) { text(4,10,"MAP DATA UNAVAILABLE"); return; }
    if(step==0) {
    // World colors 0..127; dungeon colors 128..175; UI colors 192..255.
    auto palette=sPalette;
    if(sDungeon>=0) for(unsigned group=0;group<3;++group) for(unsigned i=0;i<16;++i)
        palette[128+group*16+i]=i==0?rgb(3,5,4):(group==2?rgb(31,24,7):(i==1?rgb(7,11,8):(group==1?rgb(19,25,17):rgb(9,13,10))));
    for(unsigned y=0;y<16;++y) for(unsigned x=0;x<16;++x) sWorld[(5+y)*32+1+x]=y*16+x;
    return;
    }
    if(sDungeon<0) {
        if(step==1) {
        text(2,3,sWorldKind?"THE DARK WORLD":"KINGDOM OF HYRULE");
        text(19,6,sWorldKind?"DARK":"LIGHT"); text(19,8,"WORLD");
        text(19,12,"YOU",0xE000); text(19,14,live() && guest8(0x03002BDC)==9?"OUTSIDE":"INSIDE",0xE000);
        } else if(step==2) {
        text(2,22,sWorldPosition?"POSITION TRACKS YOUR JOURNEY":"EXPLORE TO FIND YOUR POSITION",0xE000);
        if(sWorldPosition) marker(8+(sWorldX<4096?sWorldX/32:127),40+(sWorldY<4096?sWorldY/32:127));
        }
    } else {
        if(step==1) {
        static const char* const names[]={"SEWERS","HYRULE CASTLE","EASTERN PALACE","DESERT PALACE","CASTLE TOWER","SWAMP PALACE","PALACE OF DARKNESS","MISERY MIRE","SKULL WOODS","ICE PALACE","TOWER OF HERA","THIEVES TOWN","TURTLE ROCK","GANONS TOWER"};
        text(2,3,names[sDungeon]);
        panel(20,7,11,3); text(23,8,"UP");
        } else if(step==2) {
        floorLabel(24,12,sFloor);
        panel(20,15,11,3); text(22,16,"DOWN");
        } else if(step==3) {
        panel(20,19,11,4,sFollowFloor); text(22,20,"FOLLOW"); text(22,21,"LINK",0xE000);
        bool owned=*(volatile const u16*)0x02002348 & (0x8000>>sDungeon);
        text(2,22,owned?"DUNGEON MAP":"EXPLORED ROOMS",0xE000);
        } else if(step==4) {
        unsigned room=remapRoom(*(volatile const u16*)0x03002C0A);
        if(sFloor==sGameFloor) for(unsigned i=0;i<25;++i)
            if(mapByte(layoutOffset(sDungeon)+(sFloor-lowestFloor(sDungeon))*25+i)==room) {
                marker(8+4+i%5*24+((*(volatile const u16*)0x030038F4)&511)*24/512,
                       40+4+i/5*24+((*(volatile const u16*)0x030038F0)&511)*24/512); break;
            }
        }
    }
}
// Snapshot only the guest state that affects the lower display. Rebuilding an
// unchanged inventory wastes most of a guest frame and delays its audio mixer.
static bool changedState(unsigned index,u32 value)
{
    bool changed=sUiState[index]!=value;
    sUiState[index]=value;
    return changed;
}
static bool displayChanged()
{
    bool changed=!sUiStateValid;
    sSelectionOnly=sInventoryFrame && !sMapView && sUiStateValid && sUiState[1]==sSessionReady;
    for(unsigned i=0;i<16 && sSelectionOnly;++i)
        if(sUiState[3+i]!=((volatile const u32*)0x02002320)[i]) sSelectionOnly=0;
    sUiStateValid=1;
    changed|=changedState(0,sMapView);
    changed|=changedState(1,sSessionReady);
    if(!sMapView) {
        changed|=changedState(2,guest8(0x03002C7E));
        bool detailsChanged=changedState(19,guest8(0x0300388E));
        detailsChanged|=changedState(20,*(volatile const u16*)0x03002CE2);
        detailsChanged|=changedState(21,guest8(0x030038E4));
        changed|=detailsChanged;
        for(unsigned i=0;i<16;++i)
            changed|=changedState(3+i,((volatile const u32*)0x02002320)[i]);
    } else {
        changed|=sRenderedMap<0;
        changed|=changedState(2,sDungeon);
        changed|=changedState(3,sFloor);
        changed|=changedState(4,sGameFloor);
        changed|=changedState(5,sFollowFloor);
        if(sDungeon<0) {
            changed|=changedState(6,sWorldKind);
            changed|=changedState(7,sWorldPosition);
            changed|=changedState(8,(sWorldX/32)|(sWorldY/32<<16));
            changed|=changedState(9,guest8(0x03002BDC)==9);
            bool objectives=changedState(10,guest8(0x03003890)|(guest8(0x020022DB)<<8));
            objectives|=changedState(11,guest8(0x02002354)|(guest8(0x0200235A)<<8));
            objectives|=changedState(12,guest8(0x0201094F)|(guest8(0x0201095F)<<8)|
                                       (guest8(0x0201096F)<<16)|(guest8(0x0201097F)<<24));
            if(objectives) { sRenderedMap=-1; changed=true; }
        } else {
            changed|=changedState(6,*(volatile const u16*)0x03002C0A);
            changed|=changedState(7,((*(volatile const u16*)0x030038F4)&511)*24/512);
            changed|=changedState(8,((*(volatile const u16*)0x030038F0)&511)*24/512);
            if(dungeonChanged()) { sRenderedMap=-1; changed=true; }
        }
    }
    displayServiceAudio();
    return changed;
}

enum BuildPhase { Idle, Clear, Header, Inventory, MapImage, MapLabels, Finish, Selection, MapMarkers };
static u32 sBuildPhase, sBuildStep, sBuildView, sBuildWorld;
static int sBuildDungeon, sBuildFloor, sBuildKey;
static unsigned scanlinesSince(unsigned start)
{
    unsigned end=REG_VCOUNT;
    return end>=start?end-start:end+263-start;
}
static void beginFrame()
{
    sBuildView=sMapView; sBuildDungeon=sDungeon; sBuildFloor=sFloor; sBuildWorld=sWorldKind;
    sBuildKey=sDungeon<0?(int)sWorldKind:16+sDungeon*16+sFloor+8;
    if(!sMapView) sRenderedMap=-1;
    sBuildPhase=sSelectionOnly?Selection:Clear; sBuildStep=0;
    sInventoryFrame=0;
    if(sMapView && sDungeon<0) snapshotWorldMarkers();
    ++gZeldaRenderDebug[2];
}
static void buildFrameStep()
{
    switch(sBuildPhase) {
    case Clear:
        // BG1's four-pixel inventory scroll exposes one extra tile row.
        for(unsigned i=sBuildStep;i<sBuildStep+64 && i<800;++i) { sMap[i]=0; sWorld[i]=sMapView?256:0x007F; sPanels[i]=0; }
        sBuildStep+=64;
        if(sBuildStep>=800) { sBuildPhase=Header; sBuildStep=0; }
        break;
    case Header:
        panel(1,0,15,3,!sMapView); panel(16,0,15,3,sMapView);
        text(3,1,"INVENTORY"); text(22,1,"MAP");
        sBuildPhase=!sMapView?Inventory:(sMapReady && sRenderedMap!=sBuildKey?MapImage:MapLabels);
        break;
    case Selection:
        drawInventoryStep(32+sBuildStep++);
        if(sBuildStep==kNativeInventorySteps-32) sBuildPhase=Finish;
        break;
    case Inventory:
        drawInventoryStep(sBuildStep++);
        if(sBuildStep==kNativeInventorySteps) sBuildPhase=Finish;
        break;
    case MapImage:
        if(sDungeon<0) {
            drawWorldTile(sBuildStep++);
            if(sBuildStep==256) { worldPalette(); worldMarkerPalette(); sBuildPhase=MapMarkers; sBuildStep=0; sRenderedMap=sBuildKey; }
        } else {
            drawDungeonStep(sBuildStep++);
            // Empty/concealed cells have no pixels: skip their 24 row units.
            if(sBuildStep>32 && (sBuildStep-32)%25==1 && sDrawRoomShape>=186) sBuildStep+=24;
            if(sBuildStep==32+25*25) { sBuildPhase=MapLabels; sBuildStep=0; sRenderedMap=sBuildKey; }
        }
        break;
    case MapMarkers:
        drawWorldMarkerRow(sBuildStep++);
        if(sBuildStep>=sWorldMarkerCount*8) { sBuildPhase=MapLabels; sBuildStep=0; }
        break;
    case MapLabels:
        drawMapViewStep(sBuildStep++);
        if(sBuildStep==5) sBuildPhase=Finish;
        break;
    case Finish:
        sPalette[0]=sMapView?rgb(3,5,4):0;
        gZeldaVideoDebug[6]=REG_VCOUNT;
        ++gZeldaVideoDebug[7];
        ++gZeldaRenderDebug[3];
        sFramePending=1; sBuildPhase=Idle;
        sInventoryFrame=!sMapView; sInventorySelection=sUiState[1]?sUiState[2]:0;
        break;
    }
}
static void composeFrame()
{
    if(sFramePending) return;
    // Structural changes cancel unfinished work. Position changes queue a later
    // refresh instead, so continuous movement cannot starve map completion.
    if(sBuildPhase && (sBuildView!=sMapView || sUiState[1]!=sSessionReady ||
       (sMapView?(sBuildDungeon!=sDungeon || sBuildFloor!=sFloor || sBuildWorld!=sWorldKind):
                  sUiState[2]!=guest8(0x03002C7E)))) {
        sBuildPhase=Idle; sUiStateValid=0; sRenderedMap=-1;
        ++gZeldaRenderDebug[4];
    }
    if(!sBuildPhase) {
        if((sTicks&3) || !displayChanged()) return;
        beginFrame();
    }
    unsigned start=REG_VCOUNT;
    // About 1 ms per display IRQ plus the final small unit. The guest must run
    // between slices to mix NEW music samples; FIFO servicing alone cannot do it.
    do {
        unsigned unitStart=REG_VCOUNT;
        buildFrameStep();
        displayServiceAudio();
        unsigned unit=scanlinesSince(unitStart);
        if(unit>gZeldaRenderDebug[5]) gZeldaRenderDebug[5]=unit;
    } while(sBuildPhase && scanlinesSince(start)<16);
    unsigned elapsed=scanlinesSince(start);
    ++gZeldaRenderDebug[0];
    if(elapsed>gZeldaRenderDebug[1]) gZeldaRenderDebug[1]=elapsed;
    gZeldaRenderDebug[6]=sBuildPhase; gZeldaRenderDebug[7]=sBuildStep;
}

[[gnu::noinline]] static void updateInventory()
{
    u32 packet=gZeldaTouch;
    if(packet==sPacket) ++sStale; else sStale=0;
    sPacket=packet;
    bool down=(packet&0x10000) && sStale<4;
    if(*(volatile const u32*)0x03006D10!=13) sSessionReady=0;
    else if(live()) sSessionReady=1;
    if(!sSessionReady) {
        REG_DISPCNT_SUB=0x10000; ((volatile u16*)0x05000400)[0]=0;
        sFramePending=0; sBuildPhase=Idle; sUiStateValid=0;
        sInventoryFrame=0; sMapView=0; sRenderedMap=-1; sDown=down;
        return;
    }
    trackMap();
    unsigned x=packet&255,y=(packet>>8)&255;
    if(down && !sDown) {
        if(y<24) { sMapView=x>=128; sRenderedMap=-1; }
        else if(sMapView) mapTouch(x,y);
        else if(x>=16 && x<160 && y>=32 && y<128) {
            ++gZeldaDebug[0]; equip((y-32)/24*6+(x-16)/24);
        }
    }
    sDown=down;
    gZeldaDebug[2]=packet; gZeldaDebug[3]=live();
    gZeldaDebug[4]=guest8(0x03002C7E); gZeldaDebug[5]=guest8(0x030039BC);
    gZeldaDebug[6]=sMapView?(0x10000|((sDungeon+1)<<8)|(sFloor&255)):0;
    gZeldaDebug[7]=sMapLoadStatus;
    ++sTicks;
    composeFrame();
}

// Small ITCM copy avoids slow uncached instruction fetches during publication.
// DMA channels belong to guest emulation and must not be borrowed here.
[[gnu::section(".itcm"), gnu::noinline]]
static void copyBottomWords(void* dst, const void* src, unsigned words)
{
    asm volatile(
        "1: ldmia %1!, {r3-r10}\n"
        "stmia %0!, {r3-r10}\n"
        "subs %2, %2, #8\n"
        "bne 1b\n"
        : "+r"(dst), "+r"(src), "+r"(words)
        : : "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10", "cc", "memory");
}
[[gnu::noinline]] static void publishBottomFrame()
{
    if(!sFramePending) return;
    unsigned start=REG_VCOUNT;
    // A delayed guest IRQ must retain the previous complete frame. Start early
    // enough to finish both VRAM and palette copies before visible scanout.
    if(start<192 || start>=200) { ++gZeldaVideoDebug[1]; return; }
    for(unsigned offset=0;offset<0x8000;offset+=2048) {
        copyBottomWords((void*)(0x06200000+offset),(const void*)(kZeldaBackBuffer+offset),2048/4);
        displayServiceAudio();
    }
    copyBottomWords((void*)0x05000400,(const void*)kZeldaPaletteBuffer,512/4);
    REG_BG1CNT_SUB=sNextBg1; REG_BG1VOFS_SUB=sNextScroll;
    unsigned end=REG_VCOUNT;
    gZeldaVideoDebug[2]=start; gZeldaVideoDebug[3]=end;
    if(end<192) ++gZeldaVideoDebug[4];
    unsigned elapsed=end>=start?end-start:end+263-start;
    if(elapsed>gZeldaVideoDebug[5]) gZeldaVideoDebug[5]=elapsed;
    ++gZeldaVideoDebug[0];
    sFramePending=0;
    REG_DISPCNT_SUB=0x10700;
}

extern "C" [[gnu::section(".itcm")]] void fusionScreenVBlank()
{
    publishBottomFrame();
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
    updateInventory();
}
