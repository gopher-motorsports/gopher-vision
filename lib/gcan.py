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

# build a parameter dictionary from a GopherCAN config
def get_params(config: dict):
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
            'type': type,
            **TYPES[type]
        }
    print(f'found {len(parameters)} parameters')
    return parameters

# load a GopherCAN config from a local path
def load_path(path: Path):
    with open(path) as f:
        config = yaml.safe_load(f)
    print(f'loaded GopherCAN config: {path}')
    return config

# load a GopherCAN config from a URL (gophercan-lib GitHub repo)
def load_url(url: str):
    with urllib.request.urlopen(url) as f:
        config = yaml.safe_load(f)
    print(f'loaded GopherCAN config: {url}')
    return config

# load a GopherCAN config by a name like "go4-23c.yaml"
def load(name: str):
    path = Path('../gophercan-lib/network_autogen/configs/') / name
    url = f'https://raw.githubusercontent.com/gopher-motorsports/gophercan-lib/master23/network_autogen/configs/{name}'
    try:
        config = load_path(path)
    except:
        print(f'WARNING: no config found at "{path}", checking GitHub...')
        try:
            config = load_url(url)
        except:
            raise Exception(f'ERROR: failed to load "{name}"')
    return get_params(config)
