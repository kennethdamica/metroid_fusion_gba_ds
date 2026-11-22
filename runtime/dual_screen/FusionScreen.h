#pragma once
#include "GbaHeader.h"

// Header gate only; the host packaging/test tools verify the complete US ROM.
bool fusionScreenSupports(const GbaHeader& header);
void fusionScreenInitialize();
extern "C" void fusionScreenVBlank();
extern "C" u32 gFusionScreenActive;
