#pragma once
#include <stdint.h>
#include <stddef.h>
class Sha1 {
    uint32_t h[5];
    uint64_t count;
    uint8_t block[64];
    void transform();
public:
    Sha1();
    void update(const void* data, size_t size);
    void finish(uint8_t digest[20]);
};
