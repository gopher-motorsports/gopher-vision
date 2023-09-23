import sys
from pathlib import Path
import time
from gdat import get_t0, parse

if len(sys.argv) != 2:
    raise Exception('expected "python parse-gdat.py path/to/data.gdat"')

ipath = Path(sys.argv[1])

if not ipath.is_file():
    raise Exception(f'"{ipath}" does not exist')

if ipath.suffix != '.gdat':
    raise Exception('expected a path to a .gdat file')

print(f'opening "{ipath}" ...')
(sof, ext, data) = ipath.read_bytes().partition(b'.gdat:')
print(f'read {len(data)} bytes of data')

t0 = get_t0(sof)
print(f"t0: {time.strftime('%m/%d/%Y %H:%M:%S', t0)}\n")

print('splitting packets...')
packets = parse(data)