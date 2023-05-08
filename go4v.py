# PACKET FORMAT:
# 0    1 2 3 4     5 6   7 n    n+1
# 7E   TIMESTAMP   ID    DATA   CHECKSUM

# 0x7E indicates the start of a packet
# 0x7D indicates that the next byte has been escaped (XORed with 0x20)
# CHECKSUM = sum of bytes ignoring overflow (including start delimiter), calculated on unescaped packet

from pathlib import Path
import sys
import yaml
import struct
import time
import random

START = bytes.fromhex('7e')
ESC = bytes.fromhex('7d')
CONFIG = 'go4-23c.yaml'

random.seed()
start_ms = time.time() * 1000

config_path = Path(f'../gophercan-lib/network_autogen/configs/{CONFIG}').resolve()
if not Path(config_path).exists():
    print(f'(ERROR) invalid GCAN configuration path: {config_path}')
    sys.exit()

print(f'Loading {config_path.name}...')
parameters = {}
with open(config_path) as file:
    # rebuild parameter dictionary with IDs as keys
    config = yaml.safe_load(file)
    for name, param in config['parameters'].items():
        # check for duplicate ID
        if param['id'] in parameters:
            print(f"(ERROR) \"{name}\" has the same ID as \"{parameters[param['id']]['name']}\"")
        else:
            parameters[param['id']] = param
            parameters[param['id']]['name'] = name

# formats are used in struct.unpack() to convert parameter data
# min/max are used for generating packets
ptypes = {
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

def escape(packet):
    '''Escapes a packet'''
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
    '''Unescapes a packet'''
    p = b''
    i = 0
    while i < len(packet):
        if packet[i] == int.from_bytes(ESC):
            # skip 7D control byte, unescape next byte
            i += 1
            p += (packet[i] ^ 0x20).to_bytes()
        else:
            # add raw byte
            p += packet[i].to_bytes()
        i += 1
    return p

def is_valid(packet):
    '''Verifies packet checksum

    packet: unescaped bytes object
    RETURNS: boolean
    '''
    sum = 0
    for byte in packet[:-1]:
        sum += byte
    return (sum).to_bytes(2)[-1] == packet[-1]

def parse(packet):
    '''Verifies packet integrity and parses components
    
    packet: unescaped bytes object
    RETURNS: a dictionary of packet info
    '''
    valid = is_valid(packet)

    # extract packet components
    timestamp = int.from_bytes(packet[1:5])
    id = int.from_bytes(packet[5:7])
    data = packet[7:-1]

    # convert data based on parameter type
    if id in parameters:
        type = parameters[id]['type']
        if type in ptypes:
            if len(data) == ptypes[type]['size']:
                data = struct.unpack(ptypes[type]['format'], data)[0]
            else: valid = False
        else: valid = False
    else: valid = False

    return {
        'hex': packet.hex(),
        'timestamp': timestamp,
        'id': id,
        'data': data,
        'valid': valid
    }

def generate_packet(id):
    '''Generates a packet with random data for the specififed parameter
    
    RETURNS: unescaped packet
    '''
    param_type = parameters[id]['type']
    timestamp = int(time.time() * 1000 - start_ms)
    data = random.uniform(0, 100) if param_type == 'FLOATING' else int.from_bytes(random.randbytes(ptypes[param_type]['size']), signed=ptypes[param_type]['signed'])

    timestamp = struct.pack(ptypes['UNSIGNED32']['format'], timestamp)
    id = struct.pack(ptypes['UNSIGNED16']['format'], id)
    data = struct.pack(ptypes[param_type]['format'], data)

    packet = START + timestamp + id + data
    checksum = 0
    for b in packet: checksum += b
    packet += (checksum).to_bytes(2)[-1:]
    return packet

def generate_data(ids, num_bytes):
    '''Generates a string of random packets with any of the specified ids
    
    ids: possible parameter ids
    num_bytes: # bytes to generate
    RETURNS: a bytes object of escaped packets
    '''
    b = b''
    while len(b) < num_bytes:
        id = int(random.choice(ids))
        packet = generate_packet(id)
        b += escape(packet)
    return b

def split(bytes):
    '''Splits a bytes object into packets
    
    RETURNS: a list of escaped packets
    '''
    packets = [START + pkt for pkt in bytes.split(START) if pkt]
    return packets