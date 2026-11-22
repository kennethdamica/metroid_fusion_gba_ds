.syntax unified
.cpu arm7tdmi
.arm
.section .text.start, "ax"
.global _start
_start:
    b start
    .space 188
start:
    ldr sp, =0x03007e00
    bl main
1:  b 1b
