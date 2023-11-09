import time
import struct
import random
import numpy as np
import math
from fractions import Fraction
import matplotlib.pyplot as plt

# .gdat files begin with "/PLM_YYYY-MM-DD-HH-MM-SS.gdat:" (RTC time of file creation)
# followed by a series of packets of the following format (big endian):
# 0    1 2 3 4     5 6   7 n    n+1
# 7E   TIMESTAMP   ID    DATA   CHECKSUM

# 0x7E indicates the start of a packet
# 0x7D indicates that the next byte has been escaped (XORed with 0x20)
# CHECKSUM = sum of bytes ignoring overflow, calculated on unescaped packet, including start delimiter

START = 0x7E
ESC = 0x7D
MIN_PACKET_LENGTH = 9

random.seed()
start_ms = time.time() * 1000

def get_t0(sof):
    try:
        return time.strptime(sof.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')
    except:
        print(f'failed to parse timestamp "{sof.decode()}"')
        return time.gmtime(0)

# split byte string into packets and assign data to channels
def decode_packets(bytes, channels, parameters):
    n_packets = 0
    n_errors = 0

    packet = bytearray()
    def decode():
        nonlocal n_packets
        nonlocal n_errors
        n_packets += 1
        # split into components
        # verifies packet length (unpack would fail)
        # verifies id (parameters access would fail)
        try:
            ts, id = struct.unpack('>IH', packet[1:7])
            value = struct.unpack(parameters[id]['format'], packet[7:-1])[0]
        except:
            n_errors += 1
            return
        # verify checksum
        sum = 0
        for b in packet[:-1]: sum += b
        if not sum.to_bytes(2)[-1] == packet[-1]:
            n_errors += 1
            return
        # add to channel
        channels[id]['points'].append((ts, value))

    esc = False
    for b in bytes:
        if b == START:
            # beginning new packet, decode the last one
            decode()
            packet = bytearray()
            packet.append(START)
        elif b == ESC:
            # escape next byte
            esc = True
        elif esc:
            packet.append(b ^ 0x20)
            esc = False
        else:
            packet.append(b)
    decode()
        
    return (n_packets, n_errors)

# find shift, scalar, and divisor to fit value in a s16 [-2^15, 2^15 - 1]
# value = encoded_value * 10^-shift * scalar / divisor
# encoded_value = value / 10^-shift / scalar * divisor
# to make the most of a s16: abs_max = (2^15 - 1) * 10^-shift * scalar / divisor
def get_scalars(v_min, v_max):
    abs_max = max(abs(v_min), abs(v_max))

    exp = 0
    scale = abs_max
    scf = 0
    shift = 0
    done = False

    if v_max - v_min <= 0.001:
        if -0.0001 <= abs_max <= 0.0001:
            exp = 0
            scale = 1
        else:
            exp = 1
            scale = abs_max
        scf = 8 * (10**exp) / scale
        shift = 6 - exp
        done = True

    exp = -37
    while exp < 37 and not done:
        if scale >= 8 * 10**exp and scale < 8 * 10**(exp+1):
            scf = 8 * 10**exp / scale
            shift = 6 - exp
            done = True
        exp += 1

    if not done:
        raise Exception('encoding failed')
    
    scalar, divisor = Fraction(scf).limit_denominator(2047).as_integer_ratio()
    if scalar > 2047:
        raise Exception('encoding failed')
    
    return (shift, scalar, divisor)

# decode packets from a byte string and organize into channels
def parse(bytes, parameters):
    channels = {
        id: {
            'id': id,
            'name': param['name'],
            'unit': param['unit'],
            # raw data
            'n_points': 0,              # num raw datapoints
            'points': [],
            't_min': 0,                 # min timestamp
            't_max': 0,                 # max timestamp
            'v_min': 0,                 # min value
            'v_max': 0,                 # max value
            # interpolated data
            'delta_ms': 0,
            'frequency_hz': 0,
            'sample_count': 0,          # num interpolated datapoints
            't_int': [],                # evenly spaced timestamps
            'v_int': [],                # interpolated values
            # s32 encoded data (on t_int time axis)
            # encoded_value = value / 10^-shift / scalar * divisor
            # value = encoded_value * 10^-shift * scalar / divisor
            'v_enc': [],
            'shift': 0,
            'scalar': 0,
            'divisor': 0,
            'offset': 0,
        }
        for (id, param) in parameters.items()
    }

    print('decoding packets... ', end='', flush=True)
    start = time.time()
    n_packets, n_errors = decode_packets(bytes, channels, parameters)
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')
    print(f'{n_packets} packets, {n_errors} errors')

    # remove channels with no data
    for id in list(channels.keys()):
        channels[id]['n_points'] = len(channels[id]['points'])
        if channels[id]['n_points'] == 0:
            print(f'removing empty channel: {channels[id]['name']} ({id})')
            del channels[id]

    print('sorting data... ', end='', flush=True)
    start = time.time()
    for ch in channels.values():
        # sort points by timestamp
        ch['points'].sort(key=lambda pt: pt[0])
        ch['points'] = np.array(ch['points'], dtype=np.float64)
        # timestamps = ch['points'][:,0]
        # values     = ch['points'][:,1]

        ch['t_min'] = ch['points'][:,0].min()
        ch['t_max'] = ch['points'][:,0].max()
        ch['v_min'] = ch['points'][:,1].min()
        ch['v_max'] = ch['points'][:,1].max()
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print('interpolating data... ', end='', flush=True)
    start = time.time()
    for ch in channels.values():
        # calculate time axis delta / channel frequency
        if ch['n_points'] == 1:
            # single datapoint: use 1Hz by default
            ch['delta_ms'] = 1000
            ch['frequency_hz'] = 1
        else:
            # multiple datapoints: calculate an appropriate freq
            # find the most common time delta between points
            deltas = np.diff(ch['points'][:,0])
            unique_deltas, counts = np.unique(deltas, return_counts=True)
            common_delta = int(unique_deltas[counts == counts.max()][0])
            # force a minimum frequency of 1Hz
            delta = min(common_delta, 1000)
            # round so that frequency is an integer
            while 1000 % delta != 0: delta += 1
            ch['delta_ms'] = delta
            ch['frequency_hz'] = math.trunc(1000 / delta)
        # create a new time axis with this frequency
        ch['sample_count'] = math.trunc(ch['t_max'] / ch['delta_ms'])
        ch['t_int'] = np.arange(0, ch['sample_count']) * ch['delta_ms']
        # interpolate data over the new time axis
        ch['v_int'] = np.interp(ch['t_int'], ch['points'][:,0], ch['points'][:,1])
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print('encoding channels... ', end='', flush=True)
    start = time.time()
    for id in list(channels.keys()):
        ch = channels[id]
        try:
            ch['shift'], ch['scalar'], ch['divisor'] = get_scalars(ch['v_min'], ch['v_max'])
        except:
            # encoding failed, remove channel
            print(f'failed to encode channel: {ch['name']} ({id}) min={ch['v_min']} max={ch['v_max']}')
            del channels[id]
        else:
            # encoded_value = value / 10^-shift / scalar * divisor
            ch['v_enc'] = np.array(
                [v / 10**-ch['shift'] / ch['scalar'] * ch['divisor'] for v in ch['v_int']],
                dtype=np.int32
            )
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print(f'created {len(channels)} channels')
    return channels

# plot a channel parsed from a .gdat string
def plot(ch):
    plt.suptitle(f"{ch['name']} ({ch['id']})")
    plt.title(f"{ch['n_points']} points")
    plt.xlabel('time (ms)')
    plt.ylabel(ch['unit'])

    plt.plot(ch['points'][:,0], ch['points'][:,1], '.', label='raw')
    plt.plot(ch['t_int'], ch['v_int'], '-', label='interpolated')

    decoded = [v * 10**-ch['shift'] * ch['scalar'] / ch['divisor'] for v in ch['v_enc']]
    plt.plot(ch['t_int'], decoded, '--', label='decoded')

    plt.ticklabel_format(useOffset=False)
    plt.legend(loc='best')
    plt.show()