"""Compare consecutive stable UI frames; isolated screenshots miss flicker."""
from pathlib import Path
import struct
from PIL import Image

WINDOWS={'inventory':range(20140,20173),'world_map':range(20800,20833),
         'dungeon_map':range(21766,21780)}
VIDEO_CAPTURES=','.join(str(frame) for frames in WINDOWS.values() for frame in frames)


def verify_video(root,check,debug_address=None):
    root=Path(root)
    report={}
    for name,frames in WINDOWS.items():
        images=[Image.open(root/f'bottom-{frame:06d}.png').convert('RGB').tobytes() for frame in frames]
        counts={data:images.count(data) for data in set(images)}
        reference=max(counts,key=counts.get)
        changed=[frame for frame,data in zip(frames,images) if data!=reference]
        check(f'{name}_stable_on_every_frame',not changed)
        report[name]=dict(frames=len(images),distinct_images=len(counts),changed_frames=changed)
    if debug_address is not None:
        samples=[]
        offset=debug_address-0x02000000
        for frames in WINDOWS.values():
            for frame in frames:
                memory=(root/f'ram-{frame:06d}.bin').read_bytes()
                samples.append(struct.unpack_from('<8I',memory,offset))
        check('bottom_publication_stays_in_vblank',all(s[4]==0 and 192<=s[2]<=s[3]<263 and s[5]<64 for s in samples))
        check('bottom_frames_continue_publishing',samples[-1][0]>samples[0][0]>0)
        report['publication']=dict(commits=samples[-1][0],deferred=samples[-1][1],
            overruns=samples[-1][4],max_scanlines=samples[-1][5],last_start=samples[-1][2],last_end=samples[-1][3])
    return report
