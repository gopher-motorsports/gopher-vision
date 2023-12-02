import dearpygui.dearpygui as dpg
from tkinter import filedialog
from pathlib import Path

from lib import gcan
from lib import gdat
from lib import ld

dpg.create_context()

parameters = {}

# DPG CALLBACKS

def load_config(sender):
    global parameters
    path = filedialog.askopenfilename(
        title='Open GopherCAN configuration',
        filetypes=[('YAML', '*.yaml')]
    )
    if path:
        parameters = gcan.get_params(gcan.load_path(path))
        dpg.configure_item('config_path', default_value=path, color=(45, 245, 120, 128))
        dpg.configure_item('convert_btn', enabled=True)

def convert(sender):
    global parameters
    if len(parameters) == 0: return

    paths = filedialog.askopenfilename(
        title='Select Data',
        filetypes=[('GDAT', '*.gdat')],
        multiple=True
    )

    n = 0
    dpg.configure_item('convert_loading', default_value=0.05, overlay=f'{n}/{len(paths)}')
    for path in paths:
        path = Path(path)
        try:
            print(f'converting: {path} ...')
            (sof, ext, data) = path.read_bytes().partition(b'.gdat:')
            print(f'read {len(data)} bytes of data')
            t0 = gdat.get_t0(sof)
            channels = gdat.parse(data, parameters)

            ld_path = path.with_suffix('.ld')
            if ld_path.is_file():
                print(f'overwriting: {ld_path}')
                ld_path.unlink()
            ld.write(ld_path, channels, t0)
        except Exception as e:
            print(f'failed to convert: {path}')
            print(e)
        n += 1
        dpg.configure_item('convert_loading', default_value=(n / len(paths)), overlay=f'{n}/{len(paths)}')
        dpg.add_text(ld_path, parent='convert_done', color=(255, 255, 255, 128))
    dpg.configure_item('convert_loading', overlay='')

# DPG LAYOUT

with dpg.window(tag='primary_window', horizontal_scrollbar=True):
    with dpg.group(horizontal=True):
        dpg.add_text('Load a GopherCAN configuration (.yaml):')
        dpg.add_button(label='Browse', callback=load_config)
    dpg.add_text('No configuration loaded', tag='config_path', color=(255, 255, 255, 128))
    with dpg.group(horizontal=True):
        dpg.add_text('Select data to convert (.gdat):')
        dpg.add_button(tag='convert_btn', label='Convert', enabled=False, callback=convert)
    with dpg.group(tag='convert_done'):
        dpg.add_progress_bar(tag='convert_loading', width=200)
        dpg.add_text('Done:', color=(255, 255, 255, 128))
dpg.set_primary_window('primary_window', True)

# DPG THEME

with dpg.theme() as theme_btn_green:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (10, 10, 10))
        dpg.add_theme_color(dpg.mvThemeCol_Button, (45, 245, 120))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (41, 221, 108))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (36, 196, 96))

dpg.bind_item_theme('convert_btn', theme_btn_green)

# DPG RENDERING

dpg.create_viewport(title='GopherVision', width=600, height=200)
dpg.set_viewport_vsync(True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()