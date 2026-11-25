#include "ZeldaVideo.h"
#ifndef ZELDA_MAP_ADDRESS
#define ZELDA_MAP_ADDRESS(address) (address)
#endif
// AZLE r0 map tables are read from the user's ROM, never embedded in the NDS.
// A 256x192 capture uses 96 KiB of VRAM D. Its last 32 KiB is a read-only cache.
// Do not enlarge DISPCAPCNT capture dimensions or clear D after loading this.
struct ZeldaMapCache {
    u8 worldTiles[256][16]; // original 8x8 tiles sampled to 4x4
    u8 worldLayout[2][1024]; // central 256x256 of each original 512x512 map
    u16 worldPalette[2][128];
    u8 dungeon[0xCEE]; // ROM 16F132..16FE20: shapes, floors, rooms, pointers
    u8 roomGraphics[5][2048];
    u8 markerTables[0x194]; // ROM 16ED34..16EEC8: seven objectives, nine stages
    u8 markerGraphics[2048]; // original map sprites, ROM 236420
    u16 markerPalette[3][16]; // OBJ banks 1, 2, 4, independent of room lighting
};
static_assert(sizeof(ZeldaMapCache)<=0x7000, "Map cache must leave space for the staged palette");
static volatile ZeldaMapCache* const sAtlas=(volatile ZeldaMapCache*)ZELDA_MAP_ADDRESS(0x06878000);
static unsigned sMapLoadStatus;
static u8* sMapScratch; // startup-only heap allocation, never used by display IRQs
// Default static data lives in VRAM A: use words, because byte stores are ignored.
static u32 sMapReady, sMapView, sFollowFloor=1, sWorldPosition;
static int sDungeon=-1, sFloor, sGameFloor, sRenderedMap=-1;
static unsigned sWorldX, sWorldY, sWorldKind;
static u16 sVisitedRooms[25];
static unsigned sRenderedRoom=0xFFFF, sRenderedOwnership;

// VRAM ignores byte writes. All startup reads go through aligned RAM scratch.
static bool cacheRead(u32 offset, volatile void* target, unsigned bytes)
{
    auto buffer=(u32*)sMapScratch;
    auto dest=(volatile u16*)target;
    while (bytes) {
        unsigned count=bytes>512?512:bytes;
        if ((count&1) || !readAt(offset,buffer,count)) return false;
        for (unsigned i=0;i<count/2;++i) *dest++=((u16*)buffer)[i];
        offset+=count; bytes-=count;
    }
    return true;
}
static bool cacheLz(u32 offset, volatile u8* target)
{
    // These five verified sheets each expand to exactly 2048 bytes.
    u8* input=sMapScratch; u8* output=sMapScratch+2048;
    if (!readAt(offset,input,2048) || input[0]!=0x10 || input[1]!=0 || input[2]!=8 || input[3]) return false;
    unsigned in=4,out=0;
    while (out<2048) {
        if (in>=2048) return false;
        unsigned flags=input[in++];
        for (unsigned mask=128;mask && out<2048;mask>>=1) {
            if (in>=2048) return false;
            if (flags&mask) {
                if (in+1>=2048) return false;
                unsigned a=input[in++],b=input[in++],back=((a&15)<<8)+b+1,count=(a>>4)+3;
                if (back>out || out+count>2048) return false;
                while(count--) { output[out]=output[out-back]; ++out; }
            } else output[out++]=input[in++];
        }
    }
    for(unsigned i=0;i<1024;++i) ((volatile u16*)target)[i]=output[i*2]|(output[i*2+1]<<8);
    return true;
}
static bool loadMapData()
{
    sMapLoadStatus=1;
    u8* tile=sMapScratch;
    for (unsigned t=0;t<256;++t) {
        if (!readAt(0x28A7E0+t*64,tile,64)) return false;
        for (unsigned y=0;y<4;++y)
            for (unsigned x=0;x<4;x+=2)
                ((volatile u16*)sAtlas->worldTiles[t])[y*2+x/2]=tile[y*16+x*2]|(tile[y*16+x*2+2]<<8);
    }
    sMapLoadStatus=2;
    for (unsigned world=0;world<2;++world) {
        for (unsigned row=0;row<32;++row)
            if (!cacheRead(0x3BFEF8+world*4096+(row+16)*64+16,sAtlas->worldLayout[world]+row*32,32)) return false;
        if (!cacheRead(0x3BFA58+world*256,sAtlas->worldPalette[world],256)) return false;
    }
    sMapLoadStatus=3;
    if (!cacheRead(0x16F132,sAtlas->dungeon,sizeof(sAtlas->dungeon))) return false;
    const u32 sheets[5]={0x255460,0x2521CC,0x255658,0x2523F8,0x246EA0};
    for(unsigned i=0;i<5;++i) { sMapLoadStatus=4+i; if(!cacheLz(sheets[i],sAtlas->roomGraphics[i])) return false; }
    if(!cacheRead(0x16ED34,sAtlas->markerTables,sizeof(sAtlas->markerTables)) ||
       !cacheLz(0x236420,sAtlas->markerGraphics)) return false;
    for(unsigned i=0;i<3;++i)
        if(!cacheRead(0x3B566C+(i==2?4:i+1)*32,sAtlas->markerPalette[i],32)) return false;
    sMapLoadStatus=9;
    return true;
}
static bool loadMaps()
{
    sMapScratch=new u8[4096];
    if(!sMapScratch) return false;
    bool ready=loadMapData();
    delete[] sMapScratch; sMapScratch=nullptr;
    return ready;
}
static unsigned mapByte(unsigned offset) { return sAtlas->dungeon[offset-0x16F132]; }
static unsigned mapHalf(unsigned offset) { return mapByte(offset)|(mapByte(offset+1)<<8); }
static unsigned mapPointer(unsigned offset) {
    return mapHalf(offset)|(mapHalf(offset+2)<<16);
}
static unsigned dungeonFloors(unsigned dungeon) { return mapHalf(0x16F702+dungeon*2); }
static int lowestFloor(unsigned dungeon) { return -(int)(dungeonFloors(dungeon)&15); }
static int highestFloor(unsigned dungeon) { return (int)((dungeonFloors(dungeon)>>4)&15)-1; }
static unsigned layoutOffset(unsigned dungeon) { return mapPointer(0x16FCF4+dungeon*4)-0x08000000; }
static int currentDungeon()
{
    if (!live()) return -1;
    unsigned value=*(volatile const u16*)ZELDA_MAP_ADDRESS(0x03002CE2);
    return guest8(0x03002BDC)==7 && !(value&1) && value<28 ? value/2 : -1;
}
static void trackMap()
{
    if (!live()) return;
    int dungeon=currentDungeon(), floor=(s8)guest8(0x03002C0E);
    if (dungeon!=sDungeon || floor!=sGameFloor) { sFollowFloor=true; sRenderedMap=-1; }
    sDungeon=dungeon; sGameFloor=floor;
    if(sFollowFloor) sFloor=floor;
    if(dungeon>=0) {
        if(sFloor<lowestFloor(dungeon)) sFloor=lowestFloor(dungeon);
        if(sFloor>highestFloor(dungeon)) sFloor=highestFloor(dungeon);
    }
    if (guest8(0x03002BDC)==9 && guest8(0x03002BF6)<128) {
        sWorldX=*(volatile const u16*)ZELDA_MAP_ADDRESS(0x030038F4);
        sWorldY=*(volatile const u16*)ZELDA_MAP_ADDRESS(0x030038F0);
        sWorldKind=(guest8(0x03002BF6)>>6)&1;
        sWorldPosition=true;
    }
}
static void mapTouch(unsigned x,unsigned y)
{
    if(sDungeon<0 || x<160 || x>=248) return;
    int old=sFloor;
    if(y>=56 && y<80 && sFloor<highestFloor(sDungeon)) { ++sFloor; sFollowFloor=false; }
    if(y>=120 && y<144 && sFloor>lowestFloor(sDungeon)) { --sFloor; sFollowFloor=false; }
    if(y>=152 && y<184) { sFollowFloor=true; sFloor=sGameFloor; }
    if(old!=sFloor) sRenderedMap=-1;
}
static void mapPixel(unsigned x,unsigned y,unsigned color)
{
    unsigned offset=((y/8)*16+x/8)*64+(y&7)*8+(x&7);
    auto dest=(volatile u16*)ZELDA_MAP_ADDRESS(kZeldaBackBuffer+(offset&~1));
    unsigned shift=(offset&1)*8;
    *dest=(*dest & ~(255<<shift))|(color<<shift);
}
// One 8x8 output tile, assembled from four cached 4x4 tiles. Word copies
// avoid decoding the same layout index separately for every output pixel.
ZELDA_HOT static void drawWorldTile(unsigned tile)
{
    unsigned tx=tile&15,ty=tile>>4;
    auto dst=(volatile u32*)ZELDA_MAP_ADDRESS(kZeldaBackBuffer+tile*64);
    for(unsigned half=0;half<2;++half) {
        unsigned at=(ty*2+half)*32+tx*2;
        unsigned left=sAtlas->worldLayout[sWorldKind][at];
        unsigned right=sAtlas->worldLayout[sWorldKind][at+1];
        auto l=(volatile const u32*)sAtlas->worldTiles[left];
        auto r=(volatile const u32*)sAtlas->worldTiles[right];
        for(unsigned y=0;y<4;++y) { *dst++=l[y]; *dst++=r[y]; }
    }
}
static void worldPalette()
{
    for(unsigned i=0;i<128;++i) ((volatile u16*)ZELDA_MAP_ADDRESS(kZeldaPaletteBuffer))[i]=sAtlas->worldPalette[sWorldKind][i];
}
static void drawWorld()
{
    for(unsigned tile=0;tile<256;++tile) { drawWorldTile(tile); displayServiceAudio(); }
    worldPalette();
}
#include "ZeldaMarkers.h"
static unsigned remapRoom(unsigned room)
{
    // The original map substitutes the three split dungeon-room identities.
    if(room==0x89) return 0xA9;
    if(room==0xA7) return 0x77;
    if(room==0x4F) return 0xBE;
    return room;
}
static unsigned roomShape(unsigned dungeon,unsigned room)
{
    unsigned start=layoutOffset(dungeon), count=0;
    unsigned total=(highestFloor(dungeon)-lowestFloor(dungeon)+1)*25;
    for(unsigned i=0;i<total;++i) {
        unsigned value=mapByte(start+i);
        if(value==15) continue;
        if(value==room) return mapByte(mapPointer(0x16FDE8+dungeon*4)-0x08000000+count);
        ++count;
    }
    return 0xFF;
}
static unsigned roomPixel(unsigned dungeon,unsigned shape,unsigned x,unsigned y)
{
    if(shape>=186) return 0;
    unsigned word=mapHalf(0x16F132+shape*8+(y/8*2+x/8)*2),tile=word&1023;
    if(tile<0x240 || tile>=0x2C0) return 0;
    unsigned bank;
    if(tile<0x280) bank=(dungeon==6 || dungeon>=9)?1:0;
    else bank=dungeon==12?4:((dungeon==6 || dungeon==9 || dungeon==11 || dungeon==13)?3:2);
    unsigned sx=x&7,sy=y&7;
    if(word&0x400) sx=7-sx;
    if(word&0x800) sy=7-sy;
    unsigned packed=sAtlas->roomGraphics[bank][(tile&63)*32+sy*4+sx/2];
    return (packed>>((sx&1)*4))&15;
}
static bool dungeonChanged()
{
    unsigned current=remapRoom(*(volatile const u16*)ZELDA_MAP_ADDRESS(0x03002C0A));
    unsigned owned=*(volatile const u16*)ZELDA_MAP_ADDRESS(0x02002348) & (0x8000>>sDungeon);
    bool changed=current!=sRenderedRoom || owned!=sRenderedOwnership;
    sRenderedRoom=current; sRenderedOwnership=owned;
    unsigned start=layoutOffset(sDungeon)+(sFloor-lowestFloor(sDungeon))*25;
    for(unsigned cell=0;cell<25;++cell) {
        unsigned room=mapByte(start+cell);
        unsigned visited=room==15?0:*(volatile const u16*)ZELDA_MAP_ADDRESS(0x02002000+room*2)&15;
        if(sVisitedRooms[cell]!=visited) changed=true;
        sVisitedRooms[cell]=visited;
    }
    return changed;
}
// A row at a time permits the guest music mixer to run between redraw slices.
static unsigned sDrawRoomShape, sDrawRoomBase;
ZELDA_HOT static unsigned roomRow(unsigned dungeon,unsigned word,unsigned y)
{
    unsigned tile=word&1023;
    if(tile<0x240 || tile>=0x2C0) return 0;
    unsigned bank;
    if(tile<0x280) bank=(dungeon==6 || dungeon>=9)?1:0;
    else bank=dungeon==12?4:((dungeon==6 || dungeon==9 || dungeon==11 || dungeon==13)?3:2);
    if(word&0x800) y=7-y;
    // The packed ROM cache's room sheets are only halfword-aligned.
    auto bits=(volatile const u16*)sAtlas->roomGraphics[bank]+(tile&63)*16+y*2;
    return bits[0]|(bits[1]<<16);
}
ZELDA_HOT static void drawDungeonStep(unsigned step)
{
    if(step<32) {
        auto pixels=(volatile u32*)ZELDA_MAP_ADDRESS(kZeldaBackBuffer+step*512);
        for(unsigned i=0;i<128;++i) pixels[i]=0x80808080;
        return;
    }
    unsigned cell=(step-32)/25,row=(step-32)%25;
    if(row==0) {
        unsigned start=layoutOffset(sDungeon)+(sFloor-lowestFloor(sDungeon))*25;
        unsigned room=mapByte(start+cell);
        // dungeonChanged() snapshots these before starting a complete image.
        unsigned visited=sVisitedRooms[cell];
        bool here=room==sRenderedRoom && sFloor==sGameFloor;
        sDrawRoomShape=room!=15 && (sRenderedOwnership || visited || here)?roomShape(sDungeon,room):0xFF;
        sDrawRoomBase=here?160:(visited?144:128);
        return;
    }
    if(sDrawRoomShape>=186) return;
    unsigned y=row-1,sy=y*2/3;
    unsigned a=mapHalf(0x16F132+sDrawRoomShape*8+(sy/8*2)*2);
    unsigned b=mapHalf(0x16F132+sDrawRoomShape*8+(sy/8*2+1)*2);
    unsigned left=roomRow(sDungeon,a,sy&7),right=roomRow(sDungeon,b,sy&7);
    for(unsigned x=0;x<24;++x) {
        unsigned sx=x*2/3,word=sx<8?a:b,bits=sx<8?left:right;
        sx&=7;
        if(word&0x400) sx=7-sx;
        unsigned color=(bits>>(sx*4))&15;
        if(color) mapPixel(4+(cell%5)*24+x,4+(cell/5)*24+y,sDrawRoomBase+color);
    }
}
static void drawDungeon()
{
    dungeonChanged();
    for(unsigned step=0;step<32+25*25;++step) { drawDungeonStep(step); displayServiceAudio(); }
}
