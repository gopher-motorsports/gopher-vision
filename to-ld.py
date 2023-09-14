import sys
from pathlib import Path

# check arguments
if len(sys.argv) != 3:
    raise Exception('expected "python to-ld.py path/to/input.gdat path/to/output.ld"')

ipath = Path(sys.argv[1])
opath = Path(sys.argv[2])

if not ipath.is_file():
    raise Exception(f'"{ipath}" does not exist')

if ipath.suffix != '.gdat':
    raise Exception('expected an input path to a .gdat file')

if opath.is_file():
    raise Exception(f'"{opath}" already exists')

if opath.suffix != '.ld':
    raise Exception('expected an output path to a .ld file')

# form data channels
print(f'parsing "{ipath}" ...')