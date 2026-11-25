#pragma once
// AZLE r0 English inventory assets, read from the user's verified ROM at boot.
// No game graphics or tilemaps are compiled into the runtime.
#ifdef __arm__
#define ZELDA_MENU_STORAGE [[gnu::section(".ewram.bss")]]
#else
#define ZELDA_MENU_STORAGE
#endif
#ifndef ZELDA_INVENTORY_ADDRESS
#define ZELDA_INVENTORY_ADDRESS(address) (address)
#endif
ZELDA_MENU_STORAGE static u16 sMenuLayout[1024];
ZELDA_MENU_STORAGE static u32 sMenuFont[1024];
ZELDA_MENU_STORAGE static u16 sMenuData[(0x16E004-0x16B880)/2];
static unsigned menuHalf(unsigned address) { return address>=0x16B880 && address<0x16E004 ? sMenuData[(address-0x16B880)/2] : 0x80F5; }
static unsigned menuPointer(unsigned address) { return menuHalf(address)|(menuHalf(address+2)<<16); }
// Verified compressed sizes are 362 bytes (layout) and 1583 bytes (font).
// Keep startup scratch to 2 KiB: the DS runtime shares a small remaining heap.
static bool loadMenuLz(unsigned offset, void* target, unsigned size, u8* input)
{
    if(!readAt(offset,input,2048) || input[0]!=0x10 ||
       (input[1]|(input[2]<<8)|(input[3]<<16))!=size) return false;
    auto output=(u8*)target;
    unsigned in=4,out=0;
    while(out<size) {
        if(in>=2048) return false;
        unsigned flags=input[in++];
        for(unsigned mask=128;mask && out<size;mask>>=1) {
            if(in>=2048) return false;
            if(flags&mask) {
                if(in+1>=2048) return false;
                unsigned a=input[in++],b=input[in++],back=((a&15)<<8)+b+1,count=(a>>4)+3;
                if(back>out || count>size-out) return false;
                while(count--) { output[out]=output[out-back]; ++out; }
            } else output[out++]=input[in++];
        }
    }
    return true;
}
static bool loadNativeInventory()
{
    auto scratch=new u8[2048];
    if(!scratch) return false;
    bool ok=readAt(0x16B880,sMenuData,sizeof(sMenuData)) &&
        loadMenuLz(0x3BFC58,sMenuLayout,sizeof(sMenuLayout),scratch) &&
        loadMenuLz(0x27C5CC,sMenuFont,sizeof(sMenuFont),scratch);
    delete[] scratch;
    return ok;
}
// The original menu occupies rows 9..28 of a 32x32 tilemap. On DS it
// occupies rows 3..22, leaving a separate 24-pixel tab strip above it.
static void menuPut(unsigned offset,unsigned word)
{
    unsigned tile=(offset-0x1000)/2;
    unsigned y=tile/32,x=tile%32;
    if(y>=9 && y<=28 && x>=1 && x<=30) sWorld[(y-6)*32+x]=word;
}
static void menuRun(unsigned offset,unsigned data,unsigned count)
{
    for(unsigned i=0;i<count;++i) menuPut(offset+i*2,menuHalf(data+i*2));
}
static void menuIcon(unsigned offset,unsigned data,unsigned value,unsigned maxValue)
{
    if(value>maxValue) value=0;
    data+=value*8;
    menuRun(offset,data,2); menuRun(offset+64,data+4,2);
}
static unsigned nativeItemOffset(unsigned slot) { return 0x1286+(slot%6)*6+(slot/6)*0xC0; }
static unsigned nativeNameAddress(unsigned slot,unsigned value)
{
    unsigned table=0x16DF40,entry=slot;
    if(slot%6==5 && value) { table=0x16DF5C; entry=value-1; }
    else if(slot==4 && value>1) { table=0x16DF78; entry=value-2; }
    else if(slot==22 && value>1) { table=0x16DF94; entry=value-2; }
    else if(slot==0 && value>1) { table=0x16DFCC; entry=value-2; }
    return menuPointer(table+4)-0x08000000+entry*32; // English
}
static void nativeSelection()
{
    if(!selectedOwned()) return;
    unsigned slot=sUiState[2]-1,value=inventoryByte(slot),v=inventoryVariant(slot);
    unsigned at=nativeItemOffset(slot);
    // Original green parentheses, including their flip attributes.
    menuPut(at-2,0x9053); menuPut(at+62,0x9853);
    menuPut(at+4,0x9453); menuPut(at+68,0x9C53);
    for(unsigned i=0;i<4;++i) menuPut(0x12B2+(i/2)*64+(i%2)*2,sIcons[slot][v][i]);
    unsigned name=nativeNameAddress(slot,value);
    menuRun(0x132C,name,8); menuRun(0x136C,name+16,8);
}
static void nativeDetails(unsigned step)
{
    switch(step) {
    case 0:
        // Original ITEM / DO headings and EQUIPMENT label, with English text.
        for(unsigned i=0;i<4;++i) menuPut(0x1246+i*2,0x81F8+i);
        menuPut(0x1586,0x8153); menuPut(0x1588,0x815E);
        menuRun(0x15AC,menuPointer(0x16BCA4)-0x08000000,8);
        menuRun(sUiState[19]>2?0x13EC:0x142C,menuPointer(sUiState[19]>2?0x16BD9C:0x16BD20)-0x08000000,8);
        break;
    case 1:
        menuIcon(0x15EC,0x16BAA0,inventoryByte(29),4);
        menuIcon(0x15F2,0x16BAC8,inventoryByte(30),3);
        menuIcon(0x15F8,0x16BAE8,inventoryByte(31),2);
        break;
    case 2:
        // Passive equipment, original sprites, at the bottom of the DO panel.
        menuIcon(0x1688,0x16BA68,inventoryByte(25),1);
        menuIcon(0x1690,0x16BA50,inventoryByte(24),2);
        menuIcon(0x1698,0x16BA78,inventoryByte(26),1);
        menuIcon(0x16A0,0x16BA88,inventoryByte(27),1);
        break;
    case 3:
        if(sUiState[20]<28 && !(sUiState[20]&1)) {
            unsigned mask=0x8000>>(sUiState[20]/2);
            menuIcon(0x16AC,0x16BB28,((inventoryByte(40)|(inventoryByte(41)<<8))&mask)!=0,1);
            menuIcon(0x16B2,0x16BB00,((inventoryByte(36)|(inventoryByte(37)<<8))&mask)!=0,1);
            menuIcon(0x16B8,0x16BB10,((inventoryByte(38)|(inventoryByte(39)<<8))&mask)!=0,1);
        } else {
            menuIcon(0x16AE,0x16BB78,inventoryByte(43),3);
            menuIcon(0x16B6,0x16BBE0,sUiState[21],5);
        }
        break;
    case 4:
        if(sUiState[19]>2) {
            static const u16 positions[]={0x1430,0x1434,0x14AE,0x14B2,0x14B6,0x1530,0x1534};
            for(unsigned i=0;i<7;++i) menuRun(positions[i],0x16BB98+((inventoryByte(58)>>i)&1)*4,2);
        } else {
            menuIcon(0x1472,0x16BB38,(inventoryByte(52)&1)!=0,1);
            menuIcon(0x14EE,0x16BB48,(inventoryByte(52)&2)!=0,1);
            menuIcon(0x14F6,0x16BB58,(inventoryByte(52)&4)!=0,1);
        }
        break;
    case 5:
        // Ability labels are stored as two rows of five original text tiles.
        for(unsigned i=0;i<6;++i) {
            unsigned mask=(menuHalf(0x16BE30+(i&~1))>>((i&1)*8))&255;
            if(!(inventoryByte(57)&mask)) continue;
            unsigned at=menuHalf(0x16BE36+i*2);
            unsigned data=menuPointer(0x16DFEC)-0x08000000+menuHalf(0x16BE42+i*2)*2;
            if(i<3) menuRun(at,data+10,5);
            else { menuRun(at,data,5); menuRun(at+64,data+10,5); }
        }
        break;
    case 6: nativeSelection(); break;
    }
}
static constexpr unsigned kNativeInventorySteps=32+20+24+7;
static void drawInventoryStep(unsigned step)
{
    if(step<24) {
        auto src=(volatile const u32*)ZELDA_INVENTORY_ADDRESS(0x06004000+step*512);
        auto dst=(volatile u32*)ZELDA_INVENTORY_ADDRESS(kZeldaBackBuffer+step*512);
        for(unsigned i=0;i<128;++i) dst[i]=src[i];
    } else if(step<32) {
        auto dst=(volatile u32*)ZELDA_INVENTORY_ADDRESS(kZeldaBackBuffer+0x3000+(step-24)*512);
        for(unsigned i=0;i<128;++i) dst[i]=sMenuFont[(step-24)*128+i];
    } else if(step<52) {
        unsigned row=step-32;
        if(row==0) {
            sNextBg1=1|(12<<8); sNextScroll=0;
            for(unsigned i=0;i<192;++i) sPalette[i]=((volatile const u16*)ZELDA_INVENTORY_ADDRESS(0x05000000))[i];
        }
        for(unsigned x=1;x<=30;++x) sWorld[(row+3)*32+x]=sMenuLayout[(row+9)*32+x];
    } else if(step<76) {
        unsigned slot=step-52,value=inventoryByte(slot),v=inventoryVariant(slot);
        if(value && value<128 && v<9)
            for(unsigned i=0;i<4;++i) menuPut(nativeItemOffset(slot)+(i/2)*64+(i%2)*2,sIcons[slot][v][i]);
    } else nativeDetails(step-76);
}
