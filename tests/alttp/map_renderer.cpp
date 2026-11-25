// Exercise the shipping ROM decoder/renderer against bounded host memory.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

using u8=uint8_t; using u16=uint16_t; using u32=uint32_t; using s8=int8_t;
static FILE* rom;
static bool readAt(u32 offset,void* data,unsigned bytes) { return !fseek(rom,offset,SEEK_SET) && fread(data,1,bytes,rom)==bytes; }
static u8 mainRam[0x40000],workRam[0x10000],palette[0x10000],screen[0x10000],capture[0x20000],displayCapture[0x20000];
static void* hostAddress(uintptr_t address) {
    if(address>=0x02000000 && address<0x02040000) return mainRam+address-0x02000000;
    if(address>=0x03000000 && address<0x03010000) return workRam+address-0x03000000;
    if(address>=0x05000000 && address<0x05010000) return palette+address-0x05000000;
    if(address>=0x06200000 && address<0x06210000) return screen+address-0x06200000;
    if(address>=0x06840000 && address<0x06860000) return displayCapture+address-0x06840000;
    if(address>=0x06860000 && address<0x06880000) return capture+address-0x06860000;
    abort();
}
#define ZELDA_MAP_ADDRESS(address) hostAddress(address)
static u8& guest8(u32 address) { return *(u8*)hostAddress(address); }
static bool live() { return true; }
static void displayServiceAudio() {}
#include "../../runtime/alttp/ZeldaMap.h"
static void require(bool value,const char* message) { if(!value) { fprintf(stderr,"%s\n",message); exit(1); } }
static void dump(const std::string& path,const void* data,size_t bytes) { FILE* f=fopen(path.c_str(),"wb"); require(f,"output"); require(fwrite(data,1,bytes,f)==bytes,"write"); fclose(f); }
int main(int argc,char** argv) {
    require(argc==3,"ROM and output directory required"); rom=fopen(argv[1],"rb"); require(rom,"ROM");
    memset(displayCapture,0xA5,sizeof(displayCapture));
    memset(screen,0xA5,sizeof(screen));
    memset(palette,0xA5,sizeof(palette));
    memset((void*)hostAddress(0x06860000),0xA5,0x20000);
    require(loadMaps(),"decode all map assets");
    for(unsigned i=0;i<0x18000;++i) require(((u8*)hostAddress(0x06860000))[i]==0xA5,"top capture overwritten");
    for(unsigned i=sizeof(ZeldaMapCache);i<0x8000;++i) require(((u8*)hostAddress(0x06878000))[i]==0xA5,"map cache overflow");
    u8 cache[sizeof(ZeldaMapCache)]; memcpy(cache,(void*)hostAddress(0x06878000),sizeof(cache));
    std::string out=argv[2];
    for(unsigned w=0;w<2;++w) { sWorldKind=w;drawWorld();dump(out+"/world"+std::to_string(w)+".raw",(void*)hostAddress(kZeldaBackBuffer),16384); }
    // Exercise every story stage in both worlds, including hidden coordinates,
    // cropped edge markers, collected rewards, and the return portal.
    for(unsigned world=0;world<2;++world) for(unsigned stage=0;stage<9;++stage) {
        sWorldKind=world;guest8(0x03003890)=stage;snapshotWorldMarkers();
        require(sWorldMarkerCount<=7,"objective count bounds");
        if((stage>=6)!=bool(world)) require(!sWorldMarkerCount,"objectives shown in wrong world");
        drawWorld();worldMarkerPalette();
        memset(hostAddress(kZeldaBackBuffer+0x4000),0xA5,0x4000);
        for(unsigned i=0;i<sWorldMarkerCount*8;++i) drawWorldMarkerRow(i);
        for(unsigned i=0;i<0x4000;++i) require(((u8*)hostAddress(kZeldaBackBuffer+0x4000))[i]==0xA5,"marker crossed image boundary");
        dump(out+"/markers"+std::to_string(world)+"s"+std::to_string(stage)+".raw",hostAddress(kZeldaBackBuffer),16384);
    }
    sWorldKind=0;guest8(0x03003890)=3;snapshotWorldMarkers();require(sWorldMarkerCount==4,"pendant quest markers");
    guest8(0x02002354)=4;snapshotWorldMarkers();require(sWorldMarkerCount==3,"collected pendant still marked");
    guest8(0x02002354)=7;snapshotWorldMarkers();require(sWorldMarkerCount==1,"collected pendants still marked");
    sWorldKind=1;guest8(0x03003890)=7;snapshotWorldMarkers();require(sWorldMarkerCount==7,"seven crystal markers");
    guest8(0x0200235A)=2;snapshotWorldMarkers();require(sWorldMarkerCount==6,"collected crystal still marked");
    guest8(0x0200235A)=127;snapshotWorldMarkers();require(sWorldMarkerCount==0,"collected crystals still marked");
    guest8(0x03003890)=255;snapshotWorldMarkers();require(!sWorldMarkerCount,"invalid quest stage");
    sWorldKind=0;guest8(0x03003890)=0;guest8(0x020022DB)=32;snapshotWorldMarkers();require(!sWorldMarkerCount,"suppressed objectives");
    guest8(0x0201094F)=32;guest8(0x0201096F)=32;snapshotWorldMarkers();require(sWorldMarkerCount==1,"return portal");
    sWorldKind=1;snapshotWorldMarkers();require(!sWorldMarkerCount,"portal in dark world");
    *(u16*)hostAddress(0x02002348)=0xFFFF;
    unsigned floors=0,rooms=0;
    for(int d=0;d<14;++d) for(int f=lowestFloor(d);f<=highestFloor(d);++f) {
        sDungeon=d; sFloor=f; sGameFloor=f; ++floors;
        unsigned start=layoutOffset(d)+(f-lowestFloor(d))*25;
        require(start>=0x16F71E && start+25<=0x16FCE2,"floor layout bounds");
        for(unsigned i=0;i<25;++i) {
            unsigned room=mapByte(start+i); if(room==15)continue;
            require(roomShape(d,room)<186,"room shape bounds"); ++rooms;
        }
        *(u16*)hostAddress(0x03002C0A)=0xFFFF;
        memset((void*)hostAddress(kZeldaBackBuffer+0x4000),0xA5,0x4000);
        drawDungeon();
        // Compare the incremental packed-row renderer with the original
        // per-pixel ROM decoder, including flipped tiles on every floor.
        u8 expected[16384]; memset(expected,128,sizeof(expected));
        for(unsigned cell=0;cell<25;++cell) {
            unsigned room=mapByte(start+cell); if(room==15) continue;
            unsigned shape=roomShape(d,room);
            for(unsigned y=0;y<24;++y) for(unsigned x=0;x<24;++x) {
                unsigned color=roomPixel(d,shape,x*2/3,y*2/3);
                unsigned px=4+cell%5*24+x,py=4+cell/5*24+y;
                if(color) expected[(py/8*16+px/8)*64+(py&7)*8+(px&7)]=128+color;
            }
        }
        require(!memcmp(expected,hostAddress(kZeldaBackBuffer),sizeof(expected)),"incremental dungeon pixels differ from ROM decoder");
        for(unsigned i=0;i<0x4000;++i) require(((u8*)hostAddress(kZeldaBackBuffer+0x4000))[i]==0xA5,"renderer crossed image boundary");
        dump(out+"/d"+std::to_string(d)+"f"+std::to_string(f)+".raw",(void*)hostAddress(kZeldaBackBuffer),16384);
        // Floor controls clamp at bounds and FOLLOW resets to the guest floor.
        sFloor=highestFloor(d);mapTouch(200,64);require(sFloor==highestFloor(d),"upper floor clamp");
        sFloor=lowestFloor(d);mapTouch(200,128);require(sFloor==lowestFloor(d),"lower floor clamp");
        sFloor=f; sFollowFloor=false;mapTouch(200,166);require(sFloor==f && sFollowFloor,"follow floor");
    }
    require(!memcmp(cache,(void*)hostAddress(0x06878000),sizeof(cache)),"renderer modified cached ROM data");
    // Without a dungeon map, unseen rooms stay concealed.
    sDungeon=1;sFloor=0;sGameFloor=0;*(u16*)hostAddress(0x02002348)=0;*(u16*)hostAddress(0x03002C0A)=0xFFFF;drawDungeon();
    for(unsigned i=0;i<16384;++i) require(((u8*)hostAddress(kZeldaBackBuffer))[i]==128,"unseen room exposed without map");
    for(auto byte:screen) require(byte==0xA5,"renderer changed the visible bottom frame");
    for(auto byte:palette) require(byte==0xA5,"renderer changed the visible palette");
    for(unsigned i=0;i<0x18000;++i) require(displayCapture[i]==0xA5,"renderer changed the top framebuffer");
    printf("{\"floors\":%u,\"room_cells\":%u,\"cache_bytes\":%zu}\n",floors,rooms,sizeof(ZeldaMapCache));
}
