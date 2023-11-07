import code
import platform
from pathlib import Path
import time
import sys

from tabulate import tabulate
import yaml

import gdat
import ld

paths = {
    'config': None,
    'gdat': None,
    'ld': None
}

parameters = {}
gdat_t0 = None
gdat_channels = {}
ld_metadata = {}
ld_channels = {}

def load_config(path):
    global parameters
    parameters = {}

    with open(path) as f:
        config = yaml.safe_load(f)

    types = {
        'UNSIGNED8' : { 'size': 1, 'format': '>B', 'signed': False },
        'UNSIGNED16' : { 'size': 2, 'format': '>H', 'signed': False },
        'UNSIGNED32' : { 'size': 4, 'format': '>I', 'signed': False },
        'UNSIGNED64' : { 'size': 8, 'format': '>Q', 'signed': False },
        'SIGNED8' : { 'size': 1, 'format': '>b', 'signed': True },
        'SIGNED16' : { 'size': 2, 'format': '>h', 'signed': True },
        'SIGNED32' : { 'size': 4, 'format': '>i', 'signed': True },
        'SIGNED64' : { 'size': 8, 'format': '>q', 'signed': True },
        'FLOATING' : { 'size': 4, 'format': '>f', 'signed': False }
    }

    # build a new parameter dictionary
    print('building parameter dictionary...')
    for p in config['parameters'].values():
        if p['id'] in parameters:
            print(f"WARNING: duplicate parameter id ({p['id']})")
        else:
            type = p.get('type')
            if not type in types:
                print(f"ERROR: parameter ({p['id']}) has an invalid type")
                continue

            parameters[p['id']] = {
                'id': p['id'],
                'name': p.get('motec_name') or '',
                'unit': p.get('unit') or '',
                **types[type]
            }

def load(path):
    global gdat_t0
    global gdat_channels
    global ld_metadata
    global ld_channels
    
    path = Path(path)
    if not path.is_file():
        print(f'"{path}" is not a file')
        return
    if not path.suffix in ['.yaml', '.gdat', '.ld']:
        print(f'path must lead to a .yaml/.gdat/.ld file')
        return

    print(f'loading {path.name} ...')
    match path.suffix:
        case '.yaml':
            load_config(path)
            print(f'loaded {len(parameters)} parameters')
            paths['config'] = path
        case '.gdat':
            if not len(parameters):
                print('please load a GopherCAN config first')
            else:
                (sof, ext, data) = path.read_bytes().partition(b'.gdat:')
                print(f'read {len(data)} bytes of data')
                gdat_t0 = gdat.get_t0(sof)
                print(f"t0: {time.asctime(gdat_t0)}")
                gdat_channels = gdat.parse(data, parameters)
                paths['gdat'] = path
        case '.ld':
            print('parsing data...')
            ld_metadata, ld_channels = ld.parse(path)
            print(f"loaded {len(ld_channels)} channels")
            paths['ld'] = path

def info():
    info = [
        ['config', paths['config'] or 'not loaded', f'{len(parameters)} parameters'],
        ['gdat', paths['gdat'] or 'not loaded', f'{len(gdat_channels)} channels'],
        ['ld', paths['ld'] or 'not loaded', f'{len(ld_channels)} channels']
    ]
    print(tabulate(info))

def info_config():
    if paths['config']:
        print(f"config path: {paths['config']}")
        print(f'{len(parameters)} parameters\n')
        print(tabulate(list(parameters.values()), headers='keys'))
    else:
        print('no config loaded')

def info_gdat():
    if paths['gdat']:
        print(f"gdat path: {paths['gdat']}")
        print(f"t0: {time.asctime(gdat_t0)}")
        print(f'{len(gdat_channels)} channels\n')
        ch_info = []
        for channel in gdat_channels.values():
            # exclude a few keys from the table
            ch = {k:v for k,v in channel.items() if k not in ['points', 't_int', 'v_int', 'v_enc']}
            ch_info.append(ch)
        print(tabulate(ch_info, headers='keys'))
    else:
        print('no .gdat loaded')

def info_ld():
    if paths['ld']:
        print(f"ld path: {paths['ld']}\n")
        print('HEADER')
        print(tabulate(ld_metadata['header'].items()))
        print('EVENT')
        print(tabulate(ld_metadata['event'].items()))
        print('VENUE')
        print(tabulate(ld_metadata['venue'].items()))
        print('VEHICLE')
        print(tabulate(ld_metadata['vehicle'].items()))
        print('WEATHER')
        print(tabulate(ld_metadata['weather'].items()))
        print('CHANNELS')
        ch_info = []
        for channel in ld_channels.values():
            # exclude a few keys from the table
            ch = {k:v for k,v in channel.items() if k not in ['data']}
            ch_info.append(ch)
        print(tabulate(ch_info, headers='keys'))
    else:
        print('no .ld loaded')

def plot_gdat(id):
    if not len(gdat_channels):
        print('please load a .gdat first')
    elif not id in gdat_channels:
        print(f'channel ({id}) does not exist')
    else:
        gdat.plot(gdat_channels[id])

def plot_ld(name):
    if not len(ld_channels):
        print('please load a .ld first')
    elif not name in ld_channels:
        print(f'channel ({name}) does not exist')
    else:
        ld.plot(ld_channels[name])

def convert(path):
    path = Path(path)
    if not paths['gdat']:
        print('no .gdat loaded')
        return
    if not len(gdat_channels):
        print('no gdat channels to convert')
        return
    if not path.suffix == '.ld':
        print(f'path must lead to a .ld file')
        return
    if path.is_file():
        print(f'deleting "{path}"...')
        path.unlink()
    
    ld.write(path, gdat_channels, gdat_t0)

def help():
    commands = [
        ['load(path)', 'load a .gdat, .ld, or GopherCAN config (.yaml) into memory and parse the data'],
        ['info()', 'print basic info on currently loaded data'],
        ['info_config()', 'print detailed info on a loaded GopherCAN config'],
        ['info_gdat()', 'print detailed info on a loaded .gdat file'],
        ['info_ld()', 'print detailed info on a loaded .ld file'],
        ['plot_gdat(id)', 'plot .gdat channel data'],
        ['plot_ld(name)', 'plot .ld channel data'],
        ['convert(path)', 'convert the currently loaded .gdat to a .ld at "path"'],
        ['help()', 'print available commands'],
        ['exit()', 'exit the console']
    ]
    print(tabulate(commands))

banner = (f'Welcome to Gopher Vision! (Python {platform.python_version()})\n'
          f'run help() to print available commands')
shell = code.InteractiveConsole(globals())

if __name__ == '__main__':
    # python go4v.py
    if len(sys.argv) == 1:
        shell.interact(banner=banner)

    # python go4v.py convert *.yaml path/to/*.gdat
    # python go4v.py convert *.yaml path/to/folder/
    elif sys.argv[1] == 'convert' and len(sys.argv) == 4:
        start = time.time()
        # assumes GopherCAN is in a sibling directory
        config_name = sys.argv[2]
        config_path = Path('../gophercan-lib/network_autogen/configs/') / config_name
        load(config_path)

        def convert_single(gdat_path):
            if not gdat_path.suffix == '.gdat':
                print(f'{gdat_path} is not a .gdat file')
                return
            
            load(gdat_path)
            # output .ld next to the gdat with the same name
            ld_path = Path(gdat_path).with_suffix('.ld')
            convert(ld_path)

        # gdat path could be a single file or a folder
        gdat_path = Path(sys.argv[3])
        if gdat_path.is_file():
            convert_single(gdat_path)
        elif gdat_path.is_dir():
            for file_path in gdat_path.iterdir():
                if (file_path.suffix == '.gdat'):
                    convert_single(file_path)

        elapsed = round(time.time() - start, 2)
        print(f'\nfinished in {elapsed}s')

    # python go4v.py preload *.yaml path/to/*.gdat
    elif sys.argv[1] == 'preload' and len(sys.argv) == 4:
        start = time.time()
        # assumes GopherCAN is in a sibling directory
        config_name = sys.argv[2]
        config_path = Path('../gophercan-lib/network_autogen/configs/') / config_name
        load(config_path)
        load(sys.argv[3])
        elapsed = round(time.time() - start, 2)
        print(f'\nfinished in {elapsed}s\n')

        shell.interact(banner=banner)

    # unknown argument pattern, default to shell
    else:
        shell.interact(banner=banner)