import sys
import serial
import struct
import socket
from pathlib import Path

sys.path.append('../')
from lib import gcan
sys.path.pop()

# python rx.py [PORT] [CONFIG_NAME]
# PORT can either be a serial port name or a localhost port number
# e.g. python rx.py COM4 go4-24c.yaml
# e.g. python rx.py /dev/tty.usbserial-X go4-24c.yaml
# e.g. python rx.py 5000 go4-24c.yaml
# opens the specified serial or network port, expecting to receive .gdat packets
# parses packets using the provided GopherCAN config and prints to the terminal

if len(sys.argv) != 3:
    print('invalid arguments, expected "python rx.py [PORT] [CONFIG_NAME]"')
    exit()

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

PORT = sys.argv[1]
BAUD = 230400

CONFIG_NAME = sys.argv[2]

BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

PORT_TYPE = ''
try:
    # attempt to open a network socket on localhost
    port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
    port.bind(('127.0.0.1', int(PORT)))
    PORT_TYPE = 'socket'
except:
    try:
        # attempt to open a serial port
        port = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
        PORT_TYPE = 'serial'
    except:
        print(f'ERROR: unrecognized port "{PORT}"')
        exit()

try:
    config_path = Path('../../gophercan-lib/network_autogen/configs/') / CONFIG_NAME
    config = gcan.load_path(config_path)
except:
    print(f'ERROR: no config found at "{config_path}"')
    exit()

parameters = gcan.get_params(config)
pids = list(parameters.keys())

print(f'listening on port "{PORT}"...')
while True:
    if PORT_TYPE == 'serial':
        bytes = port.read(BLOCK_SIZE)
    elif PORT_TYPE == 'socket':
        bytes = port.recv(BLOCK_SIZE)

    packets = bytes.split(START.to_bytes(1, 'big'))
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
            # print(f'failed to decode: {packet}')
            continue
        # validate checksum
        sum = START
        for b in pkt[:-1]: sum += b
        if sum.to_bytes(2, 'big')[-1] != pkt[-1]:
            # print(f'invalid checksum: {packet}')
            continue
        # print packet info
        print(f'timestamp={ts} id={id} data={value}')