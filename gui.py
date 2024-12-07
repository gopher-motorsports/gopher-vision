from sys import argv
import dearpygui.dearpygui as dpg
from dearpygui_ext.themes import create_theme_imgui_light
from dearpygui_ext.themes import create_theme_imgui_dark
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from collections import deque
import time
import threading
import serial
import serial.tools.list_ports
import csv
import os
import sys

from lib import gcan
from lib import gdat
from lib import ld
from lib import live

root = tk.Tk()
root.withdraw()

COLORS = {
    'red': (231, 76, 60),
    'green': (45, 245, 120),
    'gray': (255, 255, 255, 128)
}

PLOT_RATE_HZ = 100
PLOT_LENGTH_S = 5

T_HOSTNAME = "GopherTrackPC"

node = live.Node()
# connect to a DNS server to force socket to bind to a port
node.tx_port.open_socket()
node.tx_port.port.connect(('1.1.1.1', 80))
IP = node.tx_port.port.getsockname()[0]
is_collumn_two = False
last_coord = (0,0)
# Use tkinter to get the screen's width and height
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
parameters = {}
plot_data = {}

# Returns the directory where the script or executable is located.
def get_executable_dir():
    if getattr(sys, 'frozen', False):  # Running as an executable
        return os.path.dirname(sys.executable)
    else:  # Running as a script
        return os.path.dirname(os.path.abspath(__file__))
# path to the existing/created local presets folder
preset_folder_path = os.path.join(get_executable_dir(), "presets")
if not os.path.exists(preset_folder_path):
    os.makedirs(preset_folder_path)

# load_config gets called when "Browse" button in GopherCAN tab
# opens a file dialog to load a YAML config
def load_config(file = None):
    global node
    global parameters
    global plot_data
    # open file dialog
    # root = tk.Tk()
    # root.withdraw()
    if file:
        path = file
    else:
        path = filedialog.askopenfilename( # Gives trace trap
            title='Open GopherCAN configuration',
            filetypes=[('YAML', '*.yaml')]
        )
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
            'x': deque([0], maxlen=PLOT_LENGTH_S * PLOT_RATE_HZ),
            'y': deque([0], maxlen=PLOT_LENGTH_S * PLOT_RATE_HZ)
        } for id in parameters.keys()
    }

    # update loaded config path
    dpg.configure_item('config_path', default_value=path, color=COLORS['green'])
    # enable buttons once a config is loaded
    dpg.configure_item('load_preset', enabled=True)
    dpg.configure_item('save_preset', enabled=True)
    dpg.configure_item('delete_preset', enabled=True)
    dpg.configure_item('convert_btn', enabled=True)
    dpg.configure_item('clear_parameters', enabled=True)
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

    # add existing presets to filter-set for load and delete
    presets = os.listdir(preset_folder_path)
    for preset in presets:
        dpg.add_selectable(parent='offline_presets_list', label=preset, filter_key=preset, callback=load_preset, user_data=preset)
    
    for preset in presets:
        dpg.add_selectable(parent='offline_presets_list_delete', label=preset, filter_key=preset, callback=delete_preset, user_data=preset)



# callback for "Convert" button in Data Parser tab
# converts .gdat files to .ld
def convert():
    global parameters
    if len(parameters) == 0:
        return
    # open file dialog to select 1+ .gdat files
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
            # add path to done list
            dpg.add_text(ld_path, parent='convert_done', color=COLORS['gray'])
        except Exception as err:
            print(f'failed to convert: {path}')
            print(err)
            # add path to failed list
            dpg.add_text(path, parent='convert_failed', color=COLORS['gray'])
        # update loading bar
        n += 1
        dpg.configure_item('convert_loading', default_value=(n / len(paths)), overlay=f'{n}/{len(paths)}')


# callback for "Add Parameter" button in Telemetry tab
# creates a plot for a loaded GCAN parameter
def add_plot(sender, app_data, pid):
    global is_collumn_two
    global parameters
    global last_coord
    # check if pid is defined in loaded config
    if pid not in parameters:
        return
    # check if current plot already exists
    pids = [int(alias[7:]) for alias in dpg.get_aliases() if 'p_plot_' in alias]
    if pid in pids:
        return

    parameter = parameters[pid]

    # clean-up in case this plot was removed and re-added
    if dpg.does_alias_exist(f'p_plot_{pid}'): dpg.remove_alias(f'p_plot_{pid}')
    if dpg.does_alias_exist(f'{pid}_x'): dpg.remove_alias(f'{pid}_x')
    if dpg.does_alias_exist(f'{pid}_y'): dpg.remove_alias(f'{pid}_y')
    if dpg.does_alias_exist(f'{pid}_series'): dpg.remove_alias(f'{pid}_series')
    if dpg.does_alias_exist(f'{pid}_value'): dpg.remove_alias(f'{pid}_value')

    # add new plot
    if is_collumn_two:
        with dpg.collapsing_header(label=f"{parameter['name']} ({pid})", closable=True, default_open=True, parent='tab-telemetry', pos=(last_coord[0]+screen_width*0.5,last_coord[1] - 120)):
            with dpg.plot(tag=f'p_plot_{pid}', width=-1, height=150, no_mouse_pos=True, no_box_select=True, use_local_time=True, anti_aliased=True, pos=(last_coord[0]+screen_width*0.5,last_coord[1] - 97)):
                dpg.add_plot_axis(dpg.mvXAxis, time=True, tag=f'{pid}_x')
                dpg.add_plot_axis(dpg.mvYAxis, label=parameter['unit'], tag=f'{pid}_y')
                dpg.add_line_series(list(plot_data[pid]['x']), list(plot_data[pid]['y']), label=parameter['name'], parent=f'{pid}_y', tag=f'{pid}_series')
                dpg.add_plot_annotation(label='0.0', offset=(float('inf'), float('inf')), tag=f'{pid}_value')
        is_collumn_two = False
        last_coord = (last_coord[0]+400,last_coord[1])
    else:
        with dpg.collapsing_header(label=f"{parameter['name']} ({pid})", closable=True, default_open=True, parent='tab-telemetry', pos=(0,last_coord[1] + 55)):
            with dpg.plot(tag=f'p_plot_{pid}', width=(screen_width/2) - 8, height=150, no_mouse_pos=True, no_box_select=True, use_local_time=True, anti_aliased=True):
                dpg.add_plot_axis(dpg.mvXAxis, time=True, tag=f'{pid}_x')
                dpg.add_plot_axis(dpg.mvYAxis, label=parameter['unit'], tag=f'{pid}_y')
                dpg.add_line_series(list(plot_data[pid]['x']), list(plot_data[pid]['y']), label=parameter['name'], parent=f'{pid}_y', tag=f'{pid}_series')
                dpg.add_plot_annotation(label='0.0', offset=(float('inf'), float('inf')), tag=f'{pid}_value')
        is_collumn_two = True
        last_coord = (0,last_coord[1]+175)

def start_recording(sender, _):
    global node

    root = tk.Tk()
    root.withdraw()
    path = filedialog.asksaveasfilename(
        title='Record data',
        filetypes=[('GDAT', '*.gdat')],
        defaultextension='gdat'
    )
    root.destroy()

    if not path:
        return

    node.open_record(path)
    dpg.configure_item('record_path', default_value=path, color=COLORS['green'])

def stop_recording(sender, _):
    global node
    node.close_record()
    dpg.configure_item('record_path', default_value='Not recording', color=COLORS['red'])

def set_plot_size(sender, _):
    global PLOT_LENGTH_S
    global PLOT_RATE_HZ
    global plot_data

    PLOT_LENGTH_S = dpg.get_value('plot_length')
    PLOT_RATE_HZ = dpg.get_value('plot_rate')

    # create new deques of the right size
    plot_data = {
        id: {
            'x': deque(plot_data[id]['x'], maxlen=PLOT_LENGTH_S * PLOT_RATE_HZ),
            'y': deque(plot_data[id]['y'], maxlen=PLOT_LENGTH_S * PLOT_RATE_HZ)
        } for id in parameters.keys()
    }

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
    except Exception as err:
        print(err)
        dpg.configure_item('port_status', default_value='No port open', color=COLORS['red'])

# callback for  "Set" button when entering a network port
def set_port_socket(sender, _, host = None, port = None):
    global node
    if host is None:
        host = dpg.get_value('port_socket_host')
        port = dpg.get_value('port_socket_port')
    try:
        dpg.configure_item('port_status', default_value=f'opening {host}:{port} ...', color=COLORS['gray'])
        node.rx_port.bind_socket(host, port)
        dpg.configure_item('port_status', default_value=f'{host}:{port} open', color=COLORS['green'])
    except Exception as err:
        print(err)
        dpg.configure_item('port_status', default_value='No port open', color=COLORS['red'])

import socket # Imported here because I would like to move this function out of gui.py if possible
client = socket.socket()
connected = False

def manage_client(client_socket, addr):
    global node
    try:
        while True:
            request = client_socket.recv(1024).decode("utf-8")
            if request.lower() == "close":
                client_socket.send("closed".encode("utf-8"))
                break
            print(f"Received: {request}")
            node.add_client(addr[0], 5002)
            print("Now sending to: ")
            print(node.clients)
            client_socket.send("accepted".encode("utf-8"))
    except Exception as e:
        print(f"Error when hanlding client: {e}")
    finally:
        client_socket.close()
        print(f"Connection to client ({addr[0]}:{addr[1]}) closed")
        node.remove_client(addr[0], 5002)
        print("Now sending to: ")
        print(node.clients)

def host_trackside():
    try:
        # Use default TCP so connection request doesn't get missed
        server = socket.socket()
        server.bind(('', 5001))
        server.listen(5)
        print("Listening for connection requests")
        while True:
            client_socket, addr = server.accept()
            print("Got connection from", addr)
            thread = threading.Thread(target=manage_client, args=(client_socket, addr,))
            thread.start()
    except Exception as e:
        print("Could not host server")
        print(f"Error: {e}")
        dpg.stop_dearpygui() # TODO: consider not killing gui, just displaying message?
        exit()

# load presets from csv file
def load_preset_csv(file=None):
    if file:
        f = open(file)
    else:
        f = filedialog.askopenfile(
            title='Load GopherVision preset',
            filetypes=[('CSV', '*.csv')])

    reader = csv.DictReader(f)
    # add plots for each preset entry
    for row in reader:
        pid = int(row['id'])
        add_plot(None, None, pid)
        dpg.set_axis_limits(f'{pid}_y', float(row['y_min']), float(row['y_max']))
    f.close()

def trackside_connect(sender, _):
    global client, connected
    if connected: return
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = dpg.get_value('trackside_hostname')
    try:
        client.connect((host, 5001))
    except:
        print("Error connecting to host")
        dpg.configure_item('port_status', default_value='Connection failed', color=COLORS['red'])
        return

    client.send("connect".encode("utf-8")[:1024])
    response = client.recv(1024).decode("utf-8")

    if response == "accepted":
        # Listen for data over UDP
        set_port_socket(0, 0, IP, '5002')
        connected = True
    else:
        print(f"Received: {response}")


toggle = 0 # var for switching themes
color_R = 255
color_G = 255
color_B = 255
toggle_press = 0
# callback for dark/light mode
def toggle_mode(sender):
    global toggle
    global color_R
    global color_G
    global color_B
    global toggle_press
    toggle_press = 1
    if (toggle == 0):
        light_theme = create_theme_imgui_light() # Imports light mode from dearpygui_ext
        dpg.bind_theme(light_theme)
        toggle = 1
        color_R = 0
        color_G = 0
        color_B = 0
    else:
        dark_theme = create_theme_imgui_dark()
        dpg.bind_theme(dark_theme)
        toggle = 0
        color_R = 255
        color_G = 255
        color_B = 255

# callback for Clear
def clear_parameters(sender):
    pids = [int(alias[7:]) for alias in dpg.get_aliases() if 'p_plot_' in alias]
    for pid in pids:
        dpg.delete_item(f'{pid}_collapsing_header')
        if dpg.does_alias_exist(f'p_plot_{pid}'): dpg.remove_alias(f'p_plot_{pid}')
        if dpg.does_alias_exist(f'{pid}_x'): dpg.remove_alias(f'{pid}_x')
        if dpg.does_alias_exist(f'{pid}_y'): dpg.remove_alias(f'{pid}_y')
        if dpg.does_alias_exist(f'{pid}_series'): dpg.remove_alias(f'{pid}_series')
        if dpg.does_alias_exist(f'{pid}_value'): dpg.remove_alias(f'{pid}_value')

# load preset
def load_preset(sender, app_data, preset_name):
    f = open(preset_folder_path + "/" + preset_name)
    reader = csv.DictReader(f)
    # add plots for each preset entry
    for row in reader:
        pid = int(row['id'])
        add_plot(None, None, pid)
        dpg.set_axis_limits(f'{pid}_y', float(row['y_min']), float(row['y_max']))
    f.close()

# callback for Save Preset, gets name input
def save_preset(sender):
    with dpg.window(label="Preset Name", tag="get_preset_name_window", width=300, height=200):
        dpg.add_text("Enter preset name: ")
        dpg.add_input_text(tag="name_input")
        dpg.add_button(label="Create Preset", callback=save_preset_to_csv)

# save preset to csv file
def save_preset_to_csv(sender):
    global parameters
    plots = []
    pids = [int(alias[7:]) for alias in dpg.get_aliases() if 'p_plot_' in alias]
    # find currently visible plots
    for pid in pids:
        # if dpg.is_item_visible(f'p_plot_{pid}'):
        y_axis = dpg.get_axis_limits(f'{pid}_y')
        # TODO: axis limits on invisible plots are defaulted to 0.5 and -0.5, works for now but is not long term solution
        if (y_axis[0] == 0 and y_axis[1] == 0):
            y_axis[0] = -0.5
            y_axis[1] = 0.5
        plots.append({
            'id': pid,
            'name': parameters[pid]['name'],
            'y_min': y_axis[0],
            'y_max': y_axis[1],
            'v_pos': dpg.get_item_pos(f'p_plot_{pid}')[1]
        })
    # sort by vertical position
    plots.sort(key=lambda p: p['v_pos'])
    new_file_name = dpg.get_value("name_input") + ".csv"
    file_path = os.path.join(preset_folder_path, new_file_name)

    # Save the file
    with open(file_path, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'y_min', 'y_max'], extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(plots)
    print(f"File saved successfully at: {file_path}")
    dpg.add_selectable(parent='offline_presets_list', label=new_file_name, filter_key=new_file_name, callback=load_preset, user_data=new_file_name)
    dpg.add_selectable(parent='offline_presets_list_delete', label=new_file_name, filter_key=new_file_name, callback=delete_preset, user_data=new_file_name)
    dpg.delete_item("get_preset_name_window")


# deleting a stored preset file
def delete_preset(sender, app_data, preset_name):
    if os.path.exists(preset_folder_path + "/" + preset_name):
        os.remove(preset_folder_path + "/" + preset_name)

    presets = os.listdir(preset_folder_path)
    # delete presets list if it already exists, then re-add all presets
    dpg.delete_item('offline_presets_list', children_only=True)
    dpg.delete_item('offline_presets_list_delete', children_only=True)
    for preset in presets:
        dpg.add_selectable(parent='offline_presets_list', label=preset, filter_key=preset, callback=load_preset, user_data=preset)
    
    for preset in presets:
        dpg.add_selectable(parent='offline_presets_list_delete', label=preset, filter_key=preset, callback=delete_preset, user_data=preset)

# Use tkinter to get the screen's width and height
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

dpg.create_context()
dpg.create_viewport(title='GopherVision', width=screen_width, height=screen_height)
dpg.set_viewport_vsync(True)
dpg.set_viewport_pos([0,0])

with dpg.window(tag='window'):
    dpg.set_primary_window('window', True)

    with dpg.tab_bar(tag='tab-bar'):
        with dpg.tab(label='GopherCAN', tag='tab-gophercan'):
            with dpg.group(horizontal=True):
                dpg.add_text('Load a GopherCAN configuration (.yaml):')
                dpg.add_checkbox(tag='should_open_yaml', default_value=False, show=False)
                dpg.add_button(label='Browse', callback=lambda: dpg.set_value('should_open_yaml', True))
            dpg.add_text('No configuration loaded', tag='config_path', color=COLORS['red'])

        with dpg.tab(label='Data Parser'):
            with dpg.group(horizontal=True):
                dpg.add_text('Select data to convert (.gdat):')
                dpg.add_checkbox(tag='convert_clicked', default_value=False, show=False)
                dpg.add_button(tag='convert_btn', label='Convert', enabled=False, callback=lambda: dpg.set_value('convert_clicked', True))
            dpg.add_progress_bar(tag='convert_loading', width=200)
            with dpg.group(tag='convert_done'):
                dpg.add_text('Done:', color=COLORS['gray'])
            with dpg.group(tag='convert_failed'):
                dpg.add_text('Failed:', color=COLORS['gray'])

        with dpg.tab(label='Telemetry', tag='tab-telemetry'):
            with dpg.group(horizontal=True):
                dpg.add_button(tag='add_btn', label='Add Parameter +')
                dpg.add_button(tag='theme_toggle', label='Toggle Light/Dark Mode', callback=toggle_mode)
                dpg.add_button(tag='clear_parameters', label='Clear', callback=clear_parameters, enabled=False)
                dpg.add_button(tag='load_preset', label='Load Preset +', enabled=False)
                dpg.add_button(tag='save_preset', label='Save Preset', callback=save_preset, enabled=False)
                dpg.add_button(tag='delete_preset', label='Delete Preset +', enabled=False)
                dpg.add_button(tag='settings_btn', label='Settings')

            
            with dpg.popup('load_preset', no_move=True, mousebutton=dpg.mvMouseButton_Left):
                dpg.add_input_text(hint='Name', callback=lambda _, val: dpg.set_value('offline_presets_list', val))
                with dpg.filter_set(tag='offline_presets_list'):
                    pass

            with dpg.popup('delete_preset', no_move=True, mousebutton=dpg.mvMouseButton_Left):
                dpg.add_input_text(hint='Name', callback=lambda _, val: dpg.set_value('offline_presets_list', val))
                with dpg.filter_set(tag='offline_presets_list_delete'):
                    pass

                dpg.add_checkbox(tag='load_preset_clicked', default_value=False, show=False)
                dpg.add_checkbox(tag='save_preset_clicked', default_value=False, show=False)

            with dpg.popup('add_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
                dpg.add_input_text(hint='Name', callback=lambda _, val: dpg.set_value('parameter_list', val))
                with dpg.filter_set(tag='parameter_list'):
                    pass
       
            with dpg.popup('settings_btn', modal=True, no_move=True, mousebutton=dpg.mvMouseButton_Left):
                dpg.add_text(f'IP: {IP}', color=COLORS['gray'])
                dpg.add_separator()

                with dpg.group(horizontal=True):
                    dpg.add_button(label='Record', callback=start_recording)
                    dpg.add_button(label='Stop', callback=stop_recording)
                dpg.add_text('Not recording', tag='record_path', color=COLORS['red'])
                dpg.add_separator()

                with dpg.group(horizontal=True):
                    dpg.add_text('Plot Length (s):')
                    dpg.add_input_int(tag='plot_length', default_value=PLOT_LENGTH_S, min_value=1, min_clamped=True, callback=set_plot_size, width=100)
                with dpg.group(horizontal=True):
                    dpg.add_text('Plot Rate (Hz):')
                    dpg.add_input_int(tag='plot_rate', default_value=PLOT_RATE_HZ, min_value=1, min_clamped=True, callback=set_plot_size, width=100)
                dpg.add_separator()

                # receive port selection
                with dpg.group(horizontal=True):
                    dpg.add_text('Port:')
                    dpg.add_combo(items=['Serial Port', 'Network Socket'], callback=set_port_type, width=150)
                # dropdown for serial port selection - shown when 'Serial Port' is selected
                dpg.add_combo(tag='port_serial', items=[], callback=set_port_serial, width=100, show=False)
                # text boxes for network host and port - shown when 'Network Socket' is selected
                with dpg.group(horizontal=True):
                    dpg.add_input_text(tag='port_socket_host', hint='host', default_value='127.0.0.1', width=100, show=False)
                    dpg.add_input_text(tag='port_socket_port', hint='port', default_value='5000', width=100, show=False)
                    dpg.add_button(tag='port_socket_set', label='Set', callback=set_port_socket, show=False)
                # displays port status
                dpg.add_text('No port open', tag='port_status', color=COLORS['red'])

                # display trackside connect button if not the host
                if len(argv) < 2 or argv[1] != "host":
                    dpg.add_separator()
                    dpg.add_text('Trackside Server:')
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(tag='trackside_hostname', hint='host', default_value=T_HOSTNAME, width=150)
                        dpg.add_button(label='Connect', callback=trackside_connect)


dpg.setup_dearpygui()
dpg.show_viewport()

# creates theme for plots
def change_theme():
    if dpg.does_alias_exist('plot_theme'): dpg.remove_alias('plot_theme')
    with dpg.theme(tag="plot_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (color_R, color_G, color_B), category=dpg.mvThemeCat_Plots)
            
change_theme() # initialize theme


# Start hosting if called from cmd with argument host (python gui.py host yaml_config csv port)
if len(argv) > 1 and argv[1] == "host":
    if len(argv) > 2:
        load_config(argv[2])  # set CAN config
        if len(argv) > 3:
            load_preset_csv(argv[3])  # set csv
            if len(argv) > 4:
                set_port_serial(0, argv[4])  # set port
        dpg.set_value('tab-bar', 'tab-telemetry')  # set tab
    # change_theme() # light mode TODO: Doesn't work
    dpg.toggle_viewport_fullscreen()  # fullscreen

    # Open server to listen for connection requests
    print("starting server")
    threading.Thread(target=host_trackside, daemon=True).start()

# transfer values from receiver to plots at a configurable rate
def update_plots():
    global node
    global toggle_press
    while True:
        if (toggle_press == 1):
            change_theme()
            toggle_press = 0
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
                dpg.bind_item_theme(f'{id}_series', "plot_theme")
        time.sleep(1 / PLOT_RATE_HZ)

threading.Thread(target=update_plots, daemon=True).start()

# checks for any TKinter calls
# forces TKinter calls to run on main thread
while dpg.is_dearpygui_running():
    if dpg.get_value('should_open_yaml'):
        dpg.set_value('should_open_yaml', False)
        load_config()

    if dpg.get_value('convert_clicked'):
        dpg.set_value('convert_clicked', False)
        convert()

    if dpg.get_value('load_preset_clicked_csv'):
        dpg.set_value('load_preset_clicked_csv', False)
        load_preset_csv()

    dpg.render_dearpygui_frame()
    pass

dpg.start_dearpygui()
root.destroy()
dpg.destroy_context()