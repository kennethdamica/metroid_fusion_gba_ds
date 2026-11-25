// Exercise the shipping inventory asset loader and compositor with guarded RAM.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t;
static FILE* rom;
static bool readAt(u32 offset,void* data,unsigned count) { return !fseek(rom,offset,SEEK_SET) && fread(data,1,count,rom)==count; }
static u32 back[0x8000/4],guestTiles[0x3000/4];
static u16 palette[256],stagedPalette[256];
static constexpr unsigned kZeldaBackBuffer=0x06858000;
static void* hostAddress(uintptr_t at) {
    if(at>=kZeldaBackBuffer && at<kZeldaBackBuffer+0x8000) return (u8*)back+at-kZeldaBackBuffer;
    if(at>=0x06004000 && at<0x06007000) return (u8*)guestTiles+at-0x06004000;
    if(at==0x05000000) return palette;
    abort();
}
#define ZELDA_INVENTORY_ADDRESS(address) hostAddress(address)
static volatile u16* sWorld=(u16*)((u8*)back+0x6000);
static volatile u16* sPalette=stagedPalette;
static u32 sUiState[32],sNextBg1,sNextScroll;
static u16 sIcons[24][9][4];
static unsigned inventoryByte(unsigned i) { return (sUiState[3+i/4]>>((i&3)*8))&255; }
static unsigned inventoryVariant(unsigned slot) { return slot==3?1:inventoryByte(slot); }
static bool selectedOwned() { unsigned n=sUiState[2];return n && n<=24 && inventoryByte(n-1) && inventoryVariant(n-1)<9; }
#include "../../runtime/alttp/ZeldaInventory.h"
static void require(bool b,const char* message) { if(!b) { fprintf(stderr,"%s\n",message);exit(1); } }
static unsigned word(unsigned offset) { unsigned tile=(offset-0x1000)/2;return sWorld[tile-6*32]; }
int main(int argc,char** argv) {
    require(argc==2,"ROM required");rom=fopen(argv[1],"rb");require(rom,"ROM open");
    require(loadNativeInventory(),"decode original inventory assets");
    for(unsigned i=0;i<24;++i) { u32 p;require(readAt(0x16B5A8+i*4,&p,4),"icon pointer"); require(readAt(p-0x08000000,sIcons[i],sizeof(sIcons[i])),"icon descriptors"); }
    for(unsigned i=0;i<sizeof(guestTiles)/4;++i) guestTiles[i]=i*0x1234567;
    for(unsigned i=0;i<256;++i) palette[i]=i;
    const unsigned maxValues[24]={4,2,1,1,3,8,1,1,1,1,1,8,1,1,3,1,1,8,1,1,1,1,2,8};
    unsigned cases=0;
    for(unsigned slot=0;slot<24;++slot) for(unsigned value=1;value<=maxValues[slot];++value) {
        memset(back,0xA5,sizeof(back));memset(stagedPalette,0,sizeof(stagedPalette));memset(sUiState,0,sizeof(sUiState));
        sUiState[1]=1;sUiState[2]=slot+1;sUiState[20]=255;
        sUiState[3+slot/4]=value<<((slot&3)*8);
        for(unsigned step=0;step<kNativeInventorySteps;++step) drawInventoryStep(step);
        require(!memcmp(back,guestTiles,sizeof(guestTiles)),"guest tile copy");
        require(!memcmp((u8*)back+0x3000,sMenuFont,sizeof(sMenuFont)),"menu font copy");
        for(unsigned i=0x4000;i<0x6000;++i) require(((u8*)back)[i]==0xA5,"private tab graphics overwritten");
        for(unsigned i=0x6800;i<0x8000;++i) require(((u8*)back)[i]==0xA5,"other backgrounds overwritten");
        for(unsigned i=192;i<256;++i) require(stagedPalette[i]==0,"tab palette overwritten");
        unsigned at=nativeItemOffset(slot),v=slot==3?1:value;
        require(word(at)==sIcons[slot][v][0] && word(at+2)==sIcons[slot][v][1] && word(at+64)==sIcons[slot][v][2],"item icon does not match original descriptors");
        require(word(at-2)==0x9053 && word(at+4)==0x9453,"original selection brackets");
        unsigned name=nativeNameAddress(slot,value);require(name>=0x16B880 && name+32<=0x16E004,"name table bounds");
        u16 expected[16];require(readAt(name,expected,32),"name read");
        for(unsigned i=0;i<8;++i) require(word(0x132C+i*2)==expected[i] && word(0x136C+i*2)==expected[8+i],"item name differs from ROM");
        ++cases;
    }
    // Story and dungeon state choose distinct, original progress widgets.
    memset(sUiState,0,sizeof(sUiState));sUiState[19]=3;sUiState[20]=255;
    nativeDetails(0);nativeDetails(4);
    require(word(0x13EC)==menuHalf(menuPointer(0x16BD9C)-0x08000000),"crystals heading");
    require(word(0x1430)==menuHalf(0x16BB98),"uncollected crystal");
    sUiState[20]=2;sUiState[3+40/4]=0x4000;nativeDetails(3);
    require(word(0x16AC)==menuHalf(0x16BB28+8),"owned dungeon map icon");
    fclose(rom);printf("{\"item_variants\":%u,\"asset_bytes\":%zu}\n",cases,sizeof(sMenuLayout)+sizeof(sMenuFont)+sizeof(sMenuData));
}
