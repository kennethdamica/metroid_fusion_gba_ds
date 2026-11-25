#!/usr/bin/env python3
"""Compare FIFO/mixer telemetry from matching instrumented Zelda test windows."""
import argparse
import json
from pathlib import Path
import struct


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True,help='Control emulator run directory, containing RAM captures')
    parser.add_argument('--after',type=Path,required=True,help='Fixed instrumented emulator run directory')
    parser.add_argument('--before-shared-address',type=lambda s:int(s,0),required=True)
    parser.add_argument('--after-shared-address',type=lambda s:int(s,0),required=True)
    parser.add_argument('--start',type=int,required=True)
    parser.add_argument('--end',type=int,required=True)
    parser.add_argument('--require-no-misses',action='store_true')
    args=parser.parse_args()
    if not 0<args.start<args.end:parser.error('Choose increasing capture frames')
    result={}
    cores=[]
    for name,root,address in [('before',args.before,args.before_shared_address),('after',args.after,args.after_shared_address)]:
        if not 0x02040000<=address<=0x023FFF80:parser.error('Shared address must be in runtime main RAM')
        run=json.loads((root/'result.json').read_text())
        if run.get('status')!='passed':parser.error(f'{name} emulator run did not finish successfully')
        cores.append(run['core_sha256'])
        values=[struct.unpack_from('<6I',(root/f'ram-{frame:06d}.bin').read_bytes(),address-0x02000000+96) for frame in (args.start,args.end)]
        delta=[(b-a)&0xFFFFFFFF for a,b in zip(*values)]
        if any(not 0<delta[i]<0x80000000 for i in (2,3)) or any(delta[i]>delta[i+2] for i in (0,1)):
            parser.error(f'{name}: no valid active audio samples; check instrumentation, address and resets')
        result[name]=dict(misses=delta[:2],requests=delta[2:4],miss_rates=[delta[i]/delta[i+2] for i in (0,1)],
            max_mixer_backlog=values[-1][4],late_mixer_batches=delta[5])
    if cores[0]!=cores[1]:parser.error('Use the same patched emulator core for both runs')
    if any(abs(a-b)>max(a,b)*0.01 for a,b in zip(result['before']['requests'],result['after']['requests'])):
        parser.error('Sample counts differ by more than 1%; compare matching continuous sound scenes')
    passed=all(a<=b for a,b in zip(result['after']['miss_rates'],result['before']['miss_rates']))
    if args.require_no_misses:passed &= not any(result['after']['misses'])
    print(json.dumps(dict(start=args.start,end=args.end,status='passed' if passed else 'failed',**result),indent=2))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
