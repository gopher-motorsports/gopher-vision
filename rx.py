import serial
import time
import go4v

PORT = "COM7"
BAUD = 230400
BLOCK_SIZE = 1000 # bytes to read in each update
SAMPLE_SIZE = 10 # sample size in blocks
TIMEOUT = 1 # seconds to wait for desired block size

port = serial.Serial(PORT, BAUD, timeout=TIMEOUT)

# statistics for most recent sample
stats = {
    'throughput': 0, # bytes/second
    'error_rate': 0 # % ratio of invalid to good packets
}

sample = {
    'start': time.time(),
    'bytes': 0,
    'packets': 0,
    'errors': 0,
}

print('Listening for data...')
buffer = b''
while True:
    data = port.read(BLOCK_SIZE)
    buffer += data
    sample['bytes'] += len(data)

    # update statistics when sample is complete
    if sample['bytes'] >= SAMPLE_SIZE * BLOCK_SIZE:
        stats['throughput'] = sample['bytes'] / (time.time() - sample['start'])
        stats['error_rate'] = (sample['errors'] / sample['packets']) * 100

        sample['bytes'] = 0
        sample['packets'] = 0
        sample['errors'] = 0
        sample['start'] = time.time()

        print(stats)

    packets = go4v.split(buffer)
    if not packets: continue

    # leave the last packet in the buffer to prevent truncation
    buffer = packets[-1]

    # parse packets
    for packet in packets[:-1]:
        sample['packets'] += 1
        packet = go4v.unescape(packet)
        packet = go4v.parse(packet)
        if not packet['valid']:
            sample['errors'] += 1
