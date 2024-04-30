import dearpygui.dearpygui as dpg
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from collections import deque
import time
import threading
import serial
import serial.tools.list_ports

from lib import gcan
from lib import gdat
from lib import ld
from lib import live

COLORS = {
    'red': (231, 76, 60),
    'green': (45, 245, 120),
    'gray': (255, 255, 255, 128)
}

PLOT_SIZE = 500
PLOT_REFRESH_HZ = 100

node = live.Node()
node.tx_port.open_socket()
parameters = {}
plot_data = {}

# callback for "Browse" button in GopherCAN tab
# opens a file dialog to load a YAML config
def load_config(sender):
    global node
    global parameters
    global plot_data

    # open file dialog
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title='Open GopherCAN configuration',
        filetypes=[('YAML', '*.yaml')]
    )
    root.destroy()

    if not path:
        return
    
    # load GopherCAN parameters
    try:
        parameters = gcan.get_params(gcan.load_path(path))
    except:
        print(f'ERROR: failed to collect parameters from "{path}"')
        return
    
    node.set_parameters(parameters)
    plot_data = {
        id: {
            'x': deque([0], maxlen=PLOT_SIZE),
            'y': deque([0], maxlen=PLOT_SIZE)
        } for id in parameters.keys()
    }

    # update loaded config path
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
    # reset parameter list in telemetry tab
    dpg.delete_item('parameter_list', children_only=True)
    for parameter in parameters.values():
        dpg.add_selectable(parent='parameter_list', label=parameter['name'], filter_key=parameter['name'], callback=add_plot, user_data=parameter['id'])

# callback for "Convert" button in Data Parser tab
# converts .gdat files to .ld
def convert(sender):
    global parameters
    if len(parameters) == 0:
        return

    # open file dialog to select 1+ .gdat files
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
        except Exception as err:
            print(f'failed to convert: {path}')
            print(err)
        # update loading bar, add path to done list
        n += 1
        dpg.configure_item('convert_loading', default_value=(n / len(paths)), overlay=f'{n}/{len(paths)}')
        dpg.add_text(ld_path, parent='convert_done', color=COLORS['gray'])

# callback for "Add Parameter" button in Telemetry tab
# creates a plot for a loaded GCAN parameter
def add_plot(sender, app_data, pid):
    parameter = parameters[pid]

    # clean-up in case this plot was removed and re-added
    if dpg.does_alias_exist(f'{pid}_x'): dpg.remove_alias(f'{pid}_x')
    if dpg.does_alias_exist(f'{pid}_y'): dpg.remove_alias(f'{pid}_y')
    if dpg.does_alias_exist(f'{pid}_series'): dpg.remove_alias(f'{pid}_series')
    if dpg.does_alias_exist(f'{pid}_value'): dpg.remove_alias(f'{pid}_value')

    # add new plot
    with dpg.collapsing_header(label=f"{parameter['name']} ({pid})", closable=True, parent='tab-telemetry'):
        with dpg.plot(width=-1, height=150, no_mouse_pos=True, no_box_select=True, use_local_time=True):
            dpg.add_plot_axis(dpg.mvXAxis, time=True, tag=f'{pid}_x')
            dpg.add_plot_axis(dpg.mvYAxis, label=parameter['unit'], tag=f'{pid}_y')
            dpg.add_line_series(list(plot_data[pid]['x']), list(plot_data[pid]['y']), label=parameter['name'], parent=f'{pid}_y', tag=f'{pid}_series')
            dpg.add_plot_annotation(label='0.0', offset=(float('inf'), float('inf')), tag=f'{pid}_value')

# transfer values from receiver to plots at a fixed rate
# called as a background daemon thread
def update_plots():
    global node
    while True:
        t = time.time()
        for (id, value) in node.values.items():
            # update plot data
            plot_data[id]['x'].append(t)
            plot_data[id]['y'].append(value)
            # if plot is visible, update series
            if dpg.does_item_exist(f'{id}_series'):
                dpg.set_value(f'{id}_series', [list(plot_data[id]['x']), list(plot_data[id]['y'])])
                dpg.set_item_label(f'{id}_value', round(plot_data[id]['y'][-1], 3))
                dpg.fit_axis_data(f'{id}_x')
                dpg.fit_axis_data(f'{id}_y')
        time.sleep(1 / PLOT_REFRESH_HZ)

# display options for port selection
def set_port_type(sender, port_type):
    if port_type == 'Serial Port':
        dpg.configure_item('port_serial', show=True)
        dpg.configure_item('port_socket_host', show=False)
        dpg.configure_item('port_socket_port', show=False)
        dpg.configure_item('port_socket_set', show=False)
        ports = serial.tools.list_ports.comports()
        dpg.configure_item('port_serial', items=[p.device for p in ports])
    elif port_type == 'Network Socket':
        dpg.configure_item('port_serial', show=False)
        dpg.configure_item('port_socket_host', show=True)
        dpg.configure_item('port_socket_port', show=True)
        dpg.configure_item('port_socket_set', show=True)

# callback triggered when an item is selected in serial port dropdown
def set_port_serial(sender, port_name):
    global node
    try:
        dpg.configure_item('port_status', default_value=f'opening {port_name} ...', color=COLORS['gray'])
        node.rx_port.open_serial(port_name)
        dpg.configure_item('port_status', default_value=f'{port_name} open', color=COLORS['green'])
    except:
        dpg.configure_item('port_status', default_value='No port open', color=COLORS['red'])

# callback for  "Set" button when entering a network port
def set_port_socket(sender, _):
    global node
    host = dpg.get_value('port_socket_host')
    port = dpg.get_value('port_socket_port')
    try:
        dpg.configure_item('port_status', default_value=f'opening {host}:{port} ...', color=COLORS['gray'])
        node.rx_port.bind_socket(host, port)
        dpg.configure_item('port_status', default_value=f'{host}:{port} open', color=COLORS['green'])
    except:
        dpg.configure_item('port_status', default_value='No port open', color=COLORS['red'])

def add_client(sender, _):
    global node
    host = dpg.get_value('client_add_host')
    port = dpg.get_value('client_add_port')
    node.add_client(host, port)
    dpg.configure_item('client_btn', label=f'{len(node.clients)} clients')
    dpg.configure_item('client_list', items=[f'{client[0]} : {client[1]}' for client in node.clients])

def remove_client(sender, _):
    global node
    host = dpg.get_value('client_add_host')
    port = dpg.get_value('client_add_port')
    node.remove_client(host, port)
    dpg.configure_item('client_btn', label=f'{len(node.clients)} clients')
    dpg.configure_item('client_list', items=[f'{client[0]} : {client[1]}' for client in node.clients])

dpg.create_context()
dpg.create_viewport(title='GopherVision', width=800, height=600)
dpg.set_viewport_vsync(True)

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

        with dpg.tab(label='Telemetry', tag='tab-telemetry'):
            # receive port selection
            with dpg.group(horizontal=True):
                dpg.add_text('Port:')
                dpg.add_combo(items=['Serial Port', 'Network Socket'], callback=set_port_type, width=150)
                # dropdown for serial port selection - shown when 'Serial Port' is selected
                dpg.add_combo(tag='port_serial', items=[], callback=set_port_serial, width=100, show=False)
                # text boxes for network host and port - shown when 'Network Socket' is selected
                dpg.add_input_text(tag='port_socket_host', hint='host', default_value='127.0.0.1', width=100, show=False)
                dpg.add_input_text(tag='port_socket_port', hint='port', default_value='5000', width=100, show=False)
                dpg.add_button(tag='port_socket_set', label='Set', callback=set_port_socket, show=False)
                # displays port status
                dpg.add_text('No port open', tag='port_status', color=COLORS['red'])
            # list of clients to forward data to
            with dpg.group(horizontal=True):
                dpg.add_text('Forward:')
                dpg.add_button(tag='client_btn', label='0 clients')
            with dpg.popup('client_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
                with dpg.group(horizontal=True):
                    dpg.add_input_text(tag='client_add_host', hint='host', width=100)
                    dpg.add_input_text(tag='client_add_port', hint='port', width=100)
                    dpg.add_button(label='Add', callback=add_client)
                    dpg.add_button(label='Remove', callback=remove_client)
                dpg.add_listbox(tag='client_list', items=[])
            # button to add parameter plots
            dpg.add_button(tag='add_btn', label='Add Parameter +')
            with dpg.popup('add_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
                dpg.add_input_text(hint='Name', callback=lambda _, val: dpg.set_value('parameter_list', val))
                with dpg.filter_set(tag='parameter_list'):
                    pass

dpg.setup_dearpygui()
dpg.show_viewport()
threading.Thread(target=update_plots, daemon=True).start()
dpg.start_dearpygui()
dpg.destroy_context()