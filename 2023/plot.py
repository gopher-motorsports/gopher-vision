import dearpygui.dearpygui as dpg
from collections import deque
from pathlib import Path
import sys
import time
import go4v

if len(sys.argv) < 2:
    sys.exit('ERROR: expected "python plot.py data.gdat"')

ipath = Path(sys.argv[1])

(filename, extension, data) = ipath.read_bytes().partition(b'.gdat:')

t0 = time.strptime(filename.decode(), '/PLM_%Y-%m-%d-%H-%M-%S')

packets = [go4v.parse(go4v.unescape(p)) for p in go4v.split(data)]
errors = sum(not p['valid'] for p in packets)
error_rate = round(errors / len(packets), 5)

channels = go4v.get_channels(time.mktime(t0), packets)

def add_plot(sender, app_data, pid):
    parameter = go4v.parameters[pid]

    # clean-up in case this plot was removed and re-added
    if dpg.does_alias_exist(f'x_axis_{pid}'): dpg.remove_alias(f'x_axis_{pid}')
    if dpg.does_alias_exist(f'y_axis_{pid}'): dpg.remove_alias(f'y_axis_{pid}')
    if dpg.does_alias_exist(f'data_{pid}'): dpg.remove_alias(f'data_{pid}')

    # add new plot
    with dpg.collapsing_header(label=f"{parameter['motec_name']} ({pid})", closable=True, parent='window'):
        with dpg.plot(width=-1, height=150, no_mouse_pos=True, no_box_select=True, use_local_time=True):
            dpg.add_plot_axis(dpg.mvXAxis, time=True, tag=f'x_axis_{pid}')
            dpg.add_plot_axis(dpg.mvYAxis, label=parameter['unit'], tag=f'y_axis_{pid}')
            t = [point['time'] for point in channels[pid]['points']]
            v = [point['value'] for point in channels[pid]['points']]
            dpg.add_line_series(t, v, label=parameter['motec_name'], parent=f'y_axis_{pid}', tag=f'data_{pid}')
        dpg.add_spacer(height=10)

dpg.create_context()
dpg.create_viewport(title='Gopher Motorsports Data', width=800, height=600)
dpg.setup_dearpygui()

with dpg.window(tag='window'):
    dpg.set_primary_window('window', True)

    dpg.add_text(ipath.name)
    dpg.add_text(f'{len(data)} bytes')
    dpg.add_text(f't0: {time.asctime(t0)}')
    dpg.add_text(f'error rate: {error_rate}%')

    dpg.add_spacer(height=5)
    dpg.add_button(label='Add Parameter +', tag='add_btn')
    dpg.add_spacer(height=10)

    with dpg.popup('add_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
        dpg.add_input_text(hint='name', callback=lambda _, val: dpg.set_value('plist', val))
        with dpg.filter_set(tag='plist'):
            for parameter in go4v.parameters.values():
                dpg.add_selectable(label=parameter['motec_name'], filter_key=parameter['motec_name'], callback=add_plot, user_data=parameter['id'])

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()