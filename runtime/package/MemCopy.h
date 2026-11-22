#pragma once
#include <string.h>
// Bootstrap filesystem buffers are in ordinary RAM, not the VM's VRAM banks.
static inline void mem_copy32(const void* src, void* dst, u32 n) { memcpy(dst,src,n); }
static inline void mem_copy16(const void* src, void* dst, u32 n) { memcpy(dst,src,n); }
