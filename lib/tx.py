import sys
import serial
import struct
from pathlib import Path
import time
import random
import socket

sys.path.append('../')
import gcan
sys.path.pop()

# python tx.py [PORT] [CONFIG_NAME]
# e.g. python tx.py COM4 go4-24c.yaml
# e.g. python tx.py /dev/tty.usbserial-X go4-24c.yaml
# e.g. python tx.py 5000 go4-24c.yaml
# generates random data values for parameters in the provided GopherCAN configuration
# creates .gdat packets and sends them to the specified serial or network port
# useful for simulating a telemetry module

if len(sys.argv) != 3:
    print('invalid arguments, expected "python tx.py [PORT] [CONFIG_NAME]"')
    exit()

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

PORT = sys.argv[1]
BAUD = 230400

CONFIG_NAME = sys.argv[2]

BLOCK_SIZE = 1000 # bytes to send at a time
DELAY = 0.1 # seconds to wait between blocks

PORT_TYPE = ''
try:
    # attempt to open a network socket on localhost
    port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
    int(PORT) # checks that the supplied port is an integer
    PORT_TYPE = 'socket'
except:
    try:
        # attempt to open a serial port
        port = serial.Serial(PORT, BAUD, timeout=0)
        PORT_TYPE = 'serial'
    except:
        print(f'ERROR: unrecognized port "{PORT}"')
        exit()

try:
    config_path = CONFIG_NAME
    config = gcan.load_path(config_path)
except:
    print(f'ERROR: no config found at "{config_path}"')
    exit()

parameters = gcan.get_params(config)
pids = list(parameters.keys())
start = time.time()

# generate a gdat packet with random data for the specified parameter ID
def generate_packet():
    id = int(random.choice(pids))
    timestamp = int((time.time() - start) * 1000)

    if parameters[id]['type'] == 'FLOATING':
        data = random.uniform(-100, 100)
    else:
        if parameters[id]['signed']:
            min = -(2 ^ ((parameters[id]['size'] * 8) - 1))
            max = 2 ^ ((parameters[id]['size'] * 8) - 1) - 1
        else:
            min = 0
            max = 2 ^ (parameters[id]['size'] * 8) - 1
        data = random.randint(min, max)

    packet = START.to_bytes(1, 'big') + struct.pack('>I', timestamp) + struct.pack('>H', id) + struct.pack(parameters[id]['format'], data)
    checksum = 0
    for b in packet:
        checksum += b
    packet += (checksum).to_bytes(2, 'big')[-1:]
    return packet

print(f'transmitting on port "{PORT}"...')
while True:
    bytes_written = 0
    while bytes_written < BLOCK_SIZE:
        packet = generate_packet()
        pkt = START.to_bytes(1, 'big')
        # escape packet
        for b in packet[1:]:
            if b == ESC or b == START:
                # add 7D control byte with escaped byte
                pkt += ESC.to_bytes(1, 'big')
                pkt += (b ^ 0x20).to_bytes(1, 'big')
            else:
                # add raw byte
                pkt += (b).to_bytes(1, 'big')
        # transmit packet
        if PORT_TYPE == 'serial':
            n = port.write(pkt)
        elif PORT_TYPE == 'socket':
            n = port.sendto(pkt, ('127.0.0.1', int(PORT)))
        bytes_written += n

    time.sleep(DELAY)