.section ".itcm", "ax"
#include "AsmMacros.inc"

arm_func displayServiceAudio
    ldr r0,= 0x04000214
    ldr r1, [r0]
    tst r1, #(1 << 16)
    bxeq lr
    // Acknowledge only ARM7's sound-refill IRQ. Leave guest IRQs pending.
    mov r1, #(1 << 16)
    str r1, [r0]
    // The display's 288-byte IRQ stack cannot also hold the DMA call chain.
    // No interrupts are enabled and this private stack cannot be re-entered.
    mov r12, sp
    ldr sp,= gDisplayAudioStack + 512
    push {r12,lr}
    bl displayServiceAudioImpl
    pop {r12,lr}
    mov sp, r12
    bx lr
.pool
.end
