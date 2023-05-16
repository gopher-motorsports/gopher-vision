import serial
import time
import go4v

PORT = "COM7"
BAUD = 230400
BLOCK_SIZE = 1000 # bytes to read in each update
SAMPLE_SIZE = 5000 # bytes to read before calculating stats
TIMEOUT = 1 # seconds to wait for desired block size

port = serial.Serial(PORT, BAUD, timeout=TIMEOUT)

# latest value and corresponding timestamp for each parameter
values = {id: {'timestamp': 0, 'data': 0} for id in go4v.parameters}

stats = {
    'throughput': 0, # bytes read and parsed in the last sample (bytes/second)
    'latency': 0, # (ms)
    'error_rate': 0 # ratio of invalid to good packets in the last sample (%)
}

sample = {
    'start': time.time(),
    'bytes': 0,
    'packets': 0,
    'errors': 0,
}

def rx():
    buffer = b''
    print('Listening for data...')
    while True:
        data = port.read(BLOCK_SIZE)
        buffer += data

        # update statistics when sample is complete
        sample['bytes'] += len(data)
        if sample['bytes'] >= SAMPLE_SIZE:
            stats['throughput'] = sample['bytes'] / (time.time() - sample['start'])
            stats['error_rate'] = (sample['errors'] / sample['packets']) * 100

            sample['bytes'] = 0
            sample['packets'] = 0
            sample['errors'] = 0
            sample['start'] = time.time()

        packets = go4v.split(buffer)
        if not packets: continue

        # leave the last packet in the buffer to prevent truncation
        buffer = packets[-1]

        # parse packets
        for packet in packets[:-1]:
            sample['packets'] += 1
            packet = go4v.unescape(packet)
            packet = go4v.parse(packet)
            if packet['valid']:
                values[packet['id']]['timestamp'] = packet['timestamp']
                values[packet['id']]['data'] = packet['data']
            else:
                sample['errors'] += 1

if __name__ == "__main__":
    rx()