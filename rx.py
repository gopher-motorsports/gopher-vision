import serial
import time
import go4v
from pathlib import Path
from datetime import datetime

PORT = "COM7"
BAUD = 230400

BLOCK_SIZE = 1000 # bytes to read in each update
SAMPLE_SIZE = 5000 # bytes to read before calculating stats
TIMEOUT = 1 # seconds to wait for desired block size

SAVE_HISTORY = False # saves all data received to a .gdat log file
HISTORY_SIZE = 100000 # bytes to save before flushing to log file

port = serial.Serial(PORT, BAUD, timeout=TIMEOUT)

# latest value and corresponding timestamp for each parameter
values = {id: {'time': time.time(), 'data': 0} for id in go4v.parameters}

stats = {
    'packets': 0, # packets received
    'throughput': 0, # bytes read and parsed in the last sample (bytes/second)
    'error_rate': 0 # ratio of invalid to good packets in the last sample (%)
}

sample = {
    'start': time.time(),
    'bytes': 0,
    'packets': 0,
    'errors': 0,
}

# create history file
today = datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
history_path = Path(f'./rx_{today}.gdat')
if SAVE_HISTORY:
    with open(history_path, 'wb') as f:
        # write metadata filename header
        f.write(bytes(f'/{history_path}:\r\n', 'utf-8'))

def save_history(history):
    with open(history_path, 'ab') as f:
        f.write(history)

def rx():
    history = b''
    buffer = b''
    print('Listening for data...')
    while True:
        data = port.read(BLOCK_SIZE)
        history += data
        buffer += data

        # update statistics when sample is complete
        sample['bytes'] += len(data)
        if sample['bytes'] >= SAMPLE_SIZE:
            elapsed = time.time() - sample['start']
            stats['throughput'] = sample['bytes'] / elapsed if elapsed else float('inf')
            stats['error_rate'] = (sample['errors'] / sample['packets']) * 100

            sample['bytes'] = 0
            sample['packets'] = 0
            sample['errors'] = 0
            sample['start'] = time.time()

        # log history
        if SAVE_HISTORY and len(history) >= HISTORY_SIZE:
            save_history(history)
            history = b''

        packets = go4v.split(buffer)
        if not packets: continue

        # leave the last packet in the buffer to prevent truncation
        buffer = packets[-1]

        # parse packets
        for packet in packets[:-1]:
            stats['packets'] += 1
            sample['packets'] += 1
            packet = go4v.unescape(packet)
            packet = go4v.parse(packet)
            if packet['valid']:
                values[packet['id']]['time'] = packet['rx_time']
                values[packet['id']]['data'] = packet['data']
            else:
                sample['errors'] += 1

if __name__ == "__main__":
    rx()