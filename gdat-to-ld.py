import sys
from pathlib import Path
import struct
import gdat
import ld

if len(sys.argv) != 4:
    raise Exception('expected "python gdat-to-ld.py config.yaml path/to/input.gdat path/to/output.ld"')

# find GopherCAN config in sibling directory
config_name = sys.argv[1]
config_path = Path(f'../gophercan-lib/network_autogen/configs/{config_name}').resolve()

if not config_path.is_file():
    raise Exception(f'"{config_path}" does not exist')

ipath = Path(sys.argv[2])
opath = Path(sys.argv[3])

if not ipath.is_file():
    raise Exception(f'"{ipath}" does not exist')

if ipath.suffix != '.gdat':
    raise Exception('expected an input path to a .gdat file')

if opath.is_file():
    raise Exception(f'"{opath}" already exists')

if opath.suffix != '.ld':
    raise Exception('expected an output path to an .ld file')

print(f'loading "{config_name}"...')
parameters = gdat.load_parameters(config_path)
print(f'loaded {len(parameters)} parameters\n')

print(f'opening "{ipath}"...')
(sof, ext, data) = ipath.read_bytes().partition(b'.gdat:')
print(f'read {len(data)} bytes of data\n')

def encode(values):
    return [
        value.encode() if type(value) is str
        else value
        for value in values
    ]

# data = gdat.generate_data(parameters, 1000) # TEMP FAKE DATA
# channels = gdat.parse(data, parameters)
channels = {
    1: {
        'id': 1,
        'name': 'Channel1',
        'unit': 'C'
    }
}

for ch in channels.values():
    # order must match ld.formats['ch_meta']
    ch['meta'] = {
        'prev_ptr': 0,
        'next_ptr': 0,
        'data_ptr': 0,
        'sample_count': 1,
        '?': 0x00030004,
        'size': 2,
        'sample_rate': 1,
        'offset': 0,
        'scalar': 1,
        'divisor': 1,
        'shift': 1,
        'name': ch['name'],
        'short_name': 'CH',
        'unit': ch['unit'],
    }

    ch['data'] = [0]

event_offset = struct.calcsize(ld.formats['header'])
venue_offset = event_offset + struct.calcsize(ld.formats['event'])
vehicle_offset = venue_offset + struct.calcsize(ld.formats['venue'])
weather_offset = vehicle_offset + struct.calcsize(ld.formats['vehicle'])
meta_offset = weather_offset + struct.calcsize(ld.formats['weather'])
ch_meta_size = struct.calcsize(ld.formats['ch_meta'])
meta_size = len(channels) * ch_meta_size
data_offset = meta_offset + meta_size

# order must match ld.formats['header']
header_values = {
    'sof': 64,
    'meta_ptr': meta_offset,
    'data_ptr': data_offset,
    'event_ptr': event_offset,
    'device_serial': 21115,
    'device_type': 'ADL',
    'device_version': 560,
    'pro1': 128,
    'num_channels': len(channels),
    'num_channels2': len(channels),
    'pro2': 327700,
    'date': '29/09/2023',
    'time': '13:19:30',
    'driver': 'Driver',
    'vehicle_id': 'VehicleID',
    'engine_id': 'EngineID',
    'venue': 'Venue',
    'pro3': 45126145,
    'session': 'Session',
    'short_comment': 'Short Comment',
    'team': 'Team'
}

# order must match ld.formats['event']
event_values = {
    'event': 'Event',
    'session': 'Session',
    'long_comment': 'Long Comment',
    'venue_ptr': venue_offset,
    'weather_ptr': weather_offset
}

# order must match ld.formats['venue']
venue_values = {
    'venue': 'Venue',
    'venue_length': 100000,
    'vehicle_ptr': vehicle_offset,
    'venue_category': 'VenueCategory'
}

# order must match ld.formats['vehicle']
vehicle_values = {
    'vehicle_id': 'VehicleID',
    'vehicle_desc': 'VehicleDesc',
    'engine_id': 'EngineID',
    'vehicle_weight': 180,
    'fuel_tank': 750,
    'vehicle_type': 'VehicleType',
    'driver_type': 'DriverType',
    'diff_ratio': 24000,
    'gear1': 1110,
    'gear2': 2220,
    'gear3': 3330,
    'gear4': 4440,
    'gear5': 5550,
    'gear6': 6660,
    'gear7': 7770,
    'gear8': 8880,
    'gear9': 9990,
    'gear10': 10100,
    'vehicle_track': 45,
    'vehicle_wheelbase': 2000,
    'vehicle_comment': 'VehicleComment',
    'vehicle_number': 'VehicleNumber'
}

# order must match ld.formats['weather']
weather_values = {
    'sky': 'Sky',
    'air_temp': '200',
    'air_temp_unit': 'C',
    'track_temp': '100',
    'track_temp_unit': 'C',
    'pressure': '300',
    'pressure_unit': 'bar',
    'humidity': '30',
    'humidity_unit': '%',
    'wind_speed': '60',
    'wind_speed_unit': 'km/h',
    'wind_direction': 'WindDirection',
    'weather_comment': 'WeatherComment'
}

print('encoding...\n')
header = struct.pack(ld.formats['header'], *encode(header_values.values()))
event = struct.pack(ld.formats['event'], *encode(event_values.values()))
venue = struct.pack(ld.formats['venue'], *encode(venue_values.values()))
vehicle = struct.pack(ld.formats['vehicle'], *encode(vehicle_values.values()))
weather = struct.pack(ld.formats['weather'], *encode(weather_values.values()))

print(f'writing to "{opath}"...')
with open(opath, 'wb') as f:
    f.write(header)
    f.write(event)
    f.write(venue)
    f.write(vehicle)
    f.write(weather)

    data_size = 0
    for i, ch in enumerate(channels.values()):
        ch['meta']['data_ptr'] = data_offset + data_size
        data_size += ch['meta']['sample_count'] * ch['meta']['size']

        if i == 0: ch['meta']['prev_ptr'] = 0
        else: ch['meta']['prev_ptr'] = meta_offset + ch_meta_size * (i - 1)

        if i == len(channels) - 1: ch['meta']['next_ptr'] = 0
        else: ch['meta']['next_ptr'] = meta_offset + ch_meta_size * (i + 1)

        ch_meta = struct.pack(ld.formats['ch_meta'], *encode(ch['meta'].values()))
        f.write(ch_meta)

    for ch in channels.values():
        if ch['meta']['size'] == 2: fmt = f"<h"
        elif ch['meta']['size'] == 4: fmt = f"<i"

        data = b''
        for d in ch['data']:
            data += struct.pack(fmt, d)

        f.write(data)

print('done.')