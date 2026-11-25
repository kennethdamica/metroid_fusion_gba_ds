#include "common.h"
#include "DisplayAudio.h"
#include "Peripherals/DmaTransfer.h"
extern "C" {
void dma_dmaSound(u32 channel);
[[gnu::section(".ewram.bss"), gnu::aligned(8)]] u32 gDisplayAudioStack[128];
[[gnu::section(".ewram.bss")]] volatile u32 gDisplayAudioDebug[4];
void displayServiceAudioImpl()
{
    ++gDisplayAudioDebug[0];
    // Respect exactly the active sound DMA channels used by emu_arm7Irq.
    if(dma_state.dmaFlags & DMA_FLAG_SOUND(1)) { dma_dmaSound(1); ++gDisplayAudioDebug[1]; }
    if(dma_state.dmaFlags & DMA_FLAG_SOUND(2)) { dma_dmaSound(2); ++gDisplayAudioDebug[2]; }
    if(gDisplayAudioStack[0]!=0xDEAD57AC) ++gDisplayAudioDebug[3];
}
}
void displayAudioInitialize() { gDisplayAudioStack[0]=0xDEAD57AC; }
