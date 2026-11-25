#pragma once
// Original world-map objectives, decoded from the user's AZLE r0 tables.
// Snapshot state before composing: never write into the running game.
struct ZeldaWorldMarker { unsigned x, y, tile, palette, size; };
static ZeldaWorldMarker sWorldMarkers[8];
static unsigned sWorldMarkerCount;
static unsigned markerByte(unsigned address) { return sAtlas->markerTables[address-0x16ED34]; }
static unsigned markerHalf(unsigned address) { return markerByte(address)|(markerByte(address+1)<<8); }
static void addWorldMarker(unsigned x,unsigned y,unsigned tile,unsigned palette,unsigned size)
{
    if(sWorldMarkerCount>=8 || x>=4096 || y>=4096) return;
    sWorldMarkers[sWorldMarkerCount++]={x/32,y/32,tile,palette,size};
}
static void snapshotWorldMarkers()
{
    sWorldMarkerCount=0;
    unsigned stage=guest8(0x03003890);
    // The game keeps a return portal in slot 15, only in the light world.
    unsigned px=guest8(0x0201094F)|(guest8(0x0201095F)<<8);
    unsigned py=guest8(0x0201096F)|(guest8(0x0201097F)<<8);
    if(!sWorldKind && (px || py)) addWorldMarker(px,py,0xCA,1,16);
    if(stage>8 || (stage>=6)!=bool(sWorldKind) || (guest8(0x020022DB)&32)) return;
    for(unsigned i=0;i<7;++i) {
        if(stage==3 && i<3 && (guest8(0x02002354)&markerByte(0x16EEB6+i))) continue;
        if(stage==7 && (guest8(0x0200235A)&markerByte(0x16EEB9+i))) continue;
        unsigned x=markerHalf(0x16ED34+i*36+stage*2);
        unsigned y=markerHalf(0x16ED46+i*36+stage*2);
        unsigned style=markerHalf(0x16EE30+i*18+stage*2);
        if(x&0x8000) continue; // original table's hidden-marker sentinel
        unsigned tile=style>>8, bank=((style&255)>>1)&7;
        // Zero style denotes the flashing red objective X. Keep a steady
        // original frame here so an otherwise idle map need not be repainted.
        if(!tile) { tile=0xC8; bank=1; }
        unsigned palette=bank==4?2:bank==2?1:0;
        addWorldMarker(x,y,tile,palette,style?16:8);
    }
}
static unsigned worldMarkerPixel(unsigned tile,unsigned x,unsigned y)
{
    // The game uploads the last two 16-tile rows of this sheet to OBJ C0/E0.
    unsigned source=32+(tile-0xC0)/32*16+(tile&31)+(y/8)*16+x/8;
    if(source>=64) return 0;
    unsigned bits=sAtlas->markerGraphics[source*32+(y&7)*4+(x&7)/2];
    return (bits>>((x&1)*4))&15;
}
static void worldMarkerPalette()
{
    for(unsigned p=0;p<3;++p) for(unsigned i=0;i<16;++i)
        ((volatile u16*)ZELDA_MAP_ADDRESS(kZeldaPaletteBuffer))[128+p*16+i]=sAtlas->markerPalette[p][i];
}
// Eight output rows per marker, one small row per composition unit. Original
// 16px icons become 8px; the game's small objective X retains its 8px size.
static void drawWorldMarkerRow(unsigned step)
{
    unsigned index=step/8,row=step%8;
    if(index>=sWorldMarkerCount) return;
    const auto& m=sWorldMarkers[index];
    int y=(int)m.y-4+(int)row;
    if(y<0 || y>=128) return;
    for(unsigned col=0;col<8;++col) {
        int x=(int)m.x-4+(int)col;
        if(x<0 || x>=128) continue;
        unsigned color=worldMarkerPixel(m.tile,col*m.size/8,row*m.size/8);
        if(color) mapPixel(x,y,128+m.palette*16+color);
    }
}
