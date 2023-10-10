# file structure based on logs from the MoTeC EDL3 v5.6

# .ld files are split into several sections linked by file pointers
# layouts contain a series of (key, format) pairs for each value in a section
# values with empty keys are unused/unknown
# key lists and format strings are derived from the corresponding layout

# KEY: identifies the value
# FORMAT: mapping between byte string and Python value
# OFFSET (hex): file offset of the value
# LENGTH (hex): length of the value in bytes

import struct
import time
import numpy as np
import matplotlib.pyplot as plt

layouts = {}
keys = {}
formats = {}

# HEADER =======================================================================
layouts['header'] = (
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('sof',             'Q'),      # 0         8
    ('meta_ptr',        'I'),      # 8         4
    ('data_ptr',        'I'),      # C         4
    ('',                '20x'),    # 10        14
    ('event_ptr',       'I'),      # 24        4
    ('',                '28x'),    # 28        1C
    ('magic1',          'H'),      # 44        2         15
    ('device_serial',   'I'),      # 46        4
    ('device_type',     '8s'),     # 4A        8
    ('device_version',  'H'),      # 52        2         scale: 100
    ('magic2',          'H'),      # 54        2         128
    ('num_channels',    'H'),      # 56        2
    ('num_channels2',   'H'),      # 58        2
    ('magic3',          'I'),      # 5A        4         66036
    ('date',            '32s'),    # 5E        20
    ('time',            '32s'),    # 7E        20
    ('driver',          '64s'),    # 9E        40
    ('vehicle_id',      '64s'),    # DE        40
    ('engine_id',       '64s'),    # 11E       40
    ('venue',           '64s'),    # 15E       40
    ('',                '1088x'),  # 19E       440
    ('magic4',          'I'),      # 5DE       4         45126145
    ('',                '2x'),     # 5E2       2
    ('session',         '64s'),    # 5E4       40
    ('short_comment',   '64s'),    # 624       40
    ('',                '48x'),    # 664       30
    ('team',            '64s'),    # 694       40
)

(k, f) = zip(*layouts['header'])
keys['header'] = tuple(filter(lambda key: key != '', k))
formats['header'] = ''.join(f)

# EVENT ========================================================================
layouts['event'] = (
###  KEY              FORMAT     OFFSET (h)  LENGTH (h)
    ('',              '<'),      #
    ('event',         '64s'),    # 6D4       40
    ('session',       '64s'),    # 714       40
    ('long_comment',  '1024s'),  # 754       400
    ('venue_ptr',     'I'),      # B54       4
    ('weather_ptr',   'I'),      # B58       4
)

(k, f) = zip(*layouts['event'])
keys['event'] = tuple(filter(lambda key: key != '', k))
formats['event'] = ''.join(f)

# VENUE ========================================================================
layouts['venue'] = (
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('venue',           '64s'),    # B5C       40
    ('',                '2x'),     # B9C       2
    ('venue_length',    'I'),      # B9E       4         unit: mm
    ('',                '1028x'),  # BA2       404
    ('vehicle_ptr',     'I'),      # FA6       4
    ('venue_category',  '1024s'),  # FAA       400    
    ('',                '976x')    # 13AA      3D0
)

(k, f) = zip(*layouts['venue'])
keys['venue'] = tuple(filter(lambda key: key != '', k))
formats['venue'] = ''.join(f)

# VEHICLE ======================================================================
layouts['vehicle'] = (
###  KEY                   FORMAT     OFFSET (h)  LENGTH (h)
    ('',                   '<'),      #
    ('vehicle_id',         '64s'),    # 177A      40
    ('vehicle_desc',       '64s'),    # 17BA      40
    ('engine_id',          '64s'),    # 17FA      40
    ('vehicle_weight',     'H'),      # 183A      2         unit: kg
    ('fuel_tank',          'H'),      # 183C      2         unit: deciliter
    ('vehicle_type',       '32s'),    # 183E      20
    ('driver_type',        '32s'),    # 185E      20
    ('diff_ratio',         'H'),      # 187E      2         scale: 1000
    ('gear1',              'H'),      # 1880      2         scale: 1000
    ('gear2',              'H'),      # 1882      2         scale: 1000
    ('gear3',              'H'),      # 1884      2         scale: 1000
    ('gear4',              'H'),      # 1886      2         scale: 1000
    ('gear5',              'H'),      # 1888      2         scale: 1000
    ('gear6',              'H'),      # 188A      2         scale: 1000
    ('gear7',              'H'),      # 188C      2         scale: 1000
    ('gear8',              'H'),      # 188E      2         scale: 1000
    ('gear9',              'H'),      # 1890      2         scale: 1000
    ('gear10',             'H'),      # 1892      2         scale: 1000
    ('vehicle_track',      'H'),      # 1894      2         unit: mm
    ('vehicle_wheelbase',  'I'),      # 1896      4         unit: mm
    ('vehicle_comment',    '1028s'),  # 189A      404
    ('vehicle_number',     '64s'),    # 1C9E      40
)

(k, f) = zip(*layouts['vehicle'])
keys['vehicle'] = tuple(filter(lambda key: key != '', k))
formats['vehicle'] = ''.join(f)

# WEATHER ======================================================================
layouts['weather'] = (
###  KEY                 FORMAT     OFFSET (h)  LENGTH (h)
    ('',                 '<'),      #
    ('sky',              '64s'),    # 1CDE       40
    ('air_temp',         '16s'),    # 1D1E       10
    ('air_temp_unit',    '8s'),     # 1D2E       8
    ('track_temp',       '16s'),    # 1D36       10
    ('track_temp_unit',  '8s'),     # 1D46       8
    ('pressure',         '16s'),    # 1D4E       10
    ('pressure_unit',    '8s'),     # 1D5E       8
    ('humidity',         '16s'),    # 1D66       10
    ('humidity_unit',    '8s'),     # 1D76       8
    ('wind_speed',       '16s'),    # 1D7E       10
    ('wind_speed_unit',  '8s'),     # 1D8E       8
    ('wind_direction',   '64s'),    # 1D96       40
    ('weather_comment',  '1024s'),  # 1DD6       400
)

(k, f) = zip(*layouts['weather'])
keys['weather'] = tuple(filter(lambda key: key != '', k))
formats['weather'] = ''.join(f)

# CHANNEL METADATA =============================================================
# value = encoded_value * 10^-shift * scalar / divisor
# encoded_value = value / 10^-shift / scalar * divisor
# offset wrt meta ptr
layouts['ch_meta'] = (
###  KEY                 FORMAT     OFFSET (h)  LENGTH (h)
    ('',                 '<'),      #
    ('prev_ptr',         'I'),      # 0         4
    ('next_ptr',         'I'),      # 4         4
    ('data_ptr',         'I'),      # 8         4
    ('sample_count',     'I'),      # C         4
    ('magic1',           'I'),      # 10        4         196609
    ('size',             'H'),      # 14        2         2: s16 4: s32
    ('sample_rate',      'H'),      # 16        2
    ('offset',           'h'),      # 18        2
    ('scalar',           'h'),      # 1A        2
    ('divisor',          'h'),      # 1C        2
    ('shift',            'h'),      # 1E        2
    ('name',             '32s'),    # 20        20
    ('short_name',       '8s'),     # 40        8
    ('unit',             '12s'),    # 48        C
    ('',                 '40x'),    # 54        28
)

(k, f) = zip(*layouts['ch_meta'])
keys['ch_meta'] = tuple(filter(lambda key: key != '', k))
formats['ch_meta'] = ''.join(f)

# .ld OPERATIONS ===============================================================

# unpack a section of an .ld file
def unpack(file, offset, keys, format):
    file.seek(offset)
    data = file.read(struct.calcsize(format))
    # unpack bytes according to format, decoding & trimming strings
    values = [
        value.decode().strip().strip('\0') if type(value) is bytes
        else value
        for value in struct.unpack(format, data)
    ]
    # combine keys & values into a dictionary, ignoring empty keys
    return {k:v for k,v in zip(keys, values) if k != ''}

def parse(path):
    metadata = {}
    channels = {}
    f = open(path, 'rb')

    metadata['header'] = unpack(f, 0, keys['header'], formats['header'])

    if metadata['header']['event_ptr'] > 0:
        metadata['event'] = unpack(f, metadata['header']['event_ptr'], keys['event'], formats['event'])
    else: print('no event_ptr')

    if metadata['event']['venue_ptr'] > 0:
        metadata['venue'] = unpack(f, metadata['event']['venue_ptr'], keys['venue'], formats['venue'])
    else: print('no venue_ptr')

    if metadata['venue']['vehicle_ptr'] > 0:
        metadata['vehicle'] = unpack(f, metadata['venue']['vehicle_ptr'], keys['vehicle'], formats['vehicle'])
    else: print('no vehicle_ptr')

    if metadata['event']['weather_ptr'] > 0:
        metadata['weather'] = unpack(f, metadata['event']['weather_ptr'], keys['weather'], formats['weather'])
    else: print('no weather_ptr')

    if metadata['header']['meta_ptr'] > 0:
        next_ch = metadata['header']['meta_ptr']
        while next_ch:
            ch = unpack(f, next_ch, keys['ch_meta'], formats['ch_meta'])
            ch['meta_ptr'] = next_ch
            next_ch = ch['next_ptr']

            # check for duplicate channel
            if ch['name'] in channels:
                print(f"found duplicate channel: \"{ch['name']}\"")
                continue
            else:
                channels[ch['name']] = ch

            # get format for entire data section
            if ch['size'] == 2:
                data_fmt = f"<{ch['sample_count']}h"
            elif ch['size'] == 4:
                data_fmt = f"<{ch['sample_count']}i"
            else:
                print(f"\"{ch['name']}\" has unknown data size ({ch['size']})")
                continue

            # jump to and unpack channel data
            f.seek(ch['data_ptr'])
            data = f.read(struct.calcsize(data_fmt))
            channels[ch['name']]['data'] = [
                v * 10**-ch['shift'] * ch['scalar'] / ch['divisor']
                for v in struct.unpack(data_fmt, data)
            ]

        if len(channels) != metadata['header']['num_channels']:
            print(f"WARNING: num_channels ({metadata['header']['num_channels']})",
                  f"does not match number of channels found ({len(channels)})\n")
            
    else: print('no meta_pr')

    f.close()
    return (metadata, channels)

def plot(ch):
    plt.suptitle(ch['name'])
    plt.title(f"{ch['sample_count']} samples, {ch['sample_rate']}Hz")
    plt.xlabel('time (s)')
    plt.ylabel(ch['unit'])

    period = 1 / ch['sample_rate']
    t = np.arange(0, ch['sample_count']) * period
    plt.plot(t, ch['data'], '.')

    plt.ticklabel_format(useOffset=False)
    plt.show()

def write(path, channels, t0):
    event_offset = struct.calcsize(formats['header'])
    venue_offset = event_offset + struct.calcsize(formats['event'])
    vehicle_offset = venue_offset + struct.calcsize(formats['venue'])
    weather_offset = vehicle_offset + struct.calcsize(formats['vehicle'])
    meta_offset = weather_offset + struct.calcsize(formats['weather'])

    ch_meta_size = struct.calcsize(formats['ch_meta'])
    meta_size = len(channels) * ch_meta_size
    data_offset = meta_offset + meta_size

    # order must match formats['header']
    header_values = {
        'sof': 7567732375616,
        'meta_ptr': meta_offset,
        'data_ptr': data_offset,
        'event_ptr': event_offset,
        'magic1': 15,
        'device_serial': 21115,
        'device_type': 'ADL',
        'device_version': 560,
        'magic2': 128,
        'num_channels': len(channels),
        'num_channels2': len(channels),
        'magic3': 66036,
        'date': time.strftime('%d/%m/%Y', t0),
        'time': time.strftime('%H:%M:%S', t0),
        'driver': 'Driver',
        'vehicle_id': 'VehicleID',
        'engine_id': '',
        'venue': 'Venue',
        'magic4': 45126145,
        'session': 'Session',
        'short_comment': 'Comment',
        'team': ''
    }

    # order must match formats['event']
    event_values = {
        'event': 'Event',
        'session': 'Session',
        'long_comment': '',
        'venue_ptr': venue_offset,
        'weather_ptr': weather_offset
    }

    # order must match formats['venue']
    venue_values = {
        'venue': 'Venue',
        'venue_length': 0,
        'vehicle_ptr': vehicle_offset,
        'venue_category': ''
    }

    # order must match formats['vehicle']
    vehicle_values = {
        'vehicle_id': 'VehicleID',
        'vehicle_desc': '',
        'engine_id': '',
        'vehicle_weight': 0,
        'fuel_tank': 0,
        'vehicle_type': '',
        'driver_type': '',
        'diff_ratio': 0,
        'gear1': 0,
        'gear2': 0,
        'gear3': 0,
        'gear4': 0,
        'gear5': 0,
        'gear6': 0,
        'gear7': 0,
        'gear8': 0,
        'gear9': 0,
        'gear10': 0,
        'vehicle_track': 0,
        'vehicle_wheelbase': 0,
        'vehicle_comment': '',
        'vehicle_number': ''
    }

    # order must match formats['weather']
    weather_values = {
        'sky': '',
        'air_temp': '',
        'air_temp_unit': '',
        'track_temp': '',
        'track_temp_unit': '',
        'pressure': '',
        'pressure_unit': '',
        'humidity': '',
        'humidity_unit': '',
        'wind_speed': '',
        'wind_speed_unit': '',
        'wind_direction': '',
        'weather_comment': ''
    }

    def enc_str(values):
        return [
            value.encode() if type(value) is str else value
            for value in values
        ]

    print('packing metadata...')
    header = struct.pack(formats['header'], *enc_str(header_values.values()))
    event = struct.pack(formats['event'], *enc_str(event_values.values()))
    venue = struct.pack(formats['venue'], *enc_str(venue_values.values()))
    vehicle = struct.pack(formats['vehicle'], *enc_str(vehicle_values.values()))
    weather = struct.pack(formats['weather'], *enc_str(weather_values.values()))

    channel_metadata = b''
    data_size = 0
    print('linking channels...')
    for i, ch in enumerate(channels.values()):
        ch_meta = {
            'prev_ptr': 0,
            'next_ptr': 0,
            'data_ptr': 0,
            'sample_count': len(ch['v_enc']),
            'magic1': 196609,
            'size': 2,
            'sample_rate': ch['sample_rate'],
            'offset': ch['offset'],
            'scalar': ch['scalar'],
            'divisor': ch['divisor'],
            'shift': ch['shift'],
            'name': ch['name'],
            'short_name': '',
            'unit': ch['unit'],
        }
        ch_meta['data_ptr'] = data_offset + data_size
        data_size += ch_meta['sample_count'] * ch_meta['size']

        if i == 0: ch_meta['prev_ptr'] = 0
        else: ch_meta['prev_ptr'] = meta_offset + ch_meta_size * (i - 1)

        if i == len(channels) - 1: ch_meta['next_ptr'] = 0
        else: ch_meta['next_ptr'] = meta_offset + ch_meta_size * (i + 1)

        try:
            channel_metadata += struct.pack(formats['ch_meta'], *enc_str(ch_meta.values()))
        except:
            print(f"failed to pack channel metadata: {ch_meta} (channel {ch['id']})")

    print(f'writing to "{path}"... ', end='', flush=True)
    start = time.time()
    with open(path, 'wb') as f:
        f.write(header + event + venue + vehicle + weather + channel_metadata)

        # pack data for each channel
        # do this at write time to avoid storing large byte strings in memory
        for ch in channels.values():
            # assumes data has been encoded for a s16
            data = struct.pack(f"<{len(ch['v_enc'])}h", *ch['v_enc'])
            f.write(data)
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')