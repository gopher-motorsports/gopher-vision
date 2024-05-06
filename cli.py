import cmd
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
import time
import numpy as np

from lib import gcan
from lib import gdat
from lib import ld

console = Console()

class Shell(cmd.Cmd):
    intro = 'Welcome to GopherVision. Enter ? to list commands.'
    prompt = '\n(GopherVision) '

    config_name: str = None
    config_params = {}

    gdat_path: Path = None
    gdat_t0: time.struct_time = None
    gdat_channels = {}

    ld_path: Path = None
    ld_metadata = {}
    ld_channels = {}

    # CONSOLE COMMANDS =========================================================

    def do_load(self, arg):
        '''load .gdat, .ld, and GopherCAN configs

        load [CONFIG NAME] [PATH TO .gdat]
        e.g. "load go4-23c.yaml statefair.gdat"

        load [PATH TO .ld]
        e.g. "load statefair.ld"

        load [CONFIG NAME]
        e.g. "load go4-23c.yaml"
        '''
        args = arg.split()
        try:
            if len(args) == 1:
                path = Path(args[0])
                if path.suffix == '.ld':
                    self.load_ld(path)
                elif path.suffix == '.yaml':
                    self.load_config(args[0])
                else:
                    raise Exception('ERROR: invalid syntax, try "help load"')
            elif len(args) == 2:
                self.load_config(args[0])
                self.load_gdat(Path(args[1]))
            else:
                raise Exception('ERROR: invalid syntax, try "help load"')
        except Exception as err:
            console.print(err, style='red')

    def do_convert(self, arg):
        '''convert a .gdat file (or folder of .gdat files) to .ld

        convert [GOPHERCAN CONFIG NAME] [PATH TO .gdat]
        e.g. "convert go4-23c.yaml statefair.gdat"

        convert [GOPHERCAN CONFIG NAME] [PATH TO FOLDER]
        e.g. "convert go4-23c.yaml data/"
        '''
        config_name, gdat_path = arg.split()

        try:
            self.load_config(config_name)
        except Exception as err:
            console.print(err, style='red')
            return

        gdat_path = Path(gdat_path)
        if gdat_path.is_file():
            # convert single file
            try:
                self.load_gdat(gdat_path)
                self.convert()
            except Exception as err:
                console.print(err, style='red')
        elif gdat_path.is_dir():
            # convert all files in directory
            for path in gdat_path.iterdir():
                if path.suffix == '.gdat':
                    try:
                        self.load_gdat(path)
                        self.convert()
                        print()
                    except Exception as err:
                        console.print(err, style='red')
        else:
            console.print(f'ERROR: {gdat_path} does not exist', style='red')

    def do_info(self, arg):
        '''display info on loaded data

        info [config | gdat | ld]
        e.g. info gdat
        '''
        if arg == 'config':
            if self.config_name is None: return

            print(f'name: {self.config_name}')

            table = Table(box=box.MINIMAL)
            keys = ['id', 'name', 'unit', 'type']
            for k in keys:
                table.add_column(k)
            for p in self.config_params.values():
                table.add_row(*[str(p[k]) for k in keys])
            console.print(table)

        elif arg == 'gdat':
            if self.gdat_path is None: return

            print(f'path: {self.gdat_path}')
            print(f't0: {time.asctime(self.gdat_t0)}')

            table = Table(box=box.MINIMAL)
            keys = ['id', 'name', 'unit', 'type', 'n_points', 't_min', 't_max', 'v_min', 'v_max', 'frequency_hz', 'sample_count', 'shift', 'scalar', 'divisor', 'offset']
            for k in keys:
                table.add_column(k)
            for ch in self.gdat_channels.values():
                table.add_row(*[str(ch[k]) for k in keys])
            console.print(table)

        elif arg == 'ld':
            if self.ld_path is None: return

            print(f'path: {self.ld_path}')

            table_header = Table(title='HEADER', box=box.MINIMAL)
            table_header.add_column('key')
            table_header.add_column('value')
            for k,v in self.ld_metadata['header'].items():
                table_header.add_row(k, str(v))
            console.print(table_header)

            table_event = Table(title='EVENT', box=box.MINIMAL)
            table_event.add_column('key')
            table_event.add_column('value')
            for k,v in self.ld_metadata['event'].items():
                table_event.add_row(k, str(v))
            console.print(table_event)

            table_venue = Table(title='VENUE', box=box.MINIMAL)
            table_venue.add_column('key')
            table_venue.add_column('value')
            for k,v in self.ld_metadata['venue'].items():
                table_venue.add_row(k, str(v))
            console.print(table_venue)

            table_vehicle = Table(title='VEHICLE', box=box.MINIMAL)
            table_vehicle.add_column('key')
            table_vehicle.add_column('value')
            for k,v in self.ld_metadata['vehicle'].items():
                table_vehicle.add_row(k, str(v))
            console.print(table_vehicle)

            table_weather = Table(title='WEATHER', box=box.MINIMAL)
            table_weather.add_column('key')
            table_weather.add_column('value')
            for k,v in self.ld_metadata['weather'].items():
                table_weather.add_row(k, str(v))
            console.print(table_weather)

            table_ch = Table(title='CHANNELS', box=box.MINIMAL)
            keys = ['name', 'short_name', 'unit', 'sample_rate', 'sample_count', 'size', 'shift', 'scalar', 'divisor', 'offset', 'prev_ptr', 'meta_ptr', 'data_ptr', 'next_ptr']
            for k in keys:
                table_ch.add_column(k)
            for ch in self.ld_channels.values():
                table_ch.add_row(*[str(ch[k]) for k in keys])
            console.print(table_ch)

        else:
            console.print('ERROR: invalid syntax, try "help info"', style='red')

    def do_plot(self, arg):
        '''plot channels from a loaded .gdat or .ld

        gdat channels are referenced by id
        ld channels are referenced by name
        use "info gdat" or "info ld" to view available channels

        plot [gdat | ld] [id | name]
        e.g. "plot gdat 9"
        e.g. "plot ld Battery Volts"
        '''
        args = arg.split()

        if args[0] == 'gdat':
            id = int(args[1])
            if id in self.gdat_channels:
                gdat.plot(self.gdat_channels[id])
            else:
                console.print(f'ERROR: {id} is not a {args[0]} channel', style='red')

        elif args[0] == 'ld':
            name = ' '.join(args[1:])
            if name in self.ld_channels:
                ld.plot(self.ld_channels[name])
            else:
                console.print(f'ERROR: {name} is not a {args[0]} channel', style='red')

        else:
            console.print('ERROR: invalid syntax, try "help plot"', style='red')

    def do_query(self, arg):
        '''get the closest datapoints in a gdat channel to a specified timestamp (in seconds)

        query [id] [time]
        e.g. "query 1 169.420"
        '''
        args = arg.split()
        id = int(args[0])
        t = float(args[1]) * 1000
        if id in self.gdat_channels:
            ch = self.gdat_channels[id]
            i = np.searchsorted(ch['points'][:,0], t)

            print(f"{ch['name']} ({ch['unit']})")
            print(f'points near t = {t}ms ...')
            if i > 0:
                print(f"t = {ch['points'][i-1][0]}ms, v = {ch['points'][i-1][1]}")
            if i < ch['n_points']:
                print(f"t = {ch['points'][i][0]}ms, v = {ch['points'][i][1]}") 
        else:
            console.print(f'ERROR: {id} is not a gdat channel', style='red')

    def do_exit(self, arg):
        '''exit the console'''
        return True
    
    # UTILITIES ================================================================

    def load_config(self, name: str):
        if name == self.config_name:
            print(f'{name} has already been loaded')
            return
        
        try:
            config_path = Path('../gophercan-lib/network_autogen/configs/') / name
            self.config_params = gcan.get_params(gcan.load_path(config_path))
        except:
            raise Exception(f'ERROR: failed to load "{config_path}"')
        self.config_name = name

        if len(self.config_params) == 0:
            raise Exception('ERROR: no parameters loaded')

    def load_gdat(self, path: Path):
        if path.suffix != '.gdat':
            raise Exception('ERROR: please provide a path to a .gdat file')
        
        if path == self.gdat_path:
            print(f'{path} has already been loaded')
            return

        start = time.time()
        print(f'loading {path} ...')

        (sof, ext, data) = path.read_bytes().partition(b'.gdat:')
        print(f'read {len(data)} bytes of data')
        self.gdat_t0 = gdat.get_t0(sof)
        self.gdat_channels = gdat.parse(data, self.config_params)
        self.gdat_path = path

        elapsed = round(time.time() - start, 2)
        print(f'loaded in ({elapsed}s)')

    def load_ld(self, path: Path):
        if path.suffix != '.ld':
            raise Exception('ERROR: please provide a path to a .ld file')
        
        if path == self.ld_path:
            print(f'{path} has already been loaded')
            return
        
        start = time.time()
        print(f'loading {path} ...')

        self.ld_metadata, self.ld_channels = ld.parse(path)
        self.ld_path = path

        elapsed = round(time.time() - start, 2)
        print(f'finished in ({elapsed}s)')

    def convert(self):
        if len(self.gdat_channels) == 0:
            raise Exception('ERROR: no channels to convert')

        # output .ld next to the .gdat with the same name
        ld_path = self.gdat_path.with_suffix('.ld')
        if ld_path.is_file():
            print(f'deleting {ld_path}')
            ld_path.unlink()
        ld.write(ld_path, self.gdat_channels, self.gdat_t0)

if __name__ == '__main__':
    Shell().cmdloop()