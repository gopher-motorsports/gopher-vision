import code
import platform
from pathlib import Path

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
                'name': p.get('motec_name'),
                'unit': p.get('unit'),
                **types[type]
            }

def load(path):
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
                print('parsing data...')
                gdat_channels = gdat.parse(data, parameters)
                print(f'created {len(gdat_channels)} channels')
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
        print(f'{len(gdat_channels)} channels\n')
        ch_info = []
        for channel in gdat_channels.values():
            # exclude a few keys from the table
            ch = {k:v for k,v in channel.items() if k not in ['points', 'data']}
            ch['points'] = len(channel['points'])
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
        for ch in ld_channels.values():
            ch_info.append({
                'meta_ptr': hex(ch['meta_ptr']),
                'data_ptr': hex(ch['data_ptr']),
                'size': ch['size'],
                'name': ch['name'],
                'sample_rate': ch['sample_rate'],
                'sample_count': ch['sample_count'],
                'shift': ch['shift'],
                'scalar': ch['scalar'],
                'divisor': ch['divisor'],
                'offset': ch['offset'],
            })
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

def help():
    commands = [
        ['load(path)', 'load a .gdat, .ld, or GopherCAN config (.yaml) into memory and parse the data'],
        ['info()', 'print basic info on currently loaded data'],
        ['info_config()', 'print detailed info on a loaded GopherCAN config'],
        ['info_gdat()', 'print detailed info on a loaded .gdat file'],
        ['info_ld()', 'print detailed info on a loaded .ld file'],
        ['plot_gdat(id)', 'plot .gdat channel data'],
        ['plot_ld(name)', 'plot .ld channel data'],
        ['help()', 'print available commands'],
        ['exit()', 'exit the console']
    ]
    print(tabulate(commands))

banner = (f'Welcome to Gopher Vision! (Python {platform.python_version()})\n'
          f'run help() to print available commands')
shell = code.InteractiveConsole(globals())
shell.interact(banner=banner)