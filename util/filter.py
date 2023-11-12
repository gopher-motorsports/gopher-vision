import sys
from pathlib import Path
import struct
import time

# python filter.py [INPUT].gdat [OUTPUT].gdat [IDs]
# e.g. python filter.py data.gdat enginerpm.gdat 1
# e.g. python filter.py data.gdat temps.gdat 2,4,7
# copies packets with an ID in [IDs] from [INPUT] to [OUTPUT]
# IDs are separated by *only* a comma

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

ipath = Path(sys.argv[1])
opath = Path(sys.argv[2])
filter_ids = [int(id) for id in sys.argv[3].split(',')]

if ipath.suffix != '.gdat':
    raise Exception('ERROR: input must be a .gdat file')

if opath.suffix != '.gdat':
    raise Exception('ERROR: output must be a .gdat file')

if len(filter_ids) == 0:
    raise Exception('ERROR: please specify IDs to filter')

start = time.time()

print(f'loading {ipath} ...')
(sof, ext, data) = ipath.read_bytes().partition(b'.gdat:')
print(f'read {len(data)} bytes of data')

if opath.is_file():
    opath.unlink()

print('filtering data...')

# copy metadata
ofile = open(opath, 'wb')
ofile.write(bytes(sof + ext))

# filter packets
packets = data.split(START.to_bytes())
n_errors = 0
n_copied = 0
for packet in packets:
    # unescape packet
    pkt = bytearray()
    esc = False
    for b in packet:
        if b == ESC:
            esc = True
        elif esc:
            pkt.append(b ^ ESC_XOR)
            esc = False
        else:
            pkt.append(b)
    # unpack components
    try:
        ts, id = struct.unpack('>IH', pkt[0:6])
    except:
        n_errors += 1
        continue
    # validate checksum
    sum = START
    for b in pkt[:-1]: sum += b
    if sum.to_bytes(2)[-1] != pkt[-1]:
        n_errors += 1
        continue
    # check if id is whitelisted
    if id in filter_ids:
        # copy to output file
        ofile.write(START.to_bytes() + packet)
        n_copied += 1

print(f'{len(packets)} packets, {n_errors} errors, {n_copied} copied')

elapsed = round(time.time() - start, 2)
print(f'finished in ({elapsed}s)')