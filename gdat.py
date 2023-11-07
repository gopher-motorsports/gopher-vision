# .gdat files begin with "/PLM_YYYY-MM-DD-HH-MM-SS.gdat:" (RTC time of file creation)
# followed by a series of packets of the following format (big endian):
# 0    1 2 3 4     5 6   7 n    n+1
# 7E   TIMESTAMP   ID    DATA   CHECKSUM

# 0x7E indicates the start of a packet
# 0x7D indicates that the next byte has been escaped (XORed with 0x20)
# CHECKSUM = sum of bytes ignoring overflow (including start delimiter), calculated on unescaped packet

import time
import struct
import random
import numpy as np
import math
from fractions import Fraction
import matplotlib.pyplot as plt

START = 0x7E
ESC = 0x7D
MIN_PACKET_LENGTH = 9

random.seed()
start_ms = time.time() * 1000

def get_t0(sof):
    try:
        return time.strptime(sof.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')
    except:
        return time.gmtime(0)

def decode_packets(bytes, channels, parameters):
    packets = 0
    errors = 0

    packet = bytearray()
    def decode():
        nonlocal packets
        nonlocal errors
        packets += 1
        # split into components
        # verifies packet length (unpack would fail)
        # verifies id (parameters access would fail)
        try:
            ts, id = struct.unpack('>IH', packet[1:7])
            value = struct.unpack(parameters[id]['format'], packet[7:-1])[0]
        except:
            errors += 1
            return
        # verify checksum
        sum = 0
        for b in packet[:-1]: sum += b
        if not sum.to_bytes(2)[-1] == packet[-1]:
            errors += 1
            return
        # add to channel
        channels[id]['points'].append((ts, value))

    esc = False
    for b in bytes:
        if b == START:
            decode()
            packet = bytearray()
            packet.append(START)
        elif b == ESC:
            esc = True
        elif esc:
            packet.append(b ^ 0x20)
            esc = False
        else:
            packet.append(b)
        
    return (packets, errors)

# find shift, scalar, and divisor to fit value in a s16 [-2^15, 2^15 - 1]
# value = encoded_value * 10^-shift * scalar / divisor
# encoded_value = value / 10^-shift / scalar * divisor
# to make the most of a s16: abs_max = (2^15 - 1) * 10^-shift * scalar / divisor
def get_scalars(abs_max):
    if abs_max == 0:
        shift = 0
        scalar = 1
        divisor = 1
        return (shift, scalar, divisor)

    # start with high shift to preserve precision
    for shift in range(10, -10, -1):
        # calculate required scale to use this shift
        scale = abs_max / (2**15-1) / 10**-shift
        # convert scale to integer fraction
        scalar, divisor = Fraction(scale).limit_denominator(2**15-1).as_integer_ratio()
        if scalar == 0:
            # scale can't be represented
            continue
        elif -2**15 <= scalar <= 2**15-1:
            # both scalar & divisor will fit in s16
            break
        else:
            # adjust scalar to fit in s16 (adjust divisor to maintain fraction)
            adj = (2**15-1) / scalar
            scalar = round(scalar * adj)
            divisor = round(divisor * adj)
            # check if divisor is still valid
            if -2**15 <= divisor <= 2**15-1 and divisor != 0:
                # max encoded value
                enc_max = abs_max / 10**-shift / scalar * divisor
                # % error with this new fraction to the ideal scale
                error = ((scalar / divisor) - scale) / scale
                # 10% error is acceptable
                if enc_max <= 2**15-1 and error <= 0.1:
                    break
    else:
        raise Exception(f'failed to find scalars for ({abs_max})')

    return (shift, scalar, divisor)

def parse(bytes, parameters):
    channels = {
        id: {
            'id': id,
            'name': param['name'],
            'unit': param['unit'],
            'sample_count': 0,
            'delta_ms': 0,
            'frequency_hz': 0,
            't_min': 0,
            't_max': 0,
            'v_min': 0,
            'v_max': 0,
            # scalars to encode in s16
            'shift': 0,
            'scalar': 1,
            'divisor': 1,
            'offset': 0,
            # data
            'points': [],
            't_int': None, # interpolated timestamps
            'v_int': None, # interpolated values
            'v_enc': None, # encoded values
        }
        for (id, param) in parameters.items()
    }

    print('decoding packets... ', end='', flush=True)
    start = time.time()
    (packets, errors) = decode_packets(bytes, channels, parameters)
    for id in list(channels.keys()):
        # remove channels with no data
        if len(channels[id]['points']) == 0:
            del channels[id]
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')
    print(f'{packets} packets, {errors} errors')

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
        delta = 100 # assume 100ms if a channel has a single point
        if len(ch['points']) > 1:
            # find the most common time delta between points
            deltas = np.diff(ch['points'][:,0])
            unique_deltas, counts = np.unique(deltas, return_counts=True)
            delta = int(unique_deltas[counts == counts.max()][0])
            # round so that delta & frequency are integers
            while 1000 % delta != 0: delta += 1
        # use this delta to get channel frequency (between 1Hz and 1000Hz)
        ch['delta_ms'] = delta
        ch['frequency_hz'] = math.trunc(max(1, min(1000, 1000 / ch['delta_ms'])))
        ch['sample_count'] = math.trunc(ch['t_max'] / ch['delta_ms'])

        # interpolate points from t=0 to t=last
        # ch['v_int'] = np.interp(ch['t_int'], ch['points'][:,0], ch['points'][:,1])

        # print()
        # create a new time axis with this frequency and sample count
        t_int = list(range(ch['sample_count'])) * ch['delta_ms']
        # get closest point to each time tick
        v_int = [0] * ch['sample_count']
        i = 0
        j = 0
        ts = 0
        while j < ch['sample_count']:
            if ch['points'][i][0] == ch['points'][0][0]:
                if ts > ch['points'][i][0]:
                    i += 1
                else:
                    v_int[j] = ch['points'][i][1]
                    # print(ts, ch['points'][i][0], ch['points'][i][1])
                    j += 1
                    ts += ch['delta_ms']
            else:
                while ts > ch['points'][i+1][0]: i += 1
                v_int[j] = ch['points'][i][1]
                # print(ts, ch['points'][i][0], ch['points'][i][1])
                j += 1
                ts += ch['delta_ms']

        ch['t_int'] = np.array(t_int, dtype=np.float64)
        ch['v_int'] = np.array(v_int, dtype=np.float64)
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print('encoding channels... ', end='', flush=True)
    start = time.time()
    for ch in channels.values():
        if ch['v_int'] is None or len(ch['v_int']) == 0:
            ch['v_enc'] = []
        else:
            abs_max = max(ch['v_int'].max(), ch['v_int'].min(), key=abs)
            try:
                ch['shift'], ch['scalar'], ch['divisor'] = get_scalars(abs_max)
            except:
                print(f"failed to encode channel \"{ch['name']}\" ({ch['id']}) abs_max: {abs_max}")
                ch['v_enc'] = []
            else:
                ch['v_enc'] = np.array(
                    [v / 10**-ch['shift'] / ch['scalar'] * ch['divisor'] for v in ch['v_int']],
                    dtype=np.int16
                )
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print(f'created {len(channels)} channels')
    return channels

def plot(ch):
    plt.suptitle(f"{ch['name']} (ID: {ch['id']})")
    plt.title(f"{len(ch['points'])} points")
    plt.xlabel('time (ms)')
    plt.ylabel(ch['unit'])

    plt.plot(ch['points'][:,0], ch['points'][:,1], '.', label='raw')
    plt.plot(ch['t_int'], ch['v_int'], '-', label='interpolated')

    decoded = [v * 10**-ch['shift'] * ch['scalar'] / ch['divisor'] for v in ch['v_enc']]
    plt.plot(ch['t_int'], decoded, '--', label='decoded')

    plt.ticklabel_format(useOffset=False)
    plt.legend(loc='best')
    plt.show()