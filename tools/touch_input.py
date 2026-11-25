"""DS bottom-screen pixels to libretro pointer coordinates, top-bottom/no gap."""


def pointer_coordinates(x, y):
    if type(x) is not int or type(y) is not int or not (0 <= x < 256 and 0 <= y < 192):
        raise ValueError('Touch must be integer bottom-screen pixels: x=0..255, y=0..191')
    # Aim at pixel centers; the core maps normalized coordinates over both screens.
    return round((x + 0.5) * 65534 / 256 - 32767), round((y + 192.5) * 65534 / 384 - 32767)
