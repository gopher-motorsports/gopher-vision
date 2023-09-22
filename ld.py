# .ld files are split into several sections linked by file pointers
# layouts contain a series of (key, format) pairs for each value in a section
# values with empty keys are unused/unknown

# KEY: identifies the value
# FORMAT: mapping between byte string and Python value
# OFFSET (hex): file offset of the value wrt the beginning of the section
# LENGTH (hex): length of the value in bytes
layouts = {}

# key lists and format strings are derived from the corresponding layout
keys = {}
formats = {}

# HEADER =======================================================================
layouts['header'] = (
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('sof',             'Q'),      # 0         8
    ('meta_ptr',        'I'),      # 8         4         0x3448
    ('data_ptr',        'I'),      # C         4         0x5A10
    ('',                '20x'),    # 10        14
    ('event_ptr',       'I'),      # 24        4         0x6E2
    ('',                '30x'),    # 28        1E
    ('device_serial',   'I'),      # 46        4
    ('device_type',     '8s'),     # 4A        8
    ('device_version',  'H'),      # 52        2
    ('pro1',            'H'),      # 54        2         pro logging
    ('num_channels',    'H'),      # 56        2
    ('num_channels2',   'H'),      # 58        2
    ('',                '4x'),     # 5A        4
    ('date',            '32s'),    # 5E        20
    ('time',            '32s'),    # 7E        20
    ('driver',          '64s'),    # 9E        40
    ('vehicle_id',      '64s'),    # DE        40
    ('engine_id',       '64s'),    # 11E       40
    ('venue',           '64s'),    # 15E       40
    ('',                '1088x'),  # 19E       440
    ('pro2',            'I'),      # 5DE       4         pro logging
    ('',                '2x'),     # 5E2       2
    ('session',         '64s'),    # 5E4       40
    ('short_comment',   '64s'),    # 624       40
    ('',                '48x'),    # 664       30
    ('team',            '64s'),    # 694       40
)

(k, f) = zip(*layouts['header'])
keys['header'] = tuple(filter(lambda key: key != '', k))
formats['header'] = ''.join(f)

# EVENT =======================================================================
layouts['event'] = (
###  KEY              FORMAT     OFFSET (h)  LENGTH (h)
    ('',              '<'),      #
    ('event',         '64s'),    # 0         40
    ('session',       '64s'),    # 40        40
    ('long_comment',  '1024s'),  # 80        400
    ('venue_ptr',     'I'),      # 480       4         0x1336
    ('weather_ptr',   'I'),      # 484       4         0x2C48
)

(k, f) = zip(*layouts['event'])
keys['event'] = tuple(filter(lambda key: key != '', k))
formats['event'] = ''.join(f)

# VENUE =======================================================================
layouts['venue'] = (
###  KEY                FORMAT     OFFSET (h)  LENGTH (h)
    ('',                '<'),      #
    ('venue',           '64s'),    # 0         40
    ('',                '2x'),     # 40        2
    ('venue_length',    'I'),      # 42        4
    ('',                '1028x'),  # 46        404
    ('vehicle_ptr',     'I'),      # 44A       4         0x1F54
    ('venue_category',  '64s'),    # 44E       40
)

(k, f) = zip(*layouts['venue'])
keys['venue'] = tuple(filter(lambda key: key != '', k))
formats['venue'] = ''.join(f)

# VEHICLE =======================================================================
layouts['vehicle'] = (
###  KEY                   FORMAT     OFFSET (h)  LENGTH (h)
    ('',                   '<'),      #
    ('vehicle_id',         '64s'),    # 0         40
    ('vehicle_desc',       '64s'),    # 40        40
    ('engine_id',          '64s'),    # 80        40
    ('vehicle_weight',     'H'),      # C0        2
    ('fuel_tank',          'H'),      # C2        2
    ('vehicle_type',       '32s'),    # C4        20
    ('driver_type',        '32s'),    # E4        20
    ('diff_ratio',         'H'),      # 104       2
    ('gear1',              'H'),      # 106       2
    ('gear2',              'H'),      # 108       2
    ('gear3',              'H'),      # 10A       2
    ('gear4',              'H'),      # 10C       2
    ('gear5',              'H'),      # 10E       2
    ('gear6',              'H'),      # 110       2
    ('gear7',              'H'),      # 112       2
    ('gear8',              'H'),      # 114       2
    ('gear9',              'H'),      # 116       2
    ('gear10',             'H'),      # 118       2
    ('vehicle_track',      'H'),      # 11A       2
    ('vehicle_wheelbase',  'I'),      # 11C       4
    ('vehicle_comment',    '1028s'),  # 120       404
    ('vehicle_number',     '64s'),    # 524       400
)

(k, f) = zip(*layouts['vehicle'])
keys['vehicle'] = tuple(filter(lambda key: key != '', k))
formats['vehicle'] = ''.join(f)

# WEATHER =======================================================================
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