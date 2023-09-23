# .gdat files begin with "/PLM_YYYY-MM-DD-HH-MM-SS.gdat:" (RTC time of file creation)
# followed by a series of packets of the following format:
# 0    1 2 3 4     5 6   7 n    n+1
# 7E   TIMESTAMP   ID    DATA   CHECKSUM
# each component is big endian

# 0x7E indicates the start of a packet
# 0x7D indicates that the next byte has been escaped (XORed with 0x20)
# CHECKSUM = sum of bytes ignoring overflow (including start delimiter), calculated on unescaped packet

import time

START = bytes.fromhex('7e')
ESC = bytes.fromhex('7d')

def get_t0(sof):
    try:
        return time.strptime(sof.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')
    except:
        return time.gmtime(0)

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

def parse(bytes):
    # split byte string by start delimiter
    packets = [unescape(START + p) for p in bytes.split(START) if p]

    # split packets into components
    packets = [{
        'valid': checksum(p),
        'timestamp': int.from_bytes(p[1:5]),
        'id': int.from_bytes(p[5:7]),
        'data': p[7:-1]
    } for p in packets]

    return packets