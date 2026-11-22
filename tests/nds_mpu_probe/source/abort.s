.syntax unified
.arm
.text
.global run_abort_cases
.type run_abort_cases, %function
run_abort_cases:
    push {r4-r11,lr}
    mov r10, r0
    mrc p15, 0, r4, c1, c0, 0
    mrc p15, 0, r5, c6, c7, 0
    mrc p15, 0, r6, c5, c0, 2
    mov r11, #0x01000000
    ldr r7, [r11, #0x10]
    ldr r8, [r11, #0x14]
    ldr r0, =0xE51FF004  // low abort vector: ldr pc,[pc,#-4]
    str r0, [r11, #0x10]
    ldr r0, =abort_handler
    str r0, [r11, #0x14]
    ldr r0, =0x02080017  // MPU region 7: 4 KiB, no data access
    mcr p15, 0, r0, c6, c7, 0
    bic r0, r6, #0xF0000000
    mcr p15, 0, r0, c5, c0, 2
    bic r0, r4, #0x2000
    orr r0, r0, #1
    mcr p15, 0, r0, c1, c0, 0
    mov r9, #0
    ldr r1, =0x02080000
    ldr r0, =0x11223344
    ldr r0, [r1]        // destination must remain unchanged
    stmia r10!, {r0,r1}
    ldr r0, =0x11223344
    ldr r0, [r1], #4    // destination AND base must remain unchanged
    stmia r10!, {r0,r1}
    ldr r1, =0x02080000
    ldr r0, =0x11223344
    str r0, [r1], #4    // base must remain unchanged
    stmia r10!, {r0,r1}
    ldr r1, =0x02080004
    stmdb r1!, {r0}     // pre-decrement must be restored on abort
    stmia r10!, {r0,r1}
    str r9, [r10]
    mcr p15, 0, r4, c1, c0, 0
    mcr p15, 0, r5, c6, c7, 0
    mcr p15, 0, r6, c5, c0, 2
    str r7, [r11, #0x10]
    str r8, [r11, #0x14]
    pop {r4-r11,pc}
abort_handler:
    add r9, r9, #1
    subs pc, lr, #4     // skip the faulting ARM instruction
.size run_abort_cases, .-run_abort_cases
