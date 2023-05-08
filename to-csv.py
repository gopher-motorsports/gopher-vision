import sys
from pathlib import Path
import go4v

ipath = Path(sys.argv[1])
opath = Path(sys.argv[2])

data = ipath.read_bytes()
print(f'Read {len(data)} bytes from {ipath.name}.')