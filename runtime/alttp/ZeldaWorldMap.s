.syntax unified
.arm
.section ".zelda.hot", "ax"
.align 2
.global zeldaWorldMapHblank
.type zeldaWorldMapHblank, %function
// AZLE r0's perspective map HBlank handler (08068B7C) writes BG2X/Y/PA
// through several trapped guest I/O accesses per line. On DS those accesses
// can run into the next line, repeatedly restarting the affine background.
// Perform its integer transform directly in the host IRQ, before dispatching
// any guest work. All other Zelda effects retain the ordinary guest handler.
zeldaWorldMapHblank:
    ldr lr,= gFusionScreenActive
    ldr lr, [lr]
    cmp lr, #0
    beq 2f
    ldr lr,= 0x03002BB2 // gRam + 982: HBlank effect
    ldrb lr, [lr]
    cmp lr, #3
    bne 2f
    // Consume only this effect's guest HBlank IRQ; preserve sound and DMA.
    bic r4, r4, #2
    mov r13, #0x04000000
    ldrh lr, [r13, #6]
    cmp lr, #160
    bhs 2f
    ldr sp,= dtcmIrqStackEnd
    push {r0-r3,r12}
    mov r0, lr
    ldr r1,= 0x02001400 // guest's active scanline scale table
    add r1, r1, r0, lsl #1
    ldrh r1, [r1]
    ldr r2,= 0x03002B80 // signed camera X (gRam + 950)
    ldrsh r3, [r2]
    mov r3, r3, lsl #8
    rsb r12, r1, r1, lsl #4
    sub r3, r3, r12, lsl #3 // X * 256 - scale * 120
    mov r12, #0x04000000
    str r3, [r12, #0x28]
    ldrsh r3, [r2, #6] // camera Y (gRam + 956)
    add r2, r1, r1, lsr #1
    mul r2, r0, r2
    add r3, r2, r3, lsl #8
    str r3, [r12, #0x2C]
    strh r1, [r12, #0x20]
    ldr r1,= gZeldaMapHblankDebug
    ldr r2, [r1]
    add r2, r2, #1
    str r2, [r1]
    ldrh r2, [r12, #6]
    cmp r2, r0
    ldrne r2, [r1, #4]
    addne r2, r2, #1
    strne r2, [r1, #4]
    pop {r0-r3,r12}
2:  ldr pc,= zeldaWorldMapHblankReturn
.ltorg
.size zeldaWorldMapHblank, .-zeldaWorldMapHblank
