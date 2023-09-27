# file structure based on logs from the MoTeC EDL3 v5.6

# .ld files are split into several sections linked by file pointers
# layouts contain a series of (key, format) pairs for each value in a section
# values with empty keys are unused/unknown
# key lists and format strings are derived from the corresponding layout

# KEY: identifies the value
# FORMAT: mapping between byte string and Python value
# OFFSET (hex): file offset of the value
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
# value = (data / divisor * 10^-shift + offset) * scalar
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