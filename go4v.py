import code
import platform
from pathlib import Path

from tabulate import tabulate
import yaml

import gdat

paths = {
    'config': None,
    'gdat': None,
    'ld': None
}

parameters = {}
channels = {}

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
    global channels
    
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
            print('done')
            paths['config'] = path
        case '.gdat':
            if not len(parameters):
                print('please load a GopherCAN config first')
            else:
                (sof, ext, data) = path.read_bytes().partition(b'.gdat:')
                print(f'read {len(data)} bytes of data')
                print('parsing data...')
                channels = gdat.parse(data, parameters)
                print(f'created {len(channels)} channels')
                print('done')
                paths['gdat'] = path
        case '.ld':
            pass

def info():
    info = [
        ['config', paths['config'] or 'not loaded', f'{len(parameters)} parameters'],
        ['gdat', paths['gdat'] or 'not loaded', f'{len(channels)} channels'],
        ['ld', paths['ld'] or 'not loaded', '']
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
        print(f'{len(channels)} channels\n')
        ch_info = []
        for channel in channels.values():
            # exclude a few keys from the table
            ch = {k:v for k,v in channel.items() if k not in ['points', 'data']}
            ch['points'] = len(channel['points'])
            ch_info.append(ch)
        print(tabulate(ch_info, headers='keys'))
    else:
        print('no .gdat loaded')

def info_ld():
    if paths['ld']:
        print(f"ld path: {paths['ld']}")
    else:
        print('no .ld loaded')

def plot(id):
    if not len(channels):
        print('please load a .gdat first')
    elif not id in channels:
        print(f'channel ({id}) does not exist')
    else:
        gdat.plot(channels[id])

def help():
    commands = [
        ['load(path)', 'load a .gdat, .ld, or GopherCAN config (.yaml) into memory and parse the data'],
        ['info()', 'print basic info on currently loaded data'],
        ['info_config()', 'print detailed info on a loaded GopherCAN config'],
        ['info_gdat()', 'print detailed info on a loaded .gdat file'],
        ['info_ld()', 'print detailed info on a loaded .ld file'],
        ['plot(id)', 'plot .gdat channel data'],
        ['help()', 'print available commands'],
        ['exit()', 'exit the console']
    ]
    print(tabulate(commands))

banner = (f'Welcome to Gopher Vision! (Python {platform.python_version()})\n'
          f'run help() to print available commands')
shell = code.InteractiveConsole(globals())
shell.interact(banner=banner)