import sys
from pathlib import Path
import struct

if len(sys.argv) != 2:
    raise Exception('expected "python parse.py path/to/data.ld"')

ipath = Path(sys.argv[1])

if not ipath.is_file():
    raise Exception(f'"{ipath}" does not exist')

if ipath.suffix != '.ld':
    raise Exception('expected a path to a .ld file')

print(f'parsing "{ipath}" ...')

def parse(file, offset, format, keys):
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

# HEADER =======================================================================
# metadata shown in i2 at tools > details
# stored in .ld according to the following format
# offset wrt beginning of file

header_format = (
    '<'         # OFFSET (h)  LENGTH (h)  VALUE
    'Q'         # 0           8           start of file
    'I'         # 8           4           metadata pointer
    'I'         # C           4           data pointer
    '20x'       # 10          14          0
    'I'         # 24          4           event pointer
    '24x'       # 28          18          0
    'HHH'       # 40          6           ? ? ?
    'I'         # 46          4           device serial
    '8s'        # 4A          8           device type
    'H'         # 52          2           device version
    'HHH'       # 54          6           ? ? ?
    'I'         # 5A          4           ?
    '32s'       # 5E          20          date
    '32s'       # 7E          20          time
    '64s'       # 9E          40          driver
    '64s'       # DE          40          vehicle id
    '64s'       # 11E         40          engine id
    '64s'       # 15E         40          venue
    '64s'       # 19E         40          ?
    '1024s'     # 1DE         400         ?
    'I'         # 5DE         4           ?
    '2x'        # 5E2         2           0
    '64s'       # 5E4         40          session
    '64s'       # 624         40          short comment
    '8x'        # 664         8           0
    'I'         # 66C         4           trust lap
    '36x'       # 670         24          0
    '64s'       # 694         40          team
)

f = open(ipath, 'rb')

# assign keys to format tokens, empty strings indicate discarded values
header_keys = [
    '', 'meta_ptr', 'data_ptr', 'event_ptr', '', '', '', 'device_serial',
    'device_type', 'device_version', '', '', '', '', 'date', 'time', 'driver',
    'vehicle_id', 'engine_id', 'venue', '', '', '', 'session', 'short_comment',
    '', 'team'
]

header = parse(f, 0, header_format, header_keys)
print(header)

# EVENT ========================================================================
# event details
# offset wrt event pointer

event_format = (
    '<'         # OFFSET (h)  LENGTH (h)  VALUE
    '64s'       # 0           40          event
    '64s'       # 40          40          session
    '1024s'     # 80          400         long comment
    'I'         # 480         4           venue pointer
    'I'         # 484         4           weather pointer
)

event_keys = ['event', 'session', 'long_comment', 'venue_ptr', 'weather_ptr']

event = parse(f, header['event_ptr'], event_format, event_keys)
print(event)

# VENUE ========================================================================
# venue details
# offset wrt venue pointer

venue_format = (
    '<'         # OFFSET (h)  LENGTH (h)  VALUE
    '64s'       # 0           40          venue
    '2x'        # 40          2           0
    'I'         # 42          4           ?
    '1028x'     # 46          404         0
    'I'         # 44A         4           vehicle pointer
    '64s'       # 44E         40          venue category
)

venue_keys = ['venue', '', 'vehicle_ptr', 'venue_category']

venue = parse(f, event['venue_ptr'], venue_format, venue_keys)
print(venue)

# VEHICLE ======================================================================
# vehicle details
# offset wrt vehicle pointer

vehicle_format = (
    '<'         # OFFSET (h)  LENGTH (h)  VALUE
    '64s'       # 0           40          vehicle id
    '64s'       # 40          40          vehicle description
    '64s'       # 80          40          engine id
    'I'         # C0          4           vehicle weight
    '32s'       # C4          20          vehicle type
    '32s'       # E4          20          driver type
    'H'         # 104         2           diff ratio
    'H'         # 106         2           gear 1
    'H'         # 108         2           gear 2
    'H'         # 10A         2           gear 3
    'H'         # 10C         2           gear 4
    'H'         # 10E         2           gear 5
    'H'         # 110         2           gear 6
    'H'         # 112         2           gear 7
    'H'         # 114         2           gear 8
    'H'         # 116         2           gear 9
    'H'         # 118         2           gear 10
    'H'         # 11A         2           vehicle track
    'I'         # 11C         4           vehicle wheelbase
    '1028s'     # 120         404         vehicle comment
    '64s'       # 524         400         vehicle number
)

vehicle_keys = []

vehicle = parse(f, venue['vehicle_ptr'], vehicle_format, vehicle_keys)
print(vehicle)

# WEATHER ======================================================================
# weather details
# offset wrt weather pointer

weather_format = (
    '<'         # OFFSET (h)  LENGTH (h)  VALUE
    '64s'       # 0           40          sky
    '16s'       # 40          10          air temp
    '8s'        # 50          8           air temp unit
    '16s'       # 58          10          track temp
    '8s'        # 68          8           track temp unit
    '16s'       # 70          10          pressure
    '8s'        # 80          8           pressure unit
    '16s'       # 88          10          humidity
    '8s'        # 98          8           humidity unit
    '16s'       # A0          10          wind speed
    '8s'        # B0          8           wind speed unit
    '64s'       # B8          40          wind direction
    '1024s'     # D8          400         weather comment
)

weather_keys = []

weather = parse(f, event['weather_ptr'], weather_format, weather_keys)
print(weather)

f.close()