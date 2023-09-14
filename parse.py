import sys
from pathlib import Path
import struct

if len(sys.argv) != 2:
    raise Exception('expected "python parse.py path/to/input.ld"')

ipath = Path(sys.argv[1])

if not ipath.is_file():
    raise Exception(f'"{ipath}" does not exist')

if ipath.suffix != '.ld':
    raise Exception('expected an input path to a .ld file')

print(f'parsing "{ipath}" ...')

metadata = {
    # HEADER
    'date': '',
    'time': '',
    'driver': '',
    'vehicle_id': '',
    'venue': '',
    'short_comment': '',
    # EVENT
    'event': '',
    'session': '',
    'long_comment': ''
}

# HEADER =======================================================================
# metadata shown in i2 at tools > details
# stored in .ld according to the following format
# offset wrt beginning of file
# OFFSET (h)    LENGTH (h)    VALUE
# C             4             data pointer
# 8             4             metadata pointer
# 24            4             event pointer
# 5E            A             date
# 7E            8             time
# 9E            40            driver
# DE            40            vehicle id
# 15E           40            venue
# 624           40            short comment

# format string to unpack data according to the table above
header_fmt = (
    '<' # little endian
    '8x' # ?
    'I' # metadata pointer
    'I' # data pointer
    '20x' # ?
    'I' # event pointer
    '54x' # ?
    '10s' # date
    '22x' # ?
    '8s' # time
    '24x' # ?
    '64s' # driver
    '64s' # vehicle id
    '64x' # ?
    '64s' # venue
    '1158x' # ?
    '64s' # short comment
)

f = open(ipath, 'rb')
header = f.read(struct.calcsize(header_fmt))
header_val = struct.unpack(header_fmt, header)

# offsets of other data regions
(meta_ptr, data_ptr, event_ptr, _, _, _, _, _, _) = header_val

metadata['date'] = header_val[3].decode('ascii')
metadata['time'] = header_val[4].decode('ascii')
metadata['driver'] = header_val[5].decode('ascii').rstrip('\0')
metadata['vehicle_id'] = header_val[6].decode('ascii').rstrip('\0')
metadata['venue'] = header_val[7].decode('ascii').rstrip('\0')
metadata['short_comment'] = header_val[8].decode('ascii').rstrip('\0')

# EVENT ========================================================================
# event info
# offset wrt event pointer
# OFFSET (h)    LENGTH (h)    VALUE
# 0             40            event
# 40            40            session
# 80            400           long comment
# 480           2             venue pointer

event_fmt = (
    '<'
    '64s' # event
    '64s' # session
    '1024s' # long comment
    'H' # venue pointer
)

f.seek(event_ptr)
event = f.read(struct.calcsize(event_fmt))
event_val = struct.unpack(event_fmt, event)

(_, _, _, venue_ptr) = event_val

metadata['event'] = event_val[0].decode('ascii').rstrip('\0')
metadata['session'] = event_val[1].decode('ascii').rstrip('\0')
metadata['long_comment'] = event_val[2].decode('ascii').rstrip('\0')

# VENUE ========================================================================
# venue info
# offset wrt venue pointer
# OFFSET (h)    LENGTH (h)    VALUE
# 0             40            venue
# 44A           2             vehicle pointer

venue_fmt = (
    '<'
    '64s' # venue
    '1034x' # ?
    'H' # vehicle pointer
)

f.seek(venue_ptr)
venue = f.read(struct.calcsize(venue_fmt))
venue_val = struct.unpack(venue_fmt, venue)

(_, vehicle_ptr) = venue_val

# VEHICLE ======================================================================
# vehicle info
# offset wrt vehicle pointer
# OFFSET (h)    LENGTH (h)    VALUE
# 0             40            vehicle id

vehicle_fmt = (
    '<'
    '64s' # vehicle id
)

f.seek(vehicle_ptr)
vehicle = f.read(struct.calcsize(vehicle_fmt))
vehicle_val = struct.unpack(vehicle_fmt, vehicle)

print(metadata)
f.close()