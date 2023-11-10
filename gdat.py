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
ESC_XOR = 0x20

random.seed()
start_ms = time.time() * 1000

def get_t0(sof):
    try:
        return time.strptime(sof.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')
    except:
        print(f'failed to parse timestamp "{sof.decode()}"')
        return time.gmtime(0)

# decode packets from a byte string and organize into channels
def parse(bytes, parameters):
    channels = {
        id: {
            'id': id,
            'name': param['name'],
            'unit': param['unit'],
            # raw data
            'n_points': 0,         # num raw datapoints
            'points': [],
            't_min': 0,            # min timestamp
            't_max': 0,            # max timestamp
            'v_min': 0,            # min value
            'v_max': 0,            # max value
            # interpolated data
            'delta_ms': 0,
            'frequency_hz': 0,
            'sample_count': 0,     # num interpolated datapoints
            't_int': [],           # evenly spaced timestamps
            'v_int': [],           # interpolated values
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
    n_errors = 0
    # split byte string by start delimiter
    packets = bytes.split(START.to_bytes())
    for packet in packets:
        # unescape packet
        pkt = bytearray()
        esc = False
        for b in packet:
            if b == ESC:
                esc = True
            elif esc:
                pkt.append(b ^ ESC_XOR)
                esc = False
            else:
                pkt.append(b)
        # unpack components
        try:
            ts, id = struct.unpack('>IH', pkt[0:6])
            value = struct.unpack(parameters[id]['format'], pkt[6:-1])[0]
        except:
            n_errors += 1
            continue
        # validate checksum
        sum = START
        for b in pkt[:-1]: sum += b
        if sum.to_bytes(2)[-1] != pkt[-1]:
            n_errors += 1
            continue
        # at this point, packet is valid, add to channel
        channels[id]['points'].append((ts, value))
    elapsed = round(time.time() - start, 2)
    print(f'({elapsed}s)')
    print(f'{len(packets)} packets, {n_errors} errors')

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
        abs_max = max(abs(ch['v_min']), abs(ch['v_max']))

        # find shift, scalar, and divisor to fit value in a s32
        # encoded_value = value / 10^-shift / scalar * divisor
        if abs_max == 0:
            ch['shift'], ch['scalar'], ch['divisor'] = (12, 1, 1)
        else:
            # find the closest value of 8*10^x to abs_max
            x = math.floor(math.log10(abs_max / 8))
            # limit to x >= -6 (max shift of 12)
            # lower abs_max -> lower x (higher shift), limit prevents encoded values from overflowing
            x = max(x, -6)
            # find scale to map abs_max to 8*10^x
            scale = (8 * 10**x) / abs_max
            # find shift to map abs_max to 8*10^6
            shift = 6 - x
            # float scale -> fraction, limit scalar & divisor to 12 bits (required by .ld format)
            # idk why but mapping to 8*10^x causes fewer fraction failures than 10^x
            scalar, divisor = Fraction(scale).limit_denominator(0x7FF).as_integer_ratio()
            if scalar > 0x7FF:
                # encoding failed, remove channel
                print(f'failed to encode channel: {ch['name']} ({id}) abs_max={abs_max}')
                del channels[id]
                continue
            
            ch['shift'], ch['scalar'], ch['divisor'] = (shift, scalar, divisor)

        # encode values
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