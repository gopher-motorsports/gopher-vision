from pathlib import Path
import yaml
import urllib.request

TYPES = {
    'UNSIGNED8' : { 'size': 1, 'format': '>B', 'signed': False },
    'UNSIGNED16' : { 'size': 2, 'format': '>H', 'signed': False },
    'UNSIGNED32' : { 'size': 4, 'format': '>I', 'signed': False },
    'UNSIGNED64' : { 'size': 8, 'format': '>Q', 'signed': False },
    'SIGNED8' : { 'size': 1, 'format': '>b', 'signed': True },
    'SIGNED16' : { 'size': 2, 'format': '>h', 'signed': True },
    'SIGNED32' : { 'size': 4, 'format': '>i', 'signed': True },
    'SIGNED64' : { 'size': 8, 'format': '>q', 'signed': True },
    'FLOATING' : { 'size': 4, 'format': '>f', 'signed': True }
}

# load parameters from a GopherCAN configuration
# config_name is something like "go4-23c.yaml"
def load(config_name):
    path = Path('../gophercan-lib/network_autogen/configs/') / config_name
    url = f'https://raw.githubusercontent.com/gopher-motorsports/gophercan-lib/master23/network_autogen/configs/{config_name}'
    try:
        # look for the config in a sibling directory
        with open(path) as f:
            config = yaml.safe_load(f)
            print(f'loaded GopherCAN config: {path}')
    except:
        print(f'WARNING: no config found at "{path}"')
        try:
            # try fetching from gophercan-lib
            print('checking GitHub...')
            with urllib.request.urlopen(url) as f:
                config = yaml.safe_load(f)
                print(f'loaded GopherCAN config: {url}')
        except:
            raise Exception(f'ERROR: failed to load "{config_name}"')
    
    # build parameter dictionary
    parameters = {}
    for k,v in config['parameters'].items():
        id = v.get('id')
        if id is None:
            print(f'WARNING: {k} is missing an id')
            continue

        if id in parameters:
            print(f'WARNING: duplicate id ({id})')
            continue

        type = v.get('type')
        if not type in TYPES:
            print(f'WARNING: {k} has an unknown type ({type})')
            continue

        parameters[id] = {
            'id': id,
            'name': v.get('motec_name', ''),
            'unit': v.get('unit', ''),
            **TYPES[type]
        }
    return parameters