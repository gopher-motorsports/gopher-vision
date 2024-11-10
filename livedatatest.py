import dearpygui.dearpygui as dpg
import math
import time
import collections
import threading
import pdb

nsamples = 100

global data_y
global data_x
global data_w
global data_z
# Can use collections if you only need the last 100 samples
# data_y = collections.deque([0.0, 0.0],maxlen=nsamples)
# data_x = collections.deque([0.0, 0.0],maxlen=nsamples)

# Use a list if you need all the data. 
# Empty list of nsamples should exist at the beginning.
# Theres a cleaner way to do this probably.
data_y = [0.0] * nsamples
data_x = [0.0] * nsamples
data_w = [0.0] * nsamples
data_z = [0.0] * nsamples

def update_data():
    sample = 1
    t0 = time.time()
    frequency=0.5
    while True:

        # Get new data sample. Note we need both x and y values
        # if we want a meaningful axis unit.
        t = time.time() - t0
        y = math.sin(2.0 * math.pi * frequency * t)
        z = math.cos(2.0 * math.pi * frequency * t)
        data_x.append(t)
        data_y.append(y)
        data_w.append(t)
        data_z.append(z)
        
        #set the series x and y to the last nsamples
        dpg.set_value('series_tag', [list(data_x[-nsamples:]), list(data_y[-nsamples:])]) 
        dpg.set_value('series_tag2', [list(data_w[-nsamples:]), list(data_z[-nsamples:])])          
        dpg.fit_axis_data('x_axis')
        dpg.fit_axis_data('y_axis')
        dpg.fit_axis_data('w_axis')
        dpg.fit_axis_data('z_axis')
        
        time.sleep(0.02)
        sample=sample+1
           


dpg.create_context()
with dpg.window(label='Data 1', tag='win',width=1000, height=200):

    # create a theme for the plot
    with dpg.theme(tag="plot_theme"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 0, 0), category=dpg.mvThemeCat_Plots)
    with dpg.theme(tag="plot_theme2"):
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (150, 100, 150), category=dpg.mvThemeCat_Plots)
    
    with dpg.plot(label='Live Data', height=200, width=1000):
        # optionally create legend
        dpg.add_plot_legend()

        # REQUIRED: create x and y axes, set to auto scale.
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label='x', tag='x_axis')
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label='y', tag='y_axis')


        # series belong to a y axis. Note the tag name is used in the update
        # function update_data
        dpg.add_line_series(x=list(data_x),y=list(data_y), 
                            label='Voltage', parent='y_axis', 
                            tag='series_tag')
        
with dpg.window(label='Data 2',width=1000, height=200, tag="window2"):

    with dpg.plot(label='Live Data', height=200, width=1000):
        # optionally create legend
        dpg.add_plot_legend()

        # REQUIRED: create x and y axes, set to auto scale.
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label='w', tag='z_axis')
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label='z', tag='w_axis')


        # series belong to a y axis. Note the tag name is used in the update
        # function update_data
        dpg.add_line_series(x=list(data_w),y=list(data_z), 
                            label='Voltage', parent='w_axis', 
                            tag='series_tag2')
        
        # apply theme to series
        dpg.bind_item_theme("series_tag", "plot_theme")
        dpg.bind_item_theme("series_tag2", "plot_theme2")
        
    dpg.set_item_pos("window2", (0,200))
    
        
        
            
                            
dpg.create_viewport(title='Data', width=1050, height=640)

dpg.setup_dearpygui()
dpg.show_viewport()

thread = threading.Thread(target=update_data)
thread.start()
dpg.start_dearpygui()

dpg.destroy_context()