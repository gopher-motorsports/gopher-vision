import sys
from pathlib import Path
import struct
from ld import keys, formats

if len(sys.argv) != 2:
    raise Exception('expected "python parse-ld.py path/to/data.ld"')

ipath = Path(sys.argv[1])

if not ipath.is_file():
    raise Exception(f'"{ipath}" does not exist')

if ipath.suffix != '.ld':
    raise Exception('expected a path to an .ld file')

# unpack a section of an .ld file
def parse(file, offset, keys, format):
    file.seek(offset)
    data = f.read(struct.calcsize(format))
    # unpack bytes according to format, decoding & trimming strings
    values = [
        value.decode().strip().strip('\0') if type(value) is bytes
        else value
        for value in struct.unpack(format, data)
    ]
    # combine keys & values into a dictionary, ignoring empty keys
    return {k:v for k,v in zip(keys, values) if k != ''}

print(f'parsing "{ipath}" ...\n')
f = open(ipath, 'rb')

print('HEADER ====================')
header = parse(f, 0, keys['header'], formats['header'])
print(header)

print('\nEVENT ====================')
if header['event_ptr'] > 0:
    event = parse(f, header['event_ptr'], keys['event'], formats['event'])
    print(event)
else:
    print('event_ptr missing')

print('\nVENUE ====================')
if event['venue_ptr'] > 0:
    venue = parse(f, event['venue_ptr'], keys['venue'], formats['venue'])
    print(venue)
else:
    print('venue_ptr missing')

print('\nVEHICLE ====================')
if venue['vehicle_ptr'] > 0:
    vehicle = parse(f, venue['vehicle_ptr'], keys['vehicle'], formats['vehicle'])
    print(vehicle)
else:
    print('vehicle_ptr missing')

print('\nWEATHER ====================')
if event['weather_ptr'] > 0:
    weather = parse(f, event['weather_ptr'], keys['weather'], formats['weather'])
    print(weather)
else:
    print('weather_ptr missing')

print('\nCHANNELS ====================')
if header['meta_ptr'] > 0:
    ch_info = {}
    ch_data = {}
    num_ch = 0
    next_ch = header['meta_ptr']

    while next_ch:
        # parse channel metadata
        ch = parse(f, next_ch, keys['ch_meta'], formats['ch_meta'])
        ch['meta_ptr'] = next_ch
        num_ch += 1

        if ch['name'] in ch_info:
            print(f"found duplicate channel name: \"{ch['name']}\"")
        else:
            ch_info[ch['name']] = ch

        if ch['size'] == 2:
            fmt = f"<{ch['sample_count']}h"
        elif ch['size'] == 4:
            fmt = f"<{ch['sample_count']}i"
        else:
            print(f"\"{ch['name']}\" has unknown data size ({ch['size']})\n")

        # jump to, unpack channel data
        f.seek(ch['data_ptr'])
        data = f.read(struct.calcsize(fmt))
        ch_data[ch['name']] = [
            (x / ch['divisor'] * pow(10, ch['shift'] * -1) + ch['offset']) * ch['scalar']
            for x in struct.unpack(fmt, data)
        ]

        print(ch)
        next_ch = ch['next_ptr']

    if num_ch == header['num_channels']:
        print(f'found {num_ch} channels\n')
    else:
        print(f"WARNING: num_channels ({header['num_channels']})",
            f"does not match number of channels found ({num_ch})\n")
else:
    print('meta_ptr missing')

f.close()
print('done.')