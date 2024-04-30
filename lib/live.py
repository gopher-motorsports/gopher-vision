import threading
import socket
import serial
import time
import struct

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

BAUD = 230400
BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

# Port is a wrapper for either a serial port or network socket
# this allows a Node to receive and transmit data using a common interface
class Port:
    def __init__(self):
        self.port = None

    def read(self, size: int) -> bytes:
        if type(self.port) == socket.socket:
            return self.port.recv(size)
        elif type(self.port) == serial.Serial:
            return self.port.read(size)
        else:
            raise Exception('ERROR: unknown port type')

    def write_serial(self, data: bytes) -> int:
        if type(self.port) == serial.Serial:
            return self.port.write(data)
        else:
            raise Exception('ERROR: serial port not open')

    def send_to(self, data: bytes, host: str, port: int) -> int:
        if type(self.port) == socket.socket:
            return self.port.sendto(data, (host, int(port)))
        else:
            raise Exception('ERROR: socket not open')

    def open_serial(self, name: str, baud: int, timeout: int):
        try:
            self.port = serial.Serial(name, baud, timeout=timeout)
            print(f'opened port: {name}')
        except:
            print(f'ERROR: failed to open serial port "{name}"')
            self.close()
            raise

    # creates a UDP socket without binding to a port
    # used when sending data via send_to()
    def open_socket(self):
        self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # bind a UDP socket to the specified host:port
    def bind_socket(self, host: str = '127.0.0.1', port: int = 5000):
        try:
            self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.port.bind((host, int(port)))
            print(f'opened port: {host}:{port}')
        except:
            print(f'ERROR: failed to open socket on "{host}:{port}"')
            self.close()
            raise

    def close(self):
        if self.port != None:
            self.port.close()
            self.port = None

# a GopherVision Node receives .gdat packets from a Port
# and updates a dictionary of each parameter's most recent value
# Nodes can optionally forward received data to a set of client addresses (host:port)
class Node:
    def __init__(self):
        self.parameters = {}
        self.values = {}
        self.rx_port = Port()
        self.tx_port = Port()
        self.clients: list[tuple[str, int]] = []
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            if len(self.parameters) == 0:
                # no parameters to parse data with
                time.sleep(1)
                continue

            # attempt to read a block of data
            try:
                bytes = self.rx_port.read(BLOCK_SIZE)
            except:
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

            # forward to clients
            for host, port in self.clients:
                try:
                    self.tx_port.send_to(bytes, host, port)
                except:
                    continue

    def set_parameters(self, parameters: dict):
        self.parameters = parameters
        self.values = {
            id: 0
            for id in parameters.keys()
        }

    def add_client(self, host: str, port: int):
        if (host, port) not in self.clients:
            self.clients.append((host, port))

    def remove_client(self, host: str, port: int):
        self.clients = list(filter(lambda addr: addr != (host, port), self.clients))