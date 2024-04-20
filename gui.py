import dearpygui.dearpygui as dpg
from tkinter import filedialog
import tkinter as tk
from pathlib import Path

from lib import gcan
from lib import gdat
from lib import ld

COLORS = {
    'red': (231, 76, 60),
    'green': (45, 245, 120),
    'gray': (255, 255, 255, 128)
}

parameters = {}

def load_config(sender):
    global parameters
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title='Open GopherCAN configuration',
        filetypes=[('YAML', '*.yaml')]
    )
    root.destroy()

    if not path:
        return
    
    parameters = gcan.get_params(gcan.load_path(path))
    dpg.configure_item('config_path', default_value=path, color=COLORS['green'])
    # enable convert button once a config is loaded
    dpg.configure_item('convert_btn', enabled=True)
    # delete parameter table if it already exists
    if dpg.does_item_exist('parameter_table'):
        dpg.delete_item('parameter_table')
    # create new parameter table
    with dpg.group(tag='parameter_table', parent='tab-gophercan'):
        dpg.add_input_text(hint='Name', callback=lambda _, val: dpg.set_value('ptable', val))
        with dpg.table(tag='ptable', header_row=True, row_background=True):
            dpg.add_table_column(label='ID')
            dpg.add_table_column(label='Name')
            dpg.add_table_column(label='Unit')
            dpg.add_table_column(label='Type')
            for parameter in parameters.values():
                with dpg.table_row(filter_key=parameter['name']):
                    dpg.add_text(parameter['id'])
                    dpg.add_text(parameter['name'])
                    dpg.add_text(parameter['unit'])
                    dpg.add_text(parameter['type'])

def convert(sender):
    global parameters
    if len(parameters) == 0:
        return

    root = tk.Tk()
    root.withdraw()
    paths = filedialog.askopenfilename(
        title='Select Data',
        filetypes=[('GDAT', '*.gdat')],
        multiple=True
    )
    root.destroy()

    n = 0
    dpg.configure_item('convert_loading', default_value=0.05, overlay=f'{n}/{len(paths)}')
    for path in paths:
        path = Path(path)
        try:
            print(f'converting: {path} ...')
            # parse .gdat
            (sof, ext, data) = path.read_bytes().partition(b'.gdat:')
            print(f'read {len(data)} bytes of data')
            t0 = gdat.get_t0(sof)
            channels = gdat.parse(data, parameters)
            # write to .ld
            ld_path = path.with_suffix('.ld')
            if ld_path.is_file():
                print(f'overwriting: {ld_path}')
                ld_path.unlink()
            ld.write(ld_path, channels, t0)
        except Exception as e:
            print(f'failed to convert: {path}')
            print(e)
        # update loading bar, add path to done list
        n += 1
        dpg.configure_item('convert_loading', default_value=(n / len(paths)), overlay=f'{n}/{len(paths)}')
        dpg.add_text(ld_path, parent='convert_done', color=COLORS['gray'])
    dpg.configure_item('convert_loading', overlay='')

dpg.create_context()
dpg.create_viewport(title='GopherVision', width=800, height=600)

with dpg.window(tag='window'):
    dpg.set_primary_window('window', True)

    with dpg.tab_bar():
        with dpg.tab(label='GopherCAN', tag='tab-gophercan'):
            with dpg.group(horizontal=True):
                dpg.add_text('Load a GopherCAN configuration (.yaml):')
                dpg.add_button(label='Browse', callback=load_config)
            dpg.add_text('No configuration loaded', tag='config_path', color=COLORS['red'])

        with dpg.tab(label='Data Parser'):
            with dpg.group(horizontal=True):
                dpg.add_text('Select data to convert (.gdat):')
                dpg.add_button(tag='convert_btn', label='Convert', enabled=False, callback=convert)
            dpg.add_progress_bar(tag='convert_loading', width=200)
            with dpg.group(tag='convert_done'):
                dpg.add_text('Done:', color=COLORS['gray'])

        with dpg.tab(label='Telemetry'):
            pass

dpg.setup_dearpygui()
dpg.show_viewport()

while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

dpg.destroy_context()