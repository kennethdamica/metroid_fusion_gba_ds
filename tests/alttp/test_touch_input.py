"""Touch scripts use bottom-screen pixels and must retain joypad state."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from touch_input import pointer_coordinates


class TouchInputTests(unittest.TestCase):
    def test_pixel_centers_round_trip_through_stacked_layout(self):
        for x, y in ((0, 0), (255, 191), (128, 96), (68, 48), (28, 112)):
            nx, ny = pointer_coordinates(x, y)
            self.assertEqual(int((nx/32767 + 1)*128), x)
            self.assertEqual(int((ny/32767 + 1)*192)-192, y)

    def test_rejects_invalid_pixels(self):
        for value in ((-1, 0), (256, 0), (0, 192), (0, -1), (1.0, 1), (True, 1)):
            with self.assertRaises(ValueError):
                pointer_coordinates(*value)

    def test_driver_exposes_touch_and_movement_together(self):
        from libretro import JoypadState, Pointer, PointerState, InputDevice
        from libretro.drivers.input.iterable import PortState, IterableInputDriver
        x, y = pointer_coordinates(68, 48)
        driver = IterableInputDriver([PortState(joypad=JoypadState(right=True),
                                                pointer=PointerState((Pointer(x, y, True),)))])
        driver.poll()
        self.assertEqual(driver.state(0, InputDevice.JOYPAD, 0, 7), 1)
        self.assertEqual(driver.state(0, InputDevice.POINTER, 0, 0), x)
        self.assertEqual(driver.state(0, InputDevice.POINTER, 0, 1), y)
        self.assertEqual(driver.state(0, InputDevice.POINTER, 0, 2), 1)
        driver.poll()
        self.assertEqual(driver.state(0, InputDevice.POINTER, 0, 2), 0)
