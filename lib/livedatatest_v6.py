import dearpygui.dearpygui as dpg
import time
import threading
import yaml
import gcan
import gdat
from pathlib import Path
import serial
import struct
import sys
import socket

nsamples = 100

global y

# reads in and converts ic yaml parameters
icParameters = gcan.get_params(gcan.load_path("go4-23c.yaml"))

# data dictionary
plot_data = {
    id: {
        'x': [0.0] * nsamples,
        'y': [0.0] * nsamples
    } for id in icParameters
}

# id dictionary
windowID_dict = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

# reads data from usb
sys.path.append('../')
from lib import gcan
sys.path.pop()
if len(sys.argv) != 3:
    print('invalid arguments, expected "python livedatatest_v6.py [PORT] [CONFIG_NAME]"')
    exit()

START = 0x7E
ESC = 0x7D
ESC_XOR = 0x20

PORT = sys.argv[1]
BAUD = 230400

CONFIG_NAME = sys.argv[2]

BLOCK_SIZE = 1000 # bytes to read in each update
TIMEOUT = 1 # seconds to wait for desired block size

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
    config_path = Path('../../gopher-vision/lib') / CONFIG_NAME
    config = gcan.load_path(config_path)
except:
    print(f'ERROR: no config found at "{config_path}"')
    exit()

parameters = gcan.get_params(config)
pids = list(parameters.keys())

print(f'listening on port "{PORT}"...')

new_data = 1
id_sender = 1
def update_data(): # threaded to constantly update data
    sample = 1
    t0 = time.time()
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
            
            if id in plot_data:
                plot_data[id]['x'].append(ts)
                plot_data[id]['y'].append(value)
                if dpg.does_item_exist(f'{id}_series'):
                    dpg.set_value(f'{id}_series', [list(plot_data[id]['x'][-nsamples:]), list(plot_data[id]['y'][-nsamples:])])
                    dpg.fit_axis_data(f'{id}_x')
                    dpg.fit_axis_data(f'{id}_y')
            
            time.sleep(0.02)
            sample=sample+1

dpg.create_context()

def create_plot(id, name, pos_x, pos_y, label, y_axis): # creates plot on window
    with dpg.window(label=name, tag=f'{id}_window', width=1000, height=200): # first data window
        with dpg.plot(label=label, height=200, width=1000, tag=f'{id}_plot'):
            # REQUIRED: create x and y axes, set to auto scale.
            dpg.add_plot_axis(dpg.mvXAxis, label='x', tag=f'{id}_x')
            dpg.add_plot_axis(dpg.mvYAxis, label=y_axis, tag=f'{id}_y')

            # series belong to a y axis. Note the tag name is used in the update
            # function update_data
            dpg.add_line_series(x=list(plot_data[id]['x']), y=list(plot_data[id]['y']), 
                                label='Data type', parent=f'{id}_y', 
                                tag=f'{id}_series')
            
    dpg.set_item_pos(f'{id}_window', (pos_x, pos_y)) # moves window

# create_plot(1, 'Data Window 1', 300, 0, 'Live Data', 'y')
# create_plot(2, 'Data Window 2', 300, 200, 'Live Data', 'y')
# create_plot(3, 'Data Window 3', 300, 400, 'Live Data', 'y')
# create_plot(4, 'Data Window 4', 300, 600, 'Live Data', 'y')
# create_plot(5, 'Data Window 5', 300, 800, 'Live Data', 'y')

# plot themes
with dpg.theme(tag="plot_theme"):
    with dpg.theme_component(dpg.mvLineSeries):
        dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 0, 0), category=dpg.mvThemeCat_Plots)

with dpg.theme(tag="plot_theme2"):
    with dpg.theme_component(dpg.mvLineSeries):
        dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 100, 150), category=dpg.mvThemeCat_Plots)

with dpg.theme(tag="plot_theme3"):
    with dpg.theme_component(dpg.mvLineSeries):
        dpg.add_theme_color(dpg.mvPlotCol_Line, (100, 0, 150), category=dpg.mvThemeCat_Plots)

with dpg.theme(tag="plot_theme4"):
    with dpg.theme_component(dpg.mvLineSeries):
        dpg.add_theme_color(dpg.mvPlotCol_Line, (75, 100, 255), category=dpg.mvThemeCat_Plots)

# dpg.bind_item_theme("1_series", "plot_theme")
# dpg.bind_item_theme("2_series", "plot_theme2")
# dpg.bind_item_theme("3_series", "plot_theme3")
# dpg.bind_item_theme("4_series", "plot_theme4")
# dpg.bind_item_theme("5_series", "plot_theme4")

# create item list and dictionaries for parameters
item_list = []
unitDict = {}
idDict = {}
dataDict = {}
for i in icParameters:
    item_list.append(icParameters[i]['name'])
    idDict.update({icParameters[i]['name'] : i})
    unitDict.update({icParameters[i]['name'] : icParameters[i]['unit']})
    
# callback function for item_list
def item_list_callback(sender):
    dpg.show_item("replace_data_window")
    global name
    global unit
    name = dpg.get_item_label(sender)
    unit = unitDict[name]
start = 1
# replace function for each graph
def replace(sender, app_data, user_data):
    ID = idDict[name]
    global start
    global id_sender
    id_sender = user_data[0]
    for value in windowID_dict.values():
            if (ID == value):
                print("Error: item in graph")
                dpg.hide_item("replace_data_window")
                return
    if (start >= 5):
        dpg.delete_item(f'{windowID_dict[id_sender]}_window')
    else:
        start += 1
    x = user_data[1]
    y = user_data[2]
    windowID_dict[id_sender] = ID
    create_plot(windowID_dict[id_sender], name, x, y, name, unit)
    dpg.hide_item("replace_data_window")
# hides replace window when closed
def replace_data_window_on_close(sender):
    dpg.hide_item("replace_data_window")
# create window for replace buttons and hide it initialilly
with dpg.window(label="change data", id="replace_data_window",show = False, on_close=replace_data_window_on_close):
    dpg.add_button(label="Replace data in window 1", callback=replace, user_data=[1,300,0])
    dpg.add_button(label="Replace data in window 2", callback=replace, user_data=[2,300,200])
    dpg.add_button(label="Replace data in window 3", callback=replace, user_data=[3,300,400])
    dpg.add_button(label="Replace data in window 4", callback=replace, user_data=[4,300,600])
    dpg.add_button(label="Replace data in window 5", callback=replace, user_data=[5,300,800])


# Creates search menu to replace graphs
def search_bar_callback(sender, filter_string):
    dpg.set_value("filter_id", filter_string)
    dpg.set_value(item_list, filter_string)



# preset code starting here

def presetReplace(presetName, presetUnit, user_data):
    ID = idDict[presetName]
    global start
    global id_sender
    id_sender = user_data[0]
    for value in windowID_dict.values():
            if (ID == value):
                print("Error: item in graph")
                dpg.hide_item("replace_data_window")
                return
    if (start >= 5):
        dpg.delete_item(f'{windowID_dict[id_sender]}_window')
    x = user_data[1]
    y = user_data[2]
    windowID_dict[id_sender] = ID
    create_plot(windowID_dict[id_sender], presetName, x, y, presetName, presetUnit)
    dpg.hide_item("replace_data_window")
    
def newPreset_callback(sender, app_data, preset_key):
    # using the parameter key to change the 5 windows
    # change window 1
    # dpg.set_item_label(f'{windowID_dict[1]}_plot', store_presets_dict[preset_key][0])
    # dpg.set_item_label(f'{windowID_dict[1]}_y', unitDict[store_presets_dict[preset_key][0]])
    presetReplace(store_presets_dict[preset_key][0], unitDict[store_presets_dict[preset_key][0]], [1,300,0])
    # change window 2
    # dpg.set_item_label(f'{windowID_dict[2]}_plot', store_presets_dict[preset_key][1])
    # dpg.set_item_label(f'{windowID_dict[2]}y', unitDict[store_presets_dict[preset_key][1]])
    presetReplace(store_presets_dict[preset_key][1], unitDict[store_presets_dict[preset_key][1]], [2,300,200])
    # change window 3
    # dpg.set_item_label(f'{windowID_dict[3]}_plot', store_presets_dict[preset_key][2])
    # dpg.set_item_label(f'{windowID_dict[3]}_y', unitDict[store_presets_dict[preset_key][2]])
    presetReplace(store_presets_dict[preset_key][2], unitDict[store_presets_dict[preset_key][2]], [3,300,400])
    # change window 4
    # dpg.set_item_label(f'{windowID_dict[4]}_plot', store_presets_dict[preset_key][3])
    # dpg.set_item_label(f'{windowID_dict[4]}y', unitDict[store_presets_dict[preset_key][3]])
    presetReplace(store_presets_dict[preset_key][3], unitDict[store_presets_dict[preset_key][3]], [4,300,600])
    # change window 5
    # dpg.set_item_label(f'{windowID_dict[5]}_plot', store_presets_dict[preset_key][4])
    # dpg.set_item_label(f'{windowID_dict[5]}y', unitDict[store_presets_dict[preset_key][4]])
    presetReplace(store_presets_dict[preset_key][4], unitDict[store_presets_dict[preset_key][4]], [5,300,800])

# dictionary for storing presets
# key: name of the button for the preset
# value: a list of 5 data types
store_presets_dict = {}

# callback function for creating a new preset
def set_new_preset_name_callback (sender):
    # get current 5 window datas and store them in a list
    window1_label = dpg.get_item_label(f'{windowID_dict[1]}_plot')
    window2_label = dpg.get_item_label(f'{windowID_dict[2]}_plot')
    window3_label = dpg.get_item_label(f'{windowID_dict[3]}_plot')
    window4_label = dpg.get_item_label(f'{windowID_dict[4]}_plot')
    window5_label = dpg.get_item_label(f'{windowID_dict[5]}_plot')
    newPreset = [window1_label, window2_label, window3_label, window4_label, window5_label]

    # take in user input for name of new preset button
    newPresetName = dpg.get_value("new_preset_name_input_bar")

    # use the name of the button as the key and the list of 5 data types as the value, store in dictionary
    store_presets_dict[newPresetName] = newPreset

    # add button, passing in the user input user_data so it can be used in the callback function to access the dictionary
    dpg.add_button(label=newPresetName, callback=newPreset_callback, user_data=newPresetName, parent="presets_window")

    # close user input window after adding button
    dpg.delete_item("get_preset_name")

def create_preset_callback(sender): # allows user to input preset
    with dpg.window(label="Enter preset name: ", id="get_preset_name", width=230):
        dpg.add_input_text(width= 220, id="new_preset_name_input_bar")
        dpg.add_button(label="Add preset", callback=set_new_preset_name_callback)
    dpg.hide_item("presets_window")

# hide presets window when close button is clicked
def preset_window_on_close(sender):
    dpg.hide_item("presets_window")

# create preset window, but hidden
with dpg.window(label="change_presets", id="presets_window", width=200, height=200, on_close=preset_window_on_close, show=False):
    dpg.add_button(label="Create new preset", callback=create_preset_callback)

# callback function for presets button
# opens the presets window
def presets_callback(sender):
    dpg.show_item("presets_window")


# preset button customization
with dpg.theme(tag='button_border_theme'):
    with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 255, 100))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 0, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 255, 255, 255))
        dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 100)
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 8)



with dpg.window(label="Data Selection", width =300, height=1000):
    
    # add button for presets
    dpg.add_button(label="Presets", callback=presets_callback, width=270, tag="preset_button")
    dpg.bind_item_theme("preset_button", "button_border_theme")

    dpg.add_input_text(label="Search", callback=search_bar_callback, width= 220)
    with dpg.filter_set(id="filter_id"):
        # add button for each element in item list, using filter_set to implement search bar function
        for x in item_list:
            dpg.add_button(label=x, filter_key=x, callback=item_list_callback, width=280)
            
# end of preset code

dpg.create_viewport(title='Data', width=1300, height=1000)

dpg.setup_dearpygui()
dpg.show_viewport()

thread = threading.Thread(target=update_data)
thread.start()
dpg.start_dearpygui()

dpg.destroy_context()