ENTRY(_start)
SECTIONS {
  . = 0x08000000;
  .text : { *(.text.start) *(.text*) *(.rodata*) }
  /DISCARD/ : { *(.comment) *(.ARM.attributes) }
}
