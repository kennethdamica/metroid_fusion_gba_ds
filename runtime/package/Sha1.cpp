#include "Sha1.h"
#include <cstring>
static uint32_t rotate(uint32_t v, int n) { return (v << n) | (v >> (32-n)); }
Sha1::Sha1() : h{0x67452301,0xEFCDAB89,0x98BADCFE,0x10325476,0xC3D2E1F0}, count(0) {}
void Sha1::transform()
{
    uint32_t w[80];
    for (int i=0;i<16;++i) w[i]=(uint32_t(block[4*i])<<24)|(uint32_t(block[4*i+1])<<16)|(uint32_t(block[4*i+2])<<8)|block[4*i+3];
    for (int i=16;i<80;++i) w[i]=rotate(w[i-3]^w[i-8]^w[i-14]^w[i-16],1);
    uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4];
    for (int i=0;i<80;++i) {
        uint32_t f,k;
        if (i<20) { f=(b&c)|(~b&d);k=0x5A827999; }
        else if (i<40) { f=b^c^d;k=0x6ED9EBA1; }
        else if (i<60) { f=(b&c)|(b&d)|(c&d);k=0x8F1BBCDC; }
        else { f=b^c^d;k=0xCA62C1D6; }
        uint32_t t=rotate(a,5)+f+e+k+w[i]; e=d;d=c;c=rotate(b,30);b=a;a=t;
    }
    h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;
}
void Sha1::update(const void* input, size_t size)
{
    const auto* p=static_cast<const uint8_t*>(input);
    while (size) {
        size_t used=count&63, n=64-used;
        if (n>size) n=size;
        memcpy(block+used,p,n); count+=n;p+=n;size-=n;
        if (!(count&63)) transform();
    }
}
void Sha1::finish(uint8_t digest[20])
{
    uint64_t bits=count*8;
    uint8_t pad=0x80,zero=0;
    update(&pad,1);
    while ((count&63)!=56) update(&zero,1);
    uint8_t length[8];
    for (int i=0;i<8;++i) length[7-i]=bits>>(i*8);
    update(length,8);
    for (int i=0;i<20;++i) digest[i]=h[i/4]>>(24-(i&3)*8);
}
