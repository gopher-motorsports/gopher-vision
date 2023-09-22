import sys
from pathlib import Path
import struct
from ld import keys, formats

if len(sys.argv) != 2:
    raise Exception('expected "python parseld.py path/to/data.ld"')

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
        value.decode().rstrip('\0') if type(value) is bytes
        else value
        for value in struct.unpack(format, data)
    ]
    # combine keys & values into a dictionary, ignoring empty keys
    return {k:v for k,v in zip(keys, values) if k != ''}

print(f'parsing "{ipath}" ...\n')
f = open(ipath, 'rb')

print('HEADER ====================')
header = parse(f, 0, keys['header'], formats['header'])
print(header, '\n')

print('EVENT ====================')
event = parse(f, header['event_ptr'], keys['event'], formats['event'])
print(event, '\n')

print('VENUE ====================')
venue = parse(f, event['venue_ptr'], keys['venue'], formats['venue'])
print(venue, '\n')

print('VEHICLE ====================')
vehicle = parse(f, venue['vehicle_ptr'], keys['vehicle'], formats['vehicle'])
print(vehicle, '\n')

print('WEATHER ====================')
weather = parse(f, event['weather_ptr'], keys['weather'], formats['weather'])
print(weather, '\n')

print('CHANNELS ====================')
next_ch = header['meta_ptr']
num_ch = 0

while next_ch:
    ch = parse(f, next_ch, keys['ch_meta'], formats['ch_meta'])
    next_ch = ch['next_ptr']
    num_ch += 1
    print(ch)

if num_ch == header['num_channels']:
    print(f'found {num_ch} channels\n')
else:
    print('WARNING: num_channels does not match number of channels found\n')

f.close()
print('done.')