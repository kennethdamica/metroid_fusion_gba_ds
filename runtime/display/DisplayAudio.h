#pragma once
// Called only from the display IRQ. Services sound FIFO requests without
// re-entering the VM IRQ handler or borrowing hardware DMA channels.
extern "C" void displayServiceAudio();
void displayAudioInitialize();
