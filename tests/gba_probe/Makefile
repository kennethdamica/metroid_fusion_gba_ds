ARM := $(DEVKITARM)/bin/arm-none-eabi-
all: probe.gba
probe.elf: start.s main.c link.ld
	$(ARM)gcc -mcpu=arm7tdmi -marm -O2 -ffreestanding -fno-builtin -nostdlib -Wl,-T,link.ld -Wl,-Map,probe.map start.s main.c -o $@
probe.gba: probe.elf
	$(ARM)objcopy -O binary $< $@
	$(DEVKITPRO)/tools/bin/gbafix $@ -tGBAPROBE -cTST0 -m00
clean:
	rm -f probe.elf probe.gba probe.map
