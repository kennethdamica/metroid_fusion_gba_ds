#include <nds.h>
#include <cstring>
#include <libtwl/ipc/ipcFifo.h>
#include <libtwl/ipc/ipcSync.h>
#include <libtwl/ipc/ipcFifoSystem.h>
#include "../../../core/common/IpcChannels.h"
#include "../../../core/common/FsIpcCommand.h"
#include "ff.h"
#include "diskio.h"

static fs_ipc_cmd_t sCommand;
alignas(32) static u8 sBuffer[8192];

static DRESULT transfer(bool write, BYTE* buffer, DWORD sector, UINT count)
{
    while (count)
    {
        UINT n = count > 16 ? 16 : count;
        if (write) memcpy(sBuffer, buffer, n * 512);
        DC_FlushRange(sBuffer, n * 512);
        DC_InvalidateRange(sBuffer, n * 512);
        sCommand.cmd = write ? 6 : 5;
        sCommand.buffer = sBuffer;
        sCommand.sector = sector;
        sCommand.count = n;
        DC_FlushRange(&sCommand, sizeof(sCommand));
        ipc_setArm9SyncBits(ipc_getArm7SyncBits() + 1);
        ipc_sendWordDirect(((((u32)&sCommand) >> 2) << IPC_FIFO_MSG_CHANNEL_BITS) | IPC_CHANNEL_FS);
        while (ipc_getArm7SyncBits() != ((REG_IPCSYNC >> 8) & 15));
        DC_InvalidateRange(&sCommand, sizeof(sCommand));
        if (!sCommand.count) return RES_ERROR;
        if (!write) memcpy(buffer, sBuffer, n * 512);
        buffer += n * 512;
        sector += n;
        count -= n;
    }
    return RES_OK;
}
extern "C" DSTATUS disk_initialize(BYTE drive) { return drive == 0 ? 0 : STA_NOINIT; }
extern "C" DSTATUS disk_status(BYTE drive) { return disk_initialize(drive); }
extern "C" DRESULT disk_read(BYTE drive, BYTE* b, DWORD sector, UINT count)
{ return drive == 0 && count ? transfer(false, b, sector, count) : RES_PARERR; }
extern "C" DRESULT disk_write(BYTE drive, const BYTE* b, DWORD sector, UINT count)
{ return drive == 0 && count ? transfer(true, const_cast<BYTE*>(b), sector, count) : RES_PARERR; }
extern "C" DRESULT disk_ioctl(BYTE drive, BYTE cmd, void*)
{ return drive == 0 && cmd == CTRL_SYNC ? RES_OK : RES_PARERR; }
