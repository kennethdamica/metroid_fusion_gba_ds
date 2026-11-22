#include <nds.h>
#include <cstdio>
#include <cstring>
#include "ff.h"
#include "Package.h"
#include "Sha1.h"

static FATFS sFs;
static FIL sPackage;
static u8 sBuffer[8192];
static char sPaths[5][128];
static u32 sExtracted, sReused;
static const char* const sRoot = "fat:/_fusion/ca33f4348c2c05dd330d37b97e2c5a69531dfe87";
static const char* const sHashes[] = {
    "ca33f4348c2c05dd330d37b97e2c5a69531dfe87",
    "300c20df6731a33952ded8c436f7f186d25d3492",
    "5f36b2ea290645ee34d943220a14b54ee5ea5be5"
};
static const u32 sSizes[] = {8388608,16384,3};
static const char* const sNames[] = {"rom.gba","bios.bin","config.json"};
struct Range { u32 start, end; };
struct Manifest { char magic[8]; u32 version, abi; u8 hashes[3][20]; };

[[noreturn]] static void fail(u32 code, const char* message)
{
    iprintf("\nERROR %lu\n%s\n\nPower off and retry.\n", (unsigned long)code, message);
    // Terminal error: the core blob is no longer needed, so this reserved
    // diagnostic block may safely replace it. Never used for game state.
    memcpy((void*)0x0203E000, "PKGERROR", 8);
    *(volatile u32*)0x0203E008 = code;
    DC_FlushRange((void*)0x0203E000,32);
    while (true) asm volatile("nop");
}
static void require(FRESULT result, const char* message)
{ if (result != FR_OK) fail(10 + result, message); }
static void readExact(FIL* file, void* dest, u32 length)
{
    UINT n;
    require(f_read(file,dest,length,&n),"Cannot read SD data.");
    if (n!=length) fail(2,"Truncated package/data.");
}
static bool hashMatches(const u8 digest[20], const char* hex)
{
    static const char digits[]="0123456789abcdef";
    for (int i=0;i<20;++i)
        if (digits[digest[i]>>4]!=hex[2*i] || digits[digest[i]&15]!=hex[2*i+1]) return false;
    return true;
}
static bool verifyFile(const char* path, u32 size, const char* expected)
{
    FIL file;
    if (f_open(&file,path,FA_READ)!=FR_OK) return false;
    if (f_size(&file)!=size) { f_close(&file); return false; }
    Sha1 sha;
    bool ok=true;
    for (u32 done=0;done<size;)
    {
        UINT n, chunk=size-done;
        if (chunk>sizeof(sBuffer)) chunk=sizeof(sBuffer);
        if (f_read(&file,sBuffer,chunk,&n)!=FR_OK || n!=chunk) { ok=false;break; }
        sha.update(sBuffer,n); done+=n;
    }
    u8 digest[20]; sha.finish(digest);
    f_close(&file);
    return ok && hashMatches(digest,expected);
}
static void directory(const char* path)
{
    FRESULT result=f_mkdir(path);
    if (result!=FR_OK && result!=FR_EXIST) require(result,"Cannot create data folder.");
}
static void extract(const Range& range, unsigned index)
{
    const char* target=sPaths[index+1];
    char temporary[140]; snprintf(temporary,sizeof(temporary),"%s.part",target);
    if (verifyFile(target,sSizes[index],sHashes[index]))
    {
        ++sReused;
        f_unlink(temporary); // discard an interrupted older attempt, never a save
        iprintf("Verified %s\n",sNames[index]);
        return;
    }
    DWORD freeClusters; FATFS* fs;
    require(f_getfree("fat:",&freeClusters,&fs),"Cannot check SD free space.");
    if ((u64)freeClusters*fs->csize*512 < (u64)sSizes[index]+65536)
        fail(3,"SD full. Free at least 9 MiB.");
    FIL file;
    require(f_open(&file,temporary,FA_CREATE_ALWAYS|FA_WRITE),"Cannot create temp file.");
    require(f_lseek(&sPackage,range.start),"Bad payload offset.");
    Sha1 sha;
    iprintf("Extracting %s\n",sNames[index]);
    for (u32 done=0;done<sSizes[index];)
    {
        u32 chunk=sSizes[index]-done;
        if (chunk>sizeof(sBuffer)) chunk=sizeof(sBuffer);
        readExact(&sPackage,sBuffer,chunk);
        sha.update(sBuffer,chunk);
        UINT written;
        require(f_write(&file,sBuffer,chunk,&written),"SD write failed.");
        if (written!=chunk) fail(3,"SD full. Free at least 9 MiB.");
        done+=chunk;
        if ((done&0x7FFFF)==0) iprintf(".");
    }
    u8 digest[20]; sha.finish(digest);
    require(f_sync(&file),"Cannot sync extracted data.");
    require(f_close(&file),"Cannot close extracted data.");
    if (!hashMatches(digest,sHashes[index])) fail(4,"Payload hash mismatch.\nRebuild this NDS on your Mac.");
    // Verify the stored bytes, not only the incoming package stream.
    if (!verifyFile(temporary,sSizes[index],sHashes[index])) fail(5,"SD verification failed.");
    FRESULT removed=f_unlink(target);
    if (removed!=FR_OK && removed!=FR_NO_FILE) require(removed,"Cannot replace damaged data.");
    require(f_rename(temporary,target),"Cannot finish extraction.");
    ++sExtracted;
    iprintf(" OK\n");
}

void packagePrepare(const char* launchPath, bool storageReady)
{
    consoleDemoInit();
    iprintf("FUSION DS PACKAGE v1\n\n");
    if (!storageReady) fail(1,"DLDI storage unavailable.\nUse a compatible flashcart.");
    require(f_mount(&sFs,"fat:",1),"Cannot mount flashcart SD.");
    // Normal launchers provide argv[0]. A fixed root name supports launchers
    // that do not. Never scan for or select an unrelated package.
    const char* self=launchPath && !strncmp(launchPath,"fat:/",5) ? launchPath : "fat:/Fusion.nds";
    if (strlen(self)>=sizeof(sPaths[0])) fail(6,"NDS path too long (127 max).");
    strcpy(sPaths[0],self);
    if (f_open(&sPackage,self,FA_READ)!=FR_OK)
        fail(7,"Cannot open launched NDS.\nWithout launcher argv use\n/Fusion.nds on the SD root.");
    u32 size=f_size(&sPackage), fatOffset, fatSize;
    require(f_lseek(&sPackage,0x48),"Cannot read NDS header.");
    readExact(&sPackage,&fatOffset,4);readExact(&sPackage,&fatSize,4);
    if (fatSize!=32 || fatOffset<0x200 || fatOffset>size || size-fatOffset<32)
        fail(8,"Invalid package file table.");
    Range ranges[4];
    require(f_lseek(&sPackage,fatOffset),"Invalid file table offset.");
    readExact(&sPackage,ranges,sizeof(ranges));
    u32 previous=fatOffset+32;
    for (int i=0;i<4;++i)
    {
        if (ranges[i].start<previous || ranges[i].end<ranges[i].start || ranges[i].end>size ||
            ranges[i].end-ranges[i].start!=(i==0?sizeof(Manifest):sSizes[i-1]))
            fail(8,"Invalid package payload bounds.");
        previous=ranges[i].end;
    }
    Manifest manifest;
    require(f_lseek(&sPackage,ranges[0].start),"Invalid manifest offset.");
    readExact(&sPackage,&manifest,sizeof(manifest));
    if (memcmp(manifest.magic,"FUSPKG01",8) || manifest.version!=1 || manifest.abi!=1)
        fail(8,"Unsupported package version.");
    for (int i=0;i<3;++i)
        if (!hashMatches(manifest.hashes[i],sHashes[i])) fail(4,"Unsupported ROM/BIOS/config.");
    directory("fat:/_fusion");directory(sRoot);
    char dataPath[100];snprintf(dataPath,sizeof(dataPath),"%s/v1",sRoot);directory(dataPath);
    for (int i=0;i<3;++i) snprintf(sPaths[i+1],128,"%s/%s",dataPath,sNames[i]);
    snprintf(sPaths[4],128,"%s/rom.sav",sRoot);
    for (int i=0;i<3;++i) extract(ranges[i+1],i);
    require(f_close(&sPackage),"Cannot close NDS file.");
    require(f_mount(nullptr,"fat:",0),"Cannot release filesystem.");
    iprintf("\nStarting Fusion...\n");
}

char** packageHandoff()
{
    // Called only after the core blob has been copied to VRAM. These addresses
    // are below the core BSS at 0x02040000 and survive until its argv is read.
    auto args=(char**)0x0203F000;
    auto text=(char*)0x0203F020;
    for (int i=0;i<5;++i) { args[i]=text+i*128;strcpy(args[i],sPaths[i]); }
    args[5]=nullptr;
    memcpy((void*)0x0203E000,"PKGREADY",8);
    *(volatile u32*)0x0203E008=sExtracted;
    *(volatile u32*)0x0203E00C=sReused;
    DC_FlushRange((void*)0x0203E000,0x2000);
    return args;
}
