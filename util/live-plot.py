# python live-plot.py [PORT] [CONFIG_NAME]
# PORT can either be a serial port name or a localhost port number
# e.g. python live-plot.py COM4 go4-24c.yaml
# e.g. python live-plot.py /dev/tty.usbserial-X go4-24c.yaml
# e.g. python live-plot.py 5000 go4-24c.yaml
# opens the specified serial or network port, expecting to receive .gdat packets
# parses packets using the provided GopherCAN config
# plots data with DearPyGUI

import sys
import serial
import struct
import socket
from pathlib import Path
from collections import deque
import dearpygui.dearpygui as dpg
import threading

sys.path.append('../')
from lib import gcan
sys.path.pop()

if len(sys.argv) != 3:
    print('invalid arguments, expected "python live-plot.py [PORT]"')
    exit()

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

PORT = sys.argv[1]
BAUD = 230400

CONFIG_NAME = sys.argv[2]

BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

PLOT_SIZE = 500 # samples displayed at once

PORT_TYPE = ''
try:
    # attempt to open a network socket on localhost
    port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket
    port.bind(('127.0.0.1', int(PORT)))
    PORT_TYPE = 'socket'
except:
    try:
        # attempt to open a serial port
        port = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
        PORT_TYPE = 'serial'
    except:
        print(f'ERROR: unrecognized port "{PORT}"')
        exit()

try:
    config_path = Path('../../gophercan-lib/network_autogen/configs/') / CONFIG_NAME
    config = gcan.load_path(config_path)
except:
    print(f'ERROR: no config found at "{config_path}"')
    exit()

parameters = gcan.get_params(config)
pids = list(parameters.keys())

# create x and y deques for all parameters
channels = {
    id: {
        'x': deque([0], maxlen=PLOT_SIZE),
        'y': deque([0], maxlen=PLOT_SIZE)
    } for id in pids
}

def rx():
    print(f'listening on port "{PORT}"...')
    while True:
        if PORT_TYPE == 'serial':
            bytes = port.read(BLOCK_SIZE)
        elif PORT_TYPE == 'socket':
            bytes = port.recv(BLOCK_SIZE)

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
            channels[id]['x'].append(ts)
            channels[id]['y'].append(value)

def add_plot(sender, app_data, pid):
    parameter = parameters[pid]

    # clean-up in case this plot was removed and re-added
    if dpg.does_alias_exist(f'x_axis_{pid}'): dpg.remove_alias(f'x_axis_{pid}')
    if dpg.does_alias_exist(f'y_axis_{pid}'): dpg.remove_alias(f'y_axis_{pid}')
    if dpg.does_alias_exist(f'data_{pid}'): dpg.remove_alias(f'data_{pid}')

    # add new plot
    with dpg.collapsing_header(label=f"{parameter['name']} ({pid})", closable=True, parent='window'):
        with dpg.plot(width=-1, height=150, no_mouse_pos=True, no_box_select=True, use_local_time=True):
            dpg.add_plot_axis(dpg.mvXAxis, time=True, tag=f'x_axis_{pid}')
            dpg.add_plot_axis(dpg.mvYAxis, label=parameter['unit'], tag=f'y_axis_{pid}')
            dpg.add_line_series(list(channels[pid]['x']), list(channels[pid]['y']), label=parameter['name'], parent=f'y_axis_{pid}', tag=f'data_{pid}')
            dpg.add_plot_annotation(label='0.0', offset=(float('inf'), float('inf')), tag=f'value_{pid}')
        dpg.add_spacer(height=10)

dpg.create_context()
dpg.create_viewport(title='Gopher Motorsports Telemetry', width=800, height=600)
dpg.setup_dearpygui()

with dpg.window(tag='window'):
    dpg.set_primary_window('window', True)

    dpg.add_spacer(height=5)
    dpg.add_button(label='Add Parameter +', tag='add_btn')
    dpg.add_spacer(height=10)

    with dpg.popup('add_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
        dpg.add_input_text(hint='name', callback=lambda _, val: dpg.set_value('plist', val))
        with dpg.filter_set(tag='plist'):
            for parameter in parameters.values():
                dpg.add_selectable(label=parameter['name'], filter_key=parameter['name'], callback=add_plot, user_data=parameter['id'])

dpg.show_viewport()

# start data receiving thread
threading.Thread(target=rx, daemon=True).start()

while dpg.is_dearpygui_running():
    for (id, channel) in channels.items():
        if dpg.does_item_exist(f'data_{id}'):
            dpg.set_value(f'data_{id}', [list(channel['x']), list(channel['y'])])
            dpg.set_item_label(f'value_{id}', round(channel['y'][-1], 3))
            dpg.fit_axis_data(f'x_axis_{id}')
            dpg.fit_axis_data(f'y_axis_{id}')
    dpg.render_dearpygui_frame()

print('Exiting...')
dpg.destroy_context()