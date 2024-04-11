import sys
import serial
import struct

# python rx.py [PORT]
# e.g. python rx.py COM4
# e.g. python rx.py /dev/tty.usbserial-X
# opens a serial port, expecting to receive .gdat packets
# splits packet components and prints to terminal

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

PORT = sys.argv[1]
BAUD = 230400

BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

port = serial.Serial(PORT, BAUD, timeout=TIMEOUT)

print(f'listening on port "{PORT}"...')
while True:
    bytes = port.read(BLOCK_SIZE)
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
            value = pkt[6:-1]
        except:
            continue
        # validate checksum
        sum = START
        for b in pkt[:-1]: sum += b
        if sum.to_bytes(2, 'big')[-1] != pkt[-1]:
            continue
        # print packet info
        print(f'ts={ts} id={id} data={value.hex()}')