import struct
import time
import numpy as np
import matplotlib.pyplot as plt

# file structure based on logs from the MoTeC EDL3 v5.6

# .ld files are split into several sections linked by file pointers
# layouts contain a series of (key, format) pairs for each value in a section
# values with empty keys are unused/unknown
# a list of keys and a single combined format string are derived from the corresponding layout

# KEY: identifies the value
# FORMAT: mapping between byte string and Python value, used in struct.pack/unpack
# OFFSET (hex): file offset of the value
# LENGTH (hex): length of the value in bytes

HEADER = ( # ===================================================================
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('sof',             'Q'),      # 0         8         0x40
    ('meta_ptr',        'I'),      # 8         4
    ('data_ptr',        'I'),      # C         4
    ('',                '20x'),    # 10        14
    ('event_ptr',       'I'),      # 24        4
    ('',                '24x'),    # 28        18
    ('magic1',          'H'),      # 40        2         0x0000
    ('magic2',          'H'),      # 42        2         0x4240
    ('magic3',          'H'),      # 44        2         0x000F
    ('device_serial',   'I'),      # 46        4         21115
    ('device_type',     '8s'),     # 4A        8         ADL
    ('device_version',  'H'),      # 52        2         560
    ('magic4',          'H'),      # 54        2         0x0080
    ('num_channels',    'H'),      # 56        2
    ('num_channels2',   'H'),      # 58        2
    ('magic5',          'I'),      # 5A        4         0x00050014
    ('date',            '32s'),    # 5E        20
    ('time',            '32s'),    # 7E        20
    ('driver',          '64s'),    # 9E        40
    ('vehicle_id',      '64s'),    # DE        40
    ('engine_id',       '64s'),    # 11E       40
    ('venue',           '64s'),    # 15E       40
    ('',                '1088x'),  # 19E       440
    ('magic6',          'I'),      # 5DE       4         0x02B09201
    ('',                '2x'),     # 5E2       2
    ('session',         '64s'),    # 5E4       40
    ('short_comment',   '64s'),    # 624       40
    ('',                '8x'),     # 664       8
    ('magic7',          'H'),      # 66C       2         0x0045
    ('',                '38x'),    # 66E       26
    ('team',            '32s'),    # 694       20
    ('',                '46x'),    # 6B4       2E
)

(k, f) = zip(*HEADER)
HEADER_KEYS = tuple(filter(lambda key: key != '', k))
HEADER_FMT = ''.join(f)
HEADER_SIZE = struct.calcsize(HEADER_FMT)

EVENT = ( # ====================================================================
###  KEY              FORMAT     OFFSET (h)  LENGTH (h)
    ('',              '<'),      #
    ('event',         '64s'),    # 6E2       40
    ('session',       '64s'),    # 722       40
    ('long_comment',  '1024s'),  # 762       400
    ('venue_ptr',     'I'),      # B62       4
    ('weather_ptr',   'I'),      # B66       4
    ('',              '1996x'),  # B6A       7CC
)

(k, f) = zip(*EVENT)
EVENT_KEYS = tuple(filter(lambda key: key != '', k))
EVENT_FMT = ''.join(f)
EVENT_SIZE = struct.calcsize(EVENT_FMT)

VENUE = ( # ====================================================================
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('venue',           '64s'),    # 1336      40
    ('',                '2x'),     # 1376      2
    ('venue_length',    'I'),      # 1378      4         unit: mm
    ('',                '1028x'),  # 137C      404
    ('vehicle_ptr',     'I'),      # 1780      4
    ('venue_category',  '32s'),    # 1784      20
    ('',                '1968x')   # 17A4      7B0
)

(k, f) = zip(*VENUE)
VENUE_KEYS = tuple(filter(lambda key: key != '', k))
VENUE_FMT = ''.join(f)
VENUE_SIZE = struct.calcsize(VENUE_FMT)

VEHICLE = ( # ==================================================================
###  KEY                   FORMAT     OFFSET (h)  LENGTH (h)
    ('',                   '<'),      #
    ('vehicle_id',         '64s'),    # 1F54      40
    ('vehicle_desc',       '64s'),    # 1F94      40
    ('engine_id',          '64s'),    # 1FD4      40
    ('vehicle_weight',     'H'),      # 2014      2         unit: kg
    ('fuel_tank',          'H'),      # 2016      2         unit: deciliter
    ('vehicle_type',       '32s'),    # 2018      20
    ('driver_type',        '32s'),    # 2038      20
    ('diff_ratio',         'H'),      # 2058      2
    ('gear1',              'H'),      # 205A      2
    ('gear2',              'H'),      # 205C      2
    ('gear3',              'H'),      # 205E      2
    ('gear4',              'H'),      # 2060      2
    ('gear5',              'H'),      # 2062      2
    ('gear6',              'H'),      # 2064      2
    ('gear7',              'H'),      # 2066      2
    ('gear8',              'H'),      # 2068      2
    ('gear9',              'H'),      # 206A      2
    ('gear10',             'H'),      # 206C      2
    ('vehicle_track',      'H'),      # 206E      2         unit: mm
    ('vehicle_wheelbase',  'I'),      # 2070      4         unit: mm
    ('vehicle_comment',    '1024s'),  # 2074      400
    ('',                   '4x'),     # 2474      4
    ('vehicle_number',     '32s'),    # 2478      20
    ('',                   '1968x'),  # 2498      7B0
)

(k, f) = zip(*VEHICLE)
VEHICLE_KEYS = tuple(filter(lambda key: key != '', k))
VEHICLE_FMT = ''.join(f)
VEHICLE_SIZE = struct.calcsize(VEHICLE_FMT)

WEATHER = ( # ==================================================================
###  KEY                 FORMAT     OFFSET (h)  LENGTH (h)
    ('',                 '<'),      #
    ('sky',              '64s'),    # 2C48       40
    ('air_temp',         '16s'),    # 2C88       10
    ('air_temp_unit',    '8s'),     # 2C98       8
    ('track_temp',       '16s'),    # 2CA0       10
    ('track_temp_unit',  '8s'),     # 2CB0       8
    ('pressure',         '16s'),    # 2CB8       10
    ('pressure_unit',    '8s'),     # 2CC8       8
    ('humidity',         '16s'),    # 2CD0       10
    ('humidity_unit',    '8s'),     # 2CE0       8
    ('wind_speed',       '16s'),    # 2CE8       10
    ('wind_speed_unit',  '8s'),     # 2CF8       8
    ('wind_direction',   '64s'),    # 2D00       40
    ('weather_comment',  '1024s'),  # 2D40       400
    ('',                 '776x'),   # 3140       308
)

(k, f) = zip(*WEATHER)
WEATHER_KEYS = tuple(filter(lambda key: key != '', k))
WEATHER_FMT = ''.join(f)
WEATHER_SIZE = struct.calcsize(WEATHER_FMT)

# value = encoded_value * 10^-shift * scalar / divisor
# encoded_value = value / 10^-shift / scalar * divisor
CH_META = ( # ==================================================================
###  KEY                 FORMAT     OFFSET (h)  LENGTH (h)
    ('',                 '<'),      #
    ('prev_ptr',         'I'),      # +0        4
    ('next_ptr',         'I'),      # +4        4
    ('data_ptr',         'I'),      # +8        4
    ('sample_count',     'I'),      # +C        4
    ('magic1',           'I'),      # +10       4         s16: 0x00030001, s32: 0x0005AA55
    ('size',             'H'),      # +14       2         s16: 0x02 s32: 0x04
    ('sample_rate',      'H'),      # +16       2
    ('offset',           'h'),      # +18       2
    ('scalar',           'h'),      # +1A       2
    ('divisor',          'h'),      # +1C       2
    ('shift',            'h'),      # +1E       2
    ('name',             '32s'),    # +20       20
    ('short_name',       '8s'),     # +40       8
    ('unit',             '12s'),    # +48       C
    ('',                 '40x'),    # +54       28
)

(k, f) = zip(*CH_META)
CH_META_KEYS = tuple(filter(lambda key: key != '', k))
CH_META_FMT = ''.join(f)
CH_META_SIZE = struct.calcsize(CH_META_FMT)

# ==============================================================================

# read values from a .ld file according to the formats above
def parse(path):
    f = open(path, 'rb')

    def unpack(offset, keys, format):
        nonlocal f
        f.seek(offset)
        data = f.read(struct.calcsize(format))
        # unpack bytes according to format, decoding & trimming strings
        values = [
            value.decode().strip().strip('\0') if type(value) is bytes
            else value
            for value in struct.unpack(format, data)
        ]
        # match keys to the unpacked values, ignoring empty keys
        return {k:v for k,v in zip(keys, values) if k != ''}

    try: header = unpack(0, HEADER_KEYS, HEADER_FMT)
    except: print('ERROR: failed to unpack header')

    try: event = unpack(header['event_ptr'], EVENT_KEYS, EVENT_FMT)
    except: print('WARNING: failed to unpack event')

    try: venue = unpack(event['venue_ptr'], VENUE_KEYS, VENUE_FMT)
    except: print('WARNING: failed to unpack venue')

    try: vehicle = unpack(venue['vehicle_ptr'], VEHICLE_KEYS, VEHICLE_FMT)
    except: print('WARNING: failed to unpack vehicle')

    try: weather = unpack(event['weather_ptr'], WEATHER_KEYS, WEATHER_FMT)
    except: print('WARNING: failed to unpack weather')

    channels = {}
    next_ch = header['meta_ptr']
    while next_ch:
        ch = unpack(next_ch, CH_META_KEYS, CH_META_FMT)
        ch['meta_ptr'] = next_ch # not included in the format, but useful to keep
        next_ch = ch['next_ptr']

        # check for duplicate channel
        if ch['name'] in channels:
            print(f"WARNING: ignoring duplicate channel \"{ch['name']}\"")
            continue
        else:
            channels[ch['name']] = ch

        # get format for entire data section
        if ch['size'] == 2:
            data_fmt = f"<{ch['sample_count']}h"
        elif ch['size'] == 4:
            data_fmt = f"<{ch['sample_count']}i"
        else:
            print(f"WARNING: \"{ch['name']}\" has unknown data size ({ch['size']})")
            continue

        # jump to and unpack channel data
        f.seek(ch['data_ptr'])
        data = f.read(struct.calcsize(data_fmt))
        channels[ch['name']]['data'] = [
            v * 10**-ch['shift'] * ch['scalar'] / ch['divisor']
            for v in struct.unpack(data_fmt, data)
        ]

    if len(channels) != header['num_channels']:
        print(f"WARNING: num_channels ({header['num_channels']}) does not match number of channels found ({len(channels)})")

    f.close()
    print(f'loaded {len(channels)} channels')
    metadata = {
        'header': header,
        'event': event,
        'venue': venue,
        'vehicle': vehicle,
        'weather': weather
    }
    return (metadata, channels)

# plot a channel parsed from a .ld file
def plot(ch):
    plt.suptitle(ch['name'])
    plt.title(f"{ch['sample_count']} samples, {ch['sample_rate']}Hz")
    plt.xlabel('time (s)')
    plt.ylabel(ch['unit'])

    t = np.arange(0, ch['sample_count']) * (1 / ch['sample_rate'])
    plt.plot(t, ch['data'], '.')

    plt.ticklabel_format(useOffset=False)
    plt.show()

# create a .ld file with the provided channels and timestamp and default metadata
# see gdat.py for channel data structure
def write(path, channels, t0):
    event_offset = HEADER_SIZE
    venue_offset = event_offset + EVENT_SIZE
    vehicle_offset = venue_offset + VENUE_SIZE
    weather_offset = vehicle_offset + VEHICLE_SIZE
    meta_offset = weather_offset + WEATHER_SIZE
    data_offset = meta_offset + (len(channels) * CH_META_SIZE)

    # order must match HEADER_FMT
    header_values = {
        'sof': 0x40,
        'meta_ptr': meta_offset,
        'data_ptr': data_offset,
        'event_ptr': event_offset,
        'magic1': 0,
        'magic2': 0x4240,
        'magic3': 0x000F,
        'device_serial': 21115,
        'device_type': 'ADL',
        'device_version': 560,
        'magic4': 0x0080,
        'num_channels': len(channels),
        'num_channels2': len(channels),
        'magic5': 0x00050014,
        'date': time.strftime('%d/%m/%Y', t0),
        'time': time.strftime('%H:%M:%S', t0),
        'driver': 'Driver',
        'vehicle_id': 'VehicleID',
        'engine_id': '',
        'venue': 'Venue',
        'magic6': 0x02B09201,
        'session': 'Session',
        'short_comment': 'Comment',
        'magic7': 0x0045,
        'team': ''
    }

    # order must match EVENT_FMT
    event_values = {
        'event': 'Event',
        'session': 'Session',
        'long_comment': '',
        'venue_ptr': venue_offset,
        'weather_ptr': weather_offset
    }

    # order must match VENUE_FMT
    venue_values = {
        'venue': 'Venue',
        'venue_length': 0,
        'vehicle_ptr': vehicle_offset,
        'venue_category': ''
    }

    # order must match VEHICLE_FMT
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

    # order must match WEATHER_FMT
    weather_values = {
        'sky': 'Sunny',
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

    # convert strings to utf-8 byte strings
    def enc_str(values):
        return [
            value.encode() if type(value) is str else value
            for value in values
        ]

    print('packing metadata...')
    header = struct.pack(HEADER_FMT, *enc_str(header_values.values()))
    event = struct.pack(EVENT_FMT, *enc_str(event_values.values()))
    venue = struct.pack(VENUE_FMT, *enc_str(venue_values.values()))
    vehicle = struct.pack(VEHICLE_FMT, *enc_str(vehicle_values.values()))
    weather = struct.pack(WEATHER_FMT, *enc_str(weather_values.values()))

    print('linking channels...')
    channel_metadata = b''
    data_size = 0
    for i, ch in enumerate(channels.values()):
        # order must match CH_META_FMT
        ch_meta = {
            'prev_ptr': 0,
            'next_ptr': 0,
            'data_ptr': data_offset + data_size,
            'sample_count': len(ch['v_enc']),
            'magic1': 0x0005AA55,
            'size': 0x04,
            'sample_rate': ch['frequency_hz'],
            'offset': ch['offset'],
            'scalar': ch['scalar'],
            'divisor': ch['divisor'],
            'shift': ch['shift'],
            'name': ch['name'],
            'short_name': '',
            'unit': ch['unit'],
        }

        if i == 0: ch_meta['prev_ptr'] = 0 # first channel has no prev_ptr
        else: ch_meta['prev_ptr'] = meta_offset + CH_META_SIZE * (i - 1)

        if i == len(channels) - 1: ch_meta['next_ptr'] = 0 # last channel has no next_ptr
        else: ch_meta['next_ptr'] = meta_offset + CH_META_SIZE * (i + 1)

        data_size += ch_meta['sample_count'] * ch_meta['size']

        try:
            channel_metadata += struct.pack(CH_META_FMT, *enc_str(ch_meta.values()))
        except:
            print(f"failed to pack channel metadata ({ch['id']}): {ch_meta}")

    print(f'writing to "{path}"... ', end='', flush=True)
    start = time.time()
    with open(path, 'wb') as f:
        f.write(header + event + venue + vehicle + weather + channel_metadata)

        # pack data for each channel
        # do this at write time to avoid storing large byte strings in memory
        for ch in channels.values():
            # assumes data has been encoded for a s32
            data = struct.pack(f"<{len(ch['v_enc'])}i", *ch['v_enc'])
            f.write(data)
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')