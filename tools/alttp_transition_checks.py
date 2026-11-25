"""Repeated item/tab/floor changes and bounded redraw work in the real runtime."""
from pathlib import Path
import struct
from PIL import Image
from alttp_checks import native_highlight

# Item feedback must settle in 18 frames; full map/floor changes get 32.
TRANSITION_FRAMES=[21960,*[start+offset for start in (21980,22200) for offset in (18,38,58,92,132,172,212)],22430,22500,22520,22620,22650]
TRANSITION_CAPTURES=','.join(map(str,TRANSITION_FRAMES))


def verify_transitions(root,check,render_address=None):
    root=Path(root)
    def image(frame):return Image.open(root/f'bottom-{frame:06d}.png').convert('RGB')
    def label(frame):return image(frame).crop((192,96,208,104)).tobytes()
    for cycle in range(2):
        start=21980+cycle*220
        for offset,slot in ((38,13),(58,2)):
            frame=start+offset
            ram=(root/f'shared-wram-{frame:06d}.bin').read_bytes()
            # The opening-game tutorial may open the original inventory during
            # cycle 2. Live switching is required in cycle 1; later taps also
            # exercise the safety guard, and need not equip in a game menu.
            if cycle and ram[0x2BDC]==14:
                check(f'original_menu_retains_owned_item_{frame}',ram[0x2C7E] in (2,13))
                continue
            check(f'repeated_item_switch_{frame}',ram[0x2C7E]==slot and ram[0x2BDC] in (7,9))
            check(f'repeated_item_highlight_{frame}',native_highlight(root,frame,slot))
        check(f'repeated_floor_cycle_{cycle}',label(start+92)!=label(start+132) and label(start+92)==label(start+172)==label(start+212))
    check('held_touch_does_not_change_map',image(22520).tobytes()==image(21960).tobytes())
    check('rapid_tab_changes_finish_with_complete_map',image(22620).tobytes()==image(22650).tobytes()==image(21960).tobytes())
    report={}
    if render_address is not None:
        samples=[struct.unpack_from('<8I',f.read_bytes(),render_address-0x02000000) for f in sorted(root.glob('ram-*.bin'))]
        last=samples[-1]
        check('redraw_slices_at_most_40_scanlines',all(s[1]<=40 for s in samples))
        check('redraws_complete_after_rapid_changes',last[6]==0 and last[3]>20)
        check('interrupted_redraw_is_cancelled',last[4]>0)
        report=dict(slices=last[0],max_slice_scanlines=last[1],started=last[2],completed=last[3],cancelled=last[4],max_unit_scanlines=last[5])
    return report
