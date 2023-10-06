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
    print('decoding packets... ', end='', flush=True)
    start = time.time()
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
        
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')
    print(f'{packets} packets, {errors} errors')

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
            # scalars to encode in s16
            'shift': 0,
            'scalar': 0,
            'divisor': 0,
            'offset': 0,
            # data
            'sample_rate': 0,
            'points': [],
            't_int': None, # interpolated timestamps
            'v_int': None, # interpolated values
            'v_enc': None, # encoded values
        }
        for (id, param) in parameters.items()
    }

    # add datapoints to channels
    decode_packets(bytes, channels, parameters)

    print('sorting data... ', end='', flush=True)
    start = time.time()
    for ch in channels.values():
        if len(ch['points']):
            # sort points by timestamp
            ch['points'].sort(key=lambda pt: pt[0])
            ch['points'] = np.array(ch['points'], dtype=np.float64)
            # timestamps = ch['points'][:,0]
            # values     = ch['points'][:,1]
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print('interpolating data... ', end='', flush=True)
    start = time.time()
    for ch in channels.values():
        if len(ch['points']):
            # interpolate points from t=0 to t=last for evenly-spaced samples
            ch['t_int'] = np.linspace(0, ch['points'][:,0][-1], num=len(ch['points']))
            ch['v_int'] = np.interp(ch['t_int'], ch['points'][:,0], ch['points'][:,1])
            ch['sample_rate'] = round(len(ch['v_int']) / (ch['t_int'][-1] / 1000))
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')

    print(f'created {len(channels)} channels')
    return channels

def encode_channel(ch):
    if ch['v_enc'] is None:
        if ch['v_int'] is None:
            ch['v_enc'] = []
        else:
            abs_max = max(ch['v_int'].max(), ch['v_int'].min(), key=abs)
            ch['shift'], ch['scalar'], ch['divisor'] = get_scalars(abs_max)
            ch['v_enc'] = np.array(
                [v / 10**-ch['shift'] / ch['scalar'] * ch['divisor'] for v in ch['v_int']],
                dtype=np.int16
            )

def plot(ch):
    plt.suptitle(f"{ch['name']} (ID: {ch['id']})")
    plt.title(f"{len(ch['points'])} points")
    plt.xlabel('time (ms)')
    plt.ylabel(ch['unit'])

    plt.plot(ch['points'][:,0], ch['points'][:,1], '.', label='raw')
    plt.plot(ch['t_int'], ch['v_int'], '-', label='interpolated')

    encode_channel(ch)
    decoded = [v * 10**-ch['shift'] * ch['scalar'] / ch['divisor'] for v in ch['v_enc']]
    plt.plot(ch['t_int'], decoded, '--', label='decoded')

    plt.ticklabel_format(useOffset=False)
    plt.legend(loc='best')
    plt.show()