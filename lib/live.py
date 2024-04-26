import socket
import serial
import time
import struct
import threading

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

BAUD = 230400
BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

class Receiver:
    def __init__(self):
        self.rx_thread = threading.Thread(target=self.run, daemon=True)
        self.port = None
        self.parameters = {} # parameter dictionary loaded from a GopherCAN config
        self.values = {} # latest value of each parameter

    def run(self):
        while True:
            # attempt to read a block of data from port
            try:
                if type(self.port) == socket.socket:
                    bytes = self.port.recv(BLOCK_SIZE)
                elif type(self.port) == serial.Serial:
                    bytes = self.port.read(BLOCK_SIZE)
                else:
                    raise Exception()
            except:
                time.sleep(1)
                continue

            if len(self.parameters) == 0:
                # no parameters to parse data with
                time.sleep(1)
                continue

            # split block into packets and update channels
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
                    timestamp, id = struct.unpack('>IH', pkt[0:6])
                    value = struct.unpack(self.parameters[id]['format'], pkt[6:-1])[0]
                except:
                    continue
                # validate checksum
                sum = START
                for b in pkt[:-1]: sum += b
                if sum.to_bytes(2, 'big')[-1] != pkt[-1]:
                    continue
                # update latest value
                self.values[id] = value

    def start(self):
        self.rx_thread.start()

    def set_parameters(self, parameters: dict):
        self.parameters = parameters
        self.values = {
            id: 0
            for id in parameters.keys()
        }

    def clear_parameters(self):
        self.parameters = {}
        self.values = {}

    def open_serial_port(self, name):
        try:
            # open a serial port
            self.port = serial.Serial(name, BAUD, timeout=TIMEOUT)
            print(f'opened port: {name}')
        except:
            self.close_port()
            print(f'ERROR: failed to open serial port "{name}"')
            raise

    def open_socket(self, port_num):
        try:
            # open a UDP socket on localhost
            self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port.bind(('127.0.0.1', int(port_num)))
            print(f'opened port: 127.0.0.1:{port_num}')
        except:
            self.close_port()
            print(f'ERROR: failed to open socket on port "{port_num}"')
            raise

    def close_port(self):
        if self.port != None:
            self.port.close()
            self.port = None