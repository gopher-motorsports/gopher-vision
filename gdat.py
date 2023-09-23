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
import bisect

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
                parameters[p['id']] = {
                    'id': p['id'],
                    'name': p['motec_name'],
                    'unit': p['unit'],
                    'type': p['type'],
                    'size': types[p['type']]['size'],
                    'format': types[p['type']]['format'],
                    'signed': types[p['type']]['signed']
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
            'type': param['type'],
            'points': []
        }
        for (id, param) in parameters.items()
    }

    for p in packets:
        p = unescape(START + p)
        # verify packet size (w/o start delimiter)
        if len(p) < MIN_PACKET_LENGTH - 1:
            print(f'packet too small: {p}')
            errors += 1
            continue
        # split packet into components
        ts = int.from_bytes(p[1:5])
        id = int.from_bytes(p[5:7])
        data = p[7:-1]
        # verify checksum
        if not checksum(p):
            print(f'invalid checksum: {p}')
            errors += 1
            continue
        # decode data using parameter info
        try:
            data = struct.unpack(parameters[id]['format'], data)[0]
        except:
            print(f'failed to decode packet data: {p}')
            errors += 1
            continue
        # add to channel
        channels[id]['points'].append((ts, data))

    # sort channel data by timestamp
    for id in channels:
        channels[id]['points'].sort(key=lambda pt: pt[0])

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