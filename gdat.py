# .gdat files begin with "/PLM_YYYY-MM-DD-HH-MM-SS.gdat:" (RTC time of file creation)
# followed by a series of packets of the following format (big endian):
# 0    1 2 3 4     5 6   7 n    n+1
# 7E   TIMESTAMP   ID    DATA   CHECKSUM

# 0x7E indicates the start of a packet
# 0x7D indicates that the next byte has been escaped (XORed with 0x20)
# CHECKSUM = sum of bytes ignoring overflow (including start delimiter), calculated on unescaped packet

import time
import yaml
import struct
import random
import numpy as np
from fractions import Fraction
import matplotlib.pyplot as plt

START = bytes.fromhex('7e')
ESC = bytes.fromhex('7d')
MIN_PACKET_LENGTH = 9

random.seed()
start_ms = time.time() * 1000

def get_t0(sof):
    try:
        return time.strptime(sof.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')
    except:
        return time.gmtime(0)
    
def load_parameters(config_path):
    parameters = {}
    types = {
        'UNSIGNED8' : { 'signed': False, 'size': 1, 'format': '>B' },
        'UNSIGNED16' : { 'signed': False, 'size': 2, 'format': '>H' },
        'UNSIGNED32' : { 'signed': False, 'size': 4, 'format': '>I' },
        'UNSIGNED64' : { 'signed': False, 'size': 8, 'format': '>Q' },
        'SIGNED8' : { 'signed': True, 'size': 1, 'format': '>b' },
        'SIGNED16' : { 'signed': True, 'size': 2, 'format': '>h' },
        'SIGNED32' : { 'signed': True, 'size': 4, 'format': '>i' },
        'SIGNED64' : { 'signed': True, 'size': 8, 'format': '>q' },
        'FLOATING' : { 'signed': False, 'size': 4, 'format': '>f' }
    }

    with open(config_path) as f:
        config = yaml.safe_load(f)
        # build a new parameter dictionary
        for p in config['parameters'].values():
            if p['id'] in parameters:
                print(f"WARNING: duplicate id ({p['id']})")
            else:
                type = p.get('type')
                if type is None:
                    print(f'missing type: {p}')
                    continue

                parameters[p['id']] = {
                    'id': p['id'],
                    'name': p.get('motec_name'),
                    'unit': p.get('unit'),
                    'type': type,
                    'size': types[type]['size'],
                    'format': types[type]['format'],
                    'signed': types[type]['signed']
                }
    return parameters

def escape(packet):
    p = START
    for b in packet[1:]:
        if b == int.from_bytes(ESC) or b == int.from_bytes(START):
            # add 7D control byte with escaped byte
            p += ESC
            p += (b ^ 0x20).to_bytes()
        else:
            # add raw byte
            p += (b).to_bytes()
    return p

def unescape(packet):
    p = b''
    i = 0
    while i < len(packet):
        if packet[i] == int.from_bytes(ESC):
            # skip 7D control byte, unescape next byte
            i += 1
            if i >= len(packet): break
            p += (packet[i] ^ 0x20).to_bytes()
        else:
            # add raw byte
            p += packet[i].to_bytes()
        i += 1
    return p

def checksum(packet):
    sum = 0
    for byte in packet[:-1]:
        sum += byte
    return (sum).to_bytes(2)[-1] == packet[-1]

def parse(bytes, parameters):
    print('parsing data...')

    packets = bytes.split(START)
    errors = 0

    channels = {
        id: {
            'id': id,
            'name': param['name'],
            'unit': param['unit'],
            'points': [],
            'raw': {
                't': np.array([]),
                'd': np.array([])
            },
            'interp': {
                't': np.array([]),
                'd': np.array([])
            }
        }
        for (id, param) in parameters.items()
    }

    for p in packets:
        p = unescape(START + p)
        # verify packet size (w/o start delimiter)
        if len(p) < MIN_PACKET_LENGTH - 1:
            # print(f'packet too small: {p}')
            errors += 1
            continue
        # split packet into components
        ts = int.from_bytes(p[1:5])
        id = int.from_bytes(p[5:7])
        data = p[7:-1]
        # verify checksum
        if not checksum(p):
            # print(f'invalid checksum: {p}')
            errors += 1
            continue
        try:
            # decode data using parameter info
            # store all data as floats (double precision in python)
            data = struct.unpack(parameters[id]['format'], data)[0]
            data = float(data)
        except:
            # print(f'failed to decode packet data: '
            #       f"id: {id}, format: {parameters[id]['format']}, data: {data}")
            errors += 1
            continue
        # add to channel
        channels[id]['points'].append((ts, data))

    for id in channels:
        # sort channel data by timestamp
        channels[id]['points'].sort(key=lambda pt: pt[0])
        channels[id]['points'] = np.array(channels[id]['points'])

        if channels[id]['points'].size:
            # points w/ separated axes
            t_old = channels[id]['points'][:,0]
            d_old = channels[id]['points'][:,1]

            channels[id]['raw']['t'] = t_old
            channels[id]['raw']['d'] = d_old

            # linear interpolation - evenly-spaced samples from t=0 to final timestamp
            t_new = np.linspace(0, t_old[-1], num=len(t_old))
            d_new = np.interp(t_new, t_old, d_old)

            channels[id]['interp']['t'] = t_new
            channels[id]['interp']['d'] = d_new

    print(f'parsed {len(bytes)} bytes, {len(packets)} packets, {errors} errors\n')
    return channels

def generate_packet(param):
    ts = int(time.time() * 1000 - start_ms)
    data = random.uniform(-100, 100) if param['type'] == 'FLOATING'\
        else int.from_bytes(random.randbytes(param['size']), signed=param['signed'])
    
    packet = START
    packet += struct.pack('>I', ts)
    packet += struct.pack('>H', param['id'])
    packet += struct.pack(param['format'], data)

    checksum = 0
    for b in packet: checksum += b
    packet += (checksum).to_bytes(2)[-1:]

    return packet

def generate_data(parameters, nbytes):
    b = b''
    while len(b) < nbytes:
        param = random.choice(list(parameters.values()))
        packet = generate_packet(param)
        b += escape(packet)
    return b

# find shift, scalar, and divisor to fit value in a s16 [-2^15, 2^15 - 1]
# value = encoded_value * 10^-shift * scalar / divisor
# encoded_value = value / 10^-shift / scalar * divisor
# to make the most of a s16: abs_max = (2^15 - 1) * 10^-shift * scalar / divisor
# keep shift high to preserve precision
def get_scalars(ch):
    abs_max = max(ch['interp']['d'].max(), ch['interp']['d'].min(), key=abs)
    # print(f"abs_max: {abs_max} index: {ch['interp']['d'].tolist().index(abs_max)}\n")
    encodable = False

    if abs_max == 0:
        encodable = True
        shift = 0
        scalar = 1
        divisor = 1
        return (encodable, shift, scalar, divisor)

    for shift in range(10, -10, -1):
        # calculate required scale to use this shift
        scale = abs_max / (2**15-1) / 10**-shift
        # convert scale to integer fraction
        scalar, divisor = Fraction(scale).limit_denominator(2**15-1).as_integer_ratio()
        # print(f'\nshift: {shift} scale: {scale} scalar: {scalar} divisor: {divisor}')
        if scalar == 0:
            continue
        elif -2**15 <= scalar <= 2**15-1:
            # both scalar & divisor will fit in s16
            encodable = True
            break
        else:
            # adjust scalar to fit in s16 (adjust divisor too to maintain fraction)
            adj = (2**15-1) / scalar
            scalar = round(scalar * adj)
            divisor = round(divisor * adj)
            # check if divisor is still valid
            if -2**15 <= divisor <= 2**15-1 and divisor != 0:
                # max encoded value
                enc_max = abs_max / 10**-shift / scalar * divisor
                # % error with this new fraction to the ideal scale
                error = ((scalar / divisor) - scale) / scale
                # print(f'new_scale: {scalar / divisor} scalar: {scalar} divisor: {divisor} error: {error} enc_max: {enc_max}')
                # 10% error is acceptable if encoded value fits
                if enc_max <= 2**15-1 and error <= 0.1:
                    encodable = True
                    break
    return (encodable, shift, scalar, divisor)

def plot_channel(ch):
    plt.plot(ch['raw']['t'], ch['raw']['d'], '.', label='data')
    plt.plot(ch['interp']['t'], ch['interp']['d'], '-', label='interpolation')

    (encodable, shift, scalar, divisor) = get_scalars(ch)

    if not encodable:
        print(f"failed to encode channel ({ch['id']} {ch['name']})")
    else:
        # print(f'shift: {shift} scalar: {scalar} divisor: {divisor}')
        encoded = np.array([x / 10**-shift / scalar * divisor for x in ch['interp']['d']], dtype=np.int16)
        decoded = [x * 10**-shift * scalar / divisor for x in encoded]
        plt.plot(ch['interp']['t'], decoded, '--', label='decoded')

    plt.ticklabel_format(useOffset=False)
    plt.legend(loc='best')
    plt.show()