import dearpygui.dearpygui as dpg
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from collections import deque
import struct
import time
import threading
import socket
import serial

from lib import gcan
from lib import gdat
from lib import ld

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

BAUD = 230400
BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

PLOT_SIZE = 100

COLORS = {
    'red': (231, 76, 60),
    'green': (45, 245, 120),
    'gray': (255, 255, 255, 128)
}

parameters = {}
channels = {}
port = None

def update_port(sender, app_data):
    global port
    port_input = dpg.get_value('port_input')
    try:
        # attempt to open a network socket on localhost
        port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
        port.bind(('127.0.0.1', int(port_input)))
    except:
        try:
            # attempt to open a serial port
            port = serial.Serial(port_input, BAUD, timeout=TIMEOUT)
        except:
            print(f'ERROR: unrecognized port "{port_input}"')
            dpg.configure_item('port_invalid', show=True)
            return
    dpg.configure_item('port_invalid', show=False)
    print(f'port set: {port_input} type={type(port)}')

def rx():
    global port
    while True:
        if type(port) == socket.socket:
            bytes = port.recv(BLOCK_SIZE)
        elif type(port) == serial.Serial:
            bytes = port.read(BLOCK_SIZE)
        else:
            time.sleep(1)
            continue

        packets = bytes.split(START.to_bytes(1, 'big'))
        for packet in packets:
            # unescape packet
            pkt = bytearray()
            esc = False
            for b in packet:
                if b == ESC:
                    esc = True
                elif esc:
                    pkt.append(b ^ ESC_XOR)
                    esc = False
                else:
                    pkt.append(b)
            # unpack components
            try:
                ts, id = struct.unpack('>IH', pkt[0:6])
                value = struct.unpack(parameters[id]['format'], pkt[6:-1])[0]
            except:
                # print(f'failed to decode: {packet}')
                continue
            # validate checksum
            sum = START
            for b in pkt[:-1]: sum += b
            if sum.to_bytes(2, 'big')[-1] != pkt[-1]:
                # print(f'invalid checksum: {packet}')
                continue
            # add datapoint to channel
            try:
                channels[id]['x'].append(ts)
                channels[id]['y'].append(value)
            except:
                continue

def load_config(sender):
    global parameters
    global channels

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
    channels = {
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
            dpg.add_line_series(list(channels[pid]['x']), list(channels[pid]['y']), label=parameter['name'], parent=f'{pid}_y', tag=f'{pid}_series')
            dpg.add_plot_annotation(label='0.0', offset=(float('inf'), float('inf')), tag=f'{pid}_value')

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

        with dpg.tab(label='Telemetry', tag='tab-telemetry'):
            with dpg.group(horizontal=True):
                dpg.add_text('Port:')
                dpg.add_input_text(tag='port_input', width=150)
                dpg.add_button(label='Set', callback=update_port)
                dpg.add_text('INVALID PORT', tag='port_invalid', color=COLORS['red'], show=False)
            dpg.add_button(tag='add_btn', label='Add Parameter +')
            with dpg.popup('add_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
                dpg.add_input_text(hint='Name', callback=lambda _, val: dpg.set_value('parameter_list', val))
                with dpg.filter_set(tag='parameter_list'):
                    pass

dpg.setup_dearpygui()
dpg.show_viewport()

# start data receiving thread
threading.Thread(target=rx, daemon=True).start()

while dpg.is_dearpygui_running():
    for (id, channel) in channels.items():
        if dpg.does_item_exist(f'{id}_series'):
            dpg.set_value(f'{id}_series', [list(channel['x']), list(channel['y'])])
            dpg.set_item_label(f'{id}_value', round(channel['y'][-1], 3))
            dpg.fit_axis_data(f'{id}_x')
            dpg.fit_axis_data(f'{id}_y')
    dpg.render_dearpygui_frame()

dpg.destroy_context()