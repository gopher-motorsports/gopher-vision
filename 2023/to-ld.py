import sys
from pathlib import Path
import time
import bisect
import statistics
import go4v

if len(sys.argv) < 2:
    sys.exit('ERROR: expected "python to-ld.py data.gdat"')

ipath = Path(sys.argv[1])
opath = Path(f'{ipath.stem}.ld')

(filename, extension, data) = ipath.read_bytes().partition(b'.gdat:')
print(f'Read {len(data)} bytes from {ipath.name}')

metadata = {
    'year': 0,
    'month': 0,
    'day': 0,
    'hour': 0,
    'minute': 0,
    'second': 0,
    'venue': '',
    'event': '',
    'session': '',
    'short_comment': '',
    'long_comment': ''
}

try:
    t = time.strptime(filename.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')
except:
    sys.exit('ERROR: failed to parse metadata')
else:
    print(f'Found metadata: {time.asctime(t)}')
    metadata['year'] = t.tm_year
    metadata['month'] = t.tm_mon
    metadata['day'] = t.tm_mday
    metadata['hour'] = t.tm_hour
    metadata['minute'] = t.tm_min
    metadata['second'] = t.tm_sec

print('Please enter additional information:')
metadata['venue'] = input('Venue: ')
metadata['event'] = input('Event: ')
metadata['session'] = input('Session: ')
metadata['short_comment'] = input('Short Comment: ')
metadata['long_comment'] = input('Long Comment: ')

print('Parsing packets...')

# organize packet data into channels
channels = {id: {'points': [], 'name': param['name'], 'name_short': f'gcan{id}', 'unit': param['unit']}\
            for (id, param) in go4v.parameters.items()}

num_packets = 0
num_errors = 0
for p in go4v.split(data):
    packet = go4v.parse(go4v.unescape(p))
    num_packets += 1
    if packet['valid']:
        # insert datapoint maintaining sorted order by timestamp
        datapoint = {'t': packet['timestamp'], 'd': packet['data']}
        bisect.insort(channels[packet['id']]['points'], datapoint, key=lambda point: point['t'])
    else:
        num_errors += 1

for ch in channels:
    # datapoint extrema
    min_d = min(ch['points'], key=lambda point: point['d'])['d']
    max_d = max(ch['points'], key=lambda point: point['d'])['d']
    max_t = ch['points'][-1]['t']
    # calculate delta between timestamps
    # delta[0] = time[1] - time[0]
    deltas = [j['t'] - i['t'] for i, j in zip(ch['points'][:-1], ch['points'][1:])]
    # find most common time delta
    delta_t = statistics.mode(deltas)
    # round to nearest 1000ms
    delta_t_ms = 1000 * round(delta_t / 1000)
    # frequency clamped to 0-1000Hz
    freq_hz = max(min(1000 / delta_t_ms, 1000), 1)

    # TODO finish .ld conversion adapted from the C data parser

print(f'Error rate: {round(num_errors / num_packets, 5)}%')
