# file structure based on logs from the MoTeC EDL3 v5.6

# .ld files are split into several sections linked by file pointers
# layouts contain a series of (key, format) pairs for each value in a section
# values with empty keys are unused/unknown
# key lists and format strings are derived from the corresponding layout

# KEY: identifies the value
# FORMAT: mapping between byte string and Python value
# OFFSET (hex): file offset of the value wrt the beginning of the section
# LENGTH (hex): length of the value in bytes

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
    ('event',         '64s'),    # 0         40
    ('session',       '64s'),    # 40        40
    ('long_comment',  '1024s'),  # 80        400
    ('venue_ptr',     'I'),      # 480       4
    ('weather_ptr',   'I'),      # 484       4
)

(k, f) = zip(*layouts['event'])
keys['event'] = tuple(filter(lambda key: key != '', k))
formats['event'] = ''.join(f)

# VENUE ========================================================================
layouts['venue'] = (
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('venue',           '64s'),    # 0         40
    ('',                '2x'),     # 40        2
    ('venue_length',    'I'),      # 42        4         unit: mm
    ('',                '1028x'),  # 46        404
    ('vehicle_ptr',     'I'),      # 44A       4
    ('venue_category',  '1024s'),  # 44E       400    
    ('',                '976x')    # 84E       3D0
)

(k, f) = zip(*layouts['venue'])
keys['venue'] = tuple(filter(lambda key: key != '', k))
formats['venue'] = ''.join(f)

# VEHICLE ======================================================================
layouts['vehicle'] = (
###  KEY                   FORMAT     OFFSET (h)  LENGTH (h)
    ('',                   '<'),      #
    ('vehicle_id',         '64s'),    # 0         40
    ('vehicle_desc',       '64s'),    # 40        40
    ('engine_id',          '64s'),    # 80        40
    ('vehicle_weight',     'H'),      # C0        2         unit: kg
    ('fuel_tank',          'H'),      # C2        2         unit: deciliter
    ('vehicle_type',       '32s'),    # C4        20
    ('driver_type',        '32s'),    # E4        20
    ('diff_ratio',         'H'),      # 104       2         scale: 1000
    ('gear1',              'H'),      # 106       2         scale: 1000
    ('gear2',              'H'),      # 108       2         scale: 1000
    ('gear3',              'H'),      # 10A       2         scale: 1000
    ('gear4',              'H'),      # 10C       2         scale: 1000
    ('gear5',              'H'),      # 10E       2         scale: 1000
    ('gear6',              'H'),      # 110       2         scale: 1000
    ('gear7',              'H'),      # 112       2         scale: 1000
    ('gear8',              'H'),      # 114       2         scale: 1000
    ('gear9',              'H'),      # 116       2         scale: 1000
    ('gear10',             'H'),      # 118       2         scale: 1000
    ('vehicle_track',      'H'),      # 11A       2         unit: mm
    ('vehicle_wheelbase',  'I'),      # 11C       4         unit: mm
    ('vehicle_comment',    '1028s'),  # 120       404
    ('vehicle_number',     '64s'),    # 524       40
)

(k, f) = zip(*layouts['vehicle'])
keys['vehicle'] = tuple(filter(lambda key: key != '', k))
formats['vehicle'] = ''.join(f)

# WEATHER ======================================================================
layouts['weather'] = (
###  KEY                 FORMAT     OFFSET (h)  LENGTH (h)
    ('',                 '<'),      #
    ('sky',              '64s'),    # 0         40
    ('air_temp',         '16s'),    # 40        10
    ('air_temp_unit',    '8s'),     # 50        8
    ('track_temp',       '16s'),    # 58        10
    ('track_temp_unit',  '8s'),     # 68        8
    ('pressure',         '16s'),    # 70        10
    ('pressure_unit',    '8s'),     # 80        8
    ('humidity',         '16s'),    # 88        10
    ('humidity_unit',    '8s'),     # 98        8
    ('wind_speed',       '16s'),    # A0        10
    ('wind_speed_unit',  '8s'),     # B0        8
    ('wind_direction',   '64s'),    # B8        40
    ('weather_comment',  '1024s'),  # F8        400
)

(k, f) = zip(*layouts['weather'])
keys['weather'] = tuple(filter(lambda key: key != '', k))
formats['weather'] = ''.join(f)

# CHANNEL METADATA =============================================================
# value = (data / divisor * 10^-shift + offset) * scalar
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