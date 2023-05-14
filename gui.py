import dearpygui.dearpygui as dpg
import time
import threading
from collections import deque
import go4v
import rx

PLOT_SIZE = 500 # samples displayed at once
REFRESH_RATE = 30 # refresh rate for plots & stats (Hz)

# create x and y deques for all parameters
plots = {id: {'x': deque([0], maxlen=PLOT_SIZE), 'y': deque([0], maxlen=PLOT_SIZE)}\
         for id in go4v.parameters}

def add_plot(sender, app_data, pid):
    parameter = go4v.parameters[pid]

    # clean-up in case this plot was removed and re-added
    if dpg.does_alias_exist(f'x_axis_{pid}'): dpg.remove_alias(f'x_axis_{pid}')
    if dpg.does_alias_exist(f'y_axis_{pid}'): dpg.remove_alias(f'y_axis_{pid}')
    if dpg.does_alias_exist(f'data_{pid}'): dpg.remove_alias(f'data_{pid}')

    # add new plot
    with dpg.collapsing_header(parent='window', label=f"{parameter['motec_name']} ({pid})", closable=True):
        with dpg.plot(width=-1, height=150, no_mouse_pos=True, no_box_select=True):
            dpg.add_plot_axis(dpg.mvXAxis, tag=f'x_axis_{pid}')
            dpg.add_plot_axis(dpg.mvYAxis, label=parameter['unit'], tag=f'y_axis_{pid}')
            dpg.add_line_series([0], [0], label=parameter['motec_name'], parent=f'y_axis_{pid}', tag=f'data_{pid}')
        dpg.add_spacer(height=10)

plots_active = True
def toggle_play_pause(sender, app_data):
    global plots_active
    plots_active = not plots_active
    dpg.set_item_label('play_pause_btn', 'Pause' if plots_active else 'Play')
    dpg.bind_item_theme('play_pause_btn', 'pause_btn_theme' if plots_active else 'play_btn_theme')
    if plots_active:
        # play button was just pressed, clear plot history
        for (id, plot) in plots.items():
            plot['x'] = deque([rx.values[id]['timestamp']], maxlen=PLOT_SIZE)
            plot['y'] = deque([rx.values[id]['data']], maxlen=PLOT_SIZE)

def refresh():
    while True:
        dpg.set_value('throughput', rx.stats['throughput'])
        dpg.set_value('latency', rx.stats['latency'])
        dpg.set_value('error_rate', rx.stats['error_rate'])
        if plots_active:
            for (id, plot) in plots.items():
                plot['x'].append(rx.values[id]['timestamp'])
                plot['y'].append(rx.values[id]['data'])
                if dpg.does_item_exist(f'data_{id}'):
                    dpg.set_value(f'data_{id}', [list(plot['x']), list(plot['y'])])          
                    dpg.fit_axis_data(f'x_axis_{id}')
                    dpg.fit_axis_data(f'y_axis_{id}')
        time.sleep(1 / REFRESH_RATE)

dpg.create_context()

with dpg.window(tag='window'):
    dpg.set_primary_window('window', True)

    with dpg.group(horizontal=True, horizontal_spacing=25):
        with dpg.group(horizontal=True):
            dpg.add_text('throughput (bps):')
            dpg.add_text('0.0', tag='throughput')
        with dpg.group(horizontal=True):
            dpg.add_text('latency (ms):')
            dpg.add_text('0.0', tag='latency')
        with dpg.group(horizontal=True):
            dpg.add_text('error rate (%):')
            dpg.add_text('0.0', tag='error_rate')

    dpg.add_spacer(height=5)

    with dpg.group(horizontal=True):
        dpg.add_button(label='Add Parameter +', tag='add_btn')
        dpg.add_button(label='Pause', callback=toggle_play_pause, tag='play_pause_btn')

    dpg.add_spacer(height=10)

    with dpg.popup('add_btn', no_move=True, mousebutton=dpg.mvMouseButton_Left):
        dpg.add_input_text(hint='name', callback=lambda _, val: dpg.set_value('plist', val))
        with dpg.filter_set(tag='plist'):
            for parameter in go4v.parameters.values():
                dpg.add_selectable(label=parameter['motec_name'], filter_key=parameter['motec_name'], callback=add_plot, user_data=parameter['id'])

with dpg.theme(tag='play_btn_theme'):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (23, 32, 42))
        dpg.add_theme_color(dpg.mvThemeCol_Button, (46, 204, 113))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (13, 186, 85))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (3, 145, 62))

with dpg.theme(tag='pause_btn_theme'):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (23, 32, 42))
        dpg.add_theme_color(dpg.mvThemeCol_Button, (247, 220, 111))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (225, 196, 81))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (227, 187, 28))

dpg.bind_item_theme('play_pause_btn', 'pause_btn_theme')

dpg.create_viewport(title='Gopher Motorsports Telemetry', width=600, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()

threading.Thread(target=rx.rx).start()
threading.Thread(target=refresh).start()
dpg.start_dearpygui()

dpg.destroy_context()