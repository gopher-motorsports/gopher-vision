from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from pathlib import Path

from lib import gcan
from lib import gdat
from lib import ld

parameters = {}

def load_config():
    global yaml_path
    global parameters
    path = filedialog.askopenfilename(
        title='Select a GopherCAN configuration',
        filetypes=[('YAML', '*.yaml')]
    )
    parameters = gcan.get_params(gcan.load_path(path))

def convert():
    global parameters
    if len(parameters) == 0:
        print('no parameters loaded, please select a GopherCAN config first')
        return
    
    paths = filedialog.askopenfilename(
        title='Select GDAT file(s)',
        filetypes=[('GDAT', '*.gdat')],
        multiple=True
    )

    for path in paths:
        path = Path(path)
        print(f'working on: {path}')
        try:
            (sof, ext, data) = path.read_bytes().partition(b'.gdat:')
            print(f'read {len(data)} bytes of data')
            t0 = gdat.get_t0(sof)
            channels = gdat.parse(data, parameters)

            ld_path = path.with_suffix('.ld')
            if ld_path.is_file():
                print(f'deleting {ld_path}')
                ld_path.unlink()
            ld.write(ld_path, channels, t0)
        except:
            print(f'failed: {path} ...')

root = Tk()
root.title('GopherVision')
root_frame = ttk.Frame(root, padding=10)
root_frame.pack()

yaml_frame = ttk.Frame(root_frame)
yaml_frame.pack(fill='x')
ttk.Label(yaml_frame, text="Select a GopherCAN config (.yaml):").pack(side='left')
ttk.Button(yaml_frame, text='Browse', command=load_config).pack(side='left')

gdat_frame = ttk.Frame(root_frame)
gdat_frame.pack(fill='x')
ttk.Label(gdat_frame, text="Select one or more data files to convert (.gdat):").pack(side='left')
ttk.Button(gdat_frame, text='Convert', command=convert).pack(side='left')

root.mainloop()