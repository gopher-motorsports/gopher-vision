import yaml

def load_config(path):
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

    return parameters