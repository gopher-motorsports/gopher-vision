import sys
from pathlib import Path
import csv
import go4v

if len(sys.argv) < 3:
    sys.exit('ERROR: expected "python to-csv.py input.gdat output.csv"')

ipath = Path(sys.argv[1])
opath = Path(sys.argv[2])

(filename, extension, data) = ipath.read_bytes().partition(b'.gdat:')
print(f'Read {len(data)} bytes from {ipath.name}')
print(f'METADATA: "{(filename + extension).decode()}"')

print('Parsing packets...')
packets = [go4v.parse(go4v.unescape(p)) for p in go4v.split(data)]
errors = sum(not p['valid'] for p in packets)

print(f'ERROR RATE: {round(errors / len(packets), 5)}%')

with open(opath, 'w', newline='') as ofile:
    writer = csv.DictWriter(ofile, fieldnames=['hex', 'timestamp', 'id', 'data', 'valid'])
    writer.writeheader()
    writer.writerows(packets)

print(f'Wrote {len(packets)} packets to {opath.name}')